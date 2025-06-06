
import logging
from time import time
from typing import List

from opendex_aggregator_api.data.constants import SC_TYPE_JEXCHANGE_ORDERBOOK
from opendex_aggregator_api.data.datastore import get_swap_pools
from opendex_aggregator_api.pools.model import SwapHop, SwapPool, SwapRoute


def find_routes(token_in: str,
                token_out: str,
                max_hops: int,
                max_hops2: int,
                max_routes: int = 500) -> List[SwapRoute]:
    '''
    Find routes between token_in and token_out.

    :max_hops2: will be used if no routes are found with max_hops
    '''

    logging.info(f'Find routes {token_in} -> {token_out}')

    start = time()

    results = []

    all_pools = get_swap_pools()

    if all_pools is None:
        return []

    _find_routes_inner(token_out,
                       all_pools,
                       max_hops,
                       max_hops2,
                       max_routes,
                       [SwapRoute(hops=[],
                                  token_in=token_in,
                                  token_out='')],
                       results)

    end = time()

    logging.info(
        f'{token_in} -> {token_out} :: {len(results)} routes found in {end-start} seconds')

    return results


def sort_routes(routes: List[SwapRoute]) -> List[SwapRoute]:

    def _hop_penalty(h: SwapHop):
        if h.pool.type == SC_TYPE_JEXCHANGE_ORDERBOOK:
            return 10

        return 1

    def _route_penalty(r: SwapRoute):
        return sum((_hop_penalty(h) for h in r.hops))

    return sorted(routes, key=lambda x: _route_penalty(x))


def _find_routes_inner(token_out: str,
                       all_pools: List[SwapPool],
                       max_hops: int,
                       max_hops2: int,
                       max_routes: int,
                       candidates: List[SwapRoute],
                       results: List[SwapRoute]):

    if max_hops == 0 and len(results) > 0:
        return

    if max_hops2 == 0:
        return

    new_candidates = []

    for route in candidates:
        if len(route.hops) > 0:
            token_in = route.hops[-1].token_out
        else:
            token_in = route.token_in

        pools = [p for p in all_pools
                 if token_in in p.tokens_in]

        for pool in pools:

            next_hops = [SwapHop(pool=pool,
                                 token_in=token_in,
                                 token_out=t) for t in pool.tokens_out
                         if t != token_in and t != route.token_in]

            for next_hop in next_hops:
                next_route = SwapRoute(hops=[*route.hops, next_hop],
                                       token_in=route.token_in,
                                       token_out=next_hop.token_out)

                if next_route.token_out == token_out:
                    if len(results) < max_routes:
                        results.append(next_route)
                elif max_hops > 0:
                    new_candidates.append(next_route)

    if len(new_candidates) > 0 and len(results) < max_routes:
        _find_routes_inner(token_out,
                           all_pools,
                           max(max_hops-1, 0),
                           max(max_hops2-1, 0),
                           max_routes,
                           new_candidates,
                           results)
