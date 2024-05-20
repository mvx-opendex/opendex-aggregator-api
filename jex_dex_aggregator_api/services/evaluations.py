
from jex_dex_aggregator_api.data.datastore import get_dex_aggregator_pool
from jex_dex_aggregator_api.pools.model import SwapEvaluation, SwapRoute
from jex_dex_aggregator_api.services.tokens import get_or_fetch_token


def evaluate(route: SwapRoute,
             amount_in: int) -> SwapEvaluation:

    token = route.token_in
    amount = amount_in

    # TODO fees management

    for hop in route.hops:
        if hop.token_in != token:
            raise ValueError(f'Invalid input token [{hop.token_in}]')

        pool = get_dex_aggregator_pool(hop.pool.sc_address,
                                       hop.token_in,
                                       hop.token_out)

        if pool is None:
            raise ValueError(f'Unknown pool [{hop.pool.sc_address}]')

        esdt_in = get_or_fetch_token(hop.token_in)
        esdt_out = get_or_fetch_token(hop.token_out)

        amount = pool.estimate_amount_out(esdt_in,
                                          amount,
                                          esdt_out)

        token = hop.token_out

    if token != route.token_out:
        raise ValueError(
            f'Invalid output token after swaps [{token}] != [{route.token_out}]')

    return SwapEvaluation(amount_in=amount_in,
                          amount_out=amount,
                          route=route)
