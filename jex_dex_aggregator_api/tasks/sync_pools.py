
import asyncio
import logging
from datetime import datetime, timedelta
from itertools import product
from time import sleep
from typing import Callable, List, Tuple

import aiohttp
from multiversx_sdk_core import Address

from jex_dex_aggregator_api.data.constants import (
    SC_TYPE_ASHSWAP_STABLEPOOL, SC_TYPE_ASHSWAP_V2, SC_TYPE_EXROND,
    SC_TYPE_HATOM_MONEY_MARKET_MINT, SC_TYPE_HATOM_MONEY_MARKET_REDEEM,
    SC_TYPE_HATOM_STAKE, SC_TYPE_JEXCHANGE_LP, SC_TYPE_JEXCHANGE_LP_DEPOSIT,
    SC_TYPE_JEXCHANGE_STABLEPOOL, SC_TYPE_JEXCHANGE_STABLEPOOL_DEPOSIT,
    SC_TYPE_ONEDEX, SC_TYPE_VESTADEX, SC_TYPE_VESTAX_STAKE, SC_TYPE_XEXCHANGE)
from jex_dex_aggregator_api.data.datastore import (set_dex_aggregator_pool,
                                                   set_swap_pools)
from jex_dex_aggregator_api.data.model import VestaDexPool
from jex_dex_aggregator_api.pools.model import SwapPool
from jex_dex_aggregator_api.pools.pools import (AshSwapPoolV2,
                                                ConstantPricePool,
                                                ConstantProductPool,
                                                JexConstantProductDepositPool,
                                                JexConstantProductPool,
                                                JexStableSwapPool,
                                                JexStableSwapPoolDeposit,
                                                OneDexConstantProductPool,
                                                StableSwapPool,
                                                VestaDexConstantProductPool,
                                                XExchangeConstantProductPool)
from jex_dex_aggregator_api.services.externals import async_sc_query
from jex_dex_aggregator_api.services.parsers.ashswap import (
    parse_ashswap_stablepool_status, parse_ashswap_v2_pool_status)
from jex_dex_aggregator_api.services.parsers.common import parse_address
from jex_dex_aggregator_api.services.parsers.hatom import parse_hatom_mm
from jex_dex_aggregator_api.services.parsers.jexchange import (
    parse_jex_cp_lp_status, parse_jex_deployed_contract,
    parse_jex_stablepool_status)
from jex_dex_aggregator_api.services.parsers.onedex import parse_onedex_pair
from jex_dex_aggregator_api.services.parsers.vestadex import \
    parse_vestadex_view_pools
from jex_dex_aggregator_api.services.parsers.xexchange import \
    parse_xexchange_pool_status
from jex_dex_aggregator_api.services.tokens import (JEX_IDENTIFIER,
                                                    USDC_IDENTIFIER,
                                                    WEGLD_IDENTIFIER,
                                                    get_or_fetch_token)
from jex_dex_aggregator_api.utils.convert import hex2dec, hex2str
from jex_dex_aggregator_api.utils.env import (mvx_gateway_url,
                                              sc_address_aggregator,
                                              sc_address_hatom_staking,
                                              sc_address_jex_lp_deployer,
                                              sc_address_onedex_swap,
                                              sc_address_vestadex_router,
                                              sc_address_vestax_staking)
from jex_dex_aggregator_api.utils.redis_utils import redis_lock_and_do

_must_stop = False
_ready = False


def is_ready() -> bool:
    global _ready
    return _ready


def stop():
    global _must_stop
    _must_stop = True


def loop():
    logging.info('Starting pools sync')

    global _ready

    delta = timedelta(seconds=12)
    start = datetime.min
    while not _must_stop:
        now = datetime.now()
        if now - start > delta:

            redis_lock_and_do('sync_pools',
                              lambda: asyncio.run(
                                  _sync_all_pools(), debug=False),
                              task_ttl=timedelta(seconds=10),
                              lock_ttl=timedelta(seconds=30))

            logging.info(f'All pools synced @ {datetime.utcnow().isoformat()}')
            start = now
            _ready = True

        sleep(1)

    logging.info('Stopping pools sync')


