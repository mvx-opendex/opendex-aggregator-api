
from typing import List
import pytest

from opendex_aggregator_api.data.model import Esdt
from opendex_aggregator_api.pools.pools import StableSwapPool
from .jexchange import MAX_FEE, JexConstantProductPool, JexStableSwapPool

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
WDAI = Esdt(decimals=18,
            identifier='WDAI-000000',
            ticker='WDAI',
            name='WDAI',
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
JWLUSD = Esdt(decimals=18,
              identifier='JWLUSD-000000',
              ticker='JWLUSD',
              name='JWLUSD',
              is_lp_token=False,
              exchange='x')


@pytest.mark.parametrize('reserves,amount_in,expected', [
    ([30_000_000000000000000000, 3_000000000000000000],
     10000_000000000000000000, 744750000000000000)
])
def test_JexConstantProductPool_estimate_amount_out(reserves: List[int], amount_in: int, expected: int):
    first_token = TOKEN_IN
    second_token = TOKEN_OUT

    pool = JexConstantProductPool(
        first_token=first_token,
        first_token_reserves=reserves[0],
        lp_token_supply=999,
        second_token=second_token,
        second_token_reserves=reserves[1],
        platform_fee=20,
        lp_fee=50)

    net_amount_out, admin_fee_in, admin_fee_out = pool.estimate_amount_out(
        first_token, amount_in, second_token)

    assert net_amount_out == expected
    assert admin_fee_in == 0
    assert admin_fee_out == 1500000000000000


@pytest.mark.parametrize('reserves,net_amount_out,expected', [
    ([561_977377857549639494, 7566136_604933995627688221],
     10000_000000000000000000, 746727254314357719)
])
def test_JexConstantProductPool_estimate_amount_in(reserves: List[int], net_amount_out: int, expected: int):
    pool = JexConstantProductPool(
        first_token=TOKEN_IN,
        first_token_reserves=reserves[0],
        lp_token_supply=999,
        second_token=TOKEN_OUT,
        second_token_reserves=reserves[1],
        platform_fee=20,
        lp_fee=20)

    amount_in, admin_fee_in, admin_fee_out = pool.estimate_amount_in(
        TOKEN_OUT, net_amount_out, TOKEN_IN)

    amount_out = (net_amount_out * MAX_FEE) // (MAX_FEE - 40)
    expected_admin_fee_out = amount_out * 20 // MAX_FEE

    assert amount_in == expected
    assert admin_fee_in == 0
    assert admin_fee_out == expected_admin_fee_out


@pytest.mark.parametrize('reserves,token_in_identifier,amount_in,token_out_identifier,expected', [
    ([18_435_214786690045997381, 17_800_343931, 80_002_467145381198156678],
     WDAI.identifier, 5000_000000000000000000,
     USDT.identifier, 4967_081132)
])
def test_JexStableSwapPool_estimate_amount_out(reserves: List[int],
                                               token_in_identifier: str,
                                               amount_in: int,
                                               token_out_identifier: str,
                                               expected: int):

    tokens = [WDAI, USDT, JWLUSD]

    token_in = next((x for x in tokens
                     if x.identifier == token_in_identifier))
    token_out = next((x for x in tokens
                      if x.identifier == token_out_identifier))

    underlying_prices = [10**18] * len(tokens)

    pool = JexStableSwapPool(amp_factor=256,
                             swap_fee=500,
                             tokens=tokens,
                             reserves=reserves,
                             underlying_prices=underlying_prices,
                             lp_token_supply=0)

    net_amount_out, _, _ = pool.estimate_amount_out(
        token_in, amount_in, token_out)

    assert net_amount_out == expected


@pytest.mark.parametrize('reserves,token_in_identifier,amount_in,token_out_identifier,expected', [
    ([411_423_569165, 300_289_266690],
     USDC.identifier, 50_000_000000,
     USDT.identifier, 50_009246733)
])
def test_JexStableSwapPool_estimate_amount_out2(reserves: List[int],
                                                token_in_identifier: str,
                                                amount_in: int,
                                                token_out_identifier: str,
                                                expected: int):
    tokens = [USDT, USDC]

    token_in = next((x for x in tokens
                     if x.identifier == token_in_identifier))
    token_out = next((x for x in tokens
                      if x.identifier == token_out_identifier))

    underlying_prices = [10**18] * len(tokens)

    pool = JexStableSwapPool(amp_factor=256,
                             swap_fee=500,
                             tokens=tokens,
                             reserves=reserves,
                             underlying_prices=underlying_prices,
                             lp_token_supply=0)

    net_amount_out, _, _ = pool.estimate_amount_out(
        token_in, amount_in, token_out)

    assert net_amount_out == expected
