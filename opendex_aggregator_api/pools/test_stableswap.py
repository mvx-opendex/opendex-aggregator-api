
from typing import List
import pytest
from .stableswap import estimate_amount_out, estimate_deposit, estimate_withdraw_one_token


@pytest.mark.parametrize('reserves,underlying_prices,amount_in,expected', [
    ([1, 1], [10**18, 10**18], 0, 0),
    ([0, 1000], [10**18, 10**18], 1, 0),
    ([1000, 0], [10**18, 10**18], 1, 0),
    ([1000, 1000], [10**18, 10**18], 1, 1),
    ([1000, 1000], [10**18, 10**18], 1, 1),
    ([466_060, 518_355, 428_216], [10**18, 10**18, 10**18], 100000, 99963),
    ([15_347, 34_757], [10**18, 1_013470148086771241], 10_000, 9_884),
    ([15_347_000_000, 34_757_000_000], [
     10**18, 1_013470148086771241], 10_000_000_000, 9_884_809_278)
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
def test_estimate_deposit(reserves: List[int],
                          underlying_prices: List[int],
                          deposits: List[int],
                          lp_total_supply: int,
                          expected: int):
    assert estimate_deposit(deposits,
                            reserves,
                            underlying_prices,
                            lp_total_supply,
                            amp=256,
                            liquidity_fees=187,
                            max_fees=1_000_000) == expected


@pytest.mark.parametrize('reserves,underlying_prices,deposits,lp_total_supply,expected', [
    ([57029637408868858510691, 21177174423902697615022],
     [1054372717511654654, 10**18],
     [10_000000000000000000, 10_000000000000000000],
     78047_505004762717119399, 19_745695365935295373)
])
def test_estimate_deposit_underlying_prices(reserves: List[int], underlying_prices: List[int], deposits: List[int], lp_total_supply: int, expected: int):
    assert estimate_deposit(deposits,
                            reserves,
                            underlying_prices,
                            lp_total_supply,
                            amp=256,
                            liquidity_fees=250,
                            max_fees=1_000_000) == expected


@pytest.mark.parametrize('reserves,underlying_prices,removed_shares,lp_total_supply,expected', [
    ([50_000000000_000000000, 100_000000000_000000000],
     [2_000000000_000000000, 10**18],
     1_000000000_000000000,
     200_000000000_000000000,
     499995111_718601387)])
def test_estimate_withdraw_one_token(reserves: List[int],
                                     underlying_prices: List[int],
                                     removed_shares: int,
                                     lp_total_supply: int,
                                     expected: int):
    amount, _ = estimate_withdraw_one_token(removed_shares,
                                            i_token_out=0,
                                            amp=256,
                                            total_supply=lp_total_supply,
                                            reserves=reserves,
                                            underlying_prices=underlying_prices,
                                            liquidity_fees=0,
                                            max_fees=1_000_000)

    assert amount == expected
