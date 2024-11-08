
from dataclasses import dataclass
from typing import List, Tuple

from typing_extensions import override

from opendex_aggregator_api.data.model import Esdt
from opendex_aggregator_api.pools import stableswap
from opendex_aggregator_api.utils.math import ceildiv

from .pools import ConstantProductPool, StableSwapPool, find

MAX_FEE = 10_000


@dataclass
class JexConstantProductPool(ConstantProductPool):
    """
    JEX constant product pool with specific fees management.
    """

    lp_fee: int
    platform_fee: int

    def __init__(self,
                 first_token: Esdt,
                 first_token_reserves: int,
                 lp_token: Esdt,
                 lp_token_supply: int,
                 second_token: Esdt,
                 second_token_reserves: int,
                 lp_fee: int,
                 platform_fee: int):

        super().__init__(max_fee=MAX_FEE,
                         total_fee=lp_fee + platform_fee,
                         first_token=first_token,
                         first_token_reserves=first_token_reserves,
                         lp_token=lp_token,
                         lp_token_supply=lp_token_supply,
                         second_token=second_token,
                         second_token_reserves=second_token_reserves)

        self.lp_fee = lp_fee
        self.platform_fee = platform_fee

    @override
    def deep_copy(self):
        return JexConstantProductPool(first_token=self.first_token.model_copy(),
                                      first_token_reserves=self.first_token_reserves,
                                      lp_token=self.lp_token.model_copy(),
                                      lp_token_supply=self.lp_token_supply,
                                      second_token=self.second_token.model_copy(),
                                      second_token_reserves=self.second_token_reserves,
                                      lp_fee=self.lp_fee,
                                      platform_fee=self.platform_fee)

    @override
    def estimate_amount_out(self, token_in: Esdt, amount_in: int, token_out: Esdt) -> Tuple[int, int, int]:
        if token_in.identifier == self.first_token.identifier:
            (in_reserve_before, out_reserve_before) = (
                self.first_token_reserves, self.second_token_reserves)
        elif token_in.identifier == self.second_token.identifier:
            (in_reserve_before, out_reserve_before) = (
                self.second_token_reserves, self.first_token_reserves)
        else:
            raise ValueError(
                f'Invalid token in: {token_in.identifier} for pool {self}')

        if in_reserve_before == 0:
            return 0, 0, 0

        amount_out = (amount_in * out_reserve_before) // \
            (in_reserve_before + amount_in)

        lp_fees = (amount_out * self.lp_fee) // MAX_FEE
        platform_fees = (
            amount_out * self.platform_fee) // MAX_FEE

        net_amount_out = amount_out - lp_fees - platform_fees

        if amount_out > out_reserve_before:
            raise ValueError(f'Amount to swap to big {amount_in}')

        return net_amount_out, 0, platform_fees

    @override
    def estimate_amount_in(self, token_out: Esdt, net_amount_out: int, token_in: Esdt) -> Tuple[int, int, int]:
        in_reserve_before, out_reserve_before = self._reserves(token_in,
                                                               token_out)

        amount_out = (net_amount_out *
                      self.max_fee) // (self.max_fee - self.total_fee)

        if amount_out > out_reserve_before:
            raise ValueError(
                f'Amount out to big {amount_out} (max {out_reserve_before})')

        amount_in = ceildiv(amount_out * in_reserve_before,
                            out_reserve_before - amount_out)

        platform_fees = (amount_out * self.platform_fee) // MAX_FEE

        return int(amount_in), 0, platform_fees

    @override
    def estimated_gas(self) -> int:
        return 20_000_000

    @override
    def _source(self) -> str:
        return 'jexchange'


