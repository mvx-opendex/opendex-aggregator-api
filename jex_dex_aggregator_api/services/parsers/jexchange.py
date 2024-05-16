
from jex_dex_aggregator_api.services.parsers.common import (parse_address, parse_amount,
                                                            parse_token_identifier, parse_uint8, parse_uint32)

from jex_dex_aggregator_api.data.model import (JexCpLpStatus,
                                               JexDeployedPoolContract,
                                               JexStablePoolStatus)


def parse_jex_cp_lp_status(sc_address: str, hex_: str) -> JexCpLpStatus:
    offset = 0

    paused, read = parse_uint8(hex_[offset:])
    offset += read

    first_token, read = parse_token_identifier(hex_[offset:])
    offset += read

    first_token_reserve, read = parse_amount(hex_[offset:])
    offset += read

    second_token, read = parse_token_identifier(hex_[offset:])
    offset += read

    second_token_reserve, read = parse_amount(hex_[offset:])
    offset += read

    lp_token, read = parse_token_identifier(hex_[offset:])
    offset += read

    lp_token_supply, read = parse_amount(hex_[offset:])
    offset += read

    owner, read = parse_address(hex_[offset:])
    offset += read

    lp_fees, read = parse_uint32(hex_[offset:])
    offset += read

    platform_fees, read = parse_uint32(hex_[offset:])
    offset += read

    is_platform_fees_receiver, read = parse_uint8(hex_[offset:])
    offset += read

    if is_platform_fees_receiver == 0x01:
        platform_fees_receiver, read = parse_address(hex_[offset:])
        platform_fees_receiver = platform_fees_receiver.bech32()
        offset += read
    else:
        platform_fees_receiver = None

    vol_first_token, read = parse_amount(hex_[offset:])
    offset += read

    vol_second_token, read = parse_amount(hex_[offset:])
    offset += read

    fees_first_token, read = parse_amount(hex_[offset:])
    offset += read

    fees_second_token, read = parse_amount(hex_[offset:])
    offset += read

    fees_7_epochs_first_token, read = parse_amount(hex_[offset:])
    offset += read

    fees_7_epochs_second_token, read = parse_amount(hex_[offset:])
    offset += read

    return JexCpLpStatus(sc_address=sc_address,
                         paused=paused == 1,
                         first_token_identifier=first_token,
                         first_token_reserve=str(first_token_reserve),
                         second_token_identifier=second_token,
                         second_token_reserve=str(second_token_reserve),
                         lp_token_identifier=lp_token,
                         lp_token_supply=str(lp_token_supply),
                         owner=owner.bech32(),
                         lp_fees=lp_fees,
                         platform_fees=platform_fees,
                         platform_fees_receiver=platform_fees_receiver,
                         volume_prev_epoch=[str(vol_first_token),
                                            str(vol_second_token)],
                         fees_prev_epoch=[str(fees_first_token),
                                          str(fees_second_token)],
                         fees_last_7_epochs=[str(fees_7_epochs_first_token),
                                             str(fees_7_epochs_second_token)])


def parse_jex_stablepool_status(sc_address: str, hex_: str) -> JexStablePoolStatus:
    offset = 0

    paused, read = parse_uint8(hex_[offset:])
    offset += read

    amp_factor, read = parse_uint32(hex_[offset:])
    offset += read

    nb_tokens, read = parse_uint32(hex_[offset:])
    offset += read

    tokens = []
    offset += 8
    for _ in range(nb_tokens):
        token_id, read = parse_token_identifier(hex_[offset:])
        offset += read
        tokens.append(token_id)

    reserves = []
    offset += 8
    for _ in range(nb_tokens):
        reserve, read = parse_amount(hex_[offset:])
        offset += read
        reserves.append(str(reserve))

    lp_token, read = parse_token_identifier(hex_[offset:])
    offset += read

    lp_token_supply, read = parse_amount(hex_[offset:])
    offset += read

    owner, read = parse_address(hex_[offset:])
    offset += read

    swap_fee, read = parse_uint32(hex_[offset:])
    offset += read

    is_platform_fees_receiver, read = parse_uint8(hex_[offset:])
    offset += read

    if is_platform_fees_receiver == 0x01:
        platform_fees_receiver, read = parse_address(hex_[offset:])
        platform_fees_receiver = platform_fees_receiver.bech32()
        offset += read
    else:
        platform_fees_receiver = None

    volumes = []
    offset += 8
    for _ in range(nb_tokens):
        vol, read = parse_amount(hex_[offset:])
        offset += read
        volumes.append(str(vol))

    fees = []
    offset += 8
    for _ in range(nb_tokens):
        fee, read = parse_amount(hex_[offset:])
        offset += read
        fees.append(str(fee))

    fees_7 = []
    offset += 8
    for _ in range(nb_tokens):
        fee_7, read = parse_amount(hex_[offset:])
        offset += read
        fees_7.append(str(fee_7))

    underlying_prices = []
    offset += 8
    if offset < len(hex_):
        for _ in range(nb_tokens):
            underlying_price, read = parse_amount(hex_[offset:])
            offset += read
            underlying_prices.append(str(underlying_price))
    else:
        underlying_prices = [str(10**18)] * nb_tokens

    return JexStablePoolStatus(sc_address=sc_address,
                               paused=paused,
                               amp_factor=amp_factor,
                               nb_tokens=nb_tokens,
                               tokens=tokens,
                               reserves=reserves,
                               lp_token_identifier=lp_token,
                               lp_token_supply=str(lp_token_supply),
                               owner=owner.bech32(),
                               swap_fee=swap_fee,
                               platform_fees_receiver=platform_fees_receiver,
                               volume_prev_epoch=volumes,
                               fees_prev_epoch=fees,
                               fees_last_7_epochs=fees_7,
                               underlying_prices=underlying_prices)


def parse_jex_deployed_contract(hex_) -> JexDeployedPoolContract:
    offset = 0

    sc_type, read = parse_uint8(hex_[offset:])
    offset += read

    sc_address, read = parse_address(hex_[offset:])
    offset += read

    owner, read = parse_address(hex_[offset:])
    offset += read

    return JexDeployedPoolContract(sc_type=sc_type,
                                   sc_address=sc_address.bech32(),
                                   owner=owner.bech32())