async def _sync_all_pools():
    functions = [
        _sync_onedex_pools,
        _sync_xexchange_pools,
        _sync_ashswap_stable_pools,
        _sync_ashswap_v2_pools,
        _sync_jex_cp_pools,
        _sync_jex_stablepools,
        _sync_exrond_pools,
        _sync_vestadex_pools,
        _sync_vestax_staking_pool,
        _sync_hatom_staking_pool,
        _sync_hatom_money_markets
    ]

    tasks = [asyncio.create_task(_safely_do(f), name=f.__name__)
             for f in functions]
    results = await asyncio.gather(*tasks)

    swap_pools = []

    for task, result in zip(tasks, results):
        logging.info(f'{task.get_name()} -> {len(result)} swap pools')

        swap_pools.extend(result)

    set_swap_pools(swap_pools)

    logging.info(f'Nb swap pools: {len(swap_pools)} (total)')


async def _safely_do(function_: Callable[..., None]) -> List[SwapPool]:
    try:
        return await function_()
    except:
        logging.exception(f'Error while loading pools {function_}')


async def _sync_xexchange_pools() -> List[SwapPool]:
    logging.info('Loading xExchange pools')

    async with aiohttp.ClientSession(mvx_gateway_url()) as http_client:

        res = await async_sc_query(http_client,
                                   sc_address_aggregator(),
                                   'getXExchangePools')

        if res is not None:
            lp_statuses = [parse_xexchange_pool_status(r) for r in res]
        else:
            logging.error(
                'Error calling "getXExchangePools" from aggregator SC')
            return []

    logging.info(f'xExchange: pairs before filter {len(lp_statuses)}')

    lp_statuses = [s for s in lp_statuses
                   if s.state == 1
                   and _is_pair_valid([(s.first_token_id, str(s.first_token_reserve)),
                                      (s.second_token_id, str(s.second_token_reserve))])]

    logging.info(f'xExchange: pairs after filter {len(lp_statuses)}')

    swap_pools = []

    for lp_status in lp_statuses:
        first_token = get_or_fetch_token(lp_status.first_token_id)
        second_token = get_or_fetch_token(lp_status.second_token_id)

        if first_token is None or second_token is None:
            continue

        pool = XExchangeConstantProductPool(first_token=first_token,
                                            first_token_reserves=lp_status.first_token_reserve,
                                            lp_token_supply=lp_status.lp_token_supply,
                                            second_token=second_token,
                                            second_token_reserves=lp_status.second_token_reserve,
                                            total_fee_percent=lp_status.total_fee_percent,
                                            special_fee_percent=lp_status.special_fee_percent)

        swap_pools.append(SwapPool(name=f'xExchange: {first_token.name}/{second_token.name}',
                                   sc_address=lp_status.sc_address,
                                   tokens_in=[first_token.identifier,
                                              second_token.identifier],
                                   tokens_out=[first_token.identifier,
                                               second_token.identifier],
                                   type=SC_TYPE_XEXCHANGE))

        set_dex_aggregator_pool(
            lp_status.sc_address, first_token.identifier, second_token.identifier, pool)
        set_dex_aggregator_pool(
            lp_status.sc_address, second_token.identifier, first_token.identifier, pool)

    logging.info('Loading xExchange pools - done')

    return swap_pools


