

from dataclasses import dataclass

from typing_extensions import override

from opendex_aggregator_api.token_constants import WEGLD_IDENTIFIER

from .pools import ConstantPricePool


@dataclass
class HatomConstantPricePool(ConstantPricePool):

    @override
    def deep_copy(self):
        return HatomConstantPricePool(price=self.price,
                                      token_in=self.token_in.model_copy(),
                                      token_out=self.token_out.model_copy(),
                                      token_out_reserve=self.token_out_reserve)

    @override
    def estimated_gas(self) -> int:
        gas = 20_000_000

        if self.token_in.identifier == WEGLD_IDENTIFIER:
            gas += 5_000_000
        elif self.token_out.identifier == WEGLD_IDENTIFIER:
            gas += 5_000_000

        return gas

    @override
    def _source(self):
        return 'hatom'
