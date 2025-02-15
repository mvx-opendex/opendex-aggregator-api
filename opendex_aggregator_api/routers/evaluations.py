import asyncio
import logging
from time import time
from typing import Callable, List, Optional

import aiohttp
from fastapi import APIRouter, HTTPException, Query

from opendex_aggregator_api.data.datastore import get_tokens
from opendex_aggregator_api.data.model import Esdt
from opendex_aggregator_api.pools.model import (DynamicRoutingSwapEvaluation,
                                                SwapEvaluation, SwapRoute)
from opendex_aggregator_api.routers.adapters import (adap_dyn_eval,
                                                     adapt_static_eval)
from opendex_aggregator_api.routers.api_models import SwapEvaluationOut
from opendex_aggregator_api.routers.common import get_or_find_sorted_routes
from opendex_aggregator_api.services import evaluations as eval_svc
from opendex_aggregator_api.utils.env import mvx_gateway_url

router = APIRouter()


@router.get("/evaluate")
@router.post("/evaluate")
async def do_evaluate(token_in: str,
                      token_out: str,
                      amount_in: Optional[int] = None,
                      net_amount_out: Optional[int] = None,
                      max_hops: int = Query(default=3, ge=1, le=4),
                      with_dyn_routing: Optional[bool] = False) -> SwapEvaluationOut:

    if amount_in is None:
        if net_amount_out is None:
            raise HTTPException(status_code=400,
                                detail='Either amount_in or net_amount_out is required')
    else:
        if net_amount_out is not None:
            raise HTTPException(status_code=400,
                                detail='Either amount_in or net_amount_out is required')

    token_in_obj = _get_token(token_in)
    token_out_obj = _get_token(token_out)

    routes = get_or_find_sorted_routes(token_in,
                                       token_out,
                                       max_hops)

    if len(routes) == 0:
        return _adapt_eval_result(static_eval=None,
                                  dyn_eval=None,
                                  token_in=token_in_obj,
                                  token_out=token_out_obj)

    routes = _cutoff_routes(routes)

    start = time()

    pools_cache = {}

    async with aiohttp.ClientSession(mvx_gateway_url()) as http_client:
        if amount_in is not None:
            evals = await asyncio.gather(*[_safely_do(eval_svc.evaluate_fixed_input(r,
                                                                                    amount_in,
                                                                                    pools_cache,
                                                                                    http_client))
                                           for r in routes])
            evals = (e for e in evals if e is not None and e.net_amount_out > 1)
            evals = sorted(evals,
                           key=lambda x: x.net_amount_out,
                           reverse=True)
        else:
            evals = await asyncio.gather(*[_safely_do(eval_svc.evaluate_fixed_output(r,
                                                                                     net_amount_out,
                                                                                     pools_cache,
                                                                                     http_client))
                                           for r in routes])
            evals = (e for e in evals if e is not None and e.amount_in > 1)
            evals = sorted(evals,
                           key=lambda x: x.amount_in)

    best_static_eval = evals[0] if len(evals) > 0 else None

    if with_dyn_routing:
        dyn_routing_eval = await eval_svc.find_best_dynamic_routing_algo3(routes,
                                                                          amount_in,
                                                                          max_routes=3)
    else:
        dyn_routing_eval = None

    end = time()

    logging.info(
        f'{token_in} -> {token_out} :: evaluations computed in {end-start} seconds')

    print('Static route')
    if best_static_eval:
        print([h.pool.name for h in best_static_eval.route.hops])
        print(
            f'{amount_in} {token_in} -> {best_static_eval.net_amount_out} {token_out}')

    print('Dynamic route')
    if dyn_routing_eval:
        print(dyn_routing_eval.pretty_string())
    else:
        print('Not found')

    if best_static_eval \
        and dyn_routing_eval \
            and dyn_routing_eval.net_amount_out <= best_static_eval.net_amount_out:
        dyn_routing_eval = None

    return _adapt_eval_result(best_static_eval,
                              dyn_routing_eval,
                              token_in_obj,
                              token_out_obj)


def _adapt_eval_result(static_eval: Optional[SwapEvaluation],
                       dyn_eval: Optional[DynamicRoutingSwapEvaluation],
                       token_in: Esdt,
                       token_out: Esdt) -> SwapEvaluationOut:
    return SwapEvaluationOut(static=adapt_static_eval(static_eval,
                                                      token_in,
                                                      token_out) if static_eval else None,
                             dynamic=adap_dyn_eval(dyn_eval,
                                                   token_in,
                                                   token_out) if dyn_eval else None)


async def _safely_do(coroutine_: Callable[..., None]) -> SwapEvaluation:
    try:
        return await coroutine_
    except:
        logging.exception(f'Error during evaluation')


def _cutoff_routes(routes: List[SwapRoute]):
    max_routes = 100
    max_online = 5
    nb_online = 0

    res = []

    for route in routes:
        res.append(route)

        if len(res) >= max_routes:
            break

        if not eval_svc.can_evaluate_offline(route):
            nb_online += 1

        if nb_online == max_online:
            break

    return res


def _get_token(token_id: str) -> Esdt:
    all_tokens = get_tokens()

    if all_tokens is None:
        raise HTTPException(status_code=404)

    token = next((t for t in all_tokens if t.identifier == token_id), None)

    if token is None:
        raise HTTPException(status_code=404)

    return token
