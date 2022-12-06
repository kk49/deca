import time
import numpy as np
import io
import struct
import os
import ctypes
import sys
from .fast_file import *
from .dxgi_97 import process_image_97
from .dxgi_94_95_96 import process_image_94_95_96
from .dxgi_types import *
from numba import njit

process_image_func = None
c_process_image_lib = None
c_process_image_func = None


# https://docs.microsoft.com/en-us/windows/desktop/direct3d9/opaque-and-1-bit-alpha-textures
# https://msdn.microsoft.com/ja-jp/library/bb173059(v=vs.85).aspx
# https://docs.microsoft.com/en-us/windows/win32/api/dxgiformat/ne-dxgiformat-dxgi_format
# less than 32 bit floats
#   https://docs.microsoft.com/en-us/windows/win32/direct3d10/d3d10-graphics-programming-guide-resources-float-rules


@njit(inline='always')
def ux_to_fx_to_f32(s, e, f, den):
    if s == 1:
        s = np.float32(-1)
    else:
        s = np.float32(1)

    if e == 31 and f != 0:
        return np.float32(np.nan)
    elif e == 31 and f == 0:
        return np.float32(s * np.inf)
    elif e == 0 and f != 0:
        return np.float(s * (2.0**(e-14)) * f * den)
    elif e == 0 and f == 0:
        return np.float32(s * 0.0)
    else:
        return np.float32(s * (2.0 ** (e-15)) * (1 + f * den))


@njit(inline='always')
def u10_to_f10_in_f32(value):
    s = 0
    e = (value >> 5) & 0x1F
    f = value & 0x1F
    den = (1 / 31.0)
    return ux_to_fx_to_f32(s, e, f, den)


@njit(inline='always')
def u11_to_f11_in_f32(value):
    s = 0
    e = (value >> 6) & 0x1F
    f = value & 0x3F
    den = (1 / 63.0)
    return ux_to_fx_to_f32(s, e, f, den)


@njit(inline='always')
def u16_to_f16_in_f32(value):
    s = value >> 15
    e = (value >> 10) & 0x1F
    f = value & 0x3FF
    den = (1 / 1023.0)
    return ux_to_fx_to_f32(s, e, f, den)


@njit
def process_image_2(image, buffer, n_buffer, nx, ny):  # DXGI_FORMAT_R32G32B32A32_FLOAT
    pos = 0
    chans = [0.0] * 4
    for yi in range(ny):
        for xi in range(nx):
            chans[0], pos = ff_read_f32(buffer, n_buffer, pos)
            chans[1], pos = ff_read_f32(buffer, n_buffer, pos)
            chans[2], pos = ff_read_f32(buffer, n_buffer, pos)
            chans[3], pos = ff_read_f32(buffer, n_buffer, pos)
            image[yi, xi, :] = chans


@njit
def process_image_10(image, buffer, n_buffer, nx, ny):  # DXGI_FORMAT_R16G16B16A16_FLOAT
    pos = 0
    chans = [0] * 4
    for yi in range(ny):
        for xi in range(nx):
            chans[0], pos = ff_read_u16(buffer, n_buffer, pos)
            chans[1], pos = ff_read_u16(buffer, n_buffer, pos)
            chans[2], pos = ff_read_u16(buffer, n_buffer, pos)
            chans[3], pos = ff_read_u16(buffer, n_buffer, pos)
            image[yi, xi, 0] = u16_to_f16_in_f32(chans[0])
            image[yi, xi, 1] = u16_to_f16_in_f32(chans[1])
            image[yi, xi, 2] = u16_to_f16_in_f32(chans[2])
            image[yi, xi, 3] = u16_to_f16_in_f32(chans[3])


@njit
def process_image_26(image, buffer, n_buffer, nx, ny):  # DXGI_FORMAT_R11G11B10_FLOAT
    pos = 0
    for yi in range(ny):
        for xi in range(nx):
            chans, pos = ff_read_u32(buffer, n_buffer, pos)
            image[yi, xi, 0] = u11_to_f11_in_f32((chans >> 0) & 0x07ff)
            image[yi, xi, 1] = u11_to_f11_in_f32((chans >> 11) & 0x07ff)
            image[yi, xi, 2] = u10_to_f10_in_f32((chans >> 22) & 0x03ff)
            image[yi, xi, 3] = 1.0


