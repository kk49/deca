import numpy as np
import struct
import io
import os
import ctypes
import sys
# import time
# from deca.process_image_python import process_image_cython

process_image_func = None
c_process_image_lib = None
c_process_image_func = None

# https://docs.microsoft.com/en-us/windows/desktop/direct3d9/opaque-and-1-bit-alpha-textures
# https://msdn.microsoft.com/ja-jp/library/bb173059(v=vs.85).aspx
'''
    DXGI_FORMAT_UNKNOWN = 0,
    DXGI_FORMAT_R32G32B32A32_TYPELESS = 1,
    DXGI_FORMAT_R32G32B32A32_FLOAT = 2,
    DXGI_FORMAT_R32G32B32A32_UINT = 3,
    DXGI_FORMAT_R32G32B32A32_SINT = 4,
    DXGI_FORMAT_R32G32B32_TYPELESS = 5,
    DXGI_FORMAT_R32G32B32_FLOAT = 6,
    DXGI_FORMAT_R32G32B32_UINT = 7,
    DXGI_FORMAT_R32G32B32_SINT = 8,
    DXGI_FORMAT_R16G16B16A16_TYPELESS = 9,
    DXGI_FORMAT_R16G16B16A16_FLOAT = 10,
    DXGI_FORMAT_R16G16B16A16_UNORM = 11,
    DXGI_FORMAT_R16G16B16A16_UINT = 12,
    DXGI_FORMAT_R16G16B16A16_SNORM = 13,
    DXGI_FORMAT_R16G16B16A16_SINT = 14,
    DXGI_FORMAT_R32G32_TYPELESS = 15,
    DXGI_FORMAT_R32G32_FLOAT = 16,
    DXGI_FORMAT_R32G32_UINT = 17,
    DXGI_FORMAT_R32G32_SINT = 18,
    DXGI_FORMAT_R32G8X24_TYPELESS = 19,
    DXGI_FORMAT_D32_FLOAT_S8X24_UINT = 20,
    DXGI_FORMAT_R32_FLOAT_X8X24_TYPELESS = 21,
    DXGI_FORMAT_X32_TYPELESS_G8X24_UINT = 22,
    DXGI_FORMAT_R10G10B10A2_TYPELESS = 23,
    DXGI_FORMAT_R10G10B10A2_UNORM = 24,
    DXGI_FORMAT_R10G10B10A2_UINT = 25,
    DXGI_FORMAT_R11G11B10_FLOAT = 26,
    DXGI_FORMAT_R8G8B8A8_TYPELESS = 27,
    DXGI_FORMAT_R8G8B8A8_UNORM = 28,
    DXGI_FORMAT_R8G8B8A8_UNORM_SRGB = 29,
    DXGI_FORMAT_R8G8B8A8_UINT = 30,
    DXGI_FORMAT_R8G8B8A8_SNORM = 31,
    DXGI_FORMAT_R8G8B8A8_SINT = 32,
    DXGI_FORMAT_R16G16_TYPELESS = 33,
    DXGI_FORMAT_R16G16_FLOAT = 34,
    DXGI_FORMAT_R16G16_UNORM = 35,
    DXGI_FORMAT_R16G16_UINT = 36,
    DXGI_FORMAT_R16G16_SNORM = 37,
    DXGI_FORMAT_R16G16_SINT = 38,
    DXGI_FORMAT_R32_TYPELESS = 39,
    DXGI_FORMAT_D32_FLOAT = 40,
    DXGI_FORMAT_R32_FLOAT = 41,
    DXGI_FORMAT_R32_UINT = 42,
    DXGI_FORMAT_R32_SINT = 43,
    DXGI_FORMAT_R24G8_TYPELESS = 44,
    DXGI_FORMAT_D24_UNORM_S8_UINT = 45,
    DXGI_FORMAT_R24_UNORM_X8_TYPELESS = 46,
    DXGI_FORMAT_X24_TYPELESS_G8_UINT = 47,
    DXGI_FORMAT_R8G8_TYPELESS = 48,
    DXGI_FORMAT_R8G8_UNORM = 49,
    DXGI_FORMAT_R8G8_UINT = 50,
    DXGI_FORMAT_R8G8_SNORM = 51,
    DXGI_FORMAT_R8G8_SINT = 52,
    DXGI_FORMAT_R16_TYPELESS = 53,
    DXGI_FORMAT_R16_FLOAT = 54,
    DXGI_FORMAT_D16_UNORM = 55,
    DXGI_FORMAT_R16_UNORM = 56,
    DXGI_FORMAT_R16_UINT = 57,
    DXGI_FORMAT_R16_SNORM = 58,
    DXGI_FORMAT_R16_SINT = 59,
    DXGI_FORMAT_R8_TYPELESS = 60,
    DXGI_FORMAT_R8_UNORM = 61,
    DXGI_FORMAT_R8_UINT = 62,
    DXGI_FORMAT_R8_SNORM = 63,
    DXGI_FORMAT_R8_SINT = 64,
    DXGI_FORMAT_A8_UNORM = 65,
    DXGI_FORMAT_R1_UNORM = 66,
    DXGI_FORMAT_R9G9B9E5_SHAREDEXP = 67,
    DXGI_FORMAT_R8G8_B8G8_UNORM = 68,
    DXGI_FORMAT_G8R8_G8B8_UNORM = 69,
    DXGI_FORMAT_BC1_TYPELESS = 70,
    DXGI_FORMAT_BC1_UNORM = 71,
    DXGI_FORMAT_BC1_UNORM_SRGB = 72,
    DXGI_FORMAT_BC2_TYPELESS = 73,
    DXGI_FORMAT_BC2_UNORM = 74,
    DXGI_FORMAT_BC2_UNORM_SRGB = 75,
    DXGI_FORMAT_BC3_TYPELESS = 76,
    DXGI_FORMAT_BC3_UNORM = 77,
    DXGI_FORMAT_BC3_UNORM_SRGB = 78,
    DXGI_FORMAT_BC4_TYPELESS = 79,
    DXGI_FORMAT_BC4_UNORM = 80,
    DXGI_FORMAT_BC4_SNORM = 81,
    DXGI_FORMAT_BC5_TYPELESS = 82,
    DXGI_FORMAT_BC5_UNORM = 83,
    DXGI_FORMAT_BC5_SNORM = 84,
    DXGI_FORMAT_B5G6R5_UNORM = 85,
    DXGI_FORMAT_B5G5R5A1_UNORM = 86,
    DXGI_FORMAT_B8G8R8A8_UNORM = 87,
    DXGI_FORMAT_B8G8R8X8_UNORM = 88,
    DXGI_FORMAT_FORCE_UINT = 0xffffffffUL,
'''

