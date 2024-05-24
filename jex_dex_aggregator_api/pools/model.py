import uuid
from typing import List, Optional

from multiversx_sdk_core import Address
from pydantic import BaseModel

from jex_dex_aggregator_api.data.constants import SC_TYPES
from jex_dex_aggregator_api.utils.convert import int2hex, str2hex


class SwapPool(BaseModel):
    name: str
    sc_address: str
    tokens_in: List[str]
    tokens_out: List[str]
    type: str

    def __eq__(self, other):
        return type(self) == type(other) \
            and self.sc_address == other.sc_address \
            and self.tokens_in == other.tokens_in \
            and self.type == other.type

    def sc_type_as_code(self) -> int:
        return SC_TYPES.index(self.type)


class SwapHop(BaseModel):
    pool: SwapPool
    token_in: str
    token_out: str

    def serialize(self) -> str:
        str_ = Address.from_bech32(self.pool.sc_address).hex()
        str_ += int2hex(self.pool.sc_type_as_code(), 2)
        str_ += int2hex(len(self.token_out), 8)
        str_ += str2hex(self.token_out)
        return str_


class SwapRoute(BaseModel):
    id_: int = uuid.uuid4().__hash__()
    hops: List[SwapHop]
    token_in: str
    token_out: str

    def __hash__(self) -> int:
        return self.id_

    def is_disjointed(self, other):
        if type(other) != type(self):
            return False

        for h in self.hops:
            if any((h.pool == x.pool for x in other.hops)):
                return False

        return True

    def serialize(self) -> bytes:
        str_ = int2hex(len(self.token_in), 8)
        str_ += str2hex(self.token_in)
        str_ += int2hex(len(self.hops), 8)
        for hop in self.hops:
            str_ += hop.serialize()
        return bytes.fromhex(str_)


class SwapEvaluation(BaseModel):
    amount_in: int
    estimated_gas: int
    fee_amount: int
    fee_token: Optional[str]
    net_amount_out: int
    route: SwapRoute
    theorical_amount_out: int


class DynamicRoutingSwapEvaluation(BaseModel):
    amount_in: int
    estimated_gas: int
    evaluations: List[SwapEvaluation]
    net_amount_out: int
    theorical_amount_out: int
    token_in: str
    token_out: str

    def pretty_string(self) -> str:
        s = f'{self.amount_in} {self.token_in}  ->  {self.net_amount_out} {self.token_out}\n'
        for e in self.evaluations:
            s += f"""
  |
  +--> {e.amount_in} {self.token_in} :: "{' | '.join([h.pool.name for h in e.route.hops])}" :: {e.net_amount_out} {self.token_out} --+
"""
        return s
