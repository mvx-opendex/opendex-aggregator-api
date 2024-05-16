
import codecs


def hex2dec(hex_):
    return int(hex_, 16)


def str2hex(str_):
    return codecs.encode(bytes(str_, 'ascii'), 'hex').decode("ascii")


def hex2str(hex_):
    return codecs.decode(bytes(hex_, 'ascii'), 'hex').decode("ascii")
