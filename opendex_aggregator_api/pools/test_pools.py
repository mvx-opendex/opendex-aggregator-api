
from typing import List

import pytest

from opendex_aggregator_api.data.model import Esdt

from .pools import ConstantPricePool, ConstantProductPool, StableSwapPool

TOKEN_IN = Esdt(decimals=18,
                identifier='IN-000000',
                ticker='IN',
                name='IN',
                is_lp_token=False,
                exchange='x')
TOKEN_OUT = Esdt(decimals=18,
                 identifier='OUT-000000',
                 ticker='OUT',
                 name='OUT',
                 is_lp_token=False,
                 exchange='x')
BUSD = Esdt(decimals=18,
            identifier='BUSD-000000',
            ticker='BUSD',
            name='BUSD',
            is_lp_token=False,
            exchange='x')
USDC = Esdt(decimals=6,
            identifier='USDC-000000',
            ticker='USDC',
            name='USDC',
            is_lp_token=False,
            exchange='x')
USDT = Esdt(decimals=6,
            identifier='USDT-000000',
            ticker='USDT',
            name='USDT',
            is_lp_token=False,
            exchange='x')
SEGLD = Esdt(decimals=18,
             identifier='SEGLD-000000',
             ticker='SEGLD',
             name='SEGLD',
             is_lp_token=False,
             exchange='x')
WEGLD = Esdt(decimals=18,
             identifier='WEGLD-000000',
             ticker='WEGLD',
             name='WEGLD',
             is_lp_token=False,
             exchange='x')
LP_TOKEN = Esdt(decimals=18,
                identifier='LPTOKEN-000000',
                ticker='LPTOKEN',
                name='LPTOKEN',
                is_lp_token=True,
                exchange='exchange')


@pytest.mark.parametrize('price,reserve,amount_in,expected', [
    (10**18, 1000, 1, 1),
    (0.5*10**18, 1000, 10, 20)
])
def test_ConstantPricePool_estimate_amount_out(price: int, reserve: int, amount_in: int, expected: int):
    pool = ConstantPricePool(price, TOKEN_IN, TOKEN_OUT, reserve)

    net_amount_out, _, _ = pool.estimate_amount_out(
        TOKEN_IN, amount_in, TOKEN_OUT)

    assert net_amount_out == expected

    assert pool.estimate_theorical_amount_out(TOKEN_IN,
                                              amount_in,
                                              TOKEN_OUT) == expected


@pytest.mark.parametrize('reserves,amount_in,expected', [
    ([1000_000000000000000000, 1000_000000], 10_000000000000000000, 9_900990)
])
def test_ConstantProductPool_estimate_amount_out(reserves: List[int], amount_in: int, expected: int):
    first_token = TOKEN_IN
    second_token = TOKEN_OUT

    pool = ConstantProductPool(
        max_fee=10_000,
        total_fee=0,
        first_token=first_token,
        first_token_reserves=reserves[0],
        lp_token=LP_TOKEN,
        lp_token_supply=999,
        second_token=second_token,
        second_token_reserves=reserves[1])

    net_amount_out, _, _ = pool.estimate_amount_out(
        first_token, amount_in, second_token)

    assert net_amount_out == expected


@pytest.mark.parametrize('reserves,net_amount_out,expected', [
    ([1000_000000000000000000, 1000_000000], 9_900990, 9_999999899000000011)
])
def test_ConstantProductPool_estimate_amount_in(reserves: List[int], net_amount_out: int, expected: int):
    first_token = TOKEN_IN
    second_token = TOKEN_OUT

    pool = ConstantProductPool(
        max_fee=10_000,
        total_fee=0,
        first_token=first_token,
        first_token_reserves=reserves[0],
        lp_token=LP_TOKEN,
        lp_token_supply=999,
        second_token=second_token,
        second_token_reserves=reserves[1])

    amount_in, _, _ = pool.estimate_amount_in(
        second_token, net_amount_out, first_token)

    assert amount_in == expected


