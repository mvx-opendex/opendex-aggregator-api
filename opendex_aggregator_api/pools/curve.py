from typing import List


MAX_ITERS = 128


class DidNotConvergeException(Exception):
    pass


def D(amp: int, amounts: List[int]) -> int:
    """
    Compute the stable swap invariant

    +amp+ Amplification coefficient (A)
    +amounts+ amounts of all tokens

    Reference: https://github.com/curvefi/curve-contract/blob/7116b4a261580813ef057887c5009e22473ddb7d/tests/simulation.py#L31
    """
    n_coins = len(amounts)
    ann = amp * n_coins
    s = sum(amounts)  # sum(x_i), a.k.a S
    if s == 0:
        return 0

    d_prev = 0
    d = s

    i = 0
    while i < MAX_ITERS and abs(d - d_prev) > 1:
        i += 1
        d_p = d
        for a in amounts:
            d_p = (d_p * d) // (a * n_coins)
        d_prev = d

        d_num = (ann * s + d_p * n_coins) * d
        d_den = (ann - 1) * d + (n_coins + 1) * d_p
        d = d_num // d_den

        if abs(d_prev - d) <= 1:
            return d

    raise DidNotConvergeException("D didn't converge")


def y(amp: int, amounts: List[int], i_token_in: int, i_token_out: int, token_in_balance: int):
    """
    Calculate x[j] if one makes x[i] = x

    Done by solving quadratic equation iteratively.
    x_1**2 + x1 * (sum' - (A*n**n - 1) * D / (A * n**n)) = D ** (n + 1) / (n ** (2 * n) * prod' * A)
    x_1**2 + b*x_1 = c

    x_1 = (x_1**2 + c) / (2*x_1 + b)

    Reference: https://github.com/curvefi/curve-contract/blob/7116b4a261580813ef057887c5009e22473ddb7d/tests/simulation.py#L55
    """
    n_coins = len(amounts)
    d = D(amp, amounts)
    ann = amp * n_coins

    amounts[i_token_in] = token_in_balance
    amounts = [amounts[k] for k in range(n_coins) if k != i_token_out]

    c = d

    for y in amounts:
        c = c * d // (y * n_coins)
    c = c * d // (n_coins * ann)
    b = sum(amounts) + d // ann - d

    y_prev = 0
    y = d
    i = 0
    while i < MAX_ITERS and abs(y - y_prev) > 1:
        i += 1
        y_prev = y
        y = (y ** 2 + c) // (2 * y + b)

        if abs(y_prev - y) <= 1:
            return y

    raise DidNotConvergeException("y didn't converge")


def y_D(amp: int, amounts: List[int], i: int, _D: int):
    """
    Calculate x[j] if one makes x[i] = x

    Done by solving quadratic equation iteratively.
    x_1**2 + x1 * (sum' - (A*n**n - 1) * D / (A * n**n)) = D ** (n + 1) / (n ** (2 * n) * prod' * A)
    x_1**2 + b*x_1 = c

    x_1 = (x_1**2 + c) / (2*x_1 + b)

    Reference: https://github.com/curvefi/curve-contract/blob/7116b4a261580813ef057887c5009e22473ddb7d/tests/simulation.py#L82
    """
    n_coins = len(amounts)

    xx = [amounts[k] for k in range(n_coins) if k != i]
    S = sum(xx)
    Ann = amp * n_coins
    c = _D
    for y in xx:
        c = c * _D // (y * n_coins)
    c = c * _D // (n_coins * Ann)
    b = S + _D // Ann
    y_prev = 0
    y = _D
    while i < MAX_ITERS and abs(y - y_prev) > 1:
        y_prev = y
        y = (y ** 2 + c) // (2 * y + b - _D)
    return y  # the result is in underlying units too