@dataclass
class JexConstantProductDepositPool(JexConstantProductPool):
    """
    Special pool for deposits in JEX constant product pools.
    """

    def __init__(self,
                 first_token: Esdt,
                 first_token_reserves: int,
                 lp_token: Esdt,
                 lp_token_supply: int,
                 second_token: Esdt,
                 second_token_reserves: int,
                 lp_fee: int,
                 platform_fee: int):

        super().__init__(first_token=first_token,
                         first_token_reserves=first_token_reserves,
                         lp_token=lp_token,
                         lp_token_supply=lp_token_supply,
                         second_token=second_token,
                         second_token_reserves=second_token_reserves,
                         lp_fee=lp_fee,
                         platform_fee=platform_fee)

    @override
    def deep_copy(self):
        return JexConstantProductDepositPool(first_token=self.first_token.model_copy(),
                                             first_token_reserves=self.first_token_reserves,
                                             lp_token=self.lp_token.model_copy(),
                                             lp_token_supply=self.lp_token_supply,
                                             second_token=self.second_token.model_copy(),
                                             second_token_reserves=self.second_token_reserves,
                                             lp_fee=self.lp_fee,
                                             platform_fee=self.platform_fee)

    @override
    def estimate_amount_out(self, token_in: Esdt, amount_in: int, token_out: Esdt) -> Tuple[int, int, int]:
        first_token_reserve = self.first_token_reserves
        second_token_reserve = self.second_token_reserves

        if token_in == self.first_token:
            reserve_in = first_token_reserve
            reserve_out = second_token_reserve
        else:
            reserve_in = second_token_reserve
            reserve_out = first_token_reserve

        swap_amount = self._zap_optimal_swap_amount(reserve_in,
                                                    amount_in,
                                                    self.total_fee,
                                                    MAX_FEE)

        other_amount = (
            swap_amount * reserve_out) // (reserve_in + swap_amount)

        lp_fee = other_amount * self.lp_fee // MAX_FEE
        platform_fee = other_amount * self.platform_fee // MAX_FEE

        other_amount = other_amount - lp_fee - platform_fee

        if token_in == self.first_token:
            first_token_amount = amount_in - swap_amount
            second_token_amount = other_amount
            first_token_reserve += swap_amount
            second_token_reserve = second_token_reserve - other_amount - platform_fee
        else:
            first_token_amount = other_amount
            second_token_amount = amount_in - swap_amount
            second_token_reserve += swap_amount
            first_token_reserve = first_token_reserve - other_amount - platform_fee

        exact_second_token_amount = first_token_amount * \
            second_token_reserve // first_token_reserve

        if exact_second_token_amount <= second_token_amount:
            added_first_token = first_token_amount
        else:
            added_first_token = second_token_amount * \
                first_token_reserve // second_token_reserve

        amount_out = added_first_token * self.lp_token_supply // first_token_reserve

        return amount_out, 0, platform_fee

    @override
    def estimate_theorical_amount_out(self, token_in: Esdt, amount_in: int, token_out: Esdt) -> int:
        if self.first_token.identifier == token_in.identifier:
            in_reserve_before = self.first_token_reserves
        elif self.second_token.identifier == token_in.identifier:
            in_reserve_before = self.second_token_reserves
        else:
            raise ValueError(
                f'Invalid input tokens [{token_in.identifier}] for pool {self}')

        return amount_in * in_reserve_before // (2 * self.lp_token_supply)

    @override
    def estimated_gas(self) -> int:
        return 30_000_000

    @override
    def update_reserves(self,
                        token_in: Esdt,
                        amount_in: int,
                        token_out: Esdt,
                        amount_out: int):
        if token_in == self.first_token:
            self.first_token_reserves += amount_in
        else:
            self.second_token_reserves += amount_in


@dataclass
class JexStableSwapPool(StableSwapPool):
    """
    JEX Stable swap pool with 2 or more tokens.

    Keep this type though because it's used as discriminant for aggregation fees.
    """

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
                         max_fee=1_000_000,
                         tokens=tokens,
                         reserves=reserves,
                         underlying_prices=underlying_prices,
                         lp_token=lp_token,
                         lp_token_supply=lp_token_supply)

    @override
    def deep_copy(self):
        return JexStableSwapPool(amp_factor=self.amp_factor,
                                 swap_fee=self.swap_fee,
                                 tokens=[t.model_copy() for t in self.tokens],
                                 reserves=self.reserves.copy(),
                                 underlying_prices=self.underlying_prices.copy(),
                                 lp_token=self.lp_token.model_copy(),
                                 lp_token_supply=self.lp_token_supply)


@dataclass
class JexStableSwapPoolDeposit(StableSwapPool):

    def __init__(self,
                 amp_factor: int,
                 total_fees: int,
                 tokens: List[Esdt],
                 reserves: List[int],
                 underlying_prices: List[int],
                 lp_token: Esdt,
                 lp_token_supply: int):
        super().__init__(amp_factor=amp_factor,
                         swap_fee=total_fees,
                         max_fee=1_000_000,
                         tokens=tokens,
                         reserves=reserves,
                         underlying_prices=underlying_prices,
                         lp_token=lp_token,
                         lp_token_supply=lp_token_supply)

    @override
    def estimate_amount_out(self, token_in: Esdt, amount_in: int, token_out: Esdt) -> Tuple[int, int, int]:
        deposits = [self._normalize_amount(amount_in, t) if t.identifier ==
                    token_in.identifier else 0 for t in self.tokens]

        nb_tokens = len(self.tokens)

        liquidity_fees = (
            self.total_fees * nb_tokens) // (4 * (nb_tokens - 1))

        amount_out = stableswap.estimate_deposit(deposits=deposits,
                                                 amp=self.amp_factor,
                                                 liquidity_fees=liquidity_fees,
                                                 max_fees=self.max_fee,
                                                 lp_total_supply=self.lp_token_supply,
                                                 reserves=self.normalized_reserves,
                                                 underlying_prices=self.underlying_prices)

        admin_fee_out = amount_out * (liquidity_fees * 33) // 100

        return int(amount_out), 0, admin_fee_out

    @override
    def deep_copy(self):
        return JexStableSwapPoolDeposit(amp_factor=self.amp_factor,
                                        lp_token=self.lp_token.model_copy(),
                                        lp_token_supply=self.lp_token_supply,
                                        reserves=self.reserves.copy(),
                                        tokens=[t.model_copy()
                                                for t in self.tokens],
                                        total_fees=self.swap_fee,
                                        underlying_prices=self.underlying_prices.copy())

    @override
    def update_reserves(self,
                        token_in: Esdt,
                        amount_in: int,
                        token_out: Esdt,
                        amount_out: int):
        i_token_in, _ = find(lambda x: x.identifier ==
                             token_in.identifier, self.tokens)

        self.reserves[i_token_in] += amount_in
