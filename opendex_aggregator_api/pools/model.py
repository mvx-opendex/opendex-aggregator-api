import uuid
from typing import List, Optional

from multiversx_sdk_core import Address
from pydantic import BaseModel

from opendex_aggregator_api.data.constants import ESTIMATED_GAS_PER_SC_TYPE, SC_TYPES
from opendex_aggregator_api.utils.convert import (int2hex, int2hex_even_size,
                                                  str2hex)


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

    def estimated_gas(self) -> int:
        return ESTIMATED_GAS_PER_SC_TYPE[self.sc_type_as_code()]

    def sc_type_as_code(self) -> int:
        return SC_TYPES.index(self.type)


class SwapHop(BaseModel):
    pool: SwapPool
    token_in: str
    token_out: str

    def estimated_gas(self) -> int:
        return self.pool.estimated_gas()

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

    def estimated_gas(self) -> int:
        return sum((h.estimated_gas()
                    for h in self.hops))

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

    def build_amounts_and_routes_payload(self) -> str:

        amounts_and_routes_payload = int2hex_even_size(self.amount_in)
        amounts_and_routes_payload += '@'
        amounts_and_routes_payload += self.route.serialize().hex()

        return amounts_and_routes_payload


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

    def build_amounts_and_routes_payload(self) -> str:
        if len(self.evaluations) == 0:
            return ''

        return '@'.join((int2hex_even_size(e.amount_in) + '@' + e.route.serialize().hex()
                        for e in self.evaluations))
