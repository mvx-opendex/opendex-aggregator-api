from typing import List
from .curve import D, y
import pytest


@pytest.mark.parametrize('amp,amounts,expected', [
    (256, [1_000, 1_000], 2_000),
    (256, [514670_000000, 392640_000000, 495630_000000], 1402901591583),
])
def test_curve_D(amp: int, amounts: List[int], expected: int):
    assert D(amp, amounts) == expected


@pytest.mark.parametrize('amp,amounts,i_token_in,i_token_out,token_in_balance,expected', [
    (256, [1_000, 1_000], 0, 1, 500, 1_502),
    (256,
     [514670_000000, 392640_000000, 495630_000000],
     1, 2, 1_000000, 19499782829474),
])
def test_curve_y(amp: int, amounts: List[int], i_token_in: int, i_token_out: int, token_in_balance: int, expected: int):
    assert y(amp,
             amounts,
             i_token_in,
             i_token_out,
             token_in_balance) == expected