@njit
def process_image_28(image, buffer, n_buffer, nx, ny):  # DXGI_FORMAT_R8G8B8A8_UNORM
    pos = 0
    chans = [0] * 4
    for yi in range(ny):
        for xi in range(nx):
            chans[0], pos = ff_read_u8(buffer, n_buffer, pos)
            chans[1], pos = ff_read_u8(buffer, n_buffer, pos)
            chans[2], pos = ff_read_u8(buffer, n_buffer, pos)
            chans[3], pos = ff_read_u8(buffer, n_buffer, pos)
            image[yi, xi, :] = chans[:]


@njit
def process_image_41(image, buffer, n_buffer, nx, ny):  # DXGI_FORMAT_R32_FLOAT
    pos = 0
    chans = [0.0] * 4
    for yi in range(ny):
        for xi in range(nx):
            chans[0], pos = ff_read_f32(buffer, n_buffer, pos)
            chans[1] = 0.0
            chans[2] = 0.0
            chans[3] = 1.0
            image[yi, xi, :] = chans


@njit
def process_image_53(image, buffer, n_buffer, nx, ny):  # DXGI_FORMAT_R16_ u16
    pos = 0
    chans = [0] * 1
    for yi in range(ny):
        for xi in range(nx):
            chans[0], pos = ff_read_u16(buffer, n_buffer, pos)
            image[yi, xi, 0] = chans[0]
            image[yi, xi, 1] = 0
            image[yi, xi, 2] = 0
            image[yi, xi, 3] = 0


@njit
def process_image_54(image, buffer, n_buffer, nx, ny):  # DXGI_FORMAT_R16_FLOAT
    pos = 0
    chans = [0] * 1
    for yi in range(ny):
        for xi in range(nx):
            chans[0], pos = ff_read_u16(buffer, n_buffer, pos)
            image[yi, xi, 0] = u16_to_f16_in_f32(chans[0])
            image[yi, xi, 1] = 0
            image[yi, xi, 2] = 0
            image[yi, xi, 3] = 0

@njit
def process_image_58(image, buffer, n_buffer, nx, ny):  # DXGI_FORMAT_R16_ s16
    pos = 0
    chans = [0] * 1
    for yi in range(ny):
        for xi in range(nx):
            chans[0], pos = ff_read_s16(buffer, n_buffer, pos)
            image[yi, xi, 0] = chans[0]
            image[yi, xi, 1] = 0
            image[yi, xi, 2] = 0
            image[yi, xi, 3] = 0


@njit
def process_image_60(image, buffer, n_buffer, nx, ny):  # DXGI_FORMAT_R8_ u8
    pos = 0
    chans = [0] * 1
    for yi in range(ny):
        for xi in range(nx):
            chans[0], pos = ff_read_u8(buffer, n_buffer, pos)
            image[yi, xi, 0] = chans[0]
            image[yi, xi, 1] = 0
            image[yi, xi, 2] = 0
            image[yi, xi, 3] = 0


@njit
def process_image_63(image, buffer, n_buffer, nx, ny):  # DXGI_FORMAT_R8_ s8
    pos = 0
    chans = [0] * 1
    for yi in range(ny):
        for xi in range(nx):
            chans[0], pos = ff_read_s8(buffer, n_buffer, pos)
            image[yi, xi, 0] = chans[0]
            image[yi, xi, 1] = 0
            image[yi, xi, 2] = 0
            image[yi, xi, 3] = 0


@njit
def process_image_87(image, buffer, n_buffer, nx, ny):  # DXGI_FORMAT_B8G8R8A8_UNORM
    pos = 0
    chans = [0] * 4
    for yi in range(ny):
        for xi in range(nx):
            chans[0], pos = ff_read_u8(buffer, n_buffer, pos)
            chans[1], pos = ff_read_u8(buffer, n_buffer, pos)
            chans[2], pos = ff_read_u8(buffer, n_buffer, pos)
            chans[3], pos = ff_read_u8(buffer, n_buffer, pos)
            image[yi, xi, 0] = chans[2]
            image[yi, xi, 1] = chans[1]
            image[yi, xi, 2] = chans[0]
            image[yi, xi, 3] = chans[3]


