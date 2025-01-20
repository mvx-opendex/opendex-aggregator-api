from dataclasses import dataclass

from typing_extensions import override

from opendex_aggregator_api.pools.pools import ConstantPricePool


@dataclass
class XoxnoConstantPricePool(ConstantPricePool):

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
