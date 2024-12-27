from typing import List

from fastapi import APIRouter, Query

from opendex_aggregator_api.routers.adapters import adapt_route
from opendex_aggregator_api.routers.api_models import SwapRouteOut
from opendex_aggregator_api.routers.common import get_or_find_sorted_routes

router = APIRouter()


@router.get("/routes")
def get_routes(token_in: str,
               token_out: str,
               max_hops: int = Query(default=3, ge=1, le=4)) -> List[SwapRouteOut]:

    return [adapt_route(r)
            for r in get_or_find_sorted_routes(token_in,
                                               token_out,
                                               max_hops)]