def process_image_10(image, f, nx, ny):
    for yi in range(ny):
        for xi in range(nx):
            buf = f.read(8)
            chans = struct.unpack('HHHH', buf)
            image[yi, xi, 0] = chans[0] >> 8
            image[yi, xi, 1] = chans[1] >> 8
            image[yi, xi, 2] = chans[2] >> 8
            image[yi, xi, 3] = chans[3] >> 8


def process_image_26(image, f, nx, ny):
    for yi in range(ny):
        for xi in range(nx):
            buf = f.read(4)
            chans = struct.unpack('I', buf)[0]
            image[yi, xi, 0] = ((chans >> 21) & 0x07ff) >> 3
            image[yi, xi, 1] = ((chans >> 10) & 0x07ff) >> 3
            image[yi, xi, 2] = ((chans >> 0) & 0x03ff) >> 2
            image[yi, xi, 3] = 0xff


def process_image_28(image, f, nx, ny):
    for yi in range(ny):
        for xi in range(nx):
            buf = f.read(4)
            chans = struct.unpack('BBBB', buf)
            image[yi, xi, :] = chans[:]


def process_image_87(image, f, nx, ny):
    for yi in range(ny):
        for xi in range(nx):
            buf = f.read(4)
            chans = struct.unpack('BBBB', buf)
            image[yi, xi, 0] = chans[2]
            image[yi, xi, 1] = chans[1]
            image[yi, xi, 2] = chans[0]
            image[yi, xi, 3] = chans[3]


