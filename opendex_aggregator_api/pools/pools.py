import math
import sys
from dataclasses import dataclass
from typing import Any, Callable, Iterable, List, Optional, Tuple

from typing_extensions import override

from opendex_aggregator_api.data.model import (Esdt, ExchangeRate,
                                               LpTokenComposition)
from opendex_aggregator_api.pools import stableswap
from opendex_aggregator_api.utils.math import ceildiv


def find(function_: Callable[[Any], bool], iter_: Iterable[Any]) -> Tuple[int, Optional[Any]]:
    for i, elem in enumerate(iter_):
        if function_(elem):
            return (i, elem)
    return (-1, None)


class AbstractPool:

    def deep_copy(self) -> 'AbstractPool':
        raise NotImplementedError()

    def estimate_amount_out(self, token_in: Esdt, amount_in: int, token_out: Esdt) -> Tuple[int, int, int]:
        """
        :return: a tuple with:
        - net amount out
        - admin fee (token in) removed from reserves
        - admin fee (token out) removed from reserves
        """
        raise NotImplementedError()

    def estimate_amount_in(self, token_out: Esdt, net_amount_out: int, token_in: Esdt) -> Tuple[int, int, int]:
        """
        :return: a tuple with:
        - net amount out
        - admin fee (token in) removed from reserves
        - admin fee (token out) removed from reserves
        """
        raise NotImplementedError()

    def estimated_gas(self) -> int:
        raise NotImplementedError()

    def estimate_theorical_amount_out(self, token_in: Esdt, amount_in: int, token_out: Esdt) -> int:
        raise NotImplementedError()

    def exchange_rates(self, sc_address: str) -> List[ExchangeRate]:
        raise NotImplementedError()

    def lp_token_composition(self) -> Optional[LpTokenComposition]:
        raise NotImplementedError()

    def update_reserves(self,
                        token_in: Esdt,
                        amount_in: int,
                        token_out: Esdt,
                        amount_out: int):
        raise NotImplementedError()

    def _normalize_amount(self, amount: int, token: Esdt) -> int:
        return (amount * 10**18) // 10**token.decimals

    def _denormalize_amount(self, amount: int, token: Esdt) -> int:
        num = amount * 10**token.decimals
        den = 10**18

        return int(num // den)

    def _source(self) -> str:
        raise NotImplementedError()


@dataclass
class ConstantProductPool(AbstractPool):
    """
    Constant product pools (x*y=k)
    """

    max_fee: int
    total_fee: int

    first_token: Esdt
    first_token_reserves: int
    lp_token: Esdt
    lp_token_supply: int
    second_token: Esdt
    second_token_reserves: int

    @override
    def deep_copy(self):
        return ConstantProductPool(max_fee=self.max_fee,
                                   total_fee=self.total_fee,
                                   first_token=self.first_token.model_copy(),
                                   first_token_reserves=self.first_token_reserves,
                                   lp_token=self.lp_token.model_copy(),
                                   lp_token_supply=self.lp_token_supply,
                                   second_token=self.second_token.model_copy(),
                                   second_token_reserves=self.second_token_reserves)

    @override
    def estimate_amount_out(self, token_in: Esdt, amount_in: int, token_out: Esdt) -> Tuple[int, int, int]:
        in_reserve_before, out_reserve_before = self._reserves(token_in,
                                                               token_out)

        amount_out = (amount_in * out_reserve_before) // \
            (in_reserve_before + amount_in)

        if amount_out > out_reserve_before:
            raise ValueError(f'Amount to swap to big {amount_in}')

        fee = (amount_out * self.total_fee) // self.max_fee

        amount_out -= fee

        return int(amount_out), 0, 0

    @override
    def estimate_amount_in(self, token_out: Esdt, net_amount_out: int, token_in: Esdt) -> Tuple[int, int, int]:
        in_reserve_before, out_reserve_before = self._reserves(token_in,
                                                               token_out)

        amount_out = (net_amount_out *
                      self.max_fee) // (self.max_fee - self.total_fee)

        if amount_out > out_reserve_before:
            raise ValueError(f'Amount out to big {amount_out}')

        amount_in = ceildiv(amount_out * in_reserve_before,
                            out_reserve_before - amount_out)

        return int(amount_in), 0, 0

    @override
    def estimate_theorical_amount_out(self, token_in: Esdt, amount_in: int, token_out: Esdt) -> int:
        in_reserve, out_reserve = self._reserves(token_in, token_out)

        if in_reserve == 0:
            return 0

        fee = (amount_in * self.total_fee) // self.max_fee

        amount_in -= fee

        return (amount_in * out_reserve) // in_reserve

    @override
    def estimated_gas(self) -> int:
        return 20_000_000

    @override
    def exchange_rates(self, sc_address: str) -> List[ExchangeRate]:
        rate_num = (self.second_token_reserves * 10**self.first_token.decimals)
        rate_den = (self.first_token_reserves * 10**self.second_token.decimals)

        if rate_den == 0 or rate_num == 0:
            return []

        rate = rate_num / rate_den
        rate2 = rate_den / rate_num

        return [ExchangeRate(base_token_id=self.first_token.identifier,
                             base_token_liquidity=self.first_token_reserves,
                             quote_token_id=self.second_token.identifier,
                             quote_token_liquidity=self.second_token_reserves,
                             sc_address=sc_address,
                             source=self._source(),
                             rate=rate,
                             rate2=rate2)]

    @override
    def lp_token_composition(self) -> Optional[LpTokenComposition]:
        return LpTokenComposition(lp_token_id=self.lp_token.identifier,
                                  lp_token_supply=self.lp_token_supply,
                                  token_ids=[self.first_token.identifier,
                                             self.second_token.identifier],
                                  token_reserves=[self.first_token_reserves,
                                                  self.second_token_reserves])

    @override
    def update_reserves(self,
                        token_in: Esdt,
                        amount_in: int,
                        token_out: Esdt,
                        amount_out: int):
        if token_in == self.first_token:
            self.first_token_reserves += amount_in
            self.second_token_reserves -= amount_out
        else:
            self.second_token_reserves += amount_in
            self.first_token_reserves -= amount_out

    def _reserves(self, token_in: Esdt, token_out: Esdt) -> Tuple[int, int]:
        if token_in.identifier == self.first_token.identifier \
                and token_out.identifier == self.second_token.identifier:
            return (self.first_token_reserves, self.second_token_reserves)

        if token_in.identifier == self.second_token.identifier \
                and token_out.identifier == self.first_token.identifier:
            return (self.second_token_reserves, self.first_token_reserves)

        raise ValueError(
            f'Invalid in/out tokens [{token_in.identifier}-{token_out.identifier}] for pool {self}')

    def _zap_optimal_swap_amount(self,
                                 reserve: int,
                                 amount_in: int,
                                 fee: int,
                                 max_fee: int) -> int:
        num = int(math.sqrt((reserve * (max_fee * 2 - fee))**2 + (amount_in * reserve *
                                                                  4 * max_fee * (max_fee - fee)))) - reserve * (2 * max_fee - fee)

        den = 2 * (max_fee - fee)

        return num // den

    def __str__(self) -> str:
        return f'ConstantProductPool({self.first_token_reserves/10**self.first_token.decimals:.4f} \
 {self.first_token.identifier} + \
 {self.second_token_reserves/10**self.second_token.decimals:.4f} \
 {self.second_token.identifier} \
 fees: {self.total_fees * 100 / self.max_fees}%)'


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
    def deep_copy(self):
        return ConstantPricePool(price=self.price,
                                 token_in=self.token_in.model_copy(),
                                 token_out=self.token_out.model_copy(),
                                 token_out_reserve=self.token_out_reserve)

    @override
    def estimate_amount_out(self, token_in: Esdt, amount_in: int, token_out: Esdt) -> Tuple[int, int, int]:
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

        return int(amount_out), 0, 0

    @override
    def estimate_theorical_amount_out(self, token_in: Esdt, amount_in: int, token_out: Esdt) -> int:
        # same as normal swap
        net_amount_out, _, _ = self.estimate_amount_out(token_in,
                                                        amount_in,
                                                        token_out)

        return net_amount_out

    @override
    def estimated_gas(self) -> int:
        return 20_000_000

    @override
    def exchange_rates(self, sc_address: str) -> List[ExchangeRate]:
        rate = self.price / 10**18
        return [ExchangeRate(base_token_id=self.token_out.identifier,
                             base_token_liquidity=self.token_out_reserve,
                             quote_token_id=self.token_in.identifier,
                             quote_token_liquidity=sys.maxsize,
                             rate=rate,
                             rate2=1 / rate,
                             sc_address=sc_address,
                             source=self._source())]

    @override
    def lp_token_composition(self):
        return None

    @override
    def update_reserves(self,
                        token_in: Esdt,
                        amount_in: int,
                        token_out: Esdt,
                        amount_out: int):
        self.token_out_reserve -= amount_out


@dataclass
class StableSwapPool(AbstractPool):
    """
    Stable swap pool with 2 or more tokens.

    Example: AshSwap stable pool
    """

    amp_factor: int

    swap_fee: int
    max_fee: int

    lp_token: Esdt
    lp_token_supply: int
    tokens: List[Esdt]
    reserves: List[int]
    underlying_prices: List[int]
    normalized_reserves: List[int]

    def __init__(self,
                 amp_factor: int,
                 swap_fee: int,
                 max_fee: int,
                 tokens: List[Esdt],
                 reserves: List[int],
                 underlying_prices: List[int],
                 lp_token: Esdt,
                 lp_token_supply: int):
        self.amp_factor = amp_factor
        self.swap_fee = swap_fee
        self.max_fee = max_fee
        self.tokens = tokens
        self.reserves = reserves
        self.underlying_prices = underlying_prices
        self.lp_token = lp_token
        self.lp_token_supply = lp_token_supply
        self.normalized_reserves = [self._normalize_amount(a, t)
                                    for (a, t) in zip(self.reserves, self.tokens)]

    @override
    def deep_copy(self):
        return StableSwapPool(amp_factor=self.amp_factor,
                              swap_fee=self.swap_fee,
                              max_fee=self.max_fee,
                              tokens=[t.model_copy() for t in self.tokens],
                              reserves=self.reserves.copy(),
                              underlying_prices=self.underlying_prices.copy(),
                              lp_token=self.lp_token,
                              lp_token_supply=self.lp_token_supply)

    @override
    def estimate_amount_out(self, token_in: Esdt, amount_in: int, token_out: Esdt) -> Tuple[int, int, int]:
        i_token_in, _ = find(lambda x: x.identifier ==
                             token_in.identifier, self.tokens)
        i_token_out, _ = find(lambda x: x.identifier ==
                              token_out.identifier, self.tokens)

        normalized_amount_in = self._normalize_amount(amount_in, token_in)

        normalized_amount_out = stableswap.estimate_amount_out(
            self.amp_factor, self.normalized_reserves, self.underlying_prices,
            i_token_in, normalized_amount_in, i_token_out)

        amount_out = self._denormalize_amount(normalized_amount_out, token_out)

        fee = (amount_out * self.swap_fee) // self.max_fee

        return int(amount_out - fee), 0, 0

    # @override
    # def estimate_amount_in(self, token_out: Esdt, net_amount_out: int, token_in: Esdt) -> Tuple[int, int, int]:
    #     i_token_in, _ = find(lambda x: x.identifier ==
    #                          token_in.identifier, self.tokens)
    #     i_token_out, _ = find(lambda x: x.identifier ==
    #                           token_out.identifier, self.tokens)

    #     amount_out = (net_amount_out *
    #                   self.max_fee) // (self.max_fee - self.swap_fee)

    #     normalized_amount_out = self._normalize_amount(amount_out, token_out)

    #     normalized_amount_in = stableswap.estimate_amount_in(
    #         self.amp_factor, self.normalized_reserves, self.underlying_prices,
    #         i_token_in, normalized_amount_out, i_token_out)

    #     amount_in = self._denormalize_amount(normalized_amount_in, token_in)

    #     return int(amount_in), 0, 0

    @override
    def estimate_theorical_amount_out(self, token_in: Esdt, amount_in: int, token_out: Esdt) -> int:
        normalized_amount_in = self._normalize_amount(amount_in, token_in)

        i_token_in, _ = find(lambda x: x.identifier ==
                             token_in.identifier, self.tokens)
        i_token_out, _ = find(lambda x: x.identifier ==
                              token_out.identifier, self.tokens)

        amount_num = normalized_amount_in * self.underlying_prices[i_token_in]
        amount_den = self.underlying_prices[i_token_out]

        amount = amount_num // amount_den

        fee = (amount * self.swap_fee) // self.max_fee

        return self._denormalize_amount(amount - fee, token_out)

    @override
    def estimated_gas(self) -> int:
        return 20_000_000

    @override
    def lp_token_composition(self) -> Optional[LpTokenComposition]:
        return LpTokenComposition(lp_token_id=self.lp_token.identifier,
                                  lp_token_supply=self.lp_token_supply,
                                  token_ids=[t.identifier
                                             for t in self.tokens],
                                  token_reserves=self.reserves)

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

        self.normalized_reserves = [self._normalize_amount(a, t)
                                    for (a, t) in zip(self.reserves, self.tokens)]

    @override
    def exchange_rates(self, sc_address: str) -> List[ExchangeRate]:

        rates = []

        for i_token_in, token_in in enumerate(self.tokens):
            amount_in = (10**token_in.decimals) // 1000

            for i_token_out, token_out in enumerate(self.tokens):
                if token_in == token_out:
                    continue

                normalized_amount_in = self._normalize_amount(
                    amount_in, token_in)

                normalized_amount_out = stableswap.estimate_amount_out(
                    self.amp_factor, self.normalized_reserves, self.underlying_prices,
                    i_token_in, normalized_amount_in, i_token_out)

                if normalized_amount_out != 0:

                    rates.append(ExchangeRate(base_token_id=token_in.identifier,
                                              base_token_liquidity=self.reserves[i_token_in],
                                              quote_token_id=token_out.identifier,
                                              quote_token_liquidity=self.reserves[i_token_out],
                                              sc_address=sc_address,
                                              source=self._source(),
                                              rate=normalized_amount_in / normalized_amount_out,
                                              rate2=normalized_amount_out / normalized_amount_in))

        return rates
