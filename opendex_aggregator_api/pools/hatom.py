

from dataclasses import dataclass

from typing_extensions import override

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
    def _source(self):
        return 'hatom'
