
import pytest

from opendex_aggregator_api.data.model import Esdt

from .vestadex import VestaDexConstantProductPool

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


@pytest.mark.parametrize('reserves,amount_in,expected', [
    ([3_343_668833240686226569, 1_289_058_540919326440545772],
     10_000000000000000000, 3652_084564706615454872)])
def test_VestaDexConstantProductPool_estimate_amount_out(reserves, amount_in, expected):

    pool = VestaDexConstantProductPool(first_token=OURO,
                                       first_token_reserves=reserves[0],
                                       lp_token_supply=0,
                                       second_token=XLH,
                                       second_token_reserves=reserves[1],
                                       special_fee=42500,
                                       total_fee=50000,
                                       fee_token=OURO)

    net_amount_out, special_fee_in, special_fee_out = pool.estimate_amount_out(token_in=OURO,
                                                                               amount_in=amount_in,
                                                                               token_out=XLH)

    assert net_amount_out == expected
    assert special_fee_out == 0
    assert special_fee_in == 425000000000000000
