from dataclasses import dataclass
from typing import Tuple

from typing_extensions import override

from opendex_aggregator_api.data.model import Esdt
from opendex_aggregator_api.pools.pools import ConstantPricePool
from opendex_aggregator_api.services.tokens import WEGLD_IDENTIFIER


@dataclass
class XoxnoConstantPricePool(ConstantPricePool):

    @override
    def estimate_amount_out(self, token_in: Esdt, amount_in: int, token_out: Esdt) -> Tuple[int, int, int]:
        if token_in.identifier == WEGLD_IDENTIFIER and amount_in < 1_000_000_000_000_000_000:
            raise ValueError("Amount in must be greater than 1 ESDT")

        return super().estimate_amount_out(token_in, amount_in, token_out)

    @override
    def deep_copy(self):
        return XoxnoConstantPricePool(price=self.price,
                                      token_in=self.token_in.model_copy(),
                                      token_out=self.token_out.model_copy(),
                                      token_out_reserve=self.token_out_reserve)

    @override
    def estimated_gas(self) -> int:
        return 20_000_000

    @override
    def _source(self):
        return 'xoxno'
