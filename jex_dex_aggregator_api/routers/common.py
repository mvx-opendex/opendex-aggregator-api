from datetime import timedelta
import logging
from typing import List

from jex_dex_aggregator_api.pools.model import SwapRoute

from jex_dex_aggregator_api.services import routes as routes_svc
from jex_dex_aggregator_api.utils.redis_utils import redis_get_or_set_cache


def get_or_find_sorted_routes(token_in: str,
                              token_out: str,
                              max_hops: int) -> List[SwapRoute]:

    def _do():
        routes = routes_svc.find_routes(token_in,
                                        token_out,
                                        max_hops)

        return routes_svc.sort_routes(routes)

    cache_key = f'routes_{token_in}_{token_out}_{max_hops}'
    return redis_get_or_set_cache(cache_key,
                                  cache_ttl=timedelta(seconds=6),
                                  task=_do,
                                  parse=lambda json_: [SwapRoute.model_validate(x)
                                                       for x in json_])
