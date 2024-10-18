
from typing import List

import pytest

from opendex_aggregator_api.data.model import Esdt

from .opendex import OpendexConstantProductPool


@pytest.mark.parametrize('reserves,amount_in,expected', [
    ([10000_000000000000000000, 200_000000000000000000],
     100_000000000000000000, 1_972277227722772278)
])
def test_OpendexConstantProductPool_estimate_amount_out(reserves: List[int], amount_in: int, expected: int):
    first_token = Esdt(decimals=18,
                       identifier='IN-000000',
                       ticker='IN',
                       name='IN',
                       is_lp_token=False,
                       exchange='x')
    second_token = Esdt(decimals=18,
                        identifier='OUT-000000',
                        ticker='OUT',
                        name='OUT',
                        is_lp_token=False,
                        exchange='x')

    pool = OpendexConstantProductPool(first_token=first_token,
                                      first_token_reserves=reserves[0],
                                      lp_token_supply=999,
                                      second_token=second_token,
                                      second_token_reserves=reserves[1],
                                      total_fee=40,
                                      platform_fee=10,
                                      fee_token=second_token)

    net_amount_out, _, _ = pool.estimate_amount_out(
        first_token, amount_in, second_token)

    assert net_amount_out == expected


@pytest.mark.parametrize('reserves,amount_in,expected', [
    ([10000_000000000000000000, 200_000000000000000000],
     1_000000000000000000, 49_553224939799797010)
])
def test_OpendexConstantProductPool_estimate_amount_out_fee_in(reserves: List[int],
                                                               amount_in: int,
                                                               expected: int):
    first_token = Esdt(decimals=18,
                       identifier='OUT-000000',
                       ticker='OUT',
                       name='OUT',
                       is_lp_token=False,
                       exchange='x')
    second_token = Esdt(decimals=18,
                        identifier='IN-000000',
                        ticker='IN',
                        name='IN',
                        is_lp_token=False,
                        exchange='x')

    pool = OpendexConstantProductPool(first_token=first_token,
                                      first_token_reserves=reserves[0],
                                      lp_token_supply=999,
                                      second_token=second_token,
                                      second_token_reserves=reserves[1],
                                      total_fee=40,
                                      platform_fee=10,
                                      fee_token=second_token)

    net_amount_out, _, _ = pool.estimate_amount_out(
        second_token, amount_in, first_token)

    assert net_amount_out == expected
