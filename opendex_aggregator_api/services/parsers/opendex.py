from opendex_aggregator_api.data.model import OpendexPair
from opendex_aggregator_api.services.parsers.common import (
    parse_address, parse_amount, parse_token_identifier, parse_uint8,
    parse_uint32)


def parse_opendex_pool(hex_: str) -> OpendexPair:
    offset = 0

    sc_address, read = parse_address(hex_[offset:])
    offset += read

    owner, read = parse_address(hex_[offset:])
    offset += read

    paused, read = parse_uint8(hex_[offset:])
    offset += read

    first_token_id, read = parse_token_identifier(hex_[offset:])
    offset += read

    first_token_reserve, read = parse_amount(hex_[offset:])
    offset += read

    second_token_id, read = parse_token_identifier(hex_[offset:])
    offset += read

    second_token_reserve, read = parse_amount(hex_[offset:])
    offset += read

    lp_token_id, read = parse_token_identifier(hex_[offset:])
    offset += read

    lp_token_mint_burn_enabled, read = parse_uint8(hex_[offset:])
    offset += read

    lp_token_supply, read = parse_amount(hex_[offset:])
    offset += read

    total_fee_percent, read = parse_uint32(hex_[offset:])
    offset += read

    platform_fee_percent, read = parse_uint32(hex_[offset:])
    offset += read

    platform_fee_receiver, read = parse_address(hex_[offset:])
    offset += read

    fee_token_id_is_set, read = parse_uint8(hex_[offset:])
    offset += read

    if fee_token_id_is_set:
        fee_token_id, read = parse_token_identifier(hex_[offset:])
        offset += read
    else:
        fee_token_id = None

    return OpendexPair(sc_address=sc_address.bech32(),
                       owner=owner.bech32(),
                       paused=paused == 1,
                       first_token_id=first_token_id,
                       first_token_reserve=first_token_reserve,
                       second_token_id=second_token_id,
                       second_token_reserve=second_token_reserve,
                       lp_token_id=lp_token_id,
                       lp_token_mint_burn_enabled=lp_token_mint_burn_enabled,
                       lp_token_supply=lp_token_supply,
                       total_fee_percent=total_fee_percent,
                       platform_fee_percent=platform_fee_percent,
                       platform_fee_receiver=platform_fee_receiver.bech32(),
                       fee_token_id=fee_token_id)
