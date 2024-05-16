
from jex_dex_aggregator_api.data.model import (AshSwapStablePoolStatus,
                                               AshSwapV2PoolStatus)
from jex_dex_aggregator_api.services.parsers.common import (
    parse_address, parse_amount, parse_token_identifier, parse_uint8,
    parse_uint32, parse_uint64)


def parse_ashswap_stablepool_status(hex_: str) -> AshSwapStablePoolStatus:
    offset = 0

    sc_address, read = parse_address(hex_[offset:])
    offset += read

    state, read = parse_uint8(hex_[offset:])
    offset += read

    amp_factor, read = parse_uint32(hex_[offset:])
    offset += read

    lp_token_id, read = parse_token_identifier(hex_[offset:])
    offset += read

    lp_token_supply, read = parse_amount(hex_[offset:])
    offset += read

    nb_tokens, read = parse_uint32(hex_[offset:])
    offset += read

    tokens = []
    for _ in range(nb_tokens):
        token, read = parse_token_identifier(hex_[offset:])
        offset += read

        tokens.append(token)

    nb_underlying_prices, read = parse_uint32(hex_[offset:])
    offset += read

    underlying_prices = []
    for _ in range(nb_underlying_prices):
        underlying_price, read = parse_amount(hex_[offset:])
        offset += read

        underlying_prices.append(underlying_price)

    nb_reserves, read = parse_uint32(hex_[offset:])
    offset += read

    reserves = []
    for _ in range(nb_reserves):
        reserve, read = parse_amount(hex_[offset:])
        offset += read

        reserves.append(reserve)

    swap_fee_percent, read = parse_uint32(hex_[offset:])
    offset += read

    return AshSwapStablePoolStatus(sc_address=sc_address.bech32(),
                                   state=state,
                                   amp_factor=amp_factor,
                                   lp_token_id=lp_token_id,
                                   lp_token_supply=lp_token_supply,
                                   tokens=tokens,
                                   underlying_prices=underlying_prices,
                                   reserves=reserves,
                                   swap_fee_percent=swap_fee_percent)


def parse_ashswap_v2_pool_status(hex_: str) -> AshSwapV2PoolStatus:
    offset = 0

    sc_address, read = parse_address(hex_[offset:])
    offset += read

    state, read = parse_uint8(hex_[offset:])
    offset += read

    amp_factor, read = parse_amount(hex_[offset:])
    offset += read

    d, read = parse_amount(hex_[offset:])
    offset += read

    fee_gamma, read = parse_amount(hex_[offset:])
    offset += read

    future_a_gamma_time, read = parse_uint64(hex_[offset:])
    offset += read

    gamma, read = parse_amount(hex_[offset:])
    offset += read

    mid_fee, read = parse_amount(hex_[offset:])
    offset += read

    out_fee, read = parse_amount(hex_[offset:])
    offset += read

    price_scale, read = parse_amount(hex_[offset:])
    offset += read

    nb_reserves, read = parse_uint32(hex_[offset:])
    offset += read

    reserves = []
    for _ in range(nb_reserves):
        reserve, read = parse_amount(hex_[offset:])
        offset += read

        reserves.append(reserve)

    nb_tokens, read = parse_uint32(hex_[offset:])
    offset += read

    tokens = []
    for _ in range(nb_tokens):
        token, read = parse_token_identifier(hex_[offset:])
        offset += read

        tokens.append(token)

    nb_xps, read = parse_uint32(hex_[offset:])
    offset += read

    xps = []
    for _ in range(nb_xps):
        xp, read = parse_amount(hex_[offset:])
        offset += read

        xps.append(xp)

    return AshSwapV2PoolStatus(sc_address=sc_address.bech32(),
                               state=state,
                               amp_factor=amp_factor,
                               d=d,
                               fee_gamma=fee_gamma,
                               future_a_gamma_time=future_a_gamma_time,
                               gamma=gamma,
                               mid_fee=mid_fee,
                               out_fee=out_fee,
                               price_scale=price_scale,
                               reserves=reserves,
                               tokens=tokens,
                               xp=xps)
