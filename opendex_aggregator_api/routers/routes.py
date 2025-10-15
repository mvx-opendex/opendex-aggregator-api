from typing import List

from fastapi import APIRouter, HTTPException, Query

from opendex_aggregator_api.ignored_tokens import IGNORED_TOKENS
from opendex_aggregator_api.routers.adapters import adapt_route
from opendex_aggregator_api.routers.api_models import SwapRouteOut
from opendex_aggregator_api.routers.common import get_or_find_sorted_routes

router = APIRouter()


@router.get('/routes')
def get_routes(token_in: str,
               token_out: str,
               max_hops: int = Query(default=3, ge=1, le=4)) -> List[SwapRouteOut]:
    if token_in in IGNORED_TOKENS or token_out in IGNORED_TOKENS:
        raise HTTPException(status_code=400,
                            detail='Invalid input or output token')

    return [adapt_route(r)
            for r in get_or_find_sorted_routes(token_in,
                                               token_out,
                                               max_hops)]
