
from typing import List
import pytest
from .stableswap import estimate_amount_out, estimate_deposit


@pytest.mark.parametrize('reserves,underlying_prices,amount_in,expected', [
    ([1, 1], [10**18, 10**18], 0, 0),
    ([0, 1000], [10**18, 10**18], 1, 0),
    ([1000, 0], [10**18, 10**18], 1, 0),
    ([1000, 1000], [10**18, 10**18], 1, 1),
    ([1000, 1000], [10**18, 10**18], 1, 1),
    ([466_060, 518_355, 428_216], [10**18, 10**18, 10**18], 100000, 99963),
    ([15_347, 34_757], [10**18, 1_013470148086771241], 10_000, 9_884)
])
def test_estimate_amount_out(reserves: List[int], underlying_prices: List[int], amount_in: int, expected: int):
    assert estimate_amount_out(
        256, reserves, underlying_prices, 0, amount_in, 1) == expected


@pytest.mark.parametrize('reserves,underlying_prices,deposits,lp_total_supply,expected', [
    ([514_710_000_000, 392_730_000_000, 495_510_000_000], [
     10**18]*3, [0, 100_000_000, 50_000_000], 1_398_807_409_000, 149_599_831),

    ([514_710_000_000, 392_730_000_000, 495_510_000_000], [
        10**18]*3, [1_000_000_000, 0, 0], 1_398_807_409_000, 996_446_690),

    ([514_710_000_000, 392_730_000_000, 495_510_000_000], [
        10**18]*3, [0, 0, 0], 1_398_807_409_000, 0),

    ([514_710_000_000, 392_730_000_000, 495_510_000_000], [
        10**18]*3, [0, 0, 100_000_000_000], 1_398_807_409_000, 99_635_003_939)
])
def test_estimate_deposit(reserves: List[int], underlying_prices: List[int], deposits: List[int], lp_total_supply: int, expected: int):
    assert estimate_deposit(deposits,
                            reserves,
                            underlying_prices,
                            lp_total_supply,
                            amp=256,
                            liquidity_fees_percent_base_pts=187) == expected