async def _sync_onedex_pools() -> List[SwapPool]:
    logging.info('Loading OneDex pools')

    sc_address = sc_address_onedex_swap()
    if not sc_address:
        logging.info('OneDex swap SC address not set -> skip')
        return []

    pairs = []

    async with aiohttp.ClientSession(mvx_gateway_url()) as http_client:

        res = await async_sc_query(http_client,
                                   sc_address,
                                   function='getTotalFeePercent',
                                   args=[])
        if res:
            total_fee_percent = hex2dec(res[0])
        else:
            logging.error('Error calling "getTotalFeePercent" from OneDex SC')
            return []

        res = await async_sc_query(http_client,
                                   sc_address,
                                   function='getMainPairTokens',
                                   args=[])
        if res is not None:
            main_pair_tokens = [hex2str(r) for r in res]
        else:
            logging.error('Error calling "getMainPairTokens" from OneDex SC')
            return []

        res = await async_sc_query(http_client,
                                   sc_address,
                                   function='viewPairs',
                                   args=[])

        if res is not None:
            pairs = [parse_onedex_pair(r) for r in res]
        else:
            logging.error('Error calling "viewPairs" from OneDex SC')
            return []

        logging.info(f'OneDex: pairs before {len(pairs)}')

        pairs = [p for p in pairs
                 if p.state == 1
                 and _is_pair_valid([(p.first_token_identifier, p.first_token_reserve),
                                     (p.second_token_identifier, p.second_token_reserve)])]

        logging.info(f'OneDex: pairs after {len(pairs)}')

    swap_pools = []

    for pair in pairs:
        first_token = get_or_fetch_token(pair.first_token_identifier)
        second_token = get_or_fetch_token(pair.second_token_identifier)
        if first_token is None or second_token is None:
            continue

        pool = OneDexConstantProductPool(fees_percent_base_pts=total_fee_percent,
                                         first_token=first_token,
                                         first_token_reserves=pair.first_token_reserve,
                                         lp_token_supply=pair.lp_supply,
                                         second_token=second_token,
                                         second_token_reserves=pair.second_token_reserve,
                                         main_pair_tokens=main_pair_tokens)

        swap_pools.append(SwapPool(name=f'OneDex: {first_token.name}/{second_token.name}',
                                   sc_address=sc_address,
                                   tokens_in=[first_token.identifier,
                                              second_token.identifier],
                                   tokens_out=[first_token.identifier,
                                               second_token.identifier],
                                   type=SC_TYPE_ONEDEX))

        set_dex_aggregator_pool(
            sc_address, pair.first_token_identifier, pair.second_token_identifier, pool)
        set_dex_aggregator_pool(
            sc_address, pair.second_token_identifier, pair.first_token_identifier, pool)

    logging.info('Loading OneDex pools - done')

    return swap_pools


async def _sync_ashswap_stable_pools() -> List[SwapPool]:
    logging.info('Loading AshSwap stable pools')

    agg_sc = sc_address_aggregator()

    swap_pools = []

    async with aiohttp.ClientSession(mvx_gateway_url()) as http_client:

        res = await async_sc_query(http_client,
                                   agg_sc,
                                   'getAllAshSwapStablePools')

        pools = []

        if res is not None:
            stablepools_statuses = [parse_ashswap_stablepool_status(r)
                                    for r in res]

            stablepools_statuses = [s for s in stablepools_statuses
                                    if s.state == 1]

            for status in stablepools_statuses:

                tokens = [get_or_fetch_token(x)
                          for x in status.tokens]

                if tokens.count(None) > 0:
                    continue

                pool = StableSwapPool(amp_factor=status.amp_factor,
                                      fees_percent_base_pts=status.swap_fee_percent // 10,
                                      lp_token_supply=status.lp_token_supply,
                                      tokens=tokens,
                                      reserves=status.reserves,
                                      underlying_prices=status.underlying_prices)
                pools.append(pool)

                token_ids = [t.identifier for t in tokens]
                swap_pools.append(SwapPool(name=f"AshSwap: {'/'.join([t.name for t in tokens])}",
                                           sc_address=status.sc_address,
                                           tokens_in=token_ids,
                                           tokens_out=token_ids,
                                           type=SC_TYPE_ASHSWAP_STABLEPOOL))

                for t1, t2 in product(tokens, tokens):
                    if t1.identifier != t2.identifier:
                        set_dex_aggregator_pool(status.sc_address,
                                                t1.identifier,
                                                t2.identifier,
                                                pool)

    logging.info(f'AshSwap stable pools: {len(pools)}')

    logging.info('Loading AshSwap stable pools - done')

    return swap_pools


