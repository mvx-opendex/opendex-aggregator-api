
from jex_dex_aggregator_api.data.model import HatomMoneyMarket
from jex_dex_aggregator_api.services.parsers.common import (
    parse_address, parse_amount, parse_token_identifier)


def parse_hatom_mm(hex_) -> HatomMoneyMarket:
    offset = 0

    sc_address, read = parse_address(hex_[offset:])
    offset += read

    hatom_token_id, read = parse_token_identifier(hex_[offset:])
    offset += read

    underlying_id, read = parse_token_identifier(hex_[offset:])
    offset += read

    cash, read = parse_amount(hex_[offset:])
    offset += read

    tokens_to_underlying, read = parse_amount(hex_[offset:])
    offset += read

    underlying_to_tokens, read = parse_amount(hex_[offset:])
    offset += read

    return HatomMoneyMarket(sc_address=sc_address.bech32(),
                            hatom_token_id=hatom_token_id,
                            underlying_id=underlying_id,
                            cash=cash,
                            ratio_tokens_to_underlying=tokens_to_underlying,
                            ratio_underlying_to_tokens=underlying_to_tokens)
