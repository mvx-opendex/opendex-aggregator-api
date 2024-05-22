from typing import List, Optional

from pydantic import BaseModel


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


class SwapHop(BaseModel):
    pool: SwapPool
    token_in: str
    token_out: str


class SwapRoute(BaseModel):
    hops: List[SwapHop]
    token_in: str
    token_out: str

    def is_disjointed(self, other):
        if type(other) != type(self):
            return False

        for h in self.hops:
            if any((h.pool == x.pool for x in other.hops)):
                return False

        return True

    def serialize():
        raise NotImplementedError()


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
