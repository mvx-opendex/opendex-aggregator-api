import asyncio
import logging
from time import time
from typing import Optional

import aiohttp
from fastapi import APIRouter, Query, Response

from opendex_aggregator_api.pools.model import (DynamicRoutingSwapEvaluation,
                                                SwapEvaluation)
from opendex_aggregator_api.routers.api_models import (
    DynamicRouteSwapEvaluationOut, StaticRouteSwapEvaluationOut,
    SwapEvaluationOut)
from opendex_aggregator_api.routers.common import get_or_find_sorted_routes
from opendex_aggregator_api.services import evaluations as eval_svc
from opendex_aggregator_api.services.tokens import get_or_fetch_token
from opendex_aggregator_api.utils.env import mvx_gateway_url

router = APIRouter()


@router.get("/evaluate")
@router.post("/evaluate")
async def do_evaluate(response: Response,
                      token_in: str,
                      amount_in: int,
                      token_out: str,
                      max_hops: int = Query(default=3, ge=1, le=4),
                      with_dyn_routing: Optional[bool] = False) -> SwapEvaluationOut:
    response.headers['Access-Control-Allow-Origin'] = '*'

    routes = get_or_find_sorted_routes(token_in,
                                       token_out,
                                       max_hops)

    if len(routes) == 0:
        return _adapt_eval_result(None, None)

    start = time()

    pools_cache = {}

    async with aiohttp.ClientSession(mvx_gateway_url()) as http_client:
        evals = await asyncio.gather(*[eval_svc.evaluate(r, amount_in, pools_cache, http_client)
                                       for r in routes[:50]])

    evals = sorted(evals,
                   key=lambda x: x.net_amount_out,
                   reverse=True)

    if with_dyn_routing:

        dyn_routing_eval = await eval_svc.find_best_dynamic_routing_algo3(routes,
                                                                          amount_in)

    end = time()

    logging.info(
        f'{token_in} -> {token_out} :: evaluations computed in {end-start} seconds')

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
    token_in = get_or_fetch_token(e.route.token_in)
    token_out = get_or_fetch_token(e.route.token_out)

    net_human_amount_out = e.net_amount_out / 10**token_out.decimals
    theorical_human_amount_out = e.theorical_amount_out / 10**token_out.decimals

    human_amount_in = e.amount_in / 10**token_in.decimals
    rate = human_amount_in / net_human_amount_out if net_human_amount_out else 0
    rate2 = net_human_amount_out / human_amount_in

    if theorical_human_amount_out > 0:
        slippage_percent = 100 * (net_human_amount_out -
                                  theorical_human_amount_out) / theorical_human_amount_out
    else:
        slippage_percent = 0

    return StaticRouteSwapEvaluationOut(amount_in=str(e.amount_in),
                                        human_amount_in=human_amount_in,
                                        estimated_gas=str(e.estimated_gas),
                                        fee_amount=str(e.fee_amount),
                                        fee_token=e.fee_token,
                                        net_amount_out=str(e.net_amount_out),
                                        route=e.route,
                                        route_payload=e.route.serialize().hex(),
                                        net_human_amount_out=net_human_amount_out,
                                        rate=rate,
                                        rate2=rate2,
                                        slippage_percent=slippage_percent,
                                        theorical_amount_out=str(
                                            e.theorical_amount_out),
                                        theorical_human_amount_out=theorical_human_amount_out,
                                        tx_payload=e.build_tx_payload())


def _adap_dyn_eval(e: DynamicRoutingSwapEvaluation) -> DynamicRouteSwapEvaluationOut:
    token_in = get_or_fetch_token(e.evaluations[0].route.token_in)
    token_out = get_or_fetch_token(e.evaluations[0].route.token_out)

    human_amount_in = e.amount_in / 10**token_in.decimals
    net_human_amount_out = e.net_amount_out / 10**token_out.decimals
    rate = human_amount_in / net_human_amount_out
    rate2 = net_human_amount_out / human_amount_in

    return DynamicRouteSwapEvaluationOut(amount_in=str(e.amount_in),
                                         human_amount_in=human_amount_in,
                                         estimated_gas=str(e.estimated_gas),
                                         net_amount_out=str(e.net_amount_out),
                                         net_human_amount_out=net_human_amount_out,
                                         evals=[_adapt_static_eval(x)
                                                for x in e.evaluations],
                                         rate=rate,
                                         rate2=rate2,
                                         tx_payload=e.build_tx_payload())
