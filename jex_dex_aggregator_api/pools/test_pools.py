
from typing import List

import pytest

from jex_dex_aggregator_api.data.model import Esdt

from .pools import ConstantPricePool, ConstantProductPool, StableSwapPool


@pytest.mark.parametrize('price,reserve,amount_in,expected', [
    (10**18, 1000, 1, 1),
    (0.5*10**18, 1000, 10, 20)
])
def test_ConstantPricePool_estimate_amount_out(price: int, reserve: int, amount_in: int, expected: int):
    token_in = Esdt(decimals=18,
                    identifier='IN-000000',
                    name='IN',
                    is_lp_token=False)
    token_out = Esdt(decimals=18,
                     identifier='OUT-000000',
                     name='OUT',
                     is_lp_token=False)

    pool = ConstantPricePool(price, token_in, token_out, reserve)

    assert pool.estimate_amount_out(token_in, amount_in, token_out) == expected


@pytest.mark.parametrize('reserves,amount_in,expected', [
    ([1000_000000000000000000, 1000_000000], 10_000000000000000000, 9_900990)
])
def test_ConstantProductPool_estimate_amount_out(reserves: List[int], amount_in: int, expected: int):
    first_token = Esdt(decimals=18,
                       identifier='IN-000000',
                       name='IN',
                       is_lp_token=False)
    second_token = Esdt(decimals=6,
                        identifier='OUT-000000',
                        name='OUT',
                        is_lp_token=False)

    pool = ConstantProductPool(
        fees_percent_base_pts=0,
        first_token=first_token,
        first_token_reserves=reserves[0],
        lp_token_supply=999,
        second_token=second_token,
        second_token_reserves=reserves[1])

    assert pool.estimate_amount_out(
        first_token, amount_in, second_token) == expected


@pytest.mark.parametrize('reserves,underlying_prices,token_in_identifier,amount_in,token_out_identifier,expected', [
    ([466_060_000000000000000000, 518_355_000000, 428_216_000000], [10**18, 10**18, 10**18],
     'BUSD-40b57e', 100000_000000000000000000, 'USDC-c76f1f', 99962_775195)
])
def test_StableSwapPool_estimate_amount_out(reserves: List[int],
                                            underlying_prices: List[int],
                                            token_in_identifier: str,
                                            amount_in: int,
                                            token_out_identifier: str,
                                            expected: int):
    busd = Esdt(decimals=18,
                identifier='BUSD-40b57e',
                name='BUSD',
                is_lp_token=False)
    usdc = Esdt(decimals=6,
                identifier='USDC-c76f1f',
                name='USDC',
                is_lp_token=False)
    usdt = Esdt(decimals=6,
                identifier='USDT-f8c08c',
                name='USDT',
                is_lp_token=False)
    tokens = [busd, usdc, usdt]

    token_in = filter(lambda x: x.identifier ==
                      token_in_identifier, tokens).__next__()
    token_out = filter(lambda x: x.identifier ==
                       token_out_identifier, tokens).__next__()

    pool = StableSwapPool(amp_factor=256, fees_percent_base_pts=0, tokens=tokens,
                          reserves=reserves, underlying_prices=underlying_prices, lp_token_supply=0)

    assert pool.estimate_amount_out(token_in, amount_in, token_out) == expected


@pytest.mark.parametrize('reserves,underlying_prices,amount_in,expected', [
    ([34_757_243263043583945104, 15_347_185452846389893231],
     [1013470148086771241, 1000000000000000000],
     5000_000000000000000000, 4947_425727157696845099)
])
def test_StableSwapPool_estimate_amount_out_with_underlying_prices(
        reserves: List[int],
        underlying_prices: List[int],
        amount_in: int,
        expected: int):
    segld = Esdt(decimals=18,
                 identifier='SEGLD-000000',
                 name='SEGLD',
                 is_lp_token=False)
    wegld = Esdt(decimals=18,
                 identifier='WEGLD-000000',
                 name='WEGLD',
                 is_lp_token=False)

    token_in = wegld
    token_out = segld

    pool = StableSwapPool(amp_factor=256, fees_percent_base_pts=0, tokens=[segld, wegld],
                          reserves=reserves, underlying_prices=underlying_prices, lp_token_supply=0)

    assert pool.estimate_amount_out(token_in, amount_in, token_out) == expected