async def _sync_ashswap_v2_pools() -> List[SwapPool]:
    logging.info('Loading AshSwap V2 pools')

    agg_sc = sc_address_aggregator()

    swap_pools = []

    async with aiohttp.ClientSession(mvx_gateway_url()) as http_client:
        pools = []

        res = await async_sc_query(http_client,
                                   agg_sc,
                                   'getAllAshSwapV2Pools')

        if res is not None:
            v2_pools_statuses = [
                parse_ashswap_v2_pool_status(r) for r in res]

            v2_pools_statuses = [s for s in v2_pools_statuses
                                 if s.state == 1]

            for status in v2_pools_statuses:

                tokens = [get_or_fetch_token(x)
                          for x in status.tokens]

                if tokens.count(None) > 0:
                    continue

                pool = AshSwapPoolV2(amp=status.amp_factor,
                                     d=status.d,
                                     fee_gamma=status.fee_gamma,
                                     future_a_gamma_time=status.future_a_gamma_time,
                                     gamma=status.gamma,
                                     mid_fee=status.mid_fee,
                                     out_fee=status.out_fee,
                                     price_scale=status.price_scale,
                                     reserves=status.reserves,
                                     tokens=tokens,
                                     xp=status.xp)
                pools.append(pool)

                token_ids = [t.identifier for t in tokens]
                swap_pools.append(SwapPool(name=f"AshSwap: {'/'.join([t.name for t in tokens])}",
                                           sc_address=status.sc_address,
                                           tokens_in=token_ids,
                                           tokens_out=token_ids,
                                           type=SC_TYPE_ASHSWAP_V2))

                for t1, t2 in product(tokens, tokens):
                    if t1.identifier != t2.identifier:
                        set_dex_aggregator_pool(status.sc_address,
                                                t1.identifier,
                                                t2.identifier,
                                                pool)

    logging.info(f'AshSwap V2 pools: {len(pools)}')

    logging.info('Loading AshSwap V2 pools - done')

    return swap_pools


async def _sync_jex_cp_pools() -> List[SwapPool]:
    logging.info('Loading JEX CP pools')

    swap_pools = []

    async with aiohttp.ClientSession(mvx_gateway_url()) as http_client:

        res = await async_sc_query(http_client,
                                   sc_address_aggregator(),
                                   'getJexCpPools')

        if res is None:
            logging.error('Error fetching JEX CP pools')
            return []

        sc_addresses = [parse_address(x)[0] for i, x in enumerate(res)
                        if i % 2 == 0]

        lp_statuses = [x for i, x in enumerate(res)
                       if i % 2 == 1]

        lp_statuses = [parse_jex_cp_lp_status(sc_addresses[i].bech32(), x)
                       for i, x in enumerate(lp_statuses)]

        logging.info(f'JEX: CP pools before filter {len(lp_statuses)}')

        lp_statuses = [s for s in lp_statuses
                       if not s.paused
                       and _is_pair_valid([(s.first_token_identifier, s.first_token_reserve),
                                           (s.second_token_identifier, s.second_token_reserve)])]

        logging.info(f'JEX: CP pools after filter {len(lp_statuses)}')

        nb_pools = 0

        for lp_status in lp_statuses:

            if lp_status.paused:
                continue

            lp_fees_percent_base_pts = lp_status.lp_fees
            platform_fees_percent_base_pts = lp_status.platform_fees
            first_token = get_or_fetch_token(lp_status.first_token_identifier)
            first_token_reserves = int(lp_status.first_token_reserve)
            second_token = get_or_fetch_token(
                lp_status.second_token_identifier)
            second_token_reserves = int(lp_status.second_token_reserve)
            lp_token_supply = int(lp_status.lp_token_supply)

            lp_token = get_or_fetch_token(lp_status.lp_token_identifier)
            lp_token.is_lp_token = True

            pool = JexConstantProductPool(
                fees_percent_base_pts=lp_fees_percent_base_pts,
                platform_fees_percent_base_pts=platform_fees_percent_base_pts,
                first_token=first_token,
                first_token_reserves=first_token_reserves,
                lp_token_supply=lp_token_supply,
                second_token=second_token,
                second_token_reserves=second_token_reserves)

            set_dex_aggregator_pool(
                lp_status.sc_address, first_token.identifier, second_token.identifier, pool)
            set_dex_aggregator_pool(
                lp_status.sc_address, second_token.identifier, first_token.identifier, pool)

            swap_pools.append(SwapPool(name=f'JEX: {first_token.name}/{second_token.name}',
                                       sc_address=lp_status.sc_address,
                                       tokens_in=[first_token.identifier,
                                                  second_token.identifier],
                                       tokens_out=[first_token.identifier,
                                                   second_token.identifier],
                                       type=SC_TYPE_JEXCHANGE_LP))

            deposit_pool = JexConstantProductDepositPool(fees_percent_base_pts=0,
                                                         first_token=first_token,
                                                         first_token_reserves=first_token_reserves,
                                                         lp_token_supply=lp_token_supply,
                                                         second_token=second_token,
                                                         second_token_reserves=second_token_reserves)
            set_dex_aggregator_pool(lp_status.sc_address, first_token.identifier,
                                    lp_status.lp_token_identifier, deposit_pool)
            set_dex_aggregator_pool(lp_status.sc_address, second_token.identifier,
                                    lp_status.lp_token_identifier, deposit_pool)

            swap_pools.append(SwapPool(name=f'JEX: {first_token.name}/{second_token.name} (D)',
                                       sc_address=lp_status.sc_address,
                                       tokens_in=[first_token.identifier,
                                                  second_token.identifier],
                                       tokens_out=[
                                           lp_status.lp_token_identifier],
                                       type=SC_TYPE_JEXCHANGE_LP_DEPOSIT))

            # TODO JexConstantProductWithdrawPool

            nb_pools += 1

    logging.info(f'JEX CP pools: {nb_pools}')

    logging.info('Loading JEX CP pools - done')

    return swap_pools


