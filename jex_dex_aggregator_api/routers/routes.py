from datetime import timedelta
from typing import List

from fastapi import APIRouter, BackgroundTasks, Query, Response
from multiversx_sdk_core import Address
from pydantic import BaseModel

from jex_dex_aggregator_api.data.constants import SC_TYPES
from jex_dex_aggregator_api.services import routes as routes_svc
from jex_dex_aggregator_api.utils.convert import int2hex, str2hex
from jex_dex_aggregator_api.utils.redis_utils import redis_get_or_set_cache

router = APIRouter()


class SwapPoolOut(BaseModel):
    name: str
    sc_address: str
    type: str

    def sc_type_as_code(self) -> int:
        return SC_TYPES.index(self.type)


class SwapHopOut(BaseModel):
    pool: SwapPoolOut
    token_in: str
    token_out: str

    def serialize(self) -> str:
        str_ = Address.from_bech32(self.pool.sc_address).hex()
        str_ += int2hex(self.pool.sc_type_as_code(), 2)
        str_ += int2hex(len(self.token_out), 8)
        str_ += str2hex(self.token_out)
        return str_


class SwapRouteOut(BaseModel):
    hops: List[SwapHopOut]
    token_in: str
    token_out: str

    def serialize(self) -> str:
        str_ = int2hex(len(self.token_in), 8)
        str_ += str2hex(self.token_in)
        str_ += int2hex(len(self.hops), 8)
        for hop in self.hops:
            str_ += hop.serialize()
        return str_


@router.get("/routes")
def get_routes(response: Response,
               background_tasks: BackgroundTasks,
               token_in: str,
               token_out: str,
               max_hops: int = Query(default=3, ge=1, le=4)) -> List[SwapRouteOut]:
    response.headers['Access-Control-Allow-Origin'] = '*'

    def _do():
        return routes_svc.find_routes(token_in,
                                      token_out,
                                      max_hops)

    cache_key = f'routes_{token_in}_{token_out}_{max_hops}'
    body = redis_get_or_set_cache(cache_key,
                                  timedelta(seconds=6),
                                  _do,
                                  lambda json_: json_,
                                  deferred=True,
                                  background_tasks=background_tasks)

    return body
