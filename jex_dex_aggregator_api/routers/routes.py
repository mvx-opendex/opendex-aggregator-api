from datetime import timedelta
from typing import List

from fastapi import APIRouter, BackgroundTasks, Query, Response

from jex_dex_aggregator_api.routers.api_models import SwapRouteOut
from jex_dex_aggregator_api.services import routes as routes_svc
from jex_dex_aggregator_api.utils.redis_utils import redis_get_or_set_cache

router = APIRouter()


@router.get("/routes")
def get_routes(response: Response,
               background_tasks: BackgroundTasks,
               token_in: str,
               token_out: str,
               max_hops: int = Query(default=3, ge=1, le=4)) -> List[SwapRouteOut]:
    response.headers['Access-Control-Allow-Origin'] = '*'

    def _do():
        routes = routes_svc.find_routes(token_in,
                                        token_out,
                                        max_hops)

        return routes_svc.sort_routes(routes)

    cache_key = f'routes_{token_in}_{token_out}_{max_hops}'
    body = redis_get_or_set_cache(cache_key,
                                  timedelta(seconds=6),
                                  _do,
                                  lambda json_: json_,
                                  deferred=True,
                                  background_tasks=background_tasks)

    return body