async def _sync_jex_stablepools() -> List[SwapPool]:
    logging.info('Loading JEX stable pools')

    sc_deployer = sc_address_jex_lp_deployer()
    if sc_deployer is None:
        logging.info('OneDex swap SC address not set -> skip')
        return []

    swap_pools = []

    async with aiohttp.ClientSession(mvx_gateway_url()) as http_client:

        res = await async_sc_query(http_client, sc_deployer, 'getAllContracts')

        if res is not None:
            contracts = [parse_jex_deployed_contract(r) for r in res]
            sc_addresses = [x.sc_address
                            for x in contracts
                            if x.sc_type == 1]

        nb_pools = 0

        for sc_address in sc_addresses:
            try:
                res = await async_sc_query(http_client, sc_address, 'getStatus')

                lp_status = parse_jex_stablepool_status(sc_address, res[0])
            except:
                logging.exception(
                    f'Error parsing JEX stable pool (address={sc_address})')
                continue

            if lp_status.paused:
                continue

            tokens = [get_or_fetch_token(x)
                      for x in lp_status.tokens]
            reserves = [int(x) for x in lp_status.reserves]
            underlying_prices = [int(x) for x in lp_status.underlying_prices]

            lp_token = get_or_fetch_token(lp_status.lp_token_identifier)
            lp_token.is_lp_token = True

            lp_token_supply = int(lp_status.lp_token_supply)

            pool = JexStableSwapPool(amp_factor=lp_status.amp_factor,
                                     fees_percent_base_pts=lp_status.swap_fee / 100,
                                     lp_token_supply=lp_token_supply,
                                     tokens=tokens,
                                     reserves=reserves,
                                     underlying_prices=underlying_prices)

            token_ids = [t.identifier for t in tokens]
            swap_pools.append(SwapPool(name=f"JEX: {'/'.join([t.name for t in tokens])}",
                                       sc_address=lp_status.sc_address,
                                       tokens_in=token_ids,
                                       tokens_out=token_ids,
                                       type=SC_TYPE_JEXCHANGE_STABLEPOOL))

            deposit_pool = JexStableSwapPoolDeposit(amp_factor=lp_status.amp_factor,
                                                    fees_percent_base_pts=lp_status.swap_fee,
                                                    tokens=tokens,
                                                    lp_token_supply=lp_token_supply,
                                                    reserves=reserves,
                                                    underlying_prices=underlying_prices)
            swap_pools.append(SwapPool(name=f"JEX: {'/'.join([t.name for t in tokens])} (D)",
                                       sc_address=lp_status.sc_address,
                                       tokens_in=token_ids,
                                       tokens_out=[
                                           lp_status.lp_token_identifier],
                                       type=SC_TYPE_JEXCHANGE_STABLEPOOL_DEPOSIT))

            for t1, t2 in product(lp_status.tokens, lp_status.tokens):
                if t1 != t2:
                    set_dex_aggregator_pool(sc_address, t1, t2, pool)
            for t in lp_status.tokens:
                set_dex_aggregator_pool(sc_address,
                                        t,
                                        lp_status.lp_token_identifier,
                                        deposit_pool)

            nb_pools += 1

    logging.info(f'JEX stable pools: {nb_pools}')

    logging.info('Loading JEX stable pools - done')

    return swap_pools


