from opendex_aggregator_api.data.model import XExchangePoolStatus
from opendex_aggregator_api.services.parsers.common import (
    parse_address, parse_amount, parse_token_identifier, parse_uint8,
    parse_uint32, parse_uint64)


def parse_xexchange_pool_status(hex_: str) -> XExchangePoolStatus:
    offset = 0

    sc_address, read = parse_address(hex_[offset:])
    offset += read

    state, read = parse_uint8(hex_[offset:])
    offset += read

    first_token_id, read = parse_token_identifier(hex_[offset:])
    offset += read

    second_token_id, read = parse_token_identifier(hex_[offset:])
    offset += read

    first_token_reserve, read = parse_amount(hex_[offset:])
    offset += read

    second_token_reserve, read = parse_amount(hex_[offset:])
    offset += read

    lp_token_supply, read = parse_amount(hex_[offset:])
    offset += read

    total_fee_percent, read = parse_uint32(hex_[offset:])
    offset += read

    special_fee_percent, read = parse_uint64(hex_[offset:])
    offset += read

    return XExchangePoolStatus(sc_address=sc_address.bech32(),
                               state=state,
                               first_token_id=first_token_id,
                               second_token_id=second_token_id,
                               first_token_reserve=first_token_reserve,
                               second_token_reserve=second_token_reserve,
                               lp_token_supply=lp_token_supply,
                               total_fee_percent=total_fee_percent,
                               special_fee_percent=special_fee_percent)
