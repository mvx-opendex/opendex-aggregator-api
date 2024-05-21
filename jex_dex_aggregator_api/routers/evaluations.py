
from typing import List
from fastapi import APIRouter, BackgroundTasks, Query, Response

from jex_dex_aggregator_api.pools.model import SwapEvaluation
from jex_dex_aggregator_api.routers.api_models import SwapEvaluationOut
from jex_dex_aggregator_api.routers.common import get_or_find_sorted_routes
from jex_dex_aggregator_api.services import evaluations as eval_svc
from jex_dex_aggregator_api.services.tokens import get_or_fetch_token

router = APIRouter()


@router.get("/evaluations")
def get_evaluations(response: Response,
                    background_tasks: BackgroundTasks,
                    token_in: str,
                    amount_in: int,
                    token_out: str,
                    max_hops: int = Query(default=3, ge=1, le=4)) -> List[SwapEvaluationOut]:
    response.headers['Access-Control-Allow-Origin'] = '*'

    routes = get_or_find_sorted_routes(token_in,
                                       token_out,
                                       max_hops,
                                       background_tasks)

    evaluations = [eval_svc.evaluate(r, amount_in)
                   for r in routes]

    evaluations = sorted(evaluations,
                         key=lambda x: x.net_amount_out,
                         reverse=True)

    return [_adapt_evaluation(x) for x in evaluations[:5]]


def _adapt_evaluation(e: SwapEvaluation) -> SwapEvaluationOut:
    token_out = get_or_fetch_token(e.route.token_out)

    net_human_amount_out = e.net_amount_out / 10**token_out.decimals
    theorical_human_amount_out = e.theorical_amount_out / 10**token_out.decimals

    slippage_percent = 100 * (net_human_amount_out -
                              theorical_human_amount_out) / theorical_human_amount_out

    return SwapEvaluationOut(amount_in=str(e.amount_in),
                             estimated_gas=str(e.estimated_gas),
                             fee_amount=str(e.fee_amount),
                             fee_token=e.fee_token,
                             net_amount_out=str(e.net_amount_out),
                             route=e.route,
                             net_human_amount_out=net_human_amount_out,
                             slippage_percent=slippage_percent,
                             theorical_amount_out=str(e.theorical_amount_out),
                             theorical_human_amount_out=theorical_human_amount_out)
