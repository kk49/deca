from sys import platform
if any([platform.startswith(os_name) for os_name in ['linux', 'darwin', 'freebsd']]):
    import zugbruecke.ctypes as ctypes
    is_zug = True
elif platform.startswith('win'):
    import ctypes
    is_zug = False
else:
    raise Exception('Platform not handled {}'.format(platform))


class DecompressorOodleLZ:
    def __init__(self, dll_path=None):
        self._dll_path = dll_path
        self._zug_session = None
        self._dll = None
        self._decompress = None

    def __del__(self):
        self.shutdown()

    def shutdown(self):
        self._decompress = None
        self._dll = None
        if self._zug_session is not None:
            self._zug_session.terminate()
            self._zug_session = None

    def prepare_library(self):
        if self._dll is not None:
            pass
        elif self._dll_path is None:
            raise NotImplementedError('Missing oogle lz decompressor dll')
        else:
            if is_zug:
                self._zug_session = ctypes.session(parameter={"log_level": 0, "arch": "win64"})
                self._dll = self._zug_session.load_library(self._dll_path, 'windll')
            else:
                self._dll = ctypes.windll.LoadLibrary(self._dll_path)

            self._decompress = self._dll.OodleLZ_Decompress

            # self.decompress.argtypes = (
            #     ctypes.c_char_p, ctypes.c_uint64, ctypes.c_char_p, ctypes.c_uint64,
            #     ctypes.c_int32, ctypes.c_uint32, ctypes.c_int32, ctypes.POINTER(ctypes.c_uint64),
            #     ctypes.c_int64, ctypes.POINTER(ctypes.c_uint64), ctypes.c_uint64, ctypes.POINTER(ctypes.c_int64),
            #     ctypes.c_uint64, ctypes.c_uint32)

            self._decompress.argtypes = (
                ctypes.c_char_p, ctypes.c_uint64, ctypes.c_char_p, ctypes.c_uint64,
                ctypes.c_int32, ctypes.c_uint32, ctypes.c_int32, ctypes.c_uint64,
                ctypes.c_int64, ctypes.c_uint64, ctypes.c_uint64, ctypes.c_uint64,
                ctypes.c_uint64, ctypes.c_uint32)

            self._decompress.restype = ctypes.c_uint64

            self._decompress.memsync = [
                {'p': [0], 'l': [1], 't': 'c_char', },
                {'p': [2], 'l': [3], 't': 'c_char', },
            ]

    def decompress(self, in_buffer, in_len, out_len):
        self.prepare_library()
        assert len(in_buffer) >= in_len
        in_buffer = ctypes.create_string_buffer(in_buffer)
        out_buffer = ctypes.create_string_buffer(out_len)
        # p0 = ctypes.POINTER(ctypes.c_uint64)()
        # p1 = ctypes.POINTER(ctypes.c_uint64)()
        # p2 = ctypes.POINTER(ctypes.c_int64)()
        p0 = 0  # ctypes.POINTER(ctypes.c_uint64)()
        p1 = 0  # ctypes.POINTER(ctypes.c_uint64)()
        p2 = 0  # ctypes.POINTER(ctypes.c_int64)()

        ret = self._decompress(
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