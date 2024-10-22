
from dataclasses import dataclass
from typing import Tuple

from typing_extensions import override

from opendex_aggregator_api.data.model import Esdt
from opendex_aggregator_api.pools.pools import ConstantProductPool
from opendex_aggregator_api.utils.math import ceildiv

MAX_FEE = 100_000


@dataclass
class XExchangeConstantProductPool(ConstantProductPool):

    special_fee: int

    def __init__(self,
                 first_token: Esdt,
                 first_token_reserves: int,
                 lp_token_supply: int,
                 second_token: Esdt,
                 second_token_reserves: int,
                 special_fee: int,
                 total_fee: int):
        super().__init__(total_fee=total_fee,
                         max_fee=MAX_FEE,
                         first_token=first_token,
                         first_token_reserves=first_token_reserves,
                         lp_token_supply=lp_token_supply,
                         second_token=second_token,
                         second_token_reserves=second_token_reserves)
        self.special_fee = special_fee

    @override
    def deep_copy(self):
        return XExchangeConstantProductPool(first_token=self.first_token.model_copy(),
                                            first_token_reserves=self.first_token_reserves,
                                            lp_token_supply=self.lp_token_supply,
                                            second_token=self.second_token.model_copy(),
                                            second_token_reserves=self.second_token_reserves,
                                            special_fee=self.special_fee,
                                            total_fee=self.total_fee)

    @override
    def estimate_amount_out(self, token_in: Esdt, amount_in: int, token_out: Esdt) -> Tuple[int, int, int]:
        in_reserve, out_reserve = self._reserves(token_in,
                                                 token_out)

        amount_in_with_fee = amount_in * (MAX_FEE - self.total_fee)
        num = amount_in_with_fee * out_reserve
        den = (in_reserve * MAX_FEE) + amount_in_with_fee

        amount_out = num // den

        if amount_out > out_reserve:
            raise ValueError(f'Amount to swap to big {amount_in}')

        special_fee = (amount_in * self.special_fee) // MAX_FEE

        return amount_out, special_fee, 0

    @override
    def estimate_amount_in(self, token_out: Esdt, net_amount_out: int, token_in: Esdt) -> Tuple[int, int, int]:
        in_reserve_before, out_reserve_before = self._reserves(token_in,
                                                               token_out)

        if net_amount_out > out_reserve_before:
            raise ValueError(f'Amount out to big {net_amount_out}')

        net_amount_in = ceildiv(net_amount_out * in_reserve_before,
                                out_reserve_before - net_amount_out)

        amount_in = ((net_amount_in *
                     self.max_fee) // (self.max_fee - self.total_fee)) + 1

        special_fee = (amount_in * self.special_fee) // MAX_FEE

        return int(amount_in), special_fee, 0

    @override
    def _source(self) -> str:
        return 'xexchange'
