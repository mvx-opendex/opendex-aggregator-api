
from typing import List

import pytest

from opendex_aggregator_api.data.model import Esdt
from opendex_aggregator_api.pools.onedex import OneDexConstantProductPool

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
LP_TOKEN = Esdt(decimals=18,
                identifier='LPTOKEN-000000',
                ticker='LPTOKEN',
                name='LPTOKEN',
                is_lp_token=True,
                exchange='opendex')


@pytest.mark.parametrize('reserves,amount_in,expected', [
    ([184287905510130, 372769587709218901080],
     10000_00000000, 1999768787729676882)
])
def test_OnedexConstantProductPool_estimate_amount_out_fee_token_out(reserves: List[int], amount_in: int, expected: int):
    first_token = TOKEN_IN
    second_token = TOKEN_OUT

    pool = OneDexConstantProductPool(first_token=first_token,
                                     first_token_reserves=reserves[0],
                                     lp_token=LP_TOKEN,
                                     lp_token_supply=999,
                                     second_token=second_token,
                                     second_token_reserves=reserves[1],
                                     total_fee=60,
                                     main_pair_tokens=[TOKEN_OUT.identifier])

    net_amount_out, platform_fee_in, platform_fee_out = pool.estimate_amount_out(
        first_token, amount_in, second_token)

    assert net_amount_out == expected
    assert platform_fee_in == 0
    assert platform_fee_out == 0


@pytest.mark.parametrize('reserves,amount_in,expected', [
    ([84200061927400138307, 311825281], 1000000000000000000, 3645449)
])
def test_OnedexConstantProductPool_estimate_amount_out_fee_token_in(reserves: List[int], amount_in: int, expected: int):
    first_token = TOKEN_IN
    second_token = TOKEN_OUT

    pool = OneDexConstantProductPool(first_token=first_token,
                                     first_token_reserves=reserves[0],
                                     lp_token=LP_TOKEN,
                                     lp_token_supply=999,
                                     second_token=second_token,
                                     second_token_reserves=reserves[1],
                                     total_fee=0,
                                     main_pair_tokens=[TOKEN_IN.identifier])

    net_amount_out, platform_fee_in, platform_fee_out = pool.estimate_amount_out(
        first_token, amount_in, second_token)

    assert net_amount_out == expected
    assert platform_fee_in == 0
    assert platform_fee_out == 0
