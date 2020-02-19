from .hashes import hash32_func, hash_all_func

node_flag_compression_type_mask = 0xFF
node_flag_compression_type_shift = 0
node_flag_compression_flag_mask = 0xFF00
node_flag_compression_flag_shift = 8
node_flag_v_hash_type_mask = 0x3 << 16
node_flag_v_hash_type_4 = 0x1 << 16
node_flag_v_hash_type_6 = 0x2 << 16
node_flag_v_hash_type_8 = 0x3 << 16

node_flag_temporary_file = 1 << 20
node_flag_processed_file_raw_no_name = 1 << 21
node_flag_processed_file_raw_with_name = 1 << 22
node_flag_processed_file_type = 1 << 23
node_flag_processed_file_specific = 1 << 24


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
