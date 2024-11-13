from typing import List

from fastapi import APIRouter, HTTPException, Response

from opendex_aggregator_api.routers.api_models import TokenIdAndAmount
from opendex_aggregator_api.routers.common import get_or_find_sorted_routes
from opendex_aggregator_api.services import evaluations as eval_svc

router = APIRouter()


@router.post("/multi-eval")
async def post_multi_eval(response: Response,
                          token_out: str,
                          token_and_amounts: List[TokenIdAndAmount]):
    response.headers['Access-Control-Allow-Origin'] = '*'

    if len(token_and_amounts) < 0 or len(token_and_amounts) > 10:
        raise HTTPException(status_code=400,
                            detail='Invalid number of tokens/amounts')

    return [_eval(token_and_amount, token_out)
            for token_and_amount in token_and_amounts]


def _eval(token_and_amount: TokenIdAndAmount, token_out: str):
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
