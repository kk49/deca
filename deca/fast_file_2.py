from typing import List
import numpy as np
from numba import njit, jit


class FFError(Exception):
    pass


params = {
    'inline': 'always',
    'nogil': True,
}

@njit
def raise_error():
    raise FFError('ff_read: not enough data')


@njit(**params)
def ff_read(bufn, pos, n):
    # buffer = ff
    # n_buffer = len(buffer)

    if bufn[1] >= (pos + n):
        ret = bufn[0][pos:(pos + n)]
        return ret, pos + n
    else:
        return raise_error()


def make_read_one(data_type):
    dt = np.dtype(data_type)
    ele_size = dt.itemsize

    @njit(**params)
    def f(bufn, pos):
        new_pos = pos + ele_size
        if new_pos > bufn[1]:
            raise_error()
        v = np.frombuffer(bufn[0][pos:new_pos], dtype=dt)
        return v[0], new_pos

    return f


def make_read_many(data_type):
    dt = np.dtype(data_type)
    ele_size = dt.itemsize

    @njit(**params)
    def f(bufn, pos, count):
        new_pos = pos + ele_size * count
        if new_pos > bufn[1]:
            raise_error()
        v = np.frombuffer(bufn[0][pos:new_pos], dtype=dt)
        return list(v), new_pos

    return f


ff_read_u8 = make_read_one(np.uint8)
ff_read_s8 = make_read_one(np.int8)
ff_read_u16 = make_read_one(np.uint16)
ff_read_s16 = make_read_one(np.int16)
ff_read_u32 = make_read_one(np.uint32)
ff_read_s32 = make_read_one(np.int32)
ff_read_u64 = make_read_one(np.uint64)
ff_read_s64 = make_read_one(np.int64)
ff_read_f32 = make_read_one(np.float32)
ff_read_f64 = make_read_one(np.float64)

ff_read_u8s = make_read_many(np.uint8)
ff_read_s8s = make_read_many(np.int8)
ff_read_u16s = make_read_many(np.uint16)
ff_read_s16s = make_read_many(np.int16)
ff_read_u32s = make_read_many(np.uint32)
ff_read_s32s = make_read_many(np.int32)
ff_read_u64s = make_read_many(np.uint64)
ff_read_s64s = make_read_many(np.int64)
ff_read_f32s = make_read_many(np.float32)
ff_read_f64s = make_read_many(np.float64)


@njit(**params)
def ff_read_strz(bufn, pos):
    pos0 = pos
    while bufn[0][pos] != 0 and pos < bufn[1]:
        pos += 1
    return bufn[0][pos0:pos], pos
