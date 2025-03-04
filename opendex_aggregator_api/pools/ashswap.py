
from dataclasses import dataclass
from typing import List, Tuple

from typing_extensions import override

from opendex_aggregator_api.data.model import Esdt
from opendex_aggregator_api.pools.pools import ConstantProductPool, StableSwapPool, find

A_MULTIPLIER = 10_000
MIN_GAMMA = 10**10
MAX_GAMMA = 2*(10**16)
PRECISION = 10**18

MAX_ITERATIONS = 255


@dataclass
class AshSwapPoolV2(ConstantProductPool):

    PRECISION = 10**18

    amp: int
    d: int
    fee_gamma: int
    future_a_gamma_time: int
    gamma: int
    mid_fee: int
    out_fee: int
    price_scale: int
    reserves: List[int]
    tokens: List[Esdt]
    xp: List[int]

    def __init__(self,
                 amp: int,
                 d: int,
                 fee_gamma: int,
                 future_a_gamma_time: int,
                 gamma: int,
                 mid_fee: int,
                 out_fee: int,
                 price_scale: int,
                 reserves: List[int],
                 tokens: List[Esdt],
                 xp: List[int],
                 lp_token: Esdt,
                 lp_token_supply: int):
        assert len(tokens) == 2, 'Invalid number of tokens'
        assert len(reserves) == 2, 'Invalid number of token reserves'

        super().__init__(max_fee=PRECISION,
                         first_token=tokens[0],
                         first_token_reserves=reserves[0],
                         lp_token=lp_token,
                         lp_token_supply=lp_token_supply,
                         second_token=tokens[1],
                         second_token_reserves=reserves[1],
                         total_fee=out_fee)

        self.amp = amp
        self.d = d
        self.fee_gamma = fee_gamma
        self.future_a_gamma_time = future_a_gamma_time
        self.gamma = gamma
        self.mid_fee = mid_fee
        self.out_fee = out_fee
        self.price_scale = price_scale
        self.reserves = reserves
        self.tokens = tokens
        self.xp = xp
        self.first_token = tokens[0]
        self.first_token_reserves = reserves[0]
        self.second_token = tokens[1]
        self.second_token_reserves = reserves[1]

    @override
    def deep_copy(self):
        return AshSwapPoolV2(amp=self.amp,
                             d=self.d,
                             fee_gamma=self.fee_gamma,
                             future_a_gamma_time=self.future_a_gamma_time,
                             gamma=self.gamma,
                             mid_fee=self.mid_fee,
                             out_fee=self.out_fee,
                             price_scale=self.price_scale,
                             reserves=self.reserves.copy(),
                             tokens=[t.model_copy() for t in self.tokens],
                             xp=self.xp.copy(),
                             lp_token=self.lp_token.model_copy(),
                             lp_token_supply=self.lp_token_supply)

    @override
    def estimate_amount_out(self, token_in: Esdt, amount_in: int, token_out: Esdt) -> Tuple[int, int, int]:
        """
        Return (fee, amount_out)
        """
        if amount_in == 0:
            return 0, 0, 0

        precisions: List[int] = [10**(18-t.decimals) for t in self.tokens]
        price_scale = self.price_scale * precisions[1]

        xp = self.reserves.copy()

        d = self.d

        if self.future_a_gamma_time > 0:
            d = newton_d(
                self.amp,
                self.gamma,
                self.xp.copy(),
                self.reserves
            )

        i_token_in, _ = find(lambda x: x.identifier ==
                             token_in.identifier, self.tokens)
        i_token_out, _ = find(lambda x: x.identifier ==
                              token_out.identifier, self.tokens)

        xp[i_token_in] = xp[i_token_in] + amount_in
        xp = [
            xp[0] * precisions[0],
            (xp[1] * price_scale) // self.PRECISION,
        ]

        try:
            y = newton_y(
                self.amp,
                self.gamma,
                xp,
                d,
                i_token_out,
                self.reserves
            )
        except AssertionError as e:
            raise ValueError('Error during newton_y', e)

        dy = xp[i_token_out] - y - 1
        xp[i_token_out] = y

        if i_token_out > 0:
            dy = (dy * self.PRECISION) // price_scale
        else:
            dy = dy // precisions[0]

        fee = (dy * self._fee(xp)) // 10**10

        dy = dy - fee

        return dy, 0, fee // 3

    # @override
    # def estimate_amount_in(self, token_out: Esdt, net_amount_out: int, token_in: Esdt) -> Tuple[int, int, int]:
    #     raise NotImplementedError()

    @override
    def estimated_gas(self) -> int:
        return 30_000_000

    @override
    def estimate_theorical_amount_out(self, token_in: Esdt, amount_in: int, token_out: Esdt) -> int:
        i_token_in, _ = find(lambda x: x.identifier ==
                             token_in.identifier, self.tokens)
        i_token_out, _ = find(lambda x: x.identifier ==
                              token_out.identifier, self.tokens)

        in_reserve = self.reserves[i_token_in]
        out_reserve = self.reserves[i_token_out]

        amount_out = (amount_in * out_reserve) // in_reserve

        fee = (amount_out * self._fee(self.xp)) // 10**10

        amount_out -= fee

        return amount_out

    @override
    def update_reserves(self,
                        token_in: Esdt,
                        amount_in: int,
                        token_out: Esdt,
                        amount_out: int):

        i_token_in, _ = find(lambda x: x.identifier ==
                             token_in.identifier, self.tokens)
        i_token_out, _ = find(lambda x: x.identifier ==
                              token_out.identifier, self.tokens)

        self.reserves[i_token_in] += amount_in
        self.reserves[i_token_out] -= amount_out

    def _fee(self, xp: List[int]) -> int:
        n_coins = len(self.tokens)

        f = xp[0] + xp[1]

        f_num = self.fee_gamma * self.PRECISION

        f_den = int(self.fee_gamma + self.PRECISION -
                    (n_coins**n_coins * self.PRECISION * xp[0] // f * xp[1] // f))

        f = f_num // f_den

        f = (self.mid_fee * f) + (self.out_fee * (self.PRECISION-f))

        f = f // self.PRECISION

        return f

    @override
    def _source(self) -> str:
        return 'ashswap'

    def __str__(self) -> str:
        return f'AshSwapPoolV2({self.first_token_reserves/10**self.first_token.decimals:.4f} \
 {self.first_token.identifier} + \
 {self.second_token_reserves/10**self.second_token.decimals:.4f} \
 {self.second_token.identifier})'


@dataclass
class AshSwapStableSwapPool(StableSwapPool):
    def __init__(self,
                 amp_factor: int,
                 swap_fee: int,
                 tokens: List[Esdt],
                 reserves: List[int],
                 underlying_prices: List[int],
                 lp_token: Esdt,
                 lp_token_supply: int):
        super().__init__(amp_factor=amp_factor,
                         swap_fee=swap_fee,
                         max_fee=100_000,
                         tokens=tokens,
                         reserves=reserves,
                         underlying_prices=underlying_prices,
                         lp_token=lp_token,
                         lp_token_supply=lp_token_supply)

    @override
    def deep_copy(self):
        return AshSwapStableSwapPool(amp_factor=self.amp_factor,
                                     swap_fee=self.swap_fee,
                                     tokens=[t.model_copy()
                                             for t in self.tokens],
                                     lp_token=self.lp_token.model_copy(),
                                     lp_token_supply=self.lp_token_supply,
                                     reserves=self.reserves.copy(),
                                     underlying_prices=self.underlying_prices.copy())

    @override
    def estimated_gas(self) -> int:
        return 30_000_000

    @override
    def _source(self) -> str:
        return 'ashswap'


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

    assert x[0] > (10**9 - 1) and x[0] < (10**33) + 1, "invalid x0"
    assert ((x[1] * 10**18) // x[0]) > 10**14 - 1, "invalid x1"

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

        max_d = max(d, 10**16)

        if (diff * 10**14) < max_d:
            for _x in x:
                frac = (_x * PRECISION) // d
                assert frac > (10**16 - 1) and frac < (10 **
                                                       20) + 1, "unsafe value"
            return d
    raise DidNotConvergeException("Did not converge")


def newton_y(ann: int, gamma: int, x: List[int], d: int, i: int, reserves: List[int]) -> int:
    n_coins = len(reserves)

    min_a = (n_coins**n_coins * A_MULTIPLIER) // 10
    max_a = n_coins**n_coins * A_MULTIPLIER * 10_000

    assert ann > (min_a - 1) and ann < (max_a + 1), "Unsafe value A"
    assert gamma > (MIN_GAMMA - 1) and gamma < (MAX_GAMMA +
                                                1), "Unsafe value gamma"
    assert d > (10**17 - 1) and d < (10**33 + 1), "invalid d"

    for k in range(n_coins):
        if k != i:
            frac = (x[k] * 10**18) // d
            assert frac > (10**16 - 1) and frac < (10**20 - 1)

    x_j = x[1-i]
    y = d**2 // (x_j * n_coins**2)
    k0_i = (x_j * PRECISION * n_coins) // d
    assert k0_i > ((n_coins * 10**16) - 1) \
        and k0_i < ((n_coins * 10**20) + 1), "unsafe value"

    convergence_limit = max(x_j // 10**14, d // 10**14, 100)

    for _ in range(MAX_ITERATIONS):
        y_prev = y
        k0 = (k0_i * y * n_coins) // d
        s = x_j + y

        _g1k0 = gamma + 10**18
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

        if diff < max(convergence_limit, y // 10**14):
            frac = (y * PRECISION) // d
            assert frac > (10**16 - 1) \
                and frac < (10**20 + 1), "Unsafe value for y"
            return y

    raise DidNotConvergeException("Did not converge")
