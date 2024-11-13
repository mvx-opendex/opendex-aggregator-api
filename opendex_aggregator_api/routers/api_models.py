

from typing import List, Optional

from multiversx_sdk_core import Address
from pydantic import BaseModel, Field

from opendex_aggregator_api.data.constants import SC_TYPES
from opendex_aggregator_api.pools.model import SwapRoute
from opendex_aggregator_api.utils.convert import int2hex, str2hex


class StaticRouteSwapEvaluationOut(BaseModel):
    amount_in: str
    estimated_gas: str
    estimated_tx_fee_egld: str
    fee_amount: str
    fee_token: Optional[str]
    human_amount_in: float
    net_amount_out: str
    net_human_amount_out: float
    route: SwapRoute
    route_payload: str
    rate: float
    rate2: float
    slippage_percent: float
    theorical_amount_out: str
    theorical_human_amount_out: float
    amounts_and_routes_payload: str


class DynamicRouteSwapEvaluationOut(BaseModel):
    amount_in: str
    estimated_gas: str
    estimated_tx_fee_egld: str
    human_amount_in: float
    net_amount_out: str
    net_human_amount_out: float
    evals: List[StaticRouteSwapEvaluationOut]
    rate: float
    rate2: float
    amounts_and_routes_payload: str


class SwapEvaluationOut(BaseModel):
    dynamic: Optional[DynamicRouteSwapEvaluationOut]
    static: Optional[StaticRouteSwapEvaluationOut]


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


class TokenOut(BaseModel):
    decimals: int
    identifier: str
    ticker: str
    is_lp_token: Optional[bool] = Field(..., serialization_alias='isLpToken')
    name: str
    exchange: Optional[str]
    usd_price: Optional[float] = Field(..., serialization_alias='usdPrice')


class TokenIdAndAmount(BaseModel):
    token_id: str
    amount: str
