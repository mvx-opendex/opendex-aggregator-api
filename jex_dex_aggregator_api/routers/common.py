from datetime import timedelta
from typing import List

from fastapi import BackgroundTasks

from jex_dex_aggregator_api.pools.model import SwapRoute

from jex_dex_aggregator_api.services import routes as routes_svc
from jex_dex_aggregator_api.utils.redis_utils import redis_get_or_set_cache


def get_or_find_sorted_routes(token_in: str,
                              token_out: str,
                              max_hops: int,
                              background_tasks: BackgroundTasks) -> List[SwapRoute]:

    def _do():
        routes = routes_svc.find_routes(token_in,
                                        token_out,
                                        max_hops)

        return routes_svc.sort_routes(routes)

    cache_key = f'routes_{token_in}_{token_out}_{max_hops}'
    return redis_get_or_set_cache(cache_key,
                                  timedelta(seconds=6),
                                  _do,
                                  lambda json_: [
                                      SwapRoute.model_validate(x) for x in json_],
                                  deferred=True,
                                  background_tasks=background_tasks)
