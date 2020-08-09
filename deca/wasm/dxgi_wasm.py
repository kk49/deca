import time
import os
import sys
import wasmer
from deca.fast_file import *

wasm_process_image_lib = None
wasm_process_image_func = None


# https://docs.microsoft.com/en-us/windows/desktop/direct3d9/opaque-and-1-bit-alpha-textures
# https://msdn.microsoft.com/ja-jp/library/bb173059(v=vs.85).aspx
# https://docs.microsoft.com/en-us/windows/win32/api/dxgiformat/ne-dxgiformat-dxgi_format
# less than 32 bit floats
#   https://docs.microsoft.com/en-us/windows/win32/direct3d10/d3d10-graphics-programming-guide-resources-float-rules


def process_image_wasm(image, raw, nx, ny, pixel_format):
    if pixel_format in {2, 10, 26, 41}:  # do floating point loads in python
        return -1  # use python
    else:
        global wasm_process_image_func
        global wasm_process_image_lib

        t0 = time.time()
        raw_wasm_offset = wasm_process_image_lib.exports.alloc_bin(len(raw))
        image_wasm_offset = wasm_process_image_lib.exports.alloc_bout(image.size)

        raw_wasm = wasm_process_image_lib.memory.uint8_view(raw_wasm_offset)
        raw_wasm[:len(raw)] = raw[:]

        t1 = time.time()
        ret = wasm_process_image_func(
            image_wasm_offset,
            image.size,
            raw_wasm_offset,
            len(raw),
            nx,
            ny,
            pixel_format)

        t2 = time.time()
        # t2 = t1
        image_wasm = memoryview(wasm_process_image_lib.memory.buffer)[image_wasm_offset:image_wasm_offset+image.size]
        image[:] = np.frombuffer(image_wasm, dtype=image.dtype).reshape(image.shape)

        t3 = time.time()

        print(f'WASM Time {t3 - t0} =  {t1 - t0} + {t2 - t1} + {t3 - t2}')

        if ret == -1:
            return -1  # use python
        elif ret != 0:
            raise Exception('process_image_wasm failed with return {}'.format(ret))


def setup_image_wasm():
    global wasm_process_image_lib
    global wasm_process_image_func

    wasm_process_image_lib = None
    exe_path, exe_name = os.path.split(sys.argv[0])
    if len(exe_path) == 0:
        exe_path = '.'

    if os.path.isfile(os.path.join(exe_path, 'deca/wasm/dxgi.wasm')):
        with open(os.path.join(exe_path, 'deca/wasm/dxgi.wasm'), 'rb') as f:
            wasm_bytes = f.read()
        wasm_process_image_lib = wasmer.Instance(wasm_bytes)
        wasm_process_image_func = wasm_process_image_lib.exports.process_image

        return process_image_wasm
