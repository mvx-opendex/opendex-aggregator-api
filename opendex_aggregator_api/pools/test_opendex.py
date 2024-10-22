
from typing import List

import pytest

from opendex_aggregator_api.data.model import Esdt

from .opendex import MAX_FEE, OpendexConstantProductPool

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


@pytest.mark.parametrize('reserves,amount_in,expected', [
    ([10000_000000000000000000, 200_000000000000000000],
     100_000000000000000000, 1_972277227722772278)
])
def test_OpendexConstantProductPool_estimate_amount_out(reserves: List[int], amount_in: int, expected: int):
    first_token = TOKEN_IN
    second_token = TOKEN_OUT

    pool = OpendexConstantProductPool(first_token=first_token,
                                      first_token_reserves=reserves[0],
                                      lp_token_supply=999,
                                      second_token=second_token,
                                      second_token_reserves=reserves[1],
                                      total_fee=40,
                                      platform_fee=10,
                                      fee_token=second_token)

    net_amount_out, platform_fee_in, platform_fee_out = pool.estimate_amount_out(
        first_token, amount_in, second_token)

    amount_out = (expected * MAX_FEE) // (MAX_FEE - 40)
    expected_platform_fee = amount_out * 10 // MAX_FEE

    assert net_amount_out == expected
    assert platform_fee_in == 0
    assert platform_fee_out == expected_platform_fee


@pytest.mark.parametrize('reserves,net_amount_out,expected', [
    ([10000_000000000000000000, 200_000000000000000000],
     1_972277227722772278, 99_999999999999999999)
])
def test_OpendexConstantProductPool_estimate_amount_in(reserves: List[int], net_amount_out: int, expected: int):
    first_token = TOKEN_IN
    second_token = TOKEN_OUT

    pool = OpendexConstantProductPool(first_token=first_token,
                                      first_token_reserves=reserves[0],
                                      lp_token_supply=999,
                                      second_token=second_token,
                                      second_token_reserves=reserves[1],
                                      total_fee=40,
                                      platform_fee=10,
                                      fee_token=second_token)

    amount_in, platform_fee_in, platform_fee_out = pool.estimate_amount_in(
        second_token, net_amount_out, first_token)

    amount_out = (net_amount_out * MAX_FEE) // (MAX_FEE - 40)
    expected_platform_fee = amount_out * 10 // MAX_FEE

    assert amount_in == expected
    assert platform_fee_in == 0
    assert platform_fee_out == expected_platform_fee


@pytest.mark.parametrize('reserves,amount_in,expected', [
    ([10000_000000000000000000, 200_000000000000000000],
     1_000000000000000000, 49_553224939799797010)
])
def test_OpendexConstantProductPool_estimate_amount_out_fee_in(reserves: List[int],
                                                               amount_in: int,
                                                               expected: int):
    first_token = TOKEN_OUT
    second_token = TOKEN_IN

    pool = OpendexConstantProductPool(first_token=first_token,
                                      first_token_reserves=reserves[0],
                                      lp_token_supply=999,
                                      second_token=second_token,
                                      second_token_reserves=reserves[1],
                                      total_fee=40,
                                      platform_fee=10,
                                      fee_token=second_token)

    net_amount_out, platform_fee_in, platform_fee_out = pool.estimate_amount_out(
        second_token, amount_in, first_token)

    expected_platform_fee = amount_in * 10 // MAX_FEE

    assert net_amount_out == expected
    assert platform_fee_in == expected_platform_fee
    assert platform_fee_out == 0


@pytest.mark.parametrize('reserves,amount_out,expected', [
    ([10000_000000000000000000, 200_000000000000000000],
     49_553224939799797010, 1_000000000000000000)
])
def test_OpendexConstantProductPool_estimate_amount_in_fee_in(reserves: List[int],
                                                              amount_out: int,
                                                              expected: int):
    first_token = TOKEN_OUT
    second_token = TOKEN_IN

    pool = OpendexConstantProductPool(first_token=first_token,
                                      first_token_reserves=reserves[0],
                                      lp_token_supply=999,
                                      second_token=second_token,
                                      second_token_reserves=reserves[1],
                                      total_fee=40,
                                      platform_fee=10,
                                      fee_token=second_token)

    amount_in, platform_fee_in, platform_fee_out = pool.estimate_amount_in(
        first_token, amount_out, second_token)

    expected_platform_fee = amount_in * 10 // MAX_FEE

    assert amount_in == expected
    assert platform_fee_in == expected_platform_fee
    assert platform_fee_out == 0
