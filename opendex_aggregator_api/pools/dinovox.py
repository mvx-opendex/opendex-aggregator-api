
from dataclasses import dataclass
from typing import Tuple

from typing_extensions import override

from opendex_aggregator_api.data.model import Esdt
from opendex_aggregator_api.pools.pools import ConstantProductPool
from opendex_aggregator_api.utils.math import ceildiv

MAX_FEE = 10_000


@dataclass
class DinoVoxConstantProductPool(ConstantProductPool):

    protocol_fee: int

    def __init__(self,
                 lp_token: Esdt,
                 lp_supply: int,
                 token_a: Esdt,
                 token_a_reserve: int,
                 token_b: Esdt,
                 token_b_reserve: int,
                 fee_bps: int,
                 protocol_fee: int):
        super().__init__(total_fee=fee_bps,
                         max_fee=MAX_FEE,
                         first_token=token_a,
                         first_token_reserves=token_a_reserve,
                         lp_token=lp_token,
                         lp_token_supply=lp_supply,
                         second_token=token_b,
                         second_token_reserves=token_b_reserve)
        self.protocol_fee = protocol_fee

    @override
    def deep_copy(self):
        return DinoVoxConstantProductPool(lp_token=self.lp_token.model_copy(),
                                          lp_supply=self.lp_token_supply,
                                          token_a=self.first_token.model_copy(),
                                          token_a_reserve=self.first_token_reserves,
                                          token_b=self.second_token.model_copy(),
                                          token_b_reserve=self.second_token_reserves,
                                          fee_bps=self.total_fee,
                                          protocol_fee=self.protocol_fee)

    @override
    def estimate_amount_out(self, token_in: Esdt, amount_in: int, token_out: Esdt) -> Tuple[int, int, int]:
        in_reserve, out_reserve = self._reserves(token_in,
                                                 token_out)

        total_fee = int(amount_in * self.total_fee / MAX_FEE)
        protocol_fee = int(total_fee * self.protocol_fee / MAX_FEE)
        net_in = amount_in - total_fee

        k = in_reserve * out_reserve
        new_in_reserve = in_reserve + net_in
        new_out_reserve = int(k / new_in_reserve)

        if out_reserve < new_out_reserve:
            raise ValueError(f'Insufficient liquidity')

        amount_out = out_reserve - new_out_reserve

        return amount_out, protocol_fee, 0

    @override
    def estimate_amount_in(self, token_out: Esdt, net_amount_out: int, token_in: Esdt) -> Tuple[int, int, int]:
        raise NotImplementedError(
            'DinoVoxConstantProductPool does not support estimate_amount_in')

    @override
    def estimated_gas(self) -> int:
        return 25_000_000

    @override
    def _source(self) -> str:
        return 'dinovox'
