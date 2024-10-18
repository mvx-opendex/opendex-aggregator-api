
from dataclasses import dataclass
from typing import Tuple

from typing_extensions import override

from opendex_aggregator_api.data.model import Esdt
from opendex_aggregator_api.pools.pools import ConstantProductPool

MAX_FEE = 1_000_000


@dataclass
class VestaDexConstantProductPool(ConstantProductPool):

    fee_token: Esdt
    special_fee: int

    def __init__(self,
                 first_token: Esdt,
                 first_token_reserves: int,
                 lp_token_supply: int,
                 second_token: Esdt,
                 second_token_reserves: int,
                 total_fee: int,
                 special_fee: int,
                 fee_token: Esdt,):

        super().__init__(max_fee=MAX_FEE,
                         total_fee=total_fee,
                         first_token=first_token,
                         first_token_reserves=first_token_reserves,
                         lp_token_supply=lp_token_supply,
                         second_token=second_token,
                         second_token_reserves=second_token_reserves)

        self.fee_token = fee_token
        self.special_fee = special_fee

    @override
    def deep_copy(self) -> 'VestaDexConstantProductPool':
        return VestaDexConstantProductPool(first_token=self.first_token,
                                           first_token_reserves=self.first_token_reserves,
                                           lp_token_supply=self.lp_token_supply,
                                           second_token=self.second_token,
                                           second_token_reserves=self.second_token_reserves,
                                           total_fee=self.total_fee,
                                           special_fee=self.special_fee,
                                           fee_token=self.fee_token)

    @override
    def estimate_amount_out(self, token_in: Esdt, amount_in: int, token_out: Esdt) -> Tuple[int, int, int]:
        if token_in.identifier == self.first_token.identifier:
            (in_reserve_before, out_reserve_before) = (
                self.first_token_reserves, self.second_token_reserves)
        elif token_in.identifier == self.second_token.identifier:
            (in_reserve_before, out_reserve_before) = (
                self.second_token_reserves, self.first_token_reserves)
        else:
            raise ValueError(
                f'Invalid token in: {token_in.identifier} for pool {self}')

        if in_reserve_before == 0:
            return 0, 0, 0

        special_fee_in = 0
        special_fee_out = 0

        if self.fee_token and token_in.identifier == self.fee_token.identifier:
            lp_fee, special_fee_in = self._calculate_fees(amount_in)

            amount_in_less_fees = amount_in - lp_fee - special_fee_in

            net_amount_out = (
                amount_in_less_fees * out_reserve_before) // (in_reserve_before + amount_in_less_fees)
        else:
            amount_out = (amount_in * out_reserve_before) // \
                (in_reserve_before + amount_in)

            lp_fee, special_fee_out = self._calculate_fees(amount_out)

            net_amount_out = amount_out - lp_fee - special_fee_out

        return net_amount_out, special_fee_in, special_fee_out

    @override
    def _calculate_fees(self, amount: int) -> Tuple[int, int]:

        total_fee = (amount * self.total_fee) // MAX_FEE

        special_fee = (amount * self.special_fee) // MAX_FEE

        lp_fee = total_fee - special_fee

        return (lp_fee, special_fee)

    @override
    def _source(self) -> str:
        return 'vestadex'
