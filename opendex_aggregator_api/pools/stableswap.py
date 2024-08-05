from typing import List

from opendex_aggregator_api.pools import curve

UNDERLYING_PRICE_PRECISION = 10**18


def estimate_amount_out(amp: int,
                        reserves: List[int],
                        underlying_prices: List[int],
                        i_token_in: int,
                        amount_in: int,
                        i_token_out: int):
    """
    Estimate output amount of a stable swap.

    Note that +reserves+ and +amount_in+ must be normalized (same number of decimals)
    """

    reserves = [(r*p)//UNDERLYING_PRICE_PRECISION for (r, p)
                in zip(reserves, underlying_prices)]

    in_reserve = reserves[i_token_in]
    out_reserve = reserves[i_token_out]

    if amount_in == 0 or in_reserve == 0 or out_reserve == 0:
        return 0

    dx = amount_in * \
        underlying_prices[i_token_in] // UNDERLYING_PRICE_PRECISION

    out_reserve_after = curve.y(
        amp, reserves, i_token_in, i_token_out, dx)

    dy = (out_reserve - out_reserve_after) * \
        UNDERLYING_PRICE_PRECISION // underlying_prices[i_token_out]

    return dy


def estimate_withdraw_one_token(shares: int,
                                i_token_out: int,
                                amp: int, total_supply: int,
                                reserves: List[int],
                                underlying_prices: List[int],
                                liquidity_fees: int,
                                max_fees: int):
    N = len(reserves)
    xp = [(r*p)//UNDERLYING_PRICE_PRECISION for (r, p)
          in zip(reserves, underlying_prices)]

    # Calculate d0 and d1
    d0 = curve.D(amp, xp)
    d1 = d0 - (d0 * shares) // total_supply

    # Calculate reduction in y if D = d1
    y0 = curve.y_D(amp, xp, i_token_out, d1)
    # d1 <= d0 so y must be <= xp[i]
    dy0 = xp[i_token_out] - y0

    # Calculate imbalance fee, update xp with fees

    for j in range(N):
        if j == i_token_out:
            dx = (xp[j] * d1) // d0 - y0
        else:
            # d1 / d0 <= 1
            dx = xp[j] - (xp[j] * d1) // d0

        xp[j] -= (liquidity_fees * dx) // max_fees

    # Recalculate y with xp including imbalance fees
    y1 = curve.y_D(amp, xp, i_token_out, d1)

    # - 1 to round down
    dy = (xp[i_token_out] - y1 - 1) * \
        UNDERLYING_PRICE_PRECISION // underlying_prices[i_token_out]

    fee = dy0 - dy

    return (dy, fee)


def estimate_deposit(deposits: List[int],
                     reserves: List[int],
                     underlying_prices: List[int],
                     lp_total_supply: int,
                     amp: int,
                     liquidity_fees: int,
                     max_fees: int) -> int:
    """
    Estimate deposit in a stable pool (mint).

    Note that +reserves+ and +deposits+ must be normalized (same number of decimals)
    """

    old_xs = [(r*p)//UNDERLYING_PRICE_PRECISION for (r, p)
              in zip(reserves, underlying_prices)]

    d0 = 0
    if lp_total_supply > 0:
        d0 = curve.D(amp, old_xs)

    scaled_deposits = [(d*p)//UNDERLYING_PRICE_PRECISION for (d, p)
                       in zip(deposits, underlying_prices)]

    new_xs = [x+d for x, d in zip(old_xs, scaled_deposits)]

    d1 = curve.D(amp, new_xs)
    if d1 <= d0:
        # Liquidity did not increase (all deposits at 0)
        return 0

    new_xs2 = [0] * len(new_xs)
    if lp_total_supply > 0:
        for i in range(len(old_xs)):
            ideal_balance = (old_xs[i] * d1) // d0
            diff = abs(new_xs[i] - ideal_balance)
            fee = (diff * liquidity_fees) // max_fees
            new_xi = new_xs[i] - fee
            new_xs2[i] = new_xi

        d2 = curve.D(amp, new_xs2)
    else:
        d2 = d1

    if lp_total_supply > 0:
        shares = ((d2-d0) * lp_total_supply) // d0
    else:
        shares = d2

    return shares
