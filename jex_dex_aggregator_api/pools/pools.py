from dataclasses import dataclass
from typing import Any, Callable, Iterable, List, Optional, Tuple

from typing_extensions import override

from jex_dex_aggregator_api.data.model import Esdt
from jex_dex_aggregator_api.pools import ashswap, stableswap


def find(function_: Callable[[Any], bool], iter_: Iterable[Any]) -> Tuple[int, Optional[Any]]:
    for i, elem in enumerate(iter_):
        if function_(elem):
            return (i, elem)
    return (-1, None)


class AbstractPool:

    def estimate_amount_out(self, token_in: Esdt, amount_in: int, token_out: Esdt) -> int:
        raise NotImplementedError()

    def estimated_gas(self) -> int:
        raise NotImplementedError()

    def estimate_theorical_amount_out(self, token_in: Esdt, amount_in: int, token_out: Esdt) -> int:
        raise NotImplementedError()

    def _normalize_amount(self, amount: int, token: Esdt) -> int:
        return (amount * 10**18) // 10**token.decimals

    def _denormalize_amount(self, amount: int, token: Esdt) -> int:
        return (amount * 10**token.decimals) // 10**18


@dataclass
class ConstantProductPool(AbstractPool):
    """
    Constant product pools (x*y=k)
    """

    fees_percent_base_pts: int
    """ Fees percent basis points (1 = 0.01%) """

    first_token: Esdt
    first_token_reserves: int
    lp_token_supply: int
    second_token: Esdt
    second_token_reserves: int

    @override
    def estimate_amount_out(self, token_in: Esdt, amount_in: int, token_out: Esdt) -> int:
        in_reserve_before, out_reserve_before = self._reserves(token_in,
                                                               token_out)

        fee = (amount_in * self.fees_percent_base_pts) // 10000

        amount_in -= fee

        amount_out = (amount_in * out_reserve_before) // \
            (in_reserve_before + amount_in)

        if amount_out > out_reserve_before:
            raise ValueError(f'Amount to swap to big {amount_in}')

        return int(amount_out)

    @override
    def estimate_theorical_amount_out(self, token_in: Esdt, amount_in: int, token_out: Esdt) -> int:
        in_reserve, out_reserve = self._reserves(token_in, token_out)

        num = amount_in * out_reserve
        den = in_reserve

        return num // den

    def estimated_gas(self) -> int:
        return 20_000_000

    def _reserves(self, token_in: Esdt, token_out: Esdt) -> Tuple[int, int]:
        if token_in.identifier == self.first_token.identifier \
                and token_out.identifier == self.second_token.identifier:
            return (self.first_token_reserves, self.second_token_reserves)

        if token_in.identifier == self.second_token.identifier \
                and token_out.identifier == self.first_token.identifier:
            return (self.second_token_reserves, self.first_token_reserves)

        raise ValueError(
            f'Invalid in/out tokens [{token_in.identifier}-{token_out.identifier}] for pool {self}')

    def __str__(self) -> str:
        return f'ConstantProductPool({self.first_token_reserves/10**self.first_token.decimals:.4f} \
 {self.first_token.identifier} + \
 {self.second_token_reserves/10**self.second_token.decimals:.4f} \
 {self.second_token.identifier} \
 fees: {self.fees_percent_base_pts / 100}%)'


@dataclass
class OneDexConstantProductPool(ConstantProductPool):
    """
    OneDex constant product pool with specific fees management.
    """

    main_pair_tokens: List[str]

    def __init__(self,
                 fees_percent_base_pts: int,
                 first_token: Esdt, first_token_reserves: int,
                 lp_token_supply: int,
                 second_token: Esdt, second_token_reserves: int,
                 main_pair_tokens: List[str]):
        super().__init__(fees_percent_base_pts,
                         first_token, first_token_reserves,
                         lp_token_supply,
                         second_token, second_token_reserves)
        self.main_pair_tokens = main_pair_tokens

    @override
    def estimate_amount_out(self, token_in: Esdt, amount_in: int, token_out: Esdt) -> int:
        if token_in.identifier == self.first_token.identifier:
            (in_reserve_before, out_reserve_before) = (
                self.first_token_reserves, self.second_token_reserves)
        elif token_in.identifier == self.second_token.identifier:
            (in_reserve_before, out_reserve_before) = (
                self.second_token_reserves, self.first_token_reserves)
        else:
            raise ValueError(
                f'Invalid token in: {token_in.identifier} for pool {self}')

        try:
            self.main_pair_tokens.index(token_in.identifier)
            fee_input_token = True
        except ValueError:
            fee_input_token = False

        if fee_input_token:
            amount_in_with_fee = amount_in * \
                (10_000 - self.fees_percent_base_pts)
            numerator = amount_in_with_fee * out_reserve_before
            denominator = (in_reserve_before * 10_000) + amount_in_with_fee

            return numerator // denominator
        else:
            amount_out_without_fee = (
                amount_in * out_reserve_before) // (in_reserve_before + amount_in)

            return amount_out_without_fee * \
                (10_000 - self.fees_percent_base_pts) // 10_000


