from typing import List
import pytest

from opendex_aggregator_api.data.model import Esdt
from opendex_aggregator_api.pools.ashswap import AshSwapPoolV2

TOKEN_IN = Esdt(decimals=6,
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


@pytest.mark.parametrize('reserves,xp,amount_in,expected_amount_out,expected_admin_fee', [
    ([6610310763, 10775028285126628963544615],
     [6610310763000000000000, 8175014856796592762449],
     100_000000, 158153_183456644670162885, 208_848375516246118801)
])
def test_AshSwapPoolV2_estimate_amount_out(reserves: List[int],
                                           xp: List[int],
                                           amount_in: int,
                                           expected_amount_out: int,
                                           expected_admin_fee: int):
    first_token = TOKEN_IN
    second_token = TOKEN_OUT

    pool = AshSwapPoolV2(
        amp=400000,
        d=14713381882176947720176,
        fee_gamma=230000000000000,
        future_a_gamma_time=0,
        gamma=145000000000000,
        mid_fee=20000000,
        out_fee=40000000,
        price_scale=758700083236071,
        reserves=reserves,
        tokens=[TOKEN_IN, TOKEN_OUT],
        xp=xp,
        lp_token=None,
        lp_token_supply=0
    )

    net_amount_out, admin_fee_in, admin_fee_out = pool.estimate_amount_out(
        first_token, amount_in, second_token)

    assert net_amount_out == expected_amount_out
    assert admin_fee_in == 0
    assert admin_fee_out == expected_admin_fee