@njit
def process_image_70(image, buffer, n_buffer, nx, ny):  # DXGI_FORMAT_BC1_UNORM
    pos = 0
    bnx = max(1, nx // 4)
    bny = max(1, ny // 4)
    for yi in range(bny):
        for xi in range(bnx):
            color0, pos = ff_read_u16(buffer, n_buffer, pos)
            color1, pos = ff_read_u16(buffer, n_buffer, pos)
            bs = [0] * 4
            bs[0], pos = ff_read_u8(buffer, n_buffer, pos)
            bs[1], pos = ff_read_u8(buffer, n_buffer, pos)
            bs[2], pos = ff_read_u8(buffer, n_buffer, pos)
            bs[3], pos = ff_read_u8(buffer, n_buffer, pos)

            color0_full = np.array(
                [((color0 >> 11) & 0x1F) << 3, ((color0 >> 5) & 0x3F) << 2, ((color0 >> 0) & 0x1F) << 3, 0xFF],
                dtype=np.uint8)
            color1_full = np.array(
                [((color1 >> 11) & 0x1F) << 3, ((color1 >> 5) & 0x3F) << 2, ((color1 >> 0) & 0x1F) << 3, 0xFF],
                dtype=np.uint8)

            colors = np.zeros((4, 4), dtype=np.uint8)
            if color0 > color1:
                colors[0, :] = color0_full
                colors[1, :] = color1_full
                colors[2, :] = (2.0 * color0_full + color1_full + 1.0) // 3
                colors[3, :] = (color0_full + 2.0 * color1_full + 1.0) // 3
                colors[:, 3] = 255
            else:
                colors[0, :] = color0_full
                colors[1, :] = color1_full
                colors[2, :] = (1.0 * color0_full + color1_full) // 2
                colors[3, :] = 0
                colors[0:3, 3] = 255

            ox = xi * 4
            oy = yi * 4
            for bsi in range(4):
                b0 = bs[bsi]
                image[oy + bsi, ox + 0, :] = colors[(b0 >> 0) & 0x3]
                image[oy + bsi, ox + 1, :] = colors[(b0 >> 2) & 0x3]
                image[oy + bsi, ox + 2, :] = colors[(b0 >> 4) & 0x3]
                image[oy + bsi, ox + 3, :] = colors[(b0 >> 6) & 0x3]


@njit
def process_image_73(image, buffer, n_buffer, nx, ny):
    pos = 0
    bnx = max(1, nx // 4)
    bny = max(1, ny // 4)
    for yi in range(bny):
        for xi in range(bnx):
            # alpha setup
            alpha, pos = ff_read_u64(buffer, n_buffer, pos)

            # color setup
            color0, pos = ff_read_u16(buffer, n_buffer, pos)
            color1, pos = ff_read_u16(buffer, n_buffer, pos)
            bs = [0] * 4
            bs[0], pos = ff_read_u8(buffer, n_buffer, pos)
            bs[1], pos = ff_read_u8(buffer, n_buffer, pos)
            bs[2], pos = ff_read_u8(buffer, n_buffer, pos)
            bs[3], pos = ff_read_u8(buffer, n_buffer, pos)

            color0_full = np.array(
                [((color0 >> 11) & 0x1F) << 3, ((color0 >> 5) & 0x3F) << 2, ((color0 >> 0) & 0x1F) << 3, 0xFF],
                dtype=np.uint8)
            color1_full = np.array(
                [((color1 >> 11) & 0x1F) << 3, ((color1 >> 5) & 0x3F) << 2, ((color1 >> 0) & 0x1F) << 3, 0xFF],
                dtype=np.uint8)

            colors = np.zeros((4, 4), dtype=np.uint8)
            if color0 > color1:
                colors[0, :] = color0_full
                colors[1, :] = color1_full
                colors[2, :] = (2.0 * color0_full + color1_full + 1.0) // 3
                colors[3, :] = (color0_full + 2.0 * color1_full + 1.0) // 3
                colors[:, 3] = 255
            else:
                colors[0, :] = color0_full
                colors[1, :] = color1_full
                colors[2, :] = (1.0 * color0_full + color1_full) // 2
                colors[3, :] = 0
                colors[0:3, 3] = 255

            # write pixels
            ox = xi * 4
            oy = yi * 4
            for bsi in range(4):
                b0 = bs[bsi]
                image[oy + bsi, ox + 0, 0:3] = colors[(b0 >> 0) & 0x3][0:3]
                image[oy + bsi, ox + 1, 0:3] = colors[(b0 >> 2) & 0x3][0:3]
                image[oy + bsi, ox + 2, 0:3] = colors[(b0 >> 4) & 0x3][0:3]
                image[oy + bsi, ox + 3, 0:3] = colors[(b0 >> 6) & 0x3][0:3]
            for syi in range(4):
                for sxi in range(4):
                    image[oy + syi, ox + sxi, 3] = (alpha & 0x0f) << 4
                    alpha = alpha >> 4


@njit(fastmath=True)
def process_image_76(image, buffer, n_buffer, nx, ny):
    pos = 0
    bnx = max(1, nx // 4)
    bny = max(1, ny // 4)

    alpha = np.zeros((8,), dtype=np.uint8)
    bs = np.zeros((4,), dtype=np.uint8)
    color0_full = np.array((4,), dtype=np.uint8)
    color1_full = np.array((4,), dtype=np.uint8)
    colors = np.zeros((4, 4), dtype=np.uint8)

    for yi in range(bny):
        for xi in range(bnx):
            alpha_0, pos = ff_read_u8(buffer, n_buffer, pos)
            alpha_1, pos = ff_read_u8(buffer, n_buffer, pos)
            a0, pos = ff_read_u16(buffer, n_buffer, pos)
            a1, pos = ff_read_u16(buffer, n_buffer, pos)
            a2, pos = ff_read_u16(buffer, n_buffer, pos)
            aidx = a2 << 32 | a1 << 16 | a0

            alpha[0] = alpha_0
            alpha[1] = alpha_1
            if alpha_0 > alpha_1:
                # 6 interpolated alpha values.
                alpha[2] = (6 * alpha_0 + 1 * alpha_1) // 7  # bit code 010
                alpha[3] = (5 * alpha_0 + 2 * alpha_1) // 7   # bit code 011
                alpha[4] = (4 * alpha_0 + 3 * alpha_1) // 7   # bit code 100
                alpha[5] = (3 * alpha_0 + 4 * alpha_1) // 7   # bit code 101
                alpha[6] = (2 * alpha_0 + 5 * alpha_1) // 7   # bit code 110
                alpha[7] = (1 * alpha_0 + 6 * alpha_1) // 7   # bit code 111
            else:
                # 4 interpolated alpha values.
                alpha[2] = (4 * alpha_0 + 1 * alpha_1) // 5  # bit code 010
                alpha[3] = (3 * alpha_0 + 2 * alpha_1) // 5  # bit code 011
                alpha[4] = (2 * alpha_0 + 3 * alpha_1) // 5  # bit code 100
                alpha[5] = (1 * alpha_0 + 4 * alpha_1) // 5  # bit code 101
                alpha[6] = 0  # bit code 110
                alpha[7] = 255  # bit code 111

            color0, pos = ff_read_u16(buffer, n_buffer, pos)
            color1, pos = ff_read_u16(buffer, n_buffer, pos)
            bs[0], pos = ff_read_u8(buffer, n_buffer, pos)
            bs[1], pos = ff_read_u8(buffer, n_buffer, pos)
            bs[2], pos = ff_read_u8(buffer, n_buffer, pos)
            bs[3], pos = ff_read_u8(buffer, n_buffer, pos)

            color0_full[0] = ((color0 >> 11) & 0x1F) << 3
            color0_full[1] = ((color0 >> 5) & 0x3F) << 2
            color0_full[2] = ((color0 >> 0) & 0x1F) << 3
            color0_full[3] = 0xFF

            color1_full[0] = ((color1 >> 11) & 0x1F) << 3
            color1_full[1] = ((color1 >> 5) & 0x3F) << 2
            color1_full[2] = ((color1 >> 0) & 0x1F) << 3
            color1_full[3] = 0xFF

            if color0 > color1:
                for i in range(4):
                    colors[0, i] = color0_full[i]
                    colors[1, i] = color1_full[i]
                    colors[2, i] = (2 * color0_full[i] + color1_full[i] + 1) // 3
                    colors[3, i] = (color0_full[i] + 2 * color1_full[i] + 1) // 3
                for i in range(4):
                    colors[i, 3] = 255
            else:
                for i in range(4):
                    colors[0, i] = color0_full[i]
                    colors[1, i] = color1_full[i]
                    colors[2, i] = (1 * color0_full[i] + color1_full[i]) // 2
                    colors[3, i] = 0
                for i in range(4):
                    colors[i, 3] = 255

            # print(colors)

            ox = xi * 4
            oy = yi * 4
            for bsi in range(4):
                b0 = bs[bsi]
                for i in range(4):
                    image[oy + bsi, ox + 0, i] = colors[(b0 >> 0) & 0x3][i]
                    image[oy + bsi, ox + 1, i] = colors[(b0 >> 2) & 0x3][i]
                    image[oy + bsi, ox + 2, i] = colors[(b0 >> 4) & 0x3][i]
                    image[oy + bsi, ox + 3, i] = colors[(b0 >> 6) & 0x3][i]
            for syi in range(4):
                for sxi in range(4):
                    image[oy + syi, ox + sxi, 3] = alpha[aidx & 0x7]
                    aidx = aidx >> 3


@njit
def process_image_79(image, buffer, n_buffer, nx, ny):
    pos = 0
    bnx = max(1, nx // 4)
    bny = max(1, ny // 4)
    for yi in range(bny):
        for xi in range(bnx):
            red_0, pos = ff_read_u8(buffer, n_buffer, pos)
            red_1, pos = ff_read_u8(buffer, n_buffer, pos)
            r0, pos = ff_read_u16(buffer, n_buffer, pos)
            r1, pos = ff_read_u16(buffer, n_buffer, pos)
            r2, pos = ff_read_u16(buffer, n_buffer, pos)
            ridx = r2 << 32 | r1 << 16 | r0

            red = np.zeros((8,), dtype=np.uint8)
            red[0] = red_0
            red[1] = red_1
            if red_0 > red_1:
                # 6 interpolated red values.
                red[2] = 6. / 7 * red_0 + 1. / 7 * red_1  # bit code 010
                red[3] = 5. / 7 * red_0 + 2. / 7 * red_1  # bit code 011
                red[4] = 4. / 7 * red_0 + 3. / 7 * red_1  # bit code 100
                red[5] = 3. / 7 * red_0 + 4. / 7 * red_1  # bit code 101
                red[6] = 2. / 7 * red_0 + 5. / 7 * red_1  # bit code 110
                red[7] = 1. / 7 * red_0 + 6. / 7 * red_1  # bit code 111
            else:
                # 4 interpolated red values.
                red[2] = 4. / 5 * red_0 + 1. / 5 * red_1  # bit code 010
                red[3] = 3. / 5 * red_0 + 2. / 5 * red_1  # bit code 011
                red[4] = 2. / 5 * red_0 + 3. / 5 * red_1  # bit code 100
                red[5] = 1. / 5 * red_0 + 4. / 5 * red_1  # bit code 101
                red[6] = 0  # bit code 110
                red[7] = 255  # bit code 111
            ox = xi * 4
            oy = yi * 4
            for syi in range(4):
                for sxi in range(4):
                    image[oy + syi, ox + sxi, 0] = red[ridx & 0x7]
                    image[oy + syi, ox + sxi, 1] = 0
                    image[oy + syi, ox + sxi, 2] = 0
                    image[oy + syi, ox + sxi, 3] = 255
                    ridx = ridx >> 3


@njit
def process_image_82(image, buffer, n_buffer, nx, ny):
    pos = 0
    bnx = max(1, nx // 4)
    bny = max(1, ny // 4)
    for yi in range(bny):
        for xi in range(bnx):
            red_0, pos = ff_read_u8(buffer, n_buffer, pos)
            red_1, pos = ff_read_u8(buffer, n_buffer, pos)
            r0, pos = ff_read_u16(buffer, n_buffer, pos)
            r1, pos = ff_read_u16(buffer, n_buffer, pos)
            r2, pos = ff_read_u16(buffer, n_buffer, pos)
            ridx = r2 << 32 | r1 << 16 | r0
            red = np.zeros((8,), dtype=np.uint8)
            red[0] = red_0
            red[1] = red_1
            if red_0 > red_1:
                # 6 interpolated red values.
                red[2] = 6. / 7 * red_0 + 1. / 7 * red_1  # bit code 010
                red[3] = 5. / 7 * red_0 + 2. / 7 * red_1  # bit code 011
                red[4] = 4. / 7 * red_0 + 3. / 7 * red_1  # bit code 100
                red[5] = 3. / 7 * red_0 + 4. / 7 * red_1  # bit code 101
                red[6] = 2. / 7 * red_0 + 5. / 7 * red_1  # bit code 110
                red[7] = 1. / 7 * red_0 + 6. / 7 * red_1  # bit code 111
            else:
                # 4 interpolated red values.
                red[2] = 4. / 5 * red_0 + 1. / 5 * red_1  # bit code 010
                red[3] = 3. / 5 * red_0 + 2. / 5 * red_1  # bit code 011
                red[4] = 2. / 5 * red_0 + 3. / 5 * red_1  # bit code 100
                red[5] = 1. / 5 * red_0 + 4. / 5 * red_1  # bit code 101
                red[6] = 0  # bit code 110
                red[7] = 255  # bit code 111

            green_0, pos = ff_read_u8(buffer, n_buffer, pos)
            green_1, pos = ff_read_u8(buffer, n_buffer, pos)
            g0, pos = ff_read_u16(buffer, n_buffer, pos)
            g1, pos = ff_read_u16(buffer, n_buffer, pos)
            g2, pos = ff_read_u16(buffer, n_buffer, pos)
            gidx = g2 << 32 | g1 << 16 | g0
            green = np.zeros((8,), dtype=np.uint8)
            green[0] = green_0
            green[1] = green_1
            if green_0 > green_1:
                # 6 interpolated green values.
                green[2] = 6. / 7 * green_0 + 1. / 7 * green_1  # bit code 010
                green[3] = 5. / 7 * green_0 + 2. / 7 * green_1  # bit code 011
                green[4] = 4. / 7 * green_0 + 3. / 7 * green_1  # bit code 100
                green[5] = 3. / 7 * green_0 + 4. / 7 * green_1  # bit code 101
                green[6] = 2. / 7 * green_0 + 5. / 7 * green_1  # bit code 110
                green[7] = 1. / 7 * green_0 + 6. / 7 * green_1  # bit code 111
            else:
                # 4 interpolated green values.
                green[2] = 4. / 5 * green_0 + 1. / 5 * green_1  # bit code 010
                green[3] = 3. / 5 * green_0 + 2. / 5 * green_1  # bit code 011
                green[4] = 2. / 5 * green_0 + 3. / 5 * green_1  # bit code 100
                green[5] = 1. / 5 * green_0 + 4. / 5 * green_1  # bit code 101
                green[6] = 0  # bit code 110
                green[7] = 255  # bit code 111

            ox = xi * 4
            oy = yi * 4
            for syi in range(4):
                for sxi in range(4):
                    image[oy + syi, ox + sxi, 0] = red[ridx & 0x7]
                    image[oy + syi, ox + sxi, 1] = green[gidx & 0x7]
                    image[oy + syi, ox + sxi, 2] = 0
                    image[oy + syi, ox + sxi, 3] = 255
                    ridx = ridx >> 3
                    gidx = gidx >> 3


def process_image_python(image, raw, nx, ny, pixel_format):
    # print(f'PF = {pixel_format}')
    base_format = dxgi_base_format_db[pixel_format]

    loaders = {
        2: process_image_2,    # DXGI_FORMAT_R32G32B32A32_FLOAT
        10: process_image_10,  # DXGI_FORMAT_R16G16B16A16_FLOAT
        26: process_image_26,  # DXGI_FORMAT_R11G11B10_FLOAT
        28: process_image_28,  # DXGI_FORMAT_R8G8B8A8_UNORM
        41: process_image_41,  # DXGI_FORMAT_R32_FLOAT
        53: process_image_53,  # DXGI_FORMAT_R16_TYPELESS u16
        54: process_image_54,  # DXGI_FORMAT_R16_FLOAT f16
        58: process_image_58,  # DXGI_FORMAT_R16_SNORM s16
        60: process_image_60,  # DXGI_FORMAT_R8_TYPELESS u8
        63: process_image_63,  # DXGI_FORMAT_R8_TYPELESS s8
        70: process_image_70,  # DXGI_FORMAT_BC1_TYPELESS
        73: process_image_73,  # DXGI_FORMAT_BC2_TYPELESS
        76: process_image_76,  # DXGI_FORMAT_BC3_TYPELESS
        79: process_image_79,  # DXGI_FORMAT_BC4_TYPELESS
        82: process_image_82,  # DXGI_FORMAT_BC5_TYPELESS
        87: process_image_87,  # DXGI_FORMAT_B8G8R8A8_UNORM
        94: process_image_94_95_96,  # DXGI_FORMAT_BC6H_TYPELESS
        97: process_image_97,  # DXGI_FORMAT_BC7_TYPELESS
    }

    if base_format in loaders:
        loaders[base_format](image, raw, len(raw), nx, ny)
    else:
        raise Exception('Unknown DCC format {} base {}'.format(pixel_format, base_format))


def process_image_c(image, raw, nx, ny, pixel_format):

    if pixel_format in {2, 10, 26, 41, 94, 95, 96}:  # do floating point loads in python
        process_image_python(image, raw, nx, ny, pixel_format)
    else:
        global c_process_image_func
        ret = c_process_image_func(
            image.ctypes.data_as(ctypes.POINTER(ctypes.c_uint8)),
            len(image),
            raw,
            len(raw),
            nx,
            ny,
            pixel_format)

        if ret == -1:
            print('FALLING BACK TO PYTHON PARSER')
            process_image_python(image, raw, nx, ny, pixel_format)
        elif ret != 0:
            raise Exception('process_image_c failed with return {}'.format(ret))


def process_image(*args, **kwargs):
    global process_image_func
    global c_process_image_lib
    global c_process_image_func

    if process_image_func is None:
        c_process_image_lib = None
        exe_path, exe_name = os.path.split(sys.argv[0])
        lib_path = os.path.join("./", exe_path, "..", "..", "..", "root", "lib")

        # process_image_func = setup_image_wasm

        if process_image_func is None:
            # "C:\Program Files (x86)\Microsoft Visual Studio\2017\Community\VC\Auxiliary\Build\vcvars64.bat"
            # "cl.exe /D_USRDLL /D_WINDLL deca/process_image.c /link /DLL /OUT:process_image.dll"

            # gcc -fPIC -shared -O3 deca/process_image.c -o process_image.so
            paths = [
                "process_image.dll",
                os.path.join(lib_path, "process_image.dll"),
                "process_image.so",
                os.path.join(lib_path, "process_image.so"),
            ]

            for path in paths:
                if os.path.isfile(path):
                    print(f"Using C version of process_image from {path}")
                    if os.path.splitext(path)[1].lower() == ".dll":
                        c_process_image_lib = ctypes.WinDLL(path)
                    else:
                        c_process_image_lib = ctypes.CDLL(path)
                    break

            if c_process_image_lib is not None:
                prototype = ctypes.CFUNCTYPE(
                    ctypes.c_int,
                    ctypes.POINTER(ctypes.c_uint8),
                    ctypes.c_uint32,
                    ctypes.POINTER(ctypes.c_char),
                    ctypes.c_uint32,
                    ctypes.c_uint32,
                    ctypes.c_uint32,
                    ctypes.c_uint32,
                )
                paramflags = \
                    (1, 'dst_image_buf'), \
                    (1, 'dst_image_sz'), \
                    (1, 'src_buffer_buf'), \
                    (1, 'src_buffer_sz'), \
                    (1, 'nx'), \
                    (1, 'ny'), \
                    (1, 'pixel_format')
                c_process_image_func = prototype(("process_image", c_process_image_lib), paramflags)
                process_image_func = process_image_c
            else:
                print('Using Python version of process_image')
                process_image_func = process_image_python

    process_image_func(*args, **kwargs)

    # t0 = time.time()
    # process_image_func(*args, **kwargs)
    # t1 = time.time()
    # print('C: Runtime {}'.format(t1-t0))
    #
    # t0 = time.time()
    # process_image_python(*args, **kwargs)
    # t1 = time.time()
    # print('Py: Runtime {}'.format(t1-t0))
    #
    # if (t1 - t0) > 1.0:
    #     print('--------------------------------------------------------------')
    #     print('PT == {}'.format(args[-1]))
    #     process_image_76.inspect_types()
    #     print('--------------------------------------------------------------')
    #     for k, v in process_image_76.inspect_llvm().items():
    #         print(k, v)
    #     print('--------------------------------------------------------------')
    #     for k, v in process_image_76.inspect_asm().items():
    #         print(k, v)
    #     print('--------------------------------------------------------------')

    #
    # t0 = time.time()
    # process_image_cython(*args, **kwargs)
    # t1 = time.time()
    # print('Runtime {}'.format(t1-t0))
