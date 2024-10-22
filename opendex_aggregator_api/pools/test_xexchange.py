from typing import List

import pytest

from opendex_aggregator_api.data.model import Esdt

from .xexchange import MAX_FEE, XExchangeConstantProductPool

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
    ([30_000_000000000000000000, 3_000000000000000000],
     10000_000000000000000000, 747183979974968710)
])
def test_estimate_amount_out(reserves: List[int], amount_in: int, expected: int):
    first_token = TOKEN_IN
    second_token = TOKEN_OUT

    pool = XExchangeConstantProductPool(
        first_token=first_token,
        first_token_reserves=reserves[0],
        lp_token_supply=999,
        second_token=second_token,
        second_token_reserves=reserves[1],
        special_fee=200,
        total_fee=500)

    net_amount_out, special_fee_in, special_fee_out = pool.estimate_amount_out(
        first_token, amount_in, second_token)

    assert net_amount_out == expected
    assert special_fee_in == 20_000000000000000000
    assert special_fee_out == 0


@pytest.mark.parametrize('reserves,net_amount_out,expected', [
    ([30_000_000000000000000000, 3_000000000000000000],
     747183979974968710, 9999_999999999999984162)
])
def test_estimate_amount_in(reserves: List[int], net_amount_out: int, expected: int):
    first_token = TOKEN_IN
    second_token = TOKEN_OUT

    pool = XExchangeConstantProductPool(
        first_token=first_token,
        first_token_reserves=reserves[0],
        lp_token_supply=999,
        second_token=second_token,
        second_token_reserves=reserves[1],
        special_fee=200,
        total_fee=500)

    amount_in, special_fee_in, special_fee_out = pool.estimate_amount_in(
        second_token, net_amount_out, first_token)

    special_fee_in = amount_in * 200 // MAX_FEE

    assert amount_in == expected
    assert special_fee_in == 19_999999999999999968
    assert special_fee_out == 0
