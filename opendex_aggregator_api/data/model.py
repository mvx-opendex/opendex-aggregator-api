
from typing import List, Optional

from pydantic import BaseModel


class AshSwapStablePoolStatus(BaseModel):
    sc_address: str
    state: int
    amp_factor: int
    lp_token_id: str
    lp_token_supply: int
    tokens: List[str]
    underlying_prices: List[int]
    reserves: List[int]
    swap_fee_percent: int


class AshSwapV2PoolStatus(BaseModel):
    sc_address: str
    state: int
    amp_factor: int
    d: int
    fee_gamma: int
    future_a_gamma_time: int
    gamma: int
    mid_fee: int
    out_fee: int
    price_scale: int
    reserves: List[int]
    tokens: List[str]
    xp: List[int]
    lp_token_id: str
    lp_token_supply: int


class Esdt(BaseModel):
    decimals: int
    identifier: str
    ticker: str
    name: str
    is_lp_token: Optional[bool] = None
    exchange: Optional[str] = None
    usd_price: Optional[float] = None

    def __eq__(self, other):
        if isinstance(other, Esdt):
            return self.identifier == other.identifier
        return False

    def __hash__(self):
        return hash(self.identifier)


class JexCpLpStatus(BaseModel):
    sc_address: str
    paused: bool
    first_token_identifier: str
    first_token_reserve: str
    second_token_identifier: str
    second_token_reserve: str
    lp_token_identifier: str
    lp_token_supply: str
    owner: str
    lp_fees: int
    platform_fees: int
    platform_fees_receiver: Optional[str]
    volume_prev_epoch: List[str]
    fees_prev_epoch: List[str]
    fees_last_7_epochs: List[str]


class JexStablePoolStatus(BaseModel):
    sc_address: str
    paused: bool
    amp_factor: int
    nb_tokens: int
    tokens: List[str]
    reserves: List[str]
    lp_token_identifier: str
    lp_token_supply: str
    owner: str
    swap_fee: int
    platform_fees_receiver: Optional[str]
    volume_prev_epoch: List[str]
    fees_prev_epoch: List[str]
    fees_last_7_epochs: List[str]
    underlying_prices: List[str]


class OneDexPair(BaseModel):
    id_: int
    state: int
    first_token_identifier: str
    first_token_reserve: int
    lp_supply: int
    lp_token_identifier: str
    lp_token_decimals: int
    second_token_identifier: str
    second_token_reserve: int
    total_fee_percentage: int


class OpendexPair(BaseModel):
    sc_address: str
    owner: str
    paused: bool
    first_token_id: str
    first_token_reserve: int
    second_token_id: str
    second_token_reserve: int
    lp_token_id: Optional[str]
    lp_token_supply: int
    total_fee_percent: int
    platform_fee_percent: int
    platform_fee_receiver: str
    fee_token_id: Optional[str]


class JexDeployedPoolContract(BaseModel):
    sc_type: int
    sc_address: str
    owner: str


class XExchangePoolStatus(BaseModel):
    sc_address: str
    state: int
    first_token_id: str
    second_token_id: str
    first_token_reserve: int
    second_token_reserve: int
    lp_token_id: str
    lp_token_supply: int
    special_fee_percent: int
    total_fee_percent: int


class HatomMoneyMarket(BaseModel):
    sc_address: str
    hatom_token_id: str
    underlying_id: str
    cash: int
    ratio_tokens_to_underlying: int
    ratio_underlying_to_tokens: int


class ExchangeRate(BaseModel):
    base_token_id: str
    quote_token_id: str
    rate: float
    rate2: float
    source: str
    sc_address: str
    base_token_liquidity: int
    quote_token_liquidity: int

    def __hash__(self):
        return hash(f'{self.base_token_id}::{self.quote_token_id}::{self.sc_address}')


class LpTokenComposition(BaseModel):
    lp_token_id: str
    lp_token_supply: int
    token_ids: List[str]
    token_reserves: List[int]
