
from multiversx_sdk_core import Address

from jex_dex_aggregator_api.utils.convert import hex2dec, hex2str


def parse_address(hex_):
    # logging.debug(f'parse_address({hex_})')
    address = hex_[:64]
    address = Address.from_hex(address, 'erd')
    return address, 64


def parse_nested_str(hex_):
    offset = 0
    len = int(hex_[:8], 16)
    offset += 8
    string = hex_[offset:offset+(2*len)]
    string = hex2str(string)
    offset += 2*len
    return string, offset


parse_token_identifier = parse_nested_str


def parse_uint8(hex_):
    # logging.debug(f'parse_uint8({hex_})')
    return int(hex_[:2], 16), 2


def parse_uint16(hex_):
    # logging.debug(f'parse_uint16({hex_})')
    return int(hex_[:4], 16), 4


def parse_uint32(hex_):
    # logging.debug(f'parse_uint32({hex_})')
    return int(hex_[:8], 16), 8


def parse_uint64(hex_):
    # logging.debug(f'parse_uint64({hex_})')
    return int(hex_[:16], 16), 16


parse_nonce = parse_uint64


def parse_opt_uint64(hex_):
    offset = 0
    present = hex_[:2]
    offset += 2
    if present == '01':
        address, read = parse_uint64(hex_[offset:])
        offset += read
        return address, offset
    return None, offset


def parse_amount(hex_):
    # logging.debug(f'parse_amount({hex_})')
    len, offset = parse_uint32(hex_)
    amount = hex_[offset:offset+(2*len)] if len > 0 else '0'
    amount = hex2dec(amount)
    offset += 2*len
    return amount, offset
