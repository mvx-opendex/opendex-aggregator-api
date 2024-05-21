
from jex_dex_aggregator_api.data.datastore import get_dex_aggregator_pool
from jex_dex_aggregator_api.pools.model import SwapEvaluation, SwapRoute
from jex_dex_aggregator_api.services.tokens import (WEGLD_IDENTIFIER,
                                                    get_or_fetch_token)

FEE_MULTIPLIER = 0.05

NO_FEE_POOL_TYPES = ['jexchange',
                     'jexchange_lp',
                     'jexchange_lp_deposit',
                     'jexchange_lp_withdraw',
                     'jexchange_stablepool',
                     'jexchange_stablepool_deposit',
                     'jexchange_stablepool_withdraw']


def evaluate(route: SwapRoute,
             amount_in: int) -> SwapEvaluation:

    should_apply_fee = len(route.hops) > 1 and all(
        (h.pool.type not in NO_FEE_POOL_TYPES for h in route.hops))

    token = route.token_in
    amount = amount_in
    fee_amount = 0
    fee_token = None

    for hop in route.hops:
        if hop.token_in != token:
            raise ValueError(f'Invalid input token [{hop.token_in}]')

        pool = get_dex_aggregator_pool(hop.pool.sc_address,
                                       hop.token_in,
                                       hop.token_out)

        if pool is None:
            raise ValueError(f'Unknown pool [{hop.pool.sc_address}]')

        if should_apply_fee and hop.token_in == WEGLD_IDENTIFIER:
            fee_amount = int(amount * FEE_MULTIPLIER)
            fee_token = WEGLD_IDENTIFIER
            amount -= fee_amount

        esdt_in = get_or_fetch_token(hop.token_in)
        esdt_out = get_or_fetch_token(hop.token_out)

        amount = pool.estimate_amount_out(esdt_in,
                                          amount,
                                          esdt_out)

        token = hop.token_out

    if token != route.token_out:
        raise ValueError(
            f'Invalid output token after swaps [{token}] != [{route.token_out}]')

    if should_apply_fee and fee_amount is None:
        fee_amount = int(amount * FEE_MULTIPLIER)
        fee_token = token
        amount -= fee_amount

    return SwapEvaluation(amount_in=amount_in,
                          net_amount_out=amount,
                          fee_amount=fee_amount,
                          fee_token=fee_token,
                          route=route)