def process_image_71(image, f, nx, ny):
    bnx = max(1, nx // 4)
    bny = max(1, ny // 4)
    for yi in range(bny):
        for xi in range(bnx):
            buf = f.read(8)
            color0, color1 = struct.unpack('HH', buf[0:4])
            bs = struct.unpack('BBBB', buf[4:8])

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


def process_image_74(image, f, nx, ny):
    bnx = max(1, nx // 4)
    bny = max(1, ny // 4)
    for yi in range(bny):
        for xi in range(bnx):
            # alpha setup
            buf = f.read(8)
            alpha = struct.unpack('Q', buf)[0]

            # color setup
            buf = f.read(8)
            color0, color1 = struct.unpack('HH', buf[0:4])
            bs = struct.unpack('BBBB', buf[4:8])

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


def process_image_77(image, f, nx, ny):
    bnx = max(1, nx // 4)
    bny = max(1, ny // 4)
    for yi in range(bny):
        for xi in range(bnx):
            buf = f.read(8)
            alpha_0, alpha_1, a0, a1, a2 = struct.unpack('BBHHH', buf)
            aidx = a2 << 32 | a1 << 16 | a0

            alpha = np.zeros((8,), dtype=np.uint8)
            alpha[0] = alpha_0
            alpha[1] = alpha_1
            if alpha_0 > alpha_1:
                # 6 interpolated alpha values.
                alpha[2] = 6. / 7 * alpha_0 + 1. / 7 * alpha_1  # bit code 010
                alpha[3] = 5. / 7 * alpha_0 + 2. / 7 * alpha_1  # bit code 011
                alpha[4] = 4. / 7 * alpha_0 + 3. / 7 * alpha_1  # bit code 100
                alpha[5] = 3. / 7 * alpha_0 + 4. / 7 * alpha_1  # bit code 101
                alpha[6] = 2. / 7 * alpha_0 + 5. / 7 * alpha_1  # bit code 110
                alpha[7] = 1. / 7 * alpha_0 + 6. / 7 * alpha_1  # bit code 111
            else:
                # 4 interpolated alpha values.
                alpha[2] = 4. / 5 * alpha_0 + 1. / 5 * alpha_1  # bit code 010
                alpha[3] = 3. / 5 * alpha_0 + 2. / 5 * alpha_1  # bit code 011
                alpha[4] = 2. / 5 * alpha_0 + 3. / 5 * alpha_1  # bit code 100
                alpha[5] = 1. / 5 * alpha_0 + 4. / 5 * alpha_1  # bit code 101
                alpha[6] = 0  # bit code 110
                alpha[7] = 255  # bit code 111

            buf = f.read(8)
            color0, color1 = struct.unpack('HH', buf[0:4])
            bs = struct.unpack('BBBB', buf[4:8])

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

            # print(colors)

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
                    image[oy + syi, ox + sxi, 3] = alpha[aidx & 0x7]
                    aidx = aidx >> 3


def process_image_80(image, f, nx, ny):
    bnx = max(1, nx // 4)
    bny = max(1, ny // 4)
    for yi in range(bny):
        for xi in range(bnx):
            buf = f.read(8)
            red_0, red_1, r0, r1, r2 = struct.unpack('BBHHH', buf)
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


def process_image_83(image, f, nx, ny):
    bnx = max(1, nx // 4)
    bny = max(1, ny // 4)
    for yi in range(bny):
        for xi in range(bnx):
            buf = f.read(8)
            red_0, red_1, r0, r1, r2 = struct.unpack('BBHHH', buf)
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

            buf = f.read(8)
            green_0, green_1, g0, g1, g2 = struct.unpack('BBHHH', buf)
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
    f = io.BytesIO(raw)

    loaders = {
        10: process_image_10,  # DXGI_FORMAT_R16G16B16A16_FLOAT
        26: process_image_26,  # DXGI_FORMAT_R11G11B10_FLOAT
        28: process_image_28,  # DXGI_FORMAT_R8G8B8A8_UNORM
        87: process_image_87,  # DXGI_FORMAT_B8G8R8A8_UNORM
        71: process_image_71,  # DXGI_FORMAT_BC1_UNORM
        74: process_image_74,  # DXGI_FORMAT_BC2_UNORM
        77: process_image_77,  # DXGI_FORMAT_BC3_UNORM
        80: process_image_80,  # DXGI_FORMAT_BC4_UNORM
        83: process_image_83,  # DXGI_FORMAT_BC5_UNORM
    }

    if pixel_format in loaders:
        loaders[pixel_format](image, f, nx, ny)
    else:
        raise Exception('Unknown DCC format {}'.format(pixel_format))


def raw_data_size(pixel_format, nx, ny):
    format_db = {
        10: [True, 8],
        26: [True, 4],
        28: [True, 4],
        87: [True, 4],
        71: [False, 8],
        74: [False, 16],
        77: [False, 16],
        80: [False, 8],
        83: [False, 16],

    }

    fi = format_db[pixel_format]

    if fi[0]:
        return fi[1] * nx * ny
    else:
        return fi[1] * ((nx + 3) // 4) * ((ny + 3) // 4)


def process_image_c(image, raw, nx, ny, pixel_format):
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
        print('FALLING BACK TO PYTHON PARSER, SLACKER!!!')
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
        if len(exe_path) == 0:
            exe_path = '.'
        if os.path.isfile('process_image.dll'):
            # "C:\Program Files (x86)\Microsoft Visual Studio\2017\Community\VC\Auxiliary\Build\vcvars64.bat"
            # "cl.exe /D_USRDLL /D_WINDLL deca/process_image.c /link /DLL /OUT:process_image.dll"
            c_process_image_lib = ctypes.WinDLL('process_image.dll')
        elif os.path.isfile(os.path.join(exe_path, 'process_image.so')):
            # gcc -fPIC -shared -O3 deca/process_image.c -o process_image.so
            c_process_image_lib = ctypes.CDLL(os.path.join(exe_path, 'process_image.so'))
        elif os.path.isfile('process_image.so'):
            # gcc -fPIC -shared -O3 deca/process_image.c -o process_image.so
            c_process_image_lib = ctypes.CDLL('process_image.so')

        if c_process_image_lib is not None:
            print('Using C version of process_image')
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
            process_image_func = process_image_python

    process_image_func(*args, **kwargs)

    # t0 = time.time()
    # process_image_func(*args, **kwargs)
    # t1 = time.time()
    # print('Runtime {}'.format(t1-t0))

    # t0 = time.time()
    # process_image_python(*args, **kwargs)
    # t1 = time.time()
    # print('Runtime {}'.format(t1-t0))
    #
    # t0 = time.time()
    # process_image_cython(*args, **kwargs)
    # t1 = time.time()
    # print('Runtime {}'.format(t1-t0))
