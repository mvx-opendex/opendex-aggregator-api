
import logging
from typing import List

from jex_dex_aggregator_api.data.datastore import get_swap_pools
from jex_dex_aggregator_api.pools.model import SwapHop, SwapPool, SwapRoute


def find_routes(token_in: str,
                token_out: str,
                max_hops: int) -> List[SwapRoute]:
    logging.info(f'Find routes {token_in} -> {token_out}')

    results = []

    all_pools = get_swap_pools()

    _find_routes_inner(token_out,
                       all_pools,
                       max_hops,
                       [SwapRoute(hops=[],
                                  token_in=token_in,
                                  token_out='')],
                       results)

    return results


def sort_routes(routes: List[SwapRoute]) -> List[SwapRoute]:

    return sorted(routes, key=lambda x: len(x.hops))


def _find_routes_inner(token_out: str,
                       all_pools: List[SwapPool],
                       max_hops: int,
                       candidates: List[SwapRoute],
                       results: List[SwapRoute]):

    if max_hops == 0:
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
                    results.append(next_route)
                elif max_hops > 0:
                    new_candidates.append(next_route)

    if len(new_candidates) > 0:
        _find_routes_inner(token_out,
                           all_pools,
                           max_hops-1,
                           new_candidates,
                           results)