async def _sync_exrond_pools() -> List[SwapPool]:
    logging.info('Loading Exrond pools')

    query = '''
{
  pairs {
    address
    firstTokenReserve
    secondTokenReserve
    firstToken {
      identifier
      __typename
    }
    secondToken {
      identifier
      __typename
    }
    liquidityPoolToken {
      identifier
      supply
        __typename
    }
    totalFeePercent
    __typename
  }
}
'''
    data = {
        'query': query
    }
    url = 'https://api.exrond.com/graphql'
    # resp = requests.post(url, json=data)

    swap_pools = []

    async with aiohttp.request('POST', url=url, json=data) as resp:
        json_ = await resp.json()
        pairs = json_['data']['pairs']

        logging.info(f'Exrond: pairs before filter {len(pairs)}')

        pairs = [p for p in pairs if _is_pair_valid(
            [(p['firstToken']['identifier'], p['firstTokenReserve']),
             (p['secondToken']['identifier'], p['secondTokenReserve'])]
        )]

        logging.info(f'Exrond: pairs after filter {len(pairs)}')

        for pair in pairs:
            sc_address = pair['address']
            first_token = get_or_fetch_token(
                pair['firstToken']['identifier'])
            second_token = get_or_fetch_token(
                pair['secondToken']['identifier'])
            lp_token_identifier: str = pair['liquidityPoolToken']['identifier']

            if first_token is None or second_token is None:
                continue

            if not lp_token_identifier.startswith('LP'):
                continue

            first_token_reserves = int(pair['firstTokenReserve'])
            second_token_reserves = int(pair['secondTokenReserve'])
            fees_percent_base_pts = int(
                10_000 * float(pair['totalFeePercent']))

            pool = ConstantProductPool(fees_percent_base_pts=fees_percent_base_pts,
                                       first_token=first_token,
                                       first_token_reserves=first_token_reserves,
                                       second_token=second_token,
                                       second_token_reserves=second_token_reserves,
                                       lp_token_supply=0)

            swap_pools.append(SwapPool(name=f'Exrond: {first_token.name}/{second_token.name}',
                                       sc_address=sc_address,
                                       tokens_in=[first_token.identifier,
                                                  second_token.identifier],
                                       tokens_out=[first_token.identifier,
                                                   second_token.identifier],
                                       type=SC_TYPE_EXROND))

            set_dex_aggregator_pool(
                sc_address, first_token.identifier, second_token.identifier, pool)
            set_dex_aggregator_pool(
                sc_address, second_token.identifier, first_token.identifier, pool)

    logging.info(f'Exrond pools: {len(pairs)}')

    logging.info('Loading Exrond pools - done')

    return swap_pools


