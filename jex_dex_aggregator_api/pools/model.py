from typing import List

from pydantic import BaseModel


class SwapPool(BaseModel):
    name: str
    sc_address: str
    tokens_in: List[str]
    tokens_out: List[str]
    type: str


class SwapHop(BaseModel):
    pool: SwapPool
    token_in: str
    token_out: str


class SwapRoute(BaseModel):
    hops: List[SwapHop]
    token_in: str
    token_out: str

    def serialize():
        raise NotImplementedError()
