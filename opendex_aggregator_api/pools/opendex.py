
from dataclasses import dataclass
from typing import Optional, Tuple

from typing_extensions import override

from opendex_aggregator_api.data.model import Esdt
from opendex_aggregator_api.pools.pools import ConstantProductPool
from opendex_aggregator_api.utils.math import ceildiv

MAX_FEE = 10_000


@dataclass
class OpendexConstantProductPool(ConstantProductPool):
    fee_token: Optional[Esdt]

    platform_fee: int

    def __init__(self,
                 first_token: Esdt,
                 first_token_reserves: int,
                 lp_token_supply: int,
                 second_token: Esdt,
                 second_token_reserves: int,
                 total_fee: int,
                 platform_fee: int,
                 fee_token: Optional[Esdt]):

        super().__init__(max_fee=MAX_FEE,
                         total_fee=total_fee,
                         first_token=first_token,
                         first_token_reserves=first_token_reserves,
                         lp_token_supply=lp_token_supply,
                         second_token=second_token,
                         second_token_reserves=second_token_reserves)

        self.fee_token = fee_token
        self.platform_fee = platform_fee

    @override
    def deep_copy(self):
        return OpendexConstantProductPool(platform_fee=self.platform_fee,
                                          total_fee=self.total_fee,
                                          first_token=self.first_token.model_copy(),
                                          first_token_reserves=self.first_token_reserves,
                                          lp_token_supply=self.lp_token_supply,
                                          second_token=self.second_token.model_copy(),
                                          second_token_reserves=self.second_token_reserves,
                                          fee_token=self.fee_token.model_copy() if self.fee_token else None)

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

        platform_fee_in = 0
        platform_fee_out = 0

        if self.fee_token and token_in.identifier == self.fee_token.identifier:
            lp_fee, platform_fee_in = self._calculate_fees(amount_in)

            amount_in_less_fees = amount_in - lp_fee - platform_fee_in

            net_amount_out = (
                amount_in_less_fees * out_reserve_before) // (in_reserve_before + amount_in_less_fees)
        else:
            amount_out = (amount_in * out_reserve_before) // \
                (in_reserve_before + amount_in)

            lp_fee, platform_fee_out = self._calculate_fees(amount_out)

            net_amount_out = amount_out - lp_fee - platform_fee_out

        return net_amount_out, platform_fee_in, platform_fee_out

    @override
    def estimate_amount_in(self, token_out: Esdt, net_amount_out: int, token_in: Esdt) -> Tuple[int, int, int]:
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

        platform_fee_in = 0
        platform_fee_out = 0

        if self.fee_token is None or token_out.identifier == self.fee_token.identifier:
            amount_out = (net_amount_out *
                          self.max_fee) // (self.max_fee - self.total_fee)

            platform_fee_out = amount_out * self.platform_fee // self.max_fee
        else:
            amount_out = net_amount_out

        amount_in = ceildiv(amount_out * in_reserve_before,
                            out_reserve_before - amount_out)

        if self.fee_token and token_in.identifier == self.fee_token.identifier:
            amount_in = amount_in * \
                self.max_fee // (self.max_fee - self.total_fee)

            platform_fee_in = amount_in * self.platform_fee // self.max_fee

        return amount_in, platform_fee_in, platform_fee_out

    def _calculate_fees(self, amount: int) -> Tuple[int, int]:

        total_fee = (amount * self.total_fee) // MAX_FEE

        platform_fee = (amount * self.platform_fee) // MAX_FEE

        lp_fee = total_fee - platform_fee

        return (lp_fee, platform_fee)

    @override
    def _source(self) -> str:
        return 'opendex'
