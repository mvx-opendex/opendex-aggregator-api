
from dataclasses import dataclass
from typing import List, Tuple

from typing_extensions import override

from opendex_aggregator_api.data.model import Esdt

from .pools import ConstantProductPool

MAX_FEE = 10_000


@dataclass
class OneDexConstantProductPool(ConstantProductPool):
    """
    OneDex constant product pool with specific fees management.
    """

    main_pair_tokens: List[str]

    def __init__(self,
                 total_fee: int,
                 first_token: Esdt,
                 first_token_reserves: int,
                 lp_token_supply: int,
                 second_token: Esdt,
                 second_token_reserves: int,
                 main_pair_tokens: List[str]):
        super().__init__(max_fee=MAX_FEE,
                         total_fee=total_fee,
                         first_token=first_token,
                         first_token_reserves=first_token_reserves,
                         lp_token_supply=lp_token_supply,
                         second_token=second_token,
                         second_token_reserves=second_token_reserves)
        self.main_pair_tokens = main_pair_tokens

    @override
    def deep_copy(self):
        return OneDexConstantProductPool(total_fee=self.total_fee,
                                         first_token=self.first_token.model_copy(),
                                         first_token_reserves=self.first_token_reserves,
                                         lp_token_supply=self.lp_token_supply,
                                         second_token=self.second_token.model_copy(),
                                         second_token_reserves=self.second_token_reserves,
                                         main_pair_tokens=self.main_pair_tokens.copy())

    @override
    def estimate_amount_out(self, token_in: Esdt, amount_in: int, token_out: Esdt) -> Tuple[int, int, int]:
        in_reserve, out_reserve = self._reserves(token_in,
                                                 token_out)

        try:
            self.main_pair_tokens.index(token_in.identifier)
            fee_input_token = True
        except ValueError:
            fee_input_token = False

        if fee_input_token:
            amount_in_with_fee = amount_in * \
                (MAX_FEE - self.total_fee)
            num = amount_in_with_fee * out_reserve
            den = (in_reserve * MAX_FEE) + amount_in_with_fee
            net_amount_out = num // den

            return net_amount_out, 0, 0
        else:
            amount_out_without_fee = (
                amount_in * out_reserve) // (in_reserve + amount_in)

            fee = (amount_out_without_fee *
                   self.total_fee) // MAX_FEE

            net_amount_out = amount_out_without_fee - fee

            return net_amount_out, 0, 0

    @override
    def _source(self) -> str:
        return 'onedex'
