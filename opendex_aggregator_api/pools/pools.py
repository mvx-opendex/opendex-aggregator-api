import math
from dataclasses import dataclass
from typing import Any, Callable, Iterable, List, Optional, Tuple

from typing_extensions import override

from opendex_aggregator_api.data.model import Esdt, ExchangeRate
from opendex_aggregator_api.pools import ashswap, stableswap


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

    def estimated_gas(self) -> int:
        raise NotImplementedError()

    def estimate_theorical_amount_out(self, token_in: Esdt, amount_in: int, token_out: Esdt) -> int:
        raise NotImplementedError()

    def exchange_rates(self) -> List[ExchangeRate]:
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
    def deep_copy(self):
        return ConstantProductPool(fees_percent_base_pts=self.fees_percent_base_pts,
                                   first_token=self.first_token.model_copy(),
                                   first_token_reserves=self.first_token_reserves,
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

        fee = (amount_out * self.fees_percent_base_pts) // 10_000

        amount_out -= fee

        return int(amount_out), 0, 0

    @override
    def estimate_theorical_amount_out(self, token_in: Esdt, amount_in: int, token_out: Esdt) -> int:
        in_reserve, out_reserve = self._reserves(token_in, token_out)

        if in_reserve == 0:
            return 0

        fee = (amount_in * self.fees_percent_base_pts) // 10_000

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

    def _source(self) -> str:
        raise NotImplementedError()

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
 fees: {self.fees_percent_base_pts / 100}%)'


@dataclass
class XExchangeConstantProductPool(ConstantProductPool):

    special_fee_percent: int

    def __init__(self,
                 first_token: Esdt,
                 first_token_reserves: int,
                 lp_token_supply: int,
                 second_token: Esdt,
                 second_token_reserves: int,
                 special_fee_percent: int,
                 total_fee_percent: int):
        super().__init__(total_fee_percent // 10,
                         first_token,
                         first_token_reserves,
                         lp_token_supply,
                         second_token,
                         second_token_reserves)
        self.special_fee_percent = special_fee_percent
        self.total_fee_percent = total_fee_percent

    @override
    def deep_copy(self):
        return XExchangeConstantProductPool(first_token=self.first_token.model_copy(),
                                            first_token_reserves=self.first_token_reserves,
                                            lp_token_supply=self.lp_token_supply,
                                            second_token=self.second_token.model_copy(),
                                            second_token_reserves=self.second_token_reserves,
                                            special_fee_percent=self.special_fee_percent,
                                            total_fee_percent=self.total_fee_percent)

    @override
    def estimate_amount_out(self, token_in: Esdt, amount_in: int, token_out: Esdt) -> Tuple[int, int, int]:
        in_reserve, out_reserve = self._reserves(token_in,
                                                 token_out)

        amount_in_with_fee = amount_in * (100_000 - self.total_fee_percent)
        num = amount_in_with_fee * out_reserve
        den = (in_reserve * 100_000) + amount_in_with_fee

        amount_out = num // den

        if amount_out > out_reserve:
            raise ValueError(f'Amount to swap to big {amount_in}')

        special_fee = (amount_in * self.special_fee_percent) // 100_000

        return amount_out, special_fee, 0

    @override
    def _source(self) -> str:
        return 'xexchange'


@dataclass
class OneDexConstantProductPool(ConstantProductPool):
    """
    OneDex constant product pool with specific fees management.
    """

    main_pair_tokens: List[str]

    def __init__(self,
                 fees_percent_base_pts: int,
                 first_token: Esdt,
                 first_token_reserves: int,
                 lp_token_supply: int,
                 second_token: Esdt,
                 second_token_reserves: int,
                 main_pair_tokens: List[str]):
        super().__init__(fees_percent_base_pts,
                         first_token,
                         first_token_reserves,
                         lp_token_supply,
                         second_token,
                         second_token_reserves)
        self.main_pair_tokens = main_pair_tokens

    @override
    def deep_copy(self):
        return OneDexConstantProductPool(fees_percent_base_pts=self.fees_percent_base_pts,
                                         first_token=self.first_token.model_copy(),
                                         first_token_reserves=self.first_token_reserves,
                                         lp_token_supply=self.lp_token_supply,
                                         second_token=self.second_token.model_copy(),
                                         second_token_reserves=self.second_token_reserves,
                                         main_pair_tokens=self.main_pair_tokens.copy())

    @override
    def estimate_amount_out(self, token_in: Esdt, amount_in: int, token_out: Esdt) -> Tuple[int, int, int]:
        in_reserve, out_reserve = self._reserves(token_in,
                                                 token_out)

        try:
            self.main_pair_tokens.index(token_in.identifier)
            fee_input_token = True
        except ValueError:
            fee_input_token = False

        if fee_input_token:
            amount_in_with_fee = amount_in * \
                (10_000 - self.fees_percent_base_pts)
            num = amount_in_with_fee * out_reserve
            den = (in_reserve * 10_000) + amount_in_with_fee
            net_amount_out = num // den

            return net_amount_out, 0, 0
        else:
            amount_out_without_fee = (
                amount_in * out_reserve) // (in_reserve + amount_in)

            fee = (amount_out_without_fee *
                   self.fees_percent_base_pts) // 10_000

            net_amount_out = amount_out_without_fee - fee

            return net_amount_out, 0, 0

    @override
    def _source(self) -> str:
        return 'onedex'


