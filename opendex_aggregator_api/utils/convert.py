
import codecs
from typing import Optional


def hex2dec(hex_):
    return int(hex_, 16)


def str2hex(str_):
    return codecs.encode(bytes(str_, 'ascii'), 'hex').decode("ascii")


def hex2str(hex_):
    return codecs.decode(bytes(hex_, 'ascii'), 'hex').decode("ascii")


def int2hex(int_: int, size: Optional[int] = None):
    hex_ = hex(int_)[2:]
    len_ = len(hex_)
    if size is None:
        size = len_ if len_ % 2 == 0 else len_ + 1
    return hex(int_)[2:].rjust(size, '0')


def int2hex_even_size(int_: int) -> str:
    val = int2hex(int_)

    if len(val) % 2 == 0:
        return val

    return val.ljust(len(val)+1, '0')
