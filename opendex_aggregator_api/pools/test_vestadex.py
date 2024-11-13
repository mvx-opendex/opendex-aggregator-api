
import pytest

from opendex_aggregator_api.data.model import Esdt

from .vestadex import MAX_FEE, VestaDexConstantProductPool

OURO = Esdt(decimals=18,
            identifier='OURO-000000',
            name='OURO',
            ticker='OURO',
            is_lp_token=False,
            exchange='vestadex')
XLH = Esdt(decimals=18,
           identifier='XLH-000000',
           name='XLH',
           ticker='XLH',
           is_lp_token=False,
           exchange='vestadex')
LP_TOKEN = Esdt(decimals=18,
                identifier='LPTOKEN-000000',
                ticker='LPTOKEN',
                name='LPTOKEN',
                is_lp_token=True,
                exchange='vestadex')


@pytest.mark.parametrize('reserves,amount_in,expected', [
    ([3_343_668833240686226569, 1_289_058_540919326440545772],
     10_000000000000000000, 3651_540073770523597689)])
def test_VestaDexConstantProductPool_estimate_amount_out(reserves, amount_in, expected):

    pool = VestaDexConstantProductPool(first_token=OURO,
                                       first_token_reserves=reserves[0],
                                       lp_token=LP_TOKEN,
                                       lp_token_supply=0,
                                       second_token=XLH,
                                       second_token_reserves=reserves[1],
                                       special_fee=42_500,
                                       total_fee=50_000,
                                       fee_token=XLH)

    net_amount_out, special_fee_in, special_fee_out = pool.estimate_amount_out(token_in=OURO,
                                                                               amount_in=amount_in,
                                                                               token_out=XLH)

    amount_out = (net_amount_out * MAX_FEE) // (MAX_FEE - 50_000)
    expected_special_fee = amount_out * 42_500 // MAX_FEE

    assert net_amount_out == expected
    assert special_fee_in == 0
    assert special_fee_out == expected_special_fee


@pytest.mark.parametrize('reserves,amount_in,expected', [
    ([3_343_668833240686226569, 1_289_058_540919326440545772],
     10_000000000000000000, 3652_084564706615454872)])
def test_VestaDexConstantProductPool_estimate_amount_out_fee_in(reserves, amount_in, expected):

    pool = VestaDexConstantProductPool(first_token=OURO,
                                       first_token_reserves=reserves[0],
                                       lp_token=LP_TOKEN,
                                       lp_token_supply=0,
                                       second_token=XLH,
                                       second_token_reserves=reserves[1],
                                       special_fee=42_500,
                                       total_fee=50_000,
                                       fee_token=OURO)

    net_amount_out, special_fee_in, special_fee_out = pool.estimate_amount_out(token_in=OURO,
                                                                               amount_in=amount_in,
                                                                               token_out=XLH)

    expected_special_fee = amount_in * 42_500 // MAX_FEE

    assert net_amount_out == expected
    assert special_fee_in == expected_special_fee
    assert special_fee_out == 0
