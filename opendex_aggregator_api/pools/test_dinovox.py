from typing import List

import pytest

from opendex_aggregator_api.data.model import Esdt

from .dinovox import MAX_FEE, DinoVoxConstantProductPool

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

LP_TOKEN = Esdt(decimals=18,
                identifier='LPTOKEN-000000',
                ticker='LPTOKEN',
                name='LPTOKEN',
                is_lp_token=True,
                exchange='xexchange')


@pytest.mark.parametrize('reserves,amount_in,expected', [
    ([21890732963734405102, 2171502946503654878463],
     10000000000000000, 988547464092429567)
])
def test_estimate_amount_out(reserves: List[int], amount_in: int, expected: int):
    first_token = TOKEN_IN
    second_token = TOKEN_OUT

    pool = DinoVoxConstantProductPool(
        token_a=first_token,
        token_a_reserve=reserves[0],
        lp_token=LP_TOKEN,
        lp_supply=999,
        token_b=second_token,
        token_b_reserve=reserves[1],
        fee_bps=30,
        protocol_fee=3000)

    net_amount_out, special_fee_in, special_fee_out = pool.estimate_amount_out(
        first_token, amount_in, second_token)

    assert net_amount_out == expected
    assert special_fee_in == 9000000000000
    assert special_fee_out == 0
