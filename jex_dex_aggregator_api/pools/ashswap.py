
from functools import reduce
from typing import List

A_MULTIPLIER = 10_000
MIN_GAMMA = 10**10
MAX_GAMMA = 2*(10**16)
PRECISION = 10**18

MAX_ITERATIONS = 255


class DidNotConvergeException(Exception):
    pass


def geometric_mean(unsorted_x: List[int]):
    n_coins = len(unsorted_x)
    x = unsorted_x.copy()

    d = x[0]
    diff = 0
    for _ in range(MAX_ITERATIONS):
        d_prev = d
        tmp = 10**18
        for _x in x:
            tmp = (tmp * _x) // d
        d = (d * (n_coins - 1) * (10**18) + tmp) // (n_coins * 10**18)
        diff = abs(d - d_prev)
        if diff <= 1 or diff * (10**18) < d:
            return d
    raise DidNotConvergeException("Did not converge")


def newton_d(ann: int, gamma: int, x_unsorted: List[int], reserves: List[int]):
    n_coins = len(reserves)

    min_a = (n_coins**n_coins * A_MULTIPLIER) // 10
    max_a = n_coins**n_coins * A_MULTIPLIER * 10_000

    assert ann > (min_a - 1) and ann < (max_a + 1), "invalid ann"
    assert gamma > (MIN_GAMMA - 1) and gamma < (MAX_GAMMA + 1), "invalid gamma"

    x = sorted(x_unsorted)

    assert x[0] > (1e9 - 1) and x[0] < (1e33) + 1, "invalid x0"
    assert ((x[1] * 1e18) // x[0]) > 1e14 - 1, "invalid x1"

    d = geometric_mean(x) * n_coins
    s = sum(x)

    for _ in range(MAX_ITERATIONS):
        d_prev = d
        k0 = (x[0] * PRECISION * n_coins**n_coins * x[1]) // d**2

        g1k0 = gamma + PRECISION
        g1k0 = abs(k0 - g1k0) + 1

        mul1 = d * PRECISION * g1k0**2 * A_MULTIPLIER // (gamma**2 * ann)
        mul2 = (PRECISION * 2 * n_coins * k0) // g1k0

        neg_fprime = s + ((s * mul2) // PRECISION) + \
            ((mul1 * n_coins) // k0) - ((mul2 * d) // PRECISION)

        d_plus = (d * (neg_fprime + s)) // neg_fprime
        d_minus = d**2 // neg_fprime

        if PRECISION > k0:
            d_minus += (((d * (mul1 // neg_fprime)) // PRECISION)
                        * (PRECISION - k0)) // k0
        else:
            d_minus -= (((d * (mul1 // neg_fprime)) // PRECISION)
                        * (k0-PRECISION)) // k0

        if d_plus > d_minus:
            d = d_plus - d_minus
        else:
            d = (d_minus - d_plus) // 2

        diff = abs(d - d_prev)

        max_d = max(d, 1e16)

        if (diff * 10**14) < max_d:
            for _x in x:
                frac = (_x * PRECISION) // d
                assert frac > (1e16 - 1) and frac < (1e20) + 1, "unsafe value"
            return d
    raise DidNotConvergeException("Did not converge")


def newton_y(ann: int, gamma: int, x: List[int], d: int, i: int, reserves: List[int]) -> int:
    n_coins = len(reserves)

    min_a = (n_coins**n_coins * A_MULTIPLIER) // 10
    max_a = n_coins**n_coins * A_MULTIPLIER * 10_000

    assert ann > (min_a - 1) and ann < (max_a + 1), "Unsafe value A"
    assert gamma > (MIN_GAMMA - 1) and gamma < (MAX_GAMMA +
                                                1), "Unsafe value gamma"
    assert d > (10**17 - 1) and d < (1e33 + 1), "invalid d"

    for k in range(n_coins):
        if k != i:
            frac = (x[k] * 10**18) // d
            assert frac > (10**16 - 1) and frac < (10**20 - 1)

    x_j = x[1-i]
    y = d**2 // (x_j * n_coins**2)
    k0_i = (x_j * PRECISION * n_coins) // d
    assert k0_i > ((n_coins * 1e16) - 1) \
        and k0_i < ((n_coins * 1e20) + 1), "unsafe value"

    convergence_limit = max(x_j // 1e14, d // 1e14, 100)

    for _ in range(MAX_ITERATIONS):
        y_prev = y
        k0 = (k0_i * y * n_coins) // d
        s = x_j + y

        _g1k0 = gamma + 1e18
        _g1k0 = abs(k0 - _g1k0) + 1

        mul1 = ((((((d * PRECISION) // gamma) * _g1k0) // gamma)
                * _g1k0) * A_MULTIPLIER) // ann

        mul2 = ((k0 * 2 * PRECISION) // _g1k0) + PRECISION

        yfprime = (y * PRECISION) + (s * mul2) + mul1
        _dyfprime = d * mul2

        if yfprime < _dyfprime:
            y = y_prev // 2
            continue
        else:
            yfprime = yfprime - _dyfprime

        fprime = yfprime // y

        y_minus = mul1 // fprime
        y_plus = (((d * PRECISION) + yfprime) // fprime) + \
            ((y_minus * PRECISION) // k0)
        y_minus = y_minus + ((s * PRECISION) // fprime)

        if y_plus < y_minus:
            y = y_prev // 2
        else:
            y = y_plus - y_minus

        diff = abs(y - y_prev)

        if diff < max(convergence_limit, y // 1e14):
            frac = (y * PRECISION) // d
            assert frac > (1e16 - 1) \
                and frac < (1e20 + 1), "Unsafe value for y"
            return y

    raise DidNotConvergeException("Did not converge")
