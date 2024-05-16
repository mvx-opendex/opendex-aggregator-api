
import logging
import os
from typing import Tuple

import aiohttp
from data.datastore import get_dex_aggregator_pool
from pools.model import SwapRoute
from pools.pools import JexConstantProductPool, JexStableSwapPool
from services.externals import async_sc_query
from services.parsers.routing import parse_evaluate_response
from services.tokens import get_or_fetch_token
from utils.env import sc_address_aggregator


def can_estimate_offline(route: SwapRoute) -> bool:
    return len(list(filter(lambda h: h.pool.type in ['ashswap_stablepool_deposit',
                                                     'ashswap_stablepool_withdraw',
                                                     'dx25',
                                                     'jexchange',
                                                     'jexchange_lp_withdraw',
                                                     'jexchange_stableswap'], route.hops))) == 0


def estimate_offline(token_in: str, amount_in: int, route: SwapRoute) -> Tuple[int, int, int, str]:
    pools = [get_dex_aggregator_pool(
        h.pool.sc_address, h.token_in, h.token_out) for h in route.hops]

    should_apply_fees = len(pools) > 1 and \
        next((p for p in pools
              if isinstance(p, JexConstantProductPool) or isinstance(p, JexStableSwapPool)
              ), None) is None

    token = token_in
    amount = amount_in
    fees_applied = False
    fee_amount = 0
    fee_token = ''
    estimated_gas = 10_000_000

    for pool, hop in zip(pools, route.hops):
        if pool is None:
            logging.info(
                f'Pool not found {hop.token_in} {hop.token_out} {hop.pool.type} {hop.pool.sc_address}')
            return (0, 0, 0, '')

        if hop.token_in.startswith('WEGLD-') and should_apply_fees:
            fee_amount = (amount * 5) // 10_000
            fee_token = token
            amount -= fee_amount
            fees_applied = True

        amount = pool.estimate_amount_out(token_in=get_or_fetch_token(token),
                                          amount_in=amount,
                                          token_out=get_or_fetch_token(hop.token_out))
        token = hop.token_out

        estimated_gas += pool.estimated_gas()

    if not fees_applied and should_apply_fees:
        fee_amount = (amount * 5) // 10_000
        fee_token = token
        amount -= fee_amount

    return (amount, fee_amount, estimated_gas, fee_token)


async def estimate_online(amount_in: int,
                          route: SwapRoute,
                          http_client: aiohttp.ClientSession) -> Tuple[int, int, int, str]:
    route_payload = f'0x{route.serialize()}'
    args = [f'{amount_in}', route_payload]

    sc_address = sc_address_aggregator()

    logging.info('QUERY: evaluate (evaluate_route)')
    try:
        result = await async_sc_query(http_client=http_client,
                                      sc_address=sc_address,
                                      function='evaluate',
                                      args=args)
    except:
        logging.exception('Error during evaluation')
        return (0, 0, 0, '')

    if result is not None and len(result) > 0:
        net_amount_out, fee, estimated_gas, fee_token = \
            parse_evaluate_response(result[0])

        return (net_amount_out, fee, estimated_gas, fee_token)

    return (0, 0, 0, '')
