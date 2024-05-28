from typing import List

from opendex_aggregator_api.data.model import OneDexPair
from opendex_aggregator_api.services.parsers.common import (
    parse_amount, parse_token_identifier, parse_uint8, parse_uint32)


def parse_onedex_pair(hex_: str) -> OneDexPair:
    offset = 0

    id_, read = parse_uint32(hex_[offset:])
    offset += read

    state, read = parse_uint8(hex_[offset:])
    offset += read

    # skip enabled + owner
    offset += 2 + 64

    first_token_identifier, read = parse_token_identifier(hex_[offset:])
    offset += read

    second_token_identifier, read = parse_token_identifier(hex_[offset:])
    offset += read

    lp_token_identifier, read = parse_token_identifier(hex_[offset:])
    offset += read

    lp_token_decimals, read = parse_uint32(hex_[offset:])
    offset += read

    first_token_reserve, read = parse_amount(hex_[offset:])
    offset += read

    second_token_reserve, read = parse_amount(hex_[offset:])
    offset += read

    lp_supply, read = parse_amount(hex_[offset:])
    offset += read

    return OneDexPair(id_=id_,
                      state=state,
                      first_token_identifier=first_token_identifier,
                      first_token_reserve=first_token_reserve,
                      lp_supply=lp_supply,
                      lp_token_decimals=lp_token_decimals,
                      lp_token_identifier=lp_token_identifier,
                      second_token_identifier=second_token_identifier,
                      second_token_reserve=second_token_reserve)
