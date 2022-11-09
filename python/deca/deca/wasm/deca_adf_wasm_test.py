import time
import pprint
from deca_adf_lib import DecaAdfWasm

lib = DecaAdfWasm()

print(f'wasm memory size = {len(memoryview(lib.instance().memory.buffer))}')

test_files = [
    [5, 'test_data/animal_population_0'],
    [0, 'test_data/pistol_sa_22_01_a.modelc'],
    [0, 'test_data/savegame'],
]

for skip_bytes, fn in test_files:
    with open(fn, 'rb') as f:
        input_buffer = f.read()
    input_sz = len(input_buffer)

    lib.adf_stack = []

    t0 = time.time()

    input_wasm_offset = lib.instance().exports.alloc_bin(input_sz)

    t1 = time.time()

    input_wasm = lib.instance().memory.uint8_view(input_wasm_offset)
    input_wasm[:input_sz] = input_buffer[:]

    t2 = time.time()

    value = lib.instance().exports.process_adf(input_wasm_offset + skip_bytes, input_sz - skip_bytes)

    t3 = time.time()

    # pprint.pprint(lib.adf_stack)

    adf = lib.adf_stack.pop()

    print(f'{fn}, value = {value}, Time: {t3-t0} = {t1-t0} + {t2-t1} + {t3-t2}')
