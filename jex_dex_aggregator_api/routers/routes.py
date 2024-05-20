from typing import List

from fastapi import APIRouter, BackgroundTasks, Query, Response

from jex_dex_aggregator_api.routers.api_models import SwapRouteOut
from jex_dex_aggregator_api.routers.common import get_or_find_sorted_routes

router = APIRouter()


@router.get("/routes")
def get_routes(response: Response,
               background_tasks: BackgroundTasks,
               token_in: str,
               token_out: str,
               max_hops: int = Query(default=3, ge=1, le=4)) -> List[SwapRouteOut]:
    response.headers['Access-Control-Allow-Origin'] = '*'

    return get_or_find_sorted_routes(token_in,
                                     token_out,
                                     max_hops,
                                     background_tasks)
