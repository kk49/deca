from sys import platform
if any([platform.startswith(os_name) for os_name in ['linux', 'darwin', 'freebsd']]):
    with open('.zugbruecke.json', 'w') as f:
        f.write('{"log_level": 0, "arch": "win64"}')

    import zugbruecke as ctypes
elif platform.startswith('win'):
    import ctypes
else:
    raise Exception('Platform not handled {}'.format(platform))

oodll = ctypes.windll.LoadLibrary('/home/krys/.steam/steam/steamapps/common/Just Cause 4/oo2core_7_win64.dll')

oo_decompress = oodll.OodleLZ_Decompress

# oo_decompress.argtypes = (
#     ctypes.c_char_p, ctypes.c_uint64, ctypes.c_char_p, ctypes.c_uint64,
#     ctypes.c_int32, ctypes.c_uint32, ctypes.c_int32, ctypes.POINTER(ctypes.c_uint64),
#     ctypes.c_int64, ctypes.POINTER(ctypes.c_uint64), ctypes.c_uint64, ctypes.POINTER(ctypes.c_int64),
#     ctypes.c_uint64, ctypes.c_uint32)

oo_decompress.argtypes = (
    ctypes.c_char_p, ctypes.c_uint64, ctypes.c_char_p, ctypes.c_uint64,
    ctypes.c_int32, ctypes.c_uint32, ctypes.c_int32, ctypes.c_uint64,
    ctypes.c_int64, ctypes.c_uint64, ctypes.c_uint64, ctypes.c_uint64,
    ctypes.c_uint64, ctypes.c_uint32)

oo_decompress.restype = ctypes.c_uint64

oo_decompress.memsync = [
    {'p': [0], 'l': [1], 't': 'c_char', },
    {'p': [2], 'l': [3], 't': 'c_char', },
]


def apex_oo_decompress(in_buffer, in_len, out_len):
    assert len(in_buffer) >= in_len
    in_buffer = ctypes.create_string_buffer(in_buffer)
    out_buffer = ctypes.create_string_buffer(out_len)
    # p0 = ctypes.POINTER(ctypes.c_uint64)()
    # p1 = ctypes.POINTER(ctypes.c_uint64)()
    # p2 = ctypes.POINTER(ctypes.c_int64)()
    p0 = 0  # ctypes.POINTER(ctypes.c_uint64)()
    p1 = 0  # ctypes.POINTER(ctypes.c_uint64)()
    p2 = 0  # ctypes.POINTER(ctypes.c_int64)()

    ret = oo_decompress(
        in_buffer, in_len, out_buffer, out_len,
        1, 0, 0, p0,
        0, p1, 0, p2,
        0, 3
    )
    out_buffer = out_buffer.raw
    return out_buffer, ret

'''
OodleLZ_Decompress(
    param_2,param_3,param_4,*param_5,
    1,0,0,0,
    0,0,0,0,
    0,3);
'''