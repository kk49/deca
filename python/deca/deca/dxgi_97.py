from numba import njit
import numpy as np

"""
    reference:
    https://docs.microsoft.com/en-us/windows/win32/direct3d11/bc7-format
    https://docs.microsoft.com/en-us/windows/win32/direct3d11/bc7-format-mode-reference
    https://www.khronos.org/registry/OpenGL/extensions/ARB/ARB_texture_compression_bptc.txt
"""


@njit(inline='always')
def determine_mode(b0):
    mode = -1
    if b0 & 0x1:  # mode 0
        mode = 0
    elif b0 & 0x2:  # mode 1
        mode = 1
    elif b0 & 0x4:  # mode 2
        mode = 2
    elif b0 & 0x8:  # mode 3
        mode = 3
    elif b0 & 0x10:  # mode 4
        mode = 4
    elif b0 & 0x20:  # mode 5
        mode = 5
    elif b0 & 0x40:  # mode 6
        mode = 6
    elif b0 & 0x80:  # mode 7
        mode = 7
    return mode


@njit(inline='always')
def extract_bits(buffer, byte_offset, bit_offset, n_bits):
    byte_offset = byte_offset + bit_offset // 8
    bit_offset = bit_offset % 8
    bit_end = bit_offset + n_bits

    if bit_end > 16:
        return 0xFFFFFFFF
    elif bit_end > 8:  # across two bytes
        low_bits = (8 - bit_offset)
        mask_high = (1 << (bit_end - 8)) - 1
        mask_low = (1 << low_bits) - 1
        low = (buffer[byte_offset] >> bit_offset) & mask_low
        high = ((buffer[byte_offset + 1]) & mask_high) << low_bits
        return low | high
    else:
        low = (buffer[byte_offset] >> bit_offset) & ((1 << n_bits) - 1)
        return low


@njit()
def process_image_97(image, buffer, n_buffer, nx, ny):
    '''

    :param image:
    :param buffer:
    :param n_buffer:
    :param nx:
    :param ny:
    :return:
    '''

    # NS, skip_bits, PB, RB, ISB, CB, AB, EPB, SPB, IB, IB2
    table_m = [
        [3, 1, 4, 0, 0, 4, 0, 1, 0, 3, 0],
        [2, 2, 6, 0, 0, 6, 0, 0, 1, 3, 0],
        [3, 3, 6, 0, 0, 5, 0, 0, 0, 2, 0],
        [2, 4, 6, 0, 0, 7, 0, 1, 0, 2, 0],
        [1, 5, 0, 2, 1, 5, 6, 0, 0, 2, 3],
        [1, 6, 0, 2, 0, 7, 8, 0, 0, 2, 2],
        [1, 7, 0, 0, 0, 7, 7, 1, 0, 4, 0],
        [2, 8, 6, 0, 0, 5, 5, 1, 0, 2, 0],
    ]

    table_p1 = [0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0]

    table_p2 = [
        [0, 0, 1, 1, 0, 0, 1, 1, 0, 0, 1, 1, 0, 0, 1, 1],
        [0, 0, 0, 1, 0, 0, 0, 1, 0, 0, 0, 1, 0, 0, 0, 1],
        [0, 1, 1, 1, 0, 1, 1, 1, 0, 1, 1, 1, 0, 1, 1, 1],
        [0, 0, 0, 1, 0, 0, 1, 1, 0, 0, 1, 1, 0, 1, 1, 1],
        [0, 0, 0, 0, 0, 0, 0, 1, 0, 0, 0, 1, 0, 0, 1, 1],
        [0, 0, 1, 1, 0, 1, 1, 1, 0, 1, 1, 1, 1, 1, 1, 1],
        [0, 0, 0, 1, 0, 0, 1, 1, 0, 1, 1, 1, 1, 1, 1, 1],
        [0, 0, 0, 0, 0, 0, 0, 1, 0, 0, 1, 1, 0, 1, 1, 1],
        [0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 1, 0, 0, 1, 1],
        [0, 0, 1, 1, 0, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1],
        [0, 0, 0, 0, 0, 0, 0, 1, 0, 1, 1, 1, 1, 1, 1, 1],
        [0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 1, 0, 1, 1, 1],
        [0, 0, 0, 1, 0, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1],
        [0, 0, 0, 0, 0, 0, 0, 0, 1, 1, 1, 1, 1, 1, 1, 1],
        [0, 0, 0, 0, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1],
        [0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 1, 1, 1, 1],
        [0, 0, 0, 0, 1, 0, 0, 0, 1, 1, 1, 0, 1, 1, 1, 1],
        [0, 1, 1, 1, 0, 0, 0, 1, 0, 0, 0, 0, 0, 0, 0, 0],
        [0, 0, 0, 0, 0, 0, 0, 0, 1, 0, 0, 0, 1, 1, 1, 0],
        [0, 1, 1, 1, 0, 0, 1, 1, 0, 0, 0, 1, 0, 0, 0, 0],
        [0, 0, 1, 1, 0, 0, 0, 1, 0, 0, 0, 0, 0, 0, 0, 0],
        [0, 0, 0, 0, 1, 0, 0, 0, 1, 1, 0, 0, 1, 1, 1, 0],
        [0, 0, 0, 0, 0, 0, 0, 0, 1, 0, 0, 0, 1, 1, 0, 0],
        [0, 1, 1, 1, 0, 0, 1, 1, 0, 0, 1, 1, 0, 0, 0, 1],
        [0, 0, 1, 1, 0, 0, 0, 1, 0, 0, 0, 1, 0, 0, 0, 0],
        [0, 0, 0, 0, 1, 0, 0, 0, 1, 0, 0, 0, 1, 1, 0, 0],
        [0, 1, 1, 0, 0, 1, 1, 0, 0, 1, 1, 0, 0, 1, 1, 0],
        [0, 0, 1, 1, 0, 1, 1, 0, 0, 1, 1, 0, 1, 1, 0, 0],
        [0, 0, 0, 1, 0, 1, 1, 1, 1, 1, 1, 0, 1, 0, 0, 0],
        [0, 0, 0, 0, 1, 1, 1, 1, 1, 1, 1, 1, 0, 0, 0, 0],
        [0, 1, 1, 1, 0, 0, 0, 1, 1, 0, 0, 0, 1, 1, 1, 0],
        [0, 0, 1, 1, 1, 0, 0, 1, 1, 0, 0, 1, 1, 1, 0, 0],
        [0, 1, 0, 1, 0, 1, 0, 1, 0, 1, 0, 1, 0, 1, 0, 1],
        [0, 0, 0, 0, 1, 1, 1, 1, 0, 0, 0, 0, 1, 1, 1, 1],
        [0, 1, 0, 1, 1, 0, 1, 0, 0, 1, 0, 1, 1, 0, 1, 0],
        [0, 0, 1, 1, 0, 0, 1, 1, 1, 1, 0, 0, 1, 1, 0, 0],
        [0, 0, 1, 1, 1, 1, 0, 0, 0, 0, 1, 1, 1, 1, 0, 0],
        [0, 1, 0, 1, 0, 1, 0, 1, 1, 0, 1, 0, 1, 0, 1, 0],
        [0, 1, 1, 0, 1, 0, 0, 1, 0, 1, 1, 0, 1, 0, 0, 1],
        [0, 1, 0, 1, 1, 0, 1, 0, 1, 0, 1, 0, 0, 1, 0, 1],
        [0, 1, 1, 1, 0, 0, 1, 1, 1, 1, 0, 0, 1, 1, 1, 0],
        [0, 0, 0, 1, 0, 0, 1, 1, 1, 1, 0, 0, 1, 0, 0, 0],
        [0, 0, 1, 1, 0, 0, 1, 0, 0, 1, 0, 0, 1, 1, 0, 0],
        [0, 0, 1, 1, 1, 0, 1, 1, 1, 1, 0, 1, 1, 1, 0, 0],
        [0, 1, 1, 0, 1, 0, 0, 1, 1, 0, 0, 1, 0, 1, 1, 0],
        [0, 0, 1, 1, 1, 1, 0, 0, 1, 1, 0, 0, 0, 0, 1, 1],
        [0, 1, 1, 0, 0, 1, 1, 0, 1, 0, 0, 1, 1, 0, 0, 1],
        [0, 0, 0, 0, 0, 1, 1, 0, 0, 1, 1, 0, 0, 0, 0, 0],
        [0, 1, 0, 0, 1, 1, 1, 0, 0, 1, 0, 0, 0, 0, 0, 0],
        [0, 0, 1, 0, 0, 1, 1, 1, 0, 0, 1, 0, 0, 0, 0, 0],
        [0, 0, 0, 0, 0, 0, 1, 0, 0, 1, 1, 1, 0, 0, 1, 0],
        [0, 0, 0, 0, 0, 1, 0, 0, 1, 1, 1, 0, 0, 1, 0, 0],
        [0, 1, 1, 0, 1, 1, 0, 0, 1, 0, 0, 1, 0, 0, 1, 1],
        [0, 0, 1, 1, 0, 1, 1, 0, 1, 1, 0, 0, 1, 0, 0, 1],
        [0, 1, 1, 0, 0, 0, 1, 1, 1, 0, 0, 1, 1, 1, 0, 0],
        [0, 0, 1, 1, 1, 0, 0, 1, 1, 1, 0, 0, 0, 1, 1, 0],
        [0, 1, 1, 0, 1, 1, 0, 0, 1, 1, 0, 0, 1, 0, 0, 1],
        [0, 1, 1, 0, 0, 0, 1, 1, 0, 0, 1, 1, 1, 0, 0, 1],
        [0, 1, 1, 1, 1, 1, 1, 0, 1, 0, 0, 0, 0, 0, 0, 1],
        [0, 0, 0, 1, 1, 0, 0, 0, 1, 1, 1, 0, 0, 1, 1, 1],
        [0, 0, 0, 0, 1, 1, 1, 1, 0, 0, 1, 1, 0, 0, 1, 1],
        [0, 0, 1, 1, 0, 0, 1, 1, 1, 1, 1, 1, 0, 0, 0, 0],
        [0, 0, 1, 0, 0, 0, 1, 0, 1, 1, 1, 0, 1, 1, 1, 0],
        [0, 1, 0, 0, 0, 1, 0, 0, 0, 1, 1, 1, 0, 1, 1, 1],
    ]

    table_p3 = [
        [0, 0, 1, 1, 0, 0, 1, 1, 0, 2, 2, 1, 2, 2, 2, 2],
        [0, 0, 0, 1, 0, 0, 1, 1, 2, 2, 1, 1, 2, 2, 2, 1],
        [0, 0, 0, 0, 2, 0, 0, 1, 2, 2, 1, 1, 2, 2, 1, 1],
        [0, 2, 2, 2, 0, 0, 2, 2, 0, 0, 1, 1, 0, 1, 1, 1],
        [0, 0, 0, 0, 0, 0, 0, 0, 1, 1, 2, 2, 1, 1, 2, 2],
        [0, 0, 1, 1, 0, 0, 1, 1, 0, 0, 2, 2, 0, 0, 2, 2],
        [0, 0, 2, 2, 0, 0, 2, 2, 1, 1, 1, 1, 1, 1, 1, 1],
        [0, 0, 1, 1, 0, 0, 1, 1, 2, 2, 1, 1, 2, 2, 1, 1],
        [0, 0, 0, 0, 0, 0, 0, 0, 1, 1, 1, 1, 2, 2, 2, 2],
        [0, 0, 0, 0, 1, 1, 1, 1, 1, 1, 1, 1, 2, 2, 2, 2],
        [0, 0, 0, 0, 1, 1, 1, 1, 2, 2, 2, 2, 2, 2, 2, 2],
        [0, 0, 1, 2, 0, 0, 1, 2, 0, 0, 1, 2, 0, 0, 1, 2],
        [0, 1, 1, 2, 0, 1, 1, 2, 0, 1, 1, 2, 0, 1, 1, 2],
        [0, 1, 2, 2, 0, 1, 2, 2, 0, 1, 2, 2, 0, 1, 2, 2],
        [0, 0, 1, 1, 0, 1, 1, 2, 1, 1, 2, 2, 1, 2, 2, 2],
        [0, 0, 1, 1, 2, 0, 0, 1, 2, 2, 0, 0, 2, 2, 2, 0],
        [0, 0, 0, 1, 0, 0, 1, 1, 0, 1, 1, 2, 1, 1, 2, 2],
        [0, 1, 1, 1, 0, 0, 1, 1, 2, 0, 0, 1, 2, 2, 0, 0],
        [0, 0, 0, 0, 1, 1, 2, 2, 1, 1, 2, 2, 1, 1, 2, 2],
        [0, 0, 2, 2, 0, 0, 2, 2, 0, 0, 2, 2, 1, 1, 1, 1],
        [0, 1, 1, 1, 0, 1, 1, 1, 0, 2, 2, 2, 0, 2, 2, 2],
        [0, 0, 0, 1, 0, 0, 0, 1, 2, 2, 2, 1, 2, 2, 2, 1],
        [0, 0, 0, 0, 0, 0, 1, 1, 0, 1, 2, 2, 0, 1, 2, 2],
        [0, 0, 0, 0, 1, 1, 0, 0, 2, 2, 1, 0, 2, 2, 1, 0],
        [0, 1, 2, 2, 0, 1, 2, 2, 0, 0, 1, 1, 0, 0, 0, 0],
        [0, 0, 1, 2, 0, 0, 1, 2, 1, 1, 2, 2, 2, 2, 2, 2],
        [0, 1, 1, 0, 1, 2, 2, 1, 1, 2, 2, 1, 0, 1, 1, 0],
        [0, 0, 0, 0, 0, 1, 1, 0, 1, 2, 2, 1, 1, 2, 2, 1],
        [0, 0, 2, 2, 1, 1, 0, 2, 1, 1, 0, 2, 0, 0, 2, 2],
        [0, 1, 1, 0, 0, 1, 1, 0, 2, 0, 0, 2, 2, 2, 2, 2],
        [0, 0, 1, 1, 0, 1, 2, 2, 0, 1, 2, 2, 0, 0, 1, 1],
        [0, 0, 0, 0, 2, 0, 0, 0, 2, 2, 1, 1, 2, 2, 2, 1],
        [0, 0, 0, 0, 0, 0, 0, 2, 1, 1, 2, 2, 1, 2, 2, 2],
        [0, 2, 2, 2, 0, 0, 2, 2, 0, 0, 1, 2, 0, 0, 1, 1],
        [0, 0, 1, 1, 0, 0, 1, 2, 0, 0, 2, 2, 0, 2, 2, 2],
        [0, 1, 2, 0, 0, 1, 2, 0, 0, 1, 2, 0, 0, 1, 2, 0],
        [0, 0, 0, 0, 1, 1, 1, 1, 2, 2, 2, 2, 0, 0, 0, 0],
        [0, 1, 2, 0, 1, 2, 0, 1, 2, 0, 1, 2, 0, 1, 2, 0],
        [0, 1, 2, 0, 2, 0, 1, 2, 1, 2, 0, 1, 0, 1, 2, 0],
        [0, 0, 1, 1, 2, 2, 0, 0, 1, 1, 2, 2, 0, 0, 1, 1],
        [0, 0, 1, 1, 1, 1, 2, 2, 2, 2, 0, 0, 0, 0, 1, 1],
        [0, 1, 0, 1, 0, 1, 0, 1, 2, 2, 2, 2, 2, 2, 2, 2],
        [0, 0, 0, 0, 0, 0, 0, 0, 2, 1, 2, 1, 2, 1, 2, 1],
        [0, 0, 2, 2, 1, 1, 2, 2, 0, 0, 2, 2, 1, 1, 2, 2],
        [0, 0, 2, 2, 0, 0, 1, 1, 0, 0, 2, 2, 0, 0, 1, 1],
        [0, 2, 2, 0, 1, 2, 2, 1, 0, 2, 2, 0, 1, 2, 2, 1],
        [0, 1, 0, 1, 2, 2, 2, 2, 2, 2, 2, 2, 0, 1, 0, 1],
        [0, 0, 0, 0, 2, 1, 2, 1, 2, 1, 2, 1, 2, 1, 2, 1],
        [0, 1, 0, 1, 0, 1, 0, 1, 0, 1, 0, 1, 2, 2, 2, 2],
        [0, 2, 2, 2, 0, 1, 1, 1, 0, 2, 2, 2, 0, 1, 1, 1],
        [0, 0, 0, 2, 1, 1, 1, 2, 0, 0, 0, 2, 1, 1, 1, 2],
        [0, 0, 0, 0, 2, 1, 1, 2, 2, 1, 1, 2, 2, 1, 1, 2],
        [0, 2, 2, 2, 0, 1, 1, 1, 0, 1, 1, 1, 0, 2, 2, 2],
        [0, 0, 0, 2, 1, 1, 1, 2, 1, 1, 1, 2, 0, 0, 0, 2],
        [0, 1, 1, 0, 0, 1, 1, 0, 0, 1, 1, 0, 2, 2, 2, 2],
        [0, 0, 0, 0, 0, 0, 0, 0, 2, 1, 1, 2, 2, 1, 1, 2],
        [0, 1, 1, 0, 0, 1, 1, 0, 2, 2, 2, 2, 2, 2, 2, 2],
        [0, 0, 2, 2, 0, 0, 1, 1, 0, 0, 1, 1, 0, 0, 2, 2],
        [0, 0, 2, 2, 1, 1, 2, 2, 1, 1, 2, 2, 0, 0, 2, 2],
        [0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 2, 1, 1, 2],
        [0, 0, 0, 2, 0, 0, 0, 1, 0, 0, 0, 2, 0, 0, 0, 1],
        [0, 2, 2, 2, 1, 2, 2, 2, 0, 2, 2, 2, 1, 2, 2, 2],
        [0, 1, 0, 1, 2, 2, 2, 2, 2, 2, 2, 2, 2, 2, 2, 2],
        [0, 1, 1, 1, 2, 0, 1, 1, 2, 2, 0, 1, 2, 2, 2, 0],
    ]

    # Table.A2 (Anchor index values for the second subset of two-subset partitioning)

    table_a2 = [
        15, 15, 15, 15, 15, 15, 15, 15,
        15, 15, 15, 15, 15, 15, 15, 15,
        15, 2, 8, 2, 2, 8, 8, 15,
        2, 8, 2, 2, 8, 8, 2, 2,
        15, 15, 6, 8, 2, 8, 15, 15,
        2, 8, 2, 2, 2, 15, 15, 6,
        6, 2, 6, 8, 15, 15, 2, 2,
        15, 15, 15, 15, 15, 2, 2, 15,
    ]

    # Table.A3a (Anchor index values for the second subset of three-subset partitioning)

    table_a3a = [
        3, 3, 15, 15, 8, 3, 15, 15,
        8, 8, 6, 6, 6, 5, 3, 3,
        3, 3, 8, 15, 3, 3, 6, 10,
        5, 8, 8, 6, 8, 5, 15, 15,
        8, 15, 3, 5, 6, 10, 8, 15,
        15, 3, 15, 5, 15, 15, 15, 15,
        3, 15, 5, 5, 5, 8, 5, 10,
        5, 10, 8, 13, 15, 12, 3, 3,
    ]

    # Table.A3b (Anchor index values for the third subset of three-subset partitioning)

    table_a3b = [
        15, 8, 8, 3, 15, 15, 3, 8,
        15, 15, 15, 15, 15, 15, 15, 8,
        15, 8, 15, 3, 15, 8, 15, 8,
        3, 15, 6, 10, 15, 15, 10, 8,
        15, 3, 15, 10, 10, 8, 9, 10,
        6, 15, 8, 15, 3, 6, 6, 8,
        15, 3, 15, 15, 15, 15, 15, 15,
        15, 15, 15, 15, 3, 15, 15, 8,
    ]

    table_interpolation = [
        [0],
        [0, 64],
        [0, 21, 43, 64],
        [0, 9, 18, 27, 37, 46, 55, 64],
        [0, 4, 9, 13, 17, 21, 26, 30, 34, 38, 43, 47, 51, 55, 60, 64],
    ]

    # num subsets, end point, component
    end_points = np.zeros((3, 2, 4), dtype=np.ubyte)
    indexes_primary = [0] * 16
    indexes_secondary = [0] * 16

    pos = 0
    bnx = max(1, nx // 4)
    bny = max(1, ny // 4)
    for yi in range(bny):
        for xi in range(bnx):
            # print(' '.join(['{}'.format(v) for v in buffer[pos:pos+16]]))

            b0 = buffer[pos]
            mode = determine_mode(b0)
            tm = table_m[mode]
            num_subsets = tm[0]
            bits = tm[1:]

            bit_offset = bits[0]
            # partition number
            partition_number = 0
            if bits[1] > 0:
                partition_number = extract_bits(buffer, pos, bit_offset, bits[1])
                bit_offset += bits[1]

            # rotation
            rotation = 0
            if bits[2] > 0:
                rotation = extract_bits(buffer, pos, bit_offset, bits[2])
                bit_offset += bits[2]

            # index selection
            index_selection = 0
            if bits[3] > 0:
                index_selection = extract_bits(buffer, pos, bit_offset, bits[3])
                bit_offset += bits[3]

            # color
            if bits[4] > 0:
                for color in range(3):
                    for subset in range(num_subsets):
                        for end_point in range(2):
                            end_points[subset, end_point, color] = \
                                extract_bits(buffer, pos, bit_offset, bits[4]) << (8 - bits[4])
                            bit_offset += bits[4]

            # alpha
            if bits[5] > 0:
                for subset in range(num_subsets):
                    for end_point in range(2):
                        end_points[subset, end_point, 3] = \
                            extract_bits(buffer, pos, bit_offset, bits[5]) << (8 - bits[5])
                        bit_offset += bits[5]
            else:
                for subset in range(num_subsets):
                    for end_point in range(2):
                        end_points[subset, end_point, 3] = 255

            # per-endpoint P-bit
            if bits[6] > 0:
                for subset in range(num_subsets):
                    for end_point in range(2):
                        pbit0 = extract_bits(buffer, pos, bit_offset, 1)
                        bit_offset += 1
                        for color in range(3):
                            end_points[subset, end_point, color] |= pbit0 << (8 - bits[4] - 1) | (end_points[subset, end_point, color] >> (bits[4] + 1))
                        if bits[5] > 0:
                            end_points[subset, end_point, 3] |= pbit0 << (8 - bits[5] - 1) | (end_points[subset, end_point, 3] >> (bits[5] + 1))

            # shared P-bit
            if bits[7] > 0:
                pbit0 = extract_bits(buffer, pos, bit_offset, 1)
                pbit1 = extract_bits(buffer, pos, bit_offset+1, 1)
                bit_offset += 2

                for end_point in range(2):
                    for color in range(3):
                        end_points[0, end_point, color] |= pbit0 << (8 - bits[4] - 1) | (end_points[0, end_point, color] >> (bits[4] + 1))
                        end_points[1, end_point, color] |= pbit1 << (8 - bits[4] - 1) | (end_points[1, end_point, color] >> (bits[4] + 1))
                    if bits[5] > 0:
                        end_points[0, end_point, 3] |= pbit0 << (8 - bits[5] - 1) | (end_points[0, end_point, 3] >> (bits[5] + 1))
                        end_points[1, end_point, 3] |= pbit1 << (8 - bits[5] - 1) | (end_points[1, end_point, 3] >> (bits[5] + 1))

            if num_subsets == 1:
                p = table_p1
                anchors = [0]
            elif num_subsets == 2:
                p = table_p2[partition_number]
                anchors = [0, table_a2[partition_number]]
            elif num_subsets == 3:
                p = table_p3[partition_number]
                anchors = [0, table_a3a[partition_number], table_a3b[partition_number]]

            # primary indices
            if bits[8] > 0:
                for i in range(16):
                    n = bits[8]
                    if i == anchors[p[i]]:
                        n -= 1
                    indexes_primary[i] = extract_bits(buffer, pos, bit_offset, n)
                    bit_offset += n
            else:
                for i in range(16):
                    indexes_primary[i] = 0

            # secondary indices
            if bits[9] > 0:
                for i in range(16):
                    n = bits[9]
                    if i == anchors[p[i]]:
                        n -= 1
                    indexes_secondary[i] = extract_bits(buffer, pos, bit_offset, n)
                    bit_offset += n
            else:
                for i in range(16):
                    indexes_secondary[i] = 0

            assert bit_offset == 128

            # print(f'pi97: pos {pos}, bit_offset {bit_offset}, mode {mode}, subsets {num_subsets}, bits {bits}')
            # print(f'pi97: mode:{mode} ns:{num_subsets} pn:{partition_number} r:{rotation} is:{index_selection} bits:{bits}')
            # print(end_points)
            # print(indexes_primary)
            # print(indexes_secondary)
            # print(f'{partition_number}, {rotation}, {index_selection}, {end_points}')

            interpolate_primary = table_interpolation[bits[8]]
            interpolate_secondary = table_interpolation[bits[9]]

            ox = xi * 4
            oy = yi * 4
            texel_idx = 0

            for syi in range(4):
                for sxi in range(4):
                    part_index = p[texel_idx]

                    if index_selection == 1:
                        color_itp = interpolate_secondary[indexes_secondary[texel_idx]]
                    else:
                        color_itp = interpolate_primary[indexes_primary[texel_idx]]

                    if bits[9] > 0 and index_selection == 0:
                        alpha_itp = interpolate_secondary[indexes_secondary[texel_idx]]
                    else:
                        alpha_itp = interpolate_primary[indexes_primary[texel_idx]]

                    r = (np.uint16(end_points[part_index, 0, 0]) * (64 - color_itp) + np.uint16(end_points[part_index, 1, 0]) * color_itp + 32) >> 6
                    g = (np.uint16(end_points[part_index, 0, 1]) * (64 - color_itp) + np.uint16(end_points[part_index, 1, 1]) * color_itp + 32) >> 6
                    b = (np.uint16(end_points[part_index, 0, 2]) * (64 - color_itp) + np.uint16(end_points[part_index, 1, 2]) * color_itp + 32) >> 6
                    a = (np.uint16(end_points[part_index, 0, 3]) * (64 - alpha_itp) + np.uint16(end_points[part_index, 1, 3]) * alpha_itp + 32) >> 6

                    if rotation == 1:
                        a, r = r, a
                    elif rotation == 2:
                        a, g = g, a
                    elif rotation == 3:
                        a, b = b, a

                    image[oy + syi, ox + sxi, 0] = r
                    image[oy + syi, ox + sxi, 1] = g
                    image[oy + syi, ox + sxi, 2] = b
                    image[oy + syi, ox + sxi, 3] = a

                    texel_idx += 1

            pos += 16