@dataclass
class JexConstantProductPool(ConstantProductPool):
    """
    JEX constant product pool with specific fees management.
    """

    platform_fees_percent_base_pts: int

    @override
    def estimate_amount_out(self, token_in: Esdt, amount_in: int, token_out: Esdt) -> int:
        if token_in.identifier == self.first_token.identifier:
            (in_reserve_before, out_reserve_before) = (
                self.first_token_reserves, self.second_token_reserves)
        elif token_in.identifier == self.second_token.identifier:
            (in_reserve_before, out_reserve_before) = (
                self.second_token_reserves, self.first_token_reserves)
        else:
            raise ValueError(
                f'Invalid token in: {token_in.identifier} for pool {self}')

        amount_out = (amount_in * out_reserve_before) // \
            (in_reserve_before + amount_in)

        lp_fees = (amount_out * self.fees_percent_base_pts) // 10000
        platform_fees = (
            amount_out * self.platform_fees_percent_base_pts) // 10000

        net_amount_out = amount_out - lp_fees - platform_fees

        if amount_out > out_reserve_before:
            raise ValueError(f'Amount to swap to big {amount_in}')

        return net_amount_out

    def estimated_gas(self) -> int:
        return 20_000_000


@dataclass
class JexConstantProductDepositPool(ConstantProductPool):
    """
    Special pool for deposits in JEX constant product pools.
    """

    @override
    def estimate_amount_out(self, token_in: Esdt, amount_in: int, token_out: Esdt) -> int:
        if token_in.identifier == self.first_token.identifier:
            (in_reserve, _) = \
                (self.first_token_reserves, self.second_token_reserves)
        elif token_in.identifier == self.second_token.identifier:
            (in_reserve, _) = \
                (self.second_token_reserves, self.first_token_reserves)
        else:
            raise ValueError(f'Invalid token in: {token_in.identifier}')

        lp_amount = (amount_in * self.lp_token_supply) / (in_reserve * 2)
        lp_amount = int(lp_amount)

        return int(lp_amount)

    def estimated_gas(self) -> int:
        return 10_000_000


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
                 xp: List[int]):
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

    @override
    def estimate_amount_out(self, token_in: Esdt, amount_in: int, token_out: Esdt) -> int:
        """
        Return (fee, amount_out)
        """
        if amount_in == 0:
            return 0

        precisions = [10**(18-t.decimals) for t in self.tokens]
        price_scale = self.price_scale * precisions[1]

        xp = self.reserves.copy()

        d = self.d

        if self.future_a_gamma_time > 0:
            d = ashswap.newton_d(
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

        y = ashswap.newton_y(
            self.amp,
            self.gamma,
            xp,
            d,
            i_token_out,
            self.reserves
        )

        dy = xp[i_token_out] - y - 1
        xp[i_token_out] = y

        if i_token_out > 0:
            dy = (dy * self.PRECISION) // price_scale
        else:
            dy = dy // precisions[0]

        fee = (dy * self._fee(xp)) // 1e10
        dy = dy - fee

        return int(dy)

    def estimated_gas(self) -> int:
        return 30_000_000

    def _fee(self, xp: List[int]) -> int:
        n_coins = len(self.tokens)

        f = xp[0] + xp[1]

        f_num = self.fee_gamma * self.PRECISION

        f_den = self.fee_gamma + self.PRECISION -   \
            (n_coins**n_coins * self.PRECISION * xp[0] // f * xp[1] // f)

        f = f_num // f_den

        f = (self.mid_fee * f) + (self.out_fee * (self.PRECISION-f))

        f = f // self.PRECISION

        return f


@dataclass
class ConstantPricePool(AbstractPool):
    """
    Constant price pool.

    Example: Liquid staking pools
    """

    price: int
    """ Price (10**18 = 1).
    1 * token_out = token_in / price """

    token_in: Esdt
    token_out: Esdt
    token_out_reserve: int

    @override
    def estimate_amount_out(self, token_in: Esdt, amount_in: int, token_out: Esdt) -> int:
        if token_in.identifier != self.token_in.identifier:
            raise ValueError(f'Invalid token in: {token_in.identifier}')
        if token_out.identifier != self.token_out.identifier:
            raise ValueError(f'Invalid token out: {token_out.identifier}')

        normalized_amount_in = self._normalize_amount(amount_in, token_in)

        normalized_amount_out = (normalized_amount_in * 10**18) // self.price

        amount_out = self._denormalize_amount(normalized_amount_out, token_out)

        if amount_out > self.token_out_reserve:
            raise ValueError(
                f'Amount to swap to big {amount_out} {token_in.name} (max={self.token_out_reserve})')

        return int(amount_out)

    @override
    def estimate_theorical_amount_out(self, token_in: Esdt, amount_in: int, token_out: Esdt) -> int:
        # same as normal swap
        return self.estimate_amount_out(token_in,
                                        amount_in,
                                        token_out)

    def estimated_gas(self) -> int:
        return 20_000_000


@dataclass
class StableSwapPool(AbstractPool):
    """
    Stable swap pool with 2 or more tokens.

    Example: AshSwap stable pool
    """

    amp_factor: int

    fees_percent_base_pts: int
    """ Fees percent basis points (1 = 0.01%) """

    lp_token_supply: int
    tokens: List[Esdt]
    reserves: List[int]
    underlying_prices: List[int]
    normalized_reserves: List[int]

    def __init__(self,
                 amp_factor: int,
                 fees_percent_base_pts: int,
                 tokens: List[Esdt],
                 reserves: List[int],
                 underlying_prices: List[int],
                 lp_token_supply: int):
        self.amp_factor = amp_factor
        self.fees_percent_base_pts = fees_percent_base_pts
        self.tokens = tokens
        self.reserves = reserves
        self.underlying_prices = underlying_prices
        self.lp_token_supply = lp_token_supply
        self.normalized_reserves = [self._normalize_amount(
            a, t) for (a, t) in zip(self.reserves, self.tokens)]

    @override
    def estimate_amount_out(self, token_in: Esdt, amount_in: int, token_out: Esdt) -> int:
        i_token_in, _ = find(lambda x: x.identifier ==
                             token_in.identifier, self.tokens)
        i_token_out, _ = find(lambda x: x.identifier ==
                              token_out.identifier, self.tokens)

        normalized_amount_in = self._normalize_amount(amount_in, token_in)

        normalized_amount_out = stableswap.estimate_amount_out(
            self.amp_factor, self.normalized_reserves, self.underlying_prices,
            i_token_in, normalized_amount_in, i_token_out)

        amount_out = self._denormalize_amount(normalized_amount_out, token_out)

        fee = (amount_out * self.fees_percent_base_pts) // 10_000

        return int(amount_out - fee)

    @override
    def estimate_theorical_amount_out(self, token_in: Esdt, amount_in: int, token_out: Esdt) -> int:
        normalized_amount_in = self._normalize_amount(amount_in, token_in)

        i_token_in, _ = find(lambda x: x.identifier ==
                             token_in.identifier, self.tokens)
        i_token_out, _ = find(lambda x: x.identifier ==
                              token_out.identifier, self.tokens)

        amount_num = normalized_amount_in * self.underlying_prices[i_token_in]
        amount_den = self.underlying_prices[i_token_out]

        print(self.underlying_prices)

        return self._denormalize_amount(amount_num // amount_den, token_out)

    def estimated_gas(self) -> int:
        return 20_000_000


@dataclass
class JexStableSwapPool(StableSwapPool):
    """
    JEX Stable swap pool with 2 or more tokens.

    Keep this type though because it's used as discriminant for aggregation fees.
    """

    def __init__(self,
                 amp_factor: int,
                 fees_percent_base_pts: int,
                 tokens: List[Esdt],
                 reserves: List[int],
                 underlying_prices: List[int],
                 lp_token_supply: int):
        super().__init__(amp_factor=amp_factor,
                         fees_percent_base_pts=fees_percent_base_pts,
                         tokens=tokens,
                         reserves=reserves,
                         underlying_prices=underlying_prices,
                         lp_token_supply=lp_token_supply)


@dataclass
class JexStableSwapPoolDeposit(StableSwapPool):

    def __init__(self,
                 amp_factor: int,
                 fees_percent_base_pts: int,
                 tokens: List[Esdt],
                 reserves: List[int],
                 underlying_prices: List[int],
                 lp_token_supply: int):
        super().__init__(amp_factor=amp_factor,
                         fees_percent_base_pts=fees_percent_base_pts,
                         tokens=tokens,
                         reserves=reserves,
                         underlying_prices=underlying_prices,
                         lp_token_supply=lp_token_supply)

    @override
    def estimate_amount_out(self, token_in: Esdt, amount_in: int, token_out: Esdt) -> int:
        deposits = [self._normalize_amount(amount_in, t) if t.identifier ==
                    token_in.identifier else 0 for t in self.tokens]

        nb_tokens = len(self.tokens)

        liquidity_fees_percent_base_pts = (
            self.fees_percent_base_pts * nb_tokens) // (4 * (nb_tokens - 1))

        amount_out = stableswap.estimate_deposit(deposits=deposits,
                                                 amp=self.amp_factor,
                                                 liquidity_fees_percent_base_pts=liquidity_fees_percent_base_pts,
                                                 lp_total_supply=self.lp_token_supply,
                                                 reserves=self.normalized_reserves,
                                                 underlying_prices=self.underlying_prices)

        return int(amount_out)
