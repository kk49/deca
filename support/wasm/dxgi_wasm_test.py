import wasmer
import time

with open('dxgi.wasm', 'rb') as f:
    wasm_bytes = f.read()

instance = wasmer.Instance(wasm_bytes)
print(len(memoryview(instance.memory.buffer)))

print(instance.exports.sum(4, 5))

'''
u8 * dst_image_buf,
u32 dst_image_sz,
u8 const * src_buffer_buf,
u32 src_buffer_sz,
u32 nx,
u32 ny,
u32 pixel_format
'''

t0 = time.time()
v = instance.exports.process_image(0, 0, 0, 0, 128, 128, 71)
t1 = time.time()

print(f'Time: {t1-t0}, Return {v}:')



