from typing import Tuple

from opendex_aggregator_api.services.parsers.common import (
    parse_amount, parse_token_identifier)


def parse_evaluate_response(hex_: str) -> Tuple[int, int, str]:
    idx = 0

    net_amount_out, read = parse_amount(hex_[idx:])
    idx += read

    fee, read = parse_amount(hex_[idx:])
    idx += read

    fee_token, _ = parse_token_identifier(hex_[idx:])

    return (net_amount_out, fee, fee_token)