@pytest.mark.parametrize('reserves,amount_in,expected', [
    ([1000_000000000000000000, 1000_000000], 10_000000000000000000, 10_000000)
])
def test_ConstantProductPool_estimate_theorical_amount_out(reserves: List[int], amount_in: int, expected: int):
    first_token = TOKEN_IN
    second_token = TOKEN_OUT

    pool = ConstantProductPool(
        max_fee=10_000,
        total_fee=0,
        first_token=first_token,
        first_token_reserves=reserves[0],
        lp_token=LP_TOKEN,
        lp_token_supply=999,
        second_token=second_token,
        second_token_reserves=reserves[1])

    assert pool.estimate_theorical_amount_out(
        first_token, amount_in, second_token) == expected


@pytest.mark.parametrize('reserves,underlying_prices,token_in_identifier,amount_in,token_out_identifier,expected', [
    ([466_060_000000000000000000, 518_355_000000, 428_216_000000],
     [10**18, 10**18, 10**18],
     BUSD.identifier, 100000_000000000000000000,
     USDC.identifier, 99962_775195)
])
def test_StableSwapPool_estimate_amount_out(reserves: List[int],
                                            underlying_prices: List[int],
                                            token_in_identifier: str,
                                            amount_in: int,
                                            token_out_identifier: str,
                                            expected: int):
    tokens = [BUSD, USDC, USDT]

    token_in = filter(lambda x: x.identifier ==
                      token_in_identifier, tokens).__next__()
    token_out = filter(lambda x: x.identifier ==
                       token_out_identifier, tokens).__next__()

    pool = StableSwapPool(amp_factor=256,
                          swap_fee=0,
                          max_fee=1_000_000,
                          tokens=tokens,
                          reserves=reserves,
                          underlying_prices=underlying_prices,
                          lp_token=LP_TOKEN,
                          lp_token_supply=0)

    net_amount_out, _, _ = pool.estimate_amount_out(
        token_in, amount_in, token_out)

    assert net_amount_out == expected


@pytest.mark.parametrize('reserves,token_in_identifier,amount_in,token_out_identifier,expected', [
    ([466_060_000000000000000000, 518_355_000000, 428_216_000000],
     BUSD.identifier, 100000_000000000000000000,
     USDC.identifier, 100000_000000)
])
def test_StableSwapPool_estimate_theorical_amount_out(reserves: List[int],
                                                      token_in_identifier: str,
                                                      amount_in: int,
                                                      token_out_identifier: str,
                                                      expected: int):
    tokens = [BUSD, USDC, USDT]

    token_in = filter(lambda x: x.identifier ==
                      token_in_identifier, tokens).__next__()
    token_out = filter(lambda x: x.identifier ==
                       token_out_identifier, tokens).__next__()

    pool = StableSwapPool(amp_factor=256,
                          swap_fee=0,
                          max_fee=1_000_000,
                          tokens=tokens,
                          reserves=reserves,
                          underlying_prices=[10**18]*len(tokens),
                          lp_token=LP_TOKEN,
                          lp_token_supply=0)

    assert pool.estimate_theorical_amount_out(
        token_in, amount_in, token_out) == expected


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

    token_in = WEGLD
    token_out = SEGLD

    pool = StableSwapPool(amp_factor=256,
                          swap_fee=0,
                          max_fee=1_000_000,
                          tokens=[SEGLD, WEGLD],
                          reserves=reserves,
                          underlying_prices=underlying_prices,
                          lp_token=LP_TOKEN,
                          lp_token_supply=0)

    net_amount_out, _, _ = pool.estimate_amount_out(
        token_in, amount_in, token_out)

    assert net_amount_out == expected


@pytest.mark.parametrize('reserves,underlying_prices,amount_in,expected', [
    ([34_757_243263043583945104, 15_347_185452846389893231],
     [1200000000000000000, 1000000000000000000],
     5000_000000000000000000, 4166_666666666666666666)
])
def test_StableSwapPool_estimate_theorical_amount_out_with_underlying_prices(
        reserves: List[int],
        underlying_prices: List[int],
        amount_in: int,
        expected: int):

    token_in = WEGLD
    token_out = SEGLD

    pool = StableSwapPool(amp_factor=256,
                          swap_fee=0,
                          max_fee=1_000_000,
                          tokens=[SEGLD, WEGLD],
                          reserves=reserves,
                          underlying_prices=underlying_prices,
                          lp_token=LP_TOKEN,
                          lp_token_supply=0)

    assert pool.estimate_theorical_amount_out(token_in,
                                              amount_in,
                                              token_out) == expected
