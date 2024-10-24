

from dataclasses import dataclass

from typing_extensions import override

from .pools import ConstantPricePool


@dataclass
class HatomConstantPricePool(ConstantPricePool):

    @override
    def _source(self):
        return 'hatom'
