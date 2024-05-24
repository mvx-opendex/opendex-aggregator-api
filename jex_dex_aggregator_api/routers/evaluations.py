
import json
from typing import List, Optional

from fastapi import APIRouter, Query, Response

from jex_dex_aggregator_api.pools.model import (DynamicRoutingSwapEvaluation,
                                                SwapEvaluation)
from jex_dex_aggregator_api.routers.api_models import (
    DynamicRouteSwapEvaluationOut, StaticRouteSwapEvaluationOut,
    SwapEvaluationOut)
from jex_dex_aggregator_api.routers.common import get_or_find_sorted_routes
from jex_dex_aggregator_api.services import evaluations as eval_svc
from jex_dex_aggregator_api.services.tokens import get_or_fetch_token

router = APIRouter()


@router.get("/evaluate")
@router.post("/evaluate")
async def do_evaluate(response: Response,
                      token_in: str,
                      amount_in: int,
                      token_out: str,
                      max_hops: int = Query(default=3, ge=1, le=4)) -> SwapEvaluationOut:
    response.headers['Access-Control-Allow-Origin'] = '*'

    routes = get_or_find_sorted_routes(token_in,
                                       token_out,
                                       max_hops)

    if len(routes) == 0:
        return _adapt_eval_result(None, None)

    pools_cache = {}

    evals = [eval_svc.evaluate(r, amount_in, pools_cache)
             for r in routes[:100]]

    evals = sorted(evals,
                   key=lambda x: x.net_amount_out,
                   reverse=True)

    dyn_routing_eval = await eval_svc.find_best_dynamic_routing_algo3(routes,
                                                                      amount_in)

    print('Static route')
    print([h.pool.name for h in evals[0].route.hops])
    print(
        f'{amount_in} {token_in} -> {evals[0].net_amount_out} {token_out}')

    print('Dynamic route')
    if dyn_routing_eval:
        print(dyn_routing_eval.pretty_string())
    else:
        print('Not found')

    return _adapt_eval_result(evals[0],
                              dyn_routing_eval)


def _adapt_eval_result(static_eval: Optional[SwapEvaluation],
                       dyn_eval: Optional[DynamicRoutingSwapEvaluation]) -> SwapEvaluationOut:
    return SwapEvaluationOut(static=_adapt_static_eval(static_eval) if static_eval else None,
                             dynamic=_adap_dyn_eval(dyn_eval) if dyn_eval else None)


def _adapt_static_eval(e: SwapEvaluation) -> StaticRouteSwapEvaluationOut:
    token_out = get_or_fetch_token(e.route.token_out)

    net_human_amount_out = e.net_amount_out / 10**token_out.decimals
    theorical_human_amount_out = e.theorical_amount_out / 10**token_out.decimals

    slippage_percent = 100 * (net_human_amount_out -
                              theorical_human_amount_out) / theorical_human_amount_out

    return StaticRouteSwapEvaluationOut(amount_in=str(e.amount_in),
                                        estimated_gas=str(e.estimated_gas),
                                        fee_amount=str(e.fee_amount),
                                        fee_token=e.fee_token,
                                        net_amount_out=str(e.net_amount_out),
                                        route=e.route,
                                        net_human_amount_out=net_human_amount_out,
                                        slippage_percent=slippage_percent,
                                        theorical_amount_out=str(
                                            e.theorical_amount_out),
                                        theorical_human_amount_out=theorical_human_amount_out)


def _adap_dyn_eval(e: DynamicRoutingSwapEvaluation) -> DynamicRouteSwapEvaluationOut:
    token_out = get_or_fetch_token(e.evaluations[0].route.token_out)

    return DynamicRouteSwapEvaluationOut(amount_in=str(e.amount_in),
                                         net_amount_out=str(e.net_amount_out),
                                         net_human_amount_out=e.net_amount_out / 10**token_out.decimals,
                                         evals=[_adapt_static_eval(x)
                                                for x in e.evaluations])