async def _sync_vestadex_pools() -> List[SwapPool]:
    logging.info('Loading VestaDex pools')

    sc_address = sc_address_vestadex_router()
    if not sc_address:
        logging.info('VestaDex router SC address not set -> skip')
        return []

    pairs: List[VestaDexPool] = []
    swap_pools = []

    done = False
    from_ = 1
    size = 20

    async with aiohttp.ClientSession(mvx_gateway_url()) as http_client:

        while not done:

            res = await async_sc_query(http_client,
                                       sc_address,
                                       'viewPaginationPools',
                                       [from_, from_ + size])

            if res is not None:
                new_pairs = parse_vestadex_view_pools(res[0])

                done = len(new_pairs) < size

                pairs.extend(new_pairs)

            else:
                logging.error('Error calling "viewPools" from VestaDex SC')

                done = True

            from_ += size

    logging.info(f'VestaDex: pairs before filter {len(pairs)}')

    pairs = [p for p in pairs
             if p.pool_state == 1
             and _is_pair_valid([(p.first_token_id, p.first_token_reserve),
                                (p.second_token_id, p.second_token_reserve)])]

    logging.info(f'VestaDex: pairs after filter {len(pairs)}')

    for pair in pairs:

        first_token = get_or_fetch_token(pair.first_token_id)
        second_token = get_or_fetch_token(pair.second_token_id)

        if first_token is None or second_token is None:
            continue

        pool = VestaDexConstantProductPool(first_token=first_token,
                                           first_token_reserves=int(
                                               pair.first_token_reserve),
                                           lp_token_supply=int(
                                               pair.lp_token_supply),
                                           second_token=second_token,
                                           second_token_reserves=int(
                                               pair.second_token_reserve),
                                           special_fee_percent=pair.special_fee_percentage,
                                           total_fee_percent=pair.total_fee_percentage)

        swap_pools.append(SwapPool(name=f'VestaDex: {first_token.name}/{second_token.name}',
                                   sc_address=pair.pool_address,
                                   tokens_in=[first_token.identifier,
                                              second_token.identifier],
                                   tokens_out=[first_token.identifier,
                                               second_token.identifier],
                                   type=SC_TYPE_VESTADEX))

        set_dex_aggregator_pool(
            pair.pool_address, first_token.identifier, second_token.identifier, pool)
        set_dex_aggregator_pool(
            pair.pool_address, second_token.identifier, first_token.identifier, pool)

    logging.info(f'VestaDex pools: {len(pairs)}')

    logging.info('Loading VestaDex pools - done')

    return swap_pools


async def _sync_vestax_staking_pool() -> List[SwapPool]:
    logging.info('Loading VestaX staking pool')

    sc_address = sc_address_vestax_staking()
    if not sc_address:
        logging.info('VestaX staking SC address not set -> skip')
        return []

    swap_pools = []

    async with aiohttp.ClientSession(mvx_gateway_url()) as http_client:

        res = await async_sc_query(http_client,
                                   sc_address,
                                   function='getVegldPrice')
        if res is None:
            return []

        egld_price = hex2dec(res[0])

        token_in = get_or_fetch_token(WEGLD_IDENTIFIER)
        token_out = get_or_fetch_token('VEGLD-2b9319')

        pool = ConstantPricePool(egld_price,
                                 token_in=token_in,
                                 token_out=token_out,
                                 token_out_reserve=999*10**token_out.decimals)

        swap_pools.append(SwapPool(name=f'VestaX (stake)',
                                   sc_address=sc_address,
                                   tokens_in=[WEGLD_IDENTIFIER],
                                   tokens_out=['VEGLD-2b9319'],
                                   type=SC_TYPE_VESTAX_STAKE))

        set_dex_aggregator_pool(sc_address,
                                token_in.identifier,
                                token_out.identifier,
                                pool)

    logging.info('Loading VestaX staking pool - done')

    return swap_pools


async def _sync_hatom_staking_pool() -> List[SwapPool]:
    logging.info('Loading Hatom staking pool')

    sc_address = sc_address_hatom_staking()
    if not sc_address:
        logging.info('Hatom staking SC address not set -> skip')
        return []

    swap_pools = []

    async with aiohttp.ClientSession(mvx_gateway_url()) as http_client:

        res = await async_sc_query(http_client,
                                   sc_address,
                                   function='getExchangeRate')

        if res is None:
            return []

        egld_price = hex2dec(res[0])

        token_in = get_or_fetch_token(WEGLD_IDENTIFIER)
        token_out = get_or_fetch_token('SEGLD-3ad2d0')

        pool = ConstantPricePool(egld_price, token_in=token_in, token_out=token_out,
                                 token_out_reserve=999*10**token_out.decimals)

        swap_pools.append(SwapPool(name=f'Hatom (stake)',
                                   sc_address=sc_address,
                                   tokens_in=[WEGLD_IDENTIFIER],
                                   tokens_out=['SEGLD-3ad2d0'],
                                   type=SC_TYPE_HATOM_STAKE))

        set_dex_aggregator_pool(
            sc_address, token_in.identifier, token_out.identifier, pool)

    logging.info('Loading Hatom staking pool - done')

    return swap_pools


