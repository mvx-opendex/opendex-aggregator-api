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
    ([21890732963734405102, 2171502946503654878463],
     10000000000000000, 988547464092440366)
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
        special_fee=100,
        total_fee=300)

    net_amount_out, special_fee_in, special_fee_out = pool.estimate_amount_out(
        first_token, amount_in, second_token)

    expected_special_fee_in = amount_in * 100 // MAX_FEE

    assert net_amount_out == expected
    assert special_fee_in == expected_special_fee_in
    assert special_fee_out == 0


@pytest.mark.parametrize('reserves,net_amount_out,expected', [
    ([2171502946503654878463, 21890732963734405102],
     10000000000000000, 995413207266232876)
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
        special_fee=100,
        total_fee=300)

    amount_in, special_fee_in, special_fee_out = pool.estimate_amount_in(
        second_token, net_amount_out, first_token)

    expected_special_fee_in = amount_in * 100 // MAX_FEE

    assert amount_in == expected
    assert special_fee_in == expected_special_fee_in
    assert special_fee_out == 0
