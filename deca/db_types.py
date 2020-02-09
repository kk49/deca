import os
from .hashes import hash32_func, hash_all_func


def to_bytes(s):
    if isinstance(s, str):
        s = s.encode('ascii', 'ignore')
    return s


def to_str(s):
    if isinstance(s, bytes):
        s = s.decode('utf-8')
    return s


def make_hash_string_tuple(string):
    string = to_bytes(string)

    period_pos = string.rfind(b'.')

    if period_pos >= 0:
        ext_string = string[period_pos:]
    else:
        ext_string = b''

    ext_hash32 = hash32_func(ext_string)
    hash32, hash48, hash64 = hash_all_func(string)

    return string, hash32, hash48, hash64, ext_hash32