@dataclass
class JexConstantProductPool(ConstantProductPool):
    """
    JEX constant product pool with specific fees management.
    """

    platform_fees_percent_base_pts: int

    @override
    def deep_copy(self):
        return JexConstantProductPool(fees_percent_base_pts=self.fees_percent_base_pts,
                                      first_token=self.first_token.model_copy(),
                                      first_token_reserves=self.first_token_reserves,
                                      lp_token_supply=self.lp_token_supply,
                                      second_token=self.second_token.model_copy(),
                                      second_token_reserves=self.second_token_reserves,
                                      platform_fees_percent_base_pts=self.platform_fees_percent_base_pts)

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

        lp_fees = (amount_out * self.fees_percent_base_pts) // 10000
        platform_fees = (
            amount_out * self.platform_fees_percent_base_pts) // 10000

        net_amount_out = amount_out - lp_fees - platform_fees

        if amount_out > out_reserve_before:
            raise ValueError(f'Amount to swap to big {amount_in}')

        return net_amount_out, 0, platform_fees

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

    @override
    def deep_copy(self):
        return JexConstantProductDepositPool(fees_percent_base_pts=self.fees_percent_base_pts,
                                             platform_fees_percent_base_pts=self.platform_fees_percent_base_pts,
                                             first_token=self.first_token.model_copy(),
                                             first_token_reserves=self.first_token_reserves,
                                             lp_token_supply=self.lp_token_supply,
                                             second_token=self.second_token.model_copy(),
                                             second_token_reserves=self.second_token_reserves)

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

        max_fee = 10_000

        swap_amount = self._zap_optimal_swap_amount(reserve_in,
                                                    amount_in,
                                                    self.fees_percent_base_pts + self.platform_fees_percent_base_pts,
                                                    max_fee)

        other_amount = (
            swap_amount * reserve_out) // (reserve_in + swap_amount)

        lp_fee = other_amount * self.fees_percent_base_pts // max_fee
        platform_fee = other_amount * self.platform_fees_percent_base_pts // max_fee

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
class VestaDexConstantProductPool(XExchangeConstantProductPool):
    def __init__(self,
                 first_token: Esdt,
                 first_token_reserves: int,
                 lp_token_supply: int,
                 second_token: Esdt,
                 second_token_reserves: int,
                 special_fee_percent: int,
                 total_fee_percent: int):
        super().__init__(first_token,
                         first_token_reserves,
                         lp_token_supply,
                         second_token,
                         second_token_reserves,
                         special_fee_percent // 10,
                         total_fee_percent // 10)

    @override
    def deep_copy(self):
        return VestaDexConstantProductPool(first_token=self.first_token,
                                           first_token_reserves=self.first_token_reserves,
                                           lp_token_supply=self.lp_token_supply,
                                           second_token=self.second_token,
                                           second_token_reserves=self.second_token_reserves,
                                           special_fee_percent=self.special_fee_percent,
                                           total_fee_percent=self.total_fee_percent)

    @override
    def _source(self) -> str:
        return 'vestadex'


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
        assert len(tokens) == 2, 'Invalid number of tokens'
        assert len(reserves) == 2, 'Invalid number of token reserves'

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
                             xp=self.xp.copy())

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

        fee = (dy * self._fee(xp)) // 10**10

        dy = dy - fee

        return dy, 0, fee // 3

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
class OpendexConstantProductPool(ConstantProductPool):
    fee_token: Optional[Esdt]

    platform_fee_percent: int

    def __init__(self,
                 first_token: Esdt,
                 first_token_reserves: int,
                 lp_token_supply: int,
                 second_token: Esdt,
                 second_token_reserves: int,
                 total_fee_percent: int,
                 platform_fee_percent: int,
                 fee_token: Optional[Esdt]):

        super().__init__(fees_percent_base_pts=total_fee_percent,
                         first_token=first_token,
                         first_token_reserves=first_token_reserves,
                         lp_token_supply=lp_token_supply,
                         second_token=second_token,
                         second_token_reserves=second_token_reserves)

        self.fee_token = fee_token
        self.platform_fee_percent = platform_fee_percent

    @override
    def deep_copy(self):
        return OpendexConstantProductPool(first_token=self.first_token.model_copy(),
                                          first_token_reserves=self.first_token_reserves,
                                          lp_token_supply=self.lp_token_supply,
                                          second_token=self.second_token.model_copy(),
                                          second_token_reserves=self.second_token_reserves,
                                          total_fee_percent=self.fees_percent_base_pts,
                                          platform_fee_percent=self.platform_fee_percent,
                                          fee_token=self.fee_token.model_copy() if self.fee_token else None)

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

        platform_fee_in = 0
        platform_fee_out = 0

        if self.fee_token and token_in.identifier == self.fee_token.identifier:
            lp_fee, platform_fee_in = self._calculate_fees(amount_in)

            amount_in_less_fees = amount_in - lp_fee - platform_fee_in

            net_amount_out = (
                amount_in_less_fees * out_reserve_before) // (in_reserve_before + amount_in_less_fees)
        else:
            amount_out = (amount_in * out_reserve_before) // \
                (in_reserve_before + amount_in)

            lp_fee, platform_fee_out = self._calculate_fees(amount_out)

            net_amount_out = amount_out - lp_fee - platform_fee_out

        return net_amount_out, platform_fee_in, platform_fee_out

    def _calculate_fees(self, amount: int) -> Tuple[int, int]:
        max_fees = 10_000

        total_fee = (amount * self.fees_percent_base_pts) // max_fees

        platform_fee = (amount * self.platform_fee_percent) // max_fees

        lp_fee = total_fee - platform_fee

        return (lp_fee, platform_fee)

    @override
    def _source(self) -> str:
        return 'opendex'


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

    total_fees: int
    max_fees: int

    lp_token_supply: int
    tokens: List[Esdt]
    reserves: List[int]
    underlying_prices: List[int]
    normalized_reserves: List[int]

    def __init__(self,
                 amp_factor: int,
                 total_fees: int,
                 max_fees: int,
                 tokens: List[Esdt],
                 reserves: List[int],
                 underlying_prices: List[int],
                 lp_token_supply: int):
        self.amp_factor = amp_factor
        self.total_fees = total_fees
        self.max_fees = max_fees
        self.tokens = tokens
        self.reserves = reserves
        self.underlying_prices = underlying_prices
        self.lp_token_supply = lp_token_supply
        self.normalized_reserves = [self._normalize_amount(a, t)
                                    for (a, t) in zip(self.reserves, self.tokens)]

    @override
    def deep_copy(self):
        return StableSwapPool(amp_factor=self.amp_factor,
                              total_fees=self.total_fees,
                              max_fees=self.max_fees,
                              tokens=[t.model_copy() for t in self.tokens],
                              reserves=self.reserves.copy(),
                              underlying_prices=self.underlying_prices.copy(),
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

        fee = (amount_out * self.total_fees) // self.max_fees

        return int(amount_out - fee), 0, 0

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

        fee = (amount * self.total_fees) // self.max_fees

        return self._denormalize_amount(amount - fee, token_out)

    @override
    def estimated_gas(self) -> int:
        return 20_000_000

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


@dataclass
class JexStableSwapPool(StableSwapPool):
    """
    JEX Stable swap pool with 2 or more tokens.

    Keep this type though because it's used as discriminant for aggregation fees.
    """

    def __init__(self,
                 amp_factor: int,
                 total_fees: int,
                 max_fees: int,
                 tokens: List[Esdt],
                 reserves: List[int],
                 underlying_prices: List[int],
                 lp_token_supply: int):
        super().__init__(amp_factor=amp_factor,
                         total_fees=total_fees,
                         max_fees=max_fees,
                         tokens=tokens,
                         reserves=reserves,
                         underlying_prices=underlying_prices,
                         lp_token_supply=lp_token_supply)

    @override
    def deep_copy(self):
        return JexStableSwapPool(amp_factor=self.amp_factor,
                                 total_fees=self.total_fees,
                                 max_fees=self.max_fees,
                                 tokens=[t.model_copy() for t in self.tokens],
                                 reserves=self.reserves.copy(),
                                 underlying_prices=self.underlying_prices.copy(),
                                 lp_token_supply=self.lp_token_supply)


@dataclass
class JexStableSwapPoolDeposit(StableSwapPool):

    def __init__(self,
                 amp_factor: int,
                 total_fees: int,
                 max_fees: int,
                 tokens: List[Esdt],
                 reserves: List[int],
                 underlying_prices: List[int],
                 lp_token_supply: int):
        super().__init__(amp_factor=amp_factor,
                         total_fees=total_fees,
                         max_fees=max_fees,
                         tokens=tokens,
                         reserves=reserves,
                         underlying_prices=underlying_prices,
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
                                                 max_fees=self.max_fees,
                                                 lp_total_supply=self.lp_token_supply,
                                                 reserves=self.normalized_reserves,
                                                 underlying_prices=self.underlying_prices)

        admin_fee_out = amount_out * (liquidity_fees * 33) // 100

        return int(amount_out), 0, admin_fee_out

    @override
    def update_reserves(self,
                        token_in: Esdt,
                        amount_in: int,
                        token_out: Esdt,
                        amount_out: int):
        i_token_in, _ = find(lambda x: x.identifier ==
                             token_in.identifier, self.tokens)

        self.reserves[i_token_in] += amount_in
