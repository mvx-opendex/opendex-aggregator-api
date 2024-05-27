
import logging
from typing import Tuple

from data.datastore import get_dex_aggregator_pool
from pools.model import SwapRoute
from pools.pools import JexConstantProductPool, JexStableSwapPool
from services.tokens import get_or_fetch_token

from jex_dex_aggregator_api.data.constants import (
    SC_TYPE_ASHSWAP_STABLEPOOL_DEPOSIT, SC_TYPE_ASHSWAP_STABLEPOOL_WITHDRAW,
    SC_TYPE_DX25, SC_TYPE_JEXCHANGE_LP_WITHDRAW, SC_TYPE_JEXCHANGE_ORDERBOOK)


def can_estimate_offline(route: SwapRoute) -> bool:
    return len(list(filter(lambda h: h.pool.type in [SC_TYPE_ASHSWAP_STABLEPOOL_DEPOSIT,
                                                     SC_TYPE_ASHSWAP_STABLEPOOL_WITHDRAW,
                                                     SC_TYPE_DX25,
                                                     SC_TYPE_JEXCHANGE_ORDERBOOK,
                                                     SC_TYPE_JEXCHANGE_LP_WITHDRAW], route.hops))) == 0


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

        amount, _, _ = pool.estimate_amount_out(token_in=get_or_fetch_token(token),
                                                amount_in=amount,
                                                token_out=get_or_fetch_token(hop.token_out))
        token = hop.token_out

        estimated_gas += pool.estimated_gas()

    if not fees_applied and should_apply_fees:
        fee_amount = (amount * 5) // 10_000
        fee_token = token
        amount -= fee_amount

    return (amount, fee_amount, estimated_gas, fee_token)
