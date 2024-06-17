from typing import List, Tuple

from opendex_aggregator_api.data.model import VestaDexPool
from opendex_aggregator_api.services.parsers.common import (
    parse_address, parse_amount, parse_nested_str, parse_token_identifier, parse_uint8,
    parse_uint32, parse_uint64)


def parse_vestadex_view_pools(hex_: str) -> List[VestaDexPool]:
    pools = []

    offset = 0
    while offset < len(hex_):
        pool, read = parse_vestadex_pool(hex_[offset:])
        offset += read

        pools.append(pool)

    return pools


def parse_vestadex_pool(hex_: str) -> Tuple[VestaDexPool, int]:
    offset = 0

    sc_address, read = parse_address(hex_[offset:])
    offset += read

    state, read = parse_uint8(hex_[offset:])
    offset += read

    first_token_identifier, read = parse_token_identifier(hex_[offset:])
    offset += read

    second_token_identifier, read = parse_token_identifier(hex_[offset:])
    offset += read

    first_token_reserve, read = parse_amount(hex_[offset:])
    offset += read

    second_token_reserve, read = parse_amount(hex_[offset:])
    offset += read

    lp_token_identifier, read = parse_token_identifier(hex_[offset:])
    offset += read

    lp_token_supply, read = parse_amount(hex_[offset:])
    offset += read

    # skip
    offset += 2

    fee_token_id, read = parse_token_identifier(hex_[offset:])
    offset += read

    total_fee_percentage, read = parse_uint64(hex_[offset:])
    offset += read

    special_fee_percentage, read = parse_uint64(hex_[offset:])
    offset += read

    nb_fee_collector_addresses, read = parse_uint32(hex_[offset:])
    offset += read

    for _ in range(0, nb_fee_collector_addresses):
        _, read = parse_fee_receiver(hex_[offset:])
        offset += read

    is_router_address, read = parse_uint8(hex_[offset:])
    offset += read
    if is_router_address == 1:
        offset += 64  # skip router address

    is_initial_liquidity_address, read = parse_uint8(hex_[offset:])
    offset += read
    if is_initial_liquidity_address == 1:
        offset += 64  # skip initial liquidity address

    return VestaDexPool(first_token_id=first_token_identifier,
                        first_token_reserve=str(first_token_reserve),
                        pool_address=sc_address.bech32(),
                        pool_state=state,
                        second_token_id=second_token_identifier,
                        second_token_reserve=str(second_token_reserve),
                        lp_token_id=lp_token_identifier,
                        lp_token_supply=str(lp_token_supply),
                        fee_token_id=fee_token_id,
                        total_fee_percentage=total_fee_percentage,
                        special_fee_percentage=special_fee_percentage), offset


def parse_fee_receiver(hex_: str):
    offset = 0

    address, read = parse_address(hex_[offset:])
    offset += read

    shares, read = parse_uint64(hex_[offset:])
    offset += read

    is_method, read = parse_uint8(hex_[offset:])
    offset += read

    if is_method == 1:
        method, read = parse_nested_str(hex_[offset:])
        offset += read
    else:
        method = None

    return (address, shares), offset
