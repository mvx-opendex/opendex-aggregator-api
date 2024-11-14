from typing import List

from fastapi import APIRouter, HTTPException, Response

from opendex_aggregator_api.pools.model import SwapEvaluation
from opendex_aggregator_api.routers.adapters import adapt_static_eval
from opendex_aggregator_api.routers.api_models import (
    StaticRouteSwapEvaluationOut, TokenIdAndAmount)
from opendex_aggregator_api.routers.common import get_or_find_sorted_routes
from opendex_aggregator_api.services import evaluations as eval_svc

router = APIRouter()


@router.options("/multi-eval")
async def options_multi_eval(response: Response):
    response.headers['Access-Control-Allow-Origin'] = '*'


@router.post("/multi-eval")
async def post_multi_eval(response: Response,
                          token_out: str,
                          token_and_amounts: List[TokenIdAndAmount]) -> List[StaticRouteSwapEvaluationOut]:
    response.headers['Access-Control-Allow-Origin'] = '*'

    if len(token_and_amounts) < 0 or len(token_and_amounts) > 10:
        raise HTTPException(status_code=400,
                            detail='Invalid number of tokens/amounts')

    evals = [_eval(token_and_amount, token_out)
             for token_and_amount in token_and_amounts]

    return [adapt_static_eval(e)
            for e in evals]


def _eval(token_and_amount: TokenIdAndAmount, token_out: str) -> SwapEvaluation:
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

    return evals[0]
