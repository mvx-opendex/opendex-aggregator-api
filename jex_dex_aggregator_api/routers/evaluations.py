
from fastapi import APIRouter, BackgroundTasks, Query, Response

from jex_dex_aggregator_api.routers.common import get_or_find_sorted_routes
from jex_dex_aggregator_api.services import evaluations as eval_svc

router = APIRouter()


@router.get("/evaluations")
def get_evaluations(response: Response,
                    background_tasks: BackgroundTasks,
                    token_in: str,
                    amount_in: int,
                    token_out: str,
                    max_hops: int = Query(default=3, ge=1, le=4)):
    response.headers['Access-Control-Allow-Origin'] = '*'

    routes = get_or_find_sorted_routes(token_in,
                                       token_out,
                                       max_hops,
                                       background_tasks)

    evaluations = [eval_svc.evaluate(r, amount_in)
                   for r in routes]

    return sorted(evaluations,
                  key=lambda x: x.net_amount_out,
                  reverse=True)
