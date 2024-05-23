

from typing import List, Optional

from multiversx_sdk_core import Address
from pydantic import BaseModel

from jex_dex_aggregator_api.data.constants import SC_TYPES
from jex_dex_aggregator_api.pools.model import SwapRoute
from jex_dex_aggregator_api.utils.convert import int2hex, str2hex


class SwapEvaluationOut(BaseModel):
    amount_in: str
    estimated_gas: str
    fee_amount: str
    fee_token: Optional[str]
    net_amount_out: str
    net_human_amount_out: float
    routes: List[SwapRoute]
    slippage_percent: float
    theorical_amount_out: str
    theorical_human_amount_out: float


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
