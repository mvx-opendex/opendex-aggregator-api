from typing import List, Optional

from fastapi import APIRouter, HTTPException

from opendex_aggregator_api.pools.model import SwapEvaluation
from opendex_aggregator_api.routers.adapters import adapt_static_eval
from opendex_aggregator_api.routers.api_models import (
    StaticRouteSwapEvaluationOut, TokenIdAndAmount)
from opendex_aggregator_api.routers.common import get_or_find_sorted_routes
from opendex_aggregator_api.services import evaluations as eval_svc

router = APIRouter()


@router.post("/multi-eval")
async def post_multi_eval(token_out: str,
                          token_and_amounts: List[TokenIdAndAmount]) -> List[StaticRouteSwapEvaluationOut]:

    if len(token_and_amounts) < 0 or len(token_and_amounts) > 10:
        raise HTTPException(status_code=400,
                            detail='Invalid number of tokens/amounts')

    evals = [_eval(token_and_amount, token_out)
             for token_and_amount in token_and_amounts]

    return [adapt_static_eval(e)
            for e in evals
            if e is not None]


def _eval(token_and_amount: TokenIdAndAmount, token_out: str) -> Optional[SwapEvaluation]:
    routes = get_or_find_sorted_routes(token_and_amount.token_id,
                                       token_out,
                                       max_hops=3)

    pools_cache = {}

    evals = (eval_svc.evaluate_fixed_input_offline(r,
                                                   int(token_and_amount.amount),
                                                   pools_cache)
             for r in routes
             if eval_svc.can_evaluate_offline(r))

    evals = sorted(evals,
                   key=lambda x: x.net_amount_out,
                   reverse=True)

    if len(evals) > 0:
        return evals[0]
    else:
        return None