async def _sync_hatom_money_markets() -> List[SwapPool]:
    logging.info('Loading Hatom MM pools')

    agg_sc = sc_address_aggregator()

    swap_pools = []

    async with aiohttp.ClientSession(mvx_gateway_url()) as http_client:
        def _addr(x): return Address.from_bech32(x).pubkey

        args = [
            _addr('erd1qqqqqqqqqqqqqpgqxerzmkr80xc0qwa8vvm5ug9h8e2y7jgsqk2svevje0'),
            10**18,  # HTM
            _addr('erd1qqqqqqqqqqqqqpgqxmn4jlazsjp6gnec95423egatwcdfcjm78ss5q550k'),
            10**18,  # SEGLD
            _addr('erd1qqqqqqqqqqqqqpgqkrgsvct7hfx7ru30mfzk3uy6pxzxn6jj78ss84aldu'),
            1_000000,  # USDC
            _addr('erd1qqqqqqqqqqqqqpgqvxn0cl35r74tlw2a8d794v795jrzfxyf78sstg8pjr'),
            1_000000,  # USDT
            _addr('erd1qqqqqqqqqqqqqpgqta0tv8d5pjzmwzshrtw62n4nww9kxtl278ssspxpxu'),
            10**18,  # UTK
            _addr('erd1qqqqqqqqqqqqqpgqg47t8v5nwzvdxgf6g5jkxleuplu8y4f678ssfcg5gy'),
            10**8,  # WBTC
            _addr('erd1qqqqqqqqqqqqqpgq8h8upp38fe9p4ny9ecvsett0usu2ep7978ssypgmrs'),
            10**18  # WETH
        ]

        res = await async_sc_query(http_client,
                                   agg_sc,
                                   'getHatomMoneyMarkets',
                                   args)

        if res is not None:
            money_markets = [parse_hatom_mm(r) for r in res]
        else:
            logging.error('Error getting Hatom money markets')
            money_markets = []

        nb_mms = 0

        for mm in money_markets:
            h_token = get_or_fetch_token(mm.hatom_token_id)

            underlying_token = get_or_fetch_token(WEGLD_IDENTIFIER) \
                if mm.underlying_id == 'EGLD' \
                else get_or_fetch_token(mm.underlying_id)

            if h_token is None or underlying_token is None:
                continue

            # deposit (infinite amount)
            deposit_price = mm.ratio_tokens_to_underlying * \
                10**(18-underlying_token.decimals)

            deposit_pool = ConstantPricePool(deposit_price,
                                             underlying_token,
                                             h_token,
                                             9999999*10**h_token.decimals)

            swap_pools.append(SwapPool(name=f'Hatom: {underlying_token.name} market',
                                       sc_address=mm.sc_address,
                                       tokens_in=[underlying_token.identifier],
                                       tokens_out=[h_token.identifier],
                                       type=SC_TYPE_HATOM_MONEY_MARKET_MINT))

            # redeem
            redeem_price = mm.ratio_underlying_to_tokens * \
                10**(18-h_token.decimals)

            redeem_pool = ConstantPricePool(redeem_price,
                                            h_token,
                                            underlying_token,
                                            mm.cash)

            swap_pools.append(SwapPool(name=f'Hatom: {underlying_token.name} market',
                                       sc_address=mm.sc_address,
                                       tokens_in=[h_token.identifier],
                                       tokens_out=[
                                           underlying_token.identifier],
                                       type=SC_TYPE_HATOM_MONEY_MARKET_REDEEM))

            set_dex_aggregator_pool(mm.sc_address,
                                    underlying_token.identifier,
                                    h_token.identifier,
                                    deposit_pool)

            set_dex_aggregator_pool(mm.sc_address,
                                    h_token.identifier,
                                    underlying_token.identifier,
                                    redeem_pool)

            nb_mms += 1

    logging.info(f'Hatom money markets: {nb_mms}')

    logging.info('Loading Hatom MM pools - done')

    return swap_pools


def _is_pair_valid(tokens_reserves: List[Tuple[str, str]]) -> bool:
    is_valid = True

    for token_id, reserve in tokens_reserves:
        if token_id == JEX_IDENTIFIER and int(reserve) < 100_000*10**18:
            is_valid = False
            break
        if token_id == WEGLD_IDENTIFIER and int(reserve) < 10**18:
            is_valid = False
            break
        if token_id == USDC_IDENTIFIER and int(reserve) < 100*10**6:
            is_valid = False
            break

    return is_valid
