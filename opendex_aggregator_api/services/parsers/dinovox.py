
from opendex_aggregator_api.data.model import DinoVoxLpStatus
from opendex_aggregator_api.services.parsers.common import (
    parse_address, parse_amount, parse_token_identifier, parse_uint8,
    parse_uint64)


def parse_dinovox_lp_status(hex_: str) -> DinoVoxLpStatus:
    offset = 0

    sc_address, read = parse_address(hex_[offset:])
    offset += read

    is_active, read = parse_uint8(hex_[offset:])
    offset += read

    token_a, read = parse_token_identifier(hex_[offset:])
    offset += read

    token_b, read = parse_token_identifier(hex_[offset:])
    offset += read

    token_a_reserve, read = parse_amount(hex_[offset:])
    offset += read

    token_b_reserve, read = parse_amount(hex_[offset:])
    offset += read

    lp_token, read = parse_token_identifier(hex_[offset:])
    offset += read

    lp_supply, read = parse_amount(hex_[offset:])
    offset += read

    total_fee_percent, read = parse_uint64(hex_[offset:])
    offset += read

    protocol_fee_pct, read = parse_uint64(hex_[offset:])
    offset += read

    return DinoVoxLpStatus(sc_address=sc_address.bech32(),
                           is_active=is_active == 1,
                           token_a=token_a,
                           token_b=token_b,
                           token_a_reserve=token_a_reserve,
                           token_b_reserve=token_b_reserve,
                           lp_token=lp_token,
                           lp_supply=lp_supply,
                           total_fee_percent=total_fee_percent,
                           protocol_fee_pct=protocol_fee_pct)
