import numpy as np
cimport numpy as np
import struct
import io

ctypedef np.uint8_t u8_t

def process_image_10(np.ndarray[u8_t, ndim=3] image, f, np.int_t nx, np.int_t ny):
    cdef int yi = 0
    cdef int xi = 0
    for yi in range(ny):
        for xi in range(nx):
            buf = f.read(8)
            chans = struct.unpack('HHHH', buf)
            image[yi, xi, 0] = chans[0] >> 8
            image[yi, xi, 1] = chans[1] >> 8
            image[yi, xi, 2] = chans[2] >> 8
            image[yi, xi, 3] = chans[3] >> 8


def process_image_26(np.ndarray[u8_t, ndim=3] image, f, np.int_t nx, np.int_t ny):
    cdef int yi = 0
    cdef int xi = 0
    cdef np.uint32_t chans
    for yi in range(ny):
        for xi in range(nx):
            buf = f.read(4)
            chans = struct.unpack('I', buf)[0]
            image[yi, xi, 0] = ((chans >> 21) & 0x07ff) >> 3
            image[yi, xi, 1] = ((chans >> 10) & 0x07ff) >> 3
            image[yi, xi, 2] = ((chans >> 0) & 0x03ff) >> 2
            image[yi, xi, 3] = 0xff


def process_image_28(np.ndarray[u8_t, ndim=3] image, f, np.int_t nx, np.int_t ny):
    cdef int yi = 0
    cdef int xi = 0
    for yi in range(ny):
        for xi in range(nx):
            buf = f.read(4)
            chans = struct.unpack('BBBB', buf)
            image[yi, xi, :] = chans[:]


def process_image_87(np.ndarray[u8_t, ndim=3] image, f, np.int_t nx, np.int_t ny):
    cdef int yi = 0
    cdef int xi = 0
    for yi in range(ny):
        for xi in range(nx):
            buf = f.read(4)
            chans = struct.unpack('BBBB', buf)
            image[yi, xi, 0] = chans[2]
            image[yi, xi, 1] = chans[1]
            image[yi, xi, 2] = chans[0]
            image[yi, xi, 3] = chans[3]


def process_image_71(np.ndarray[u8_t, ndim=3] image, f, np.int_t nx, np.int_t ny):
    cdef np.int_t yi = 0
    cdef np.int_t xi = 0
    cdef np.int_t ox = 0
    cdef np.int_t oy = 0
    cdef np.int_t bsi = 0
    cdef np.uint8_t b0
    cdef np.uint16_t color0
    cdef np.uint16_t color1
    cdef np.ndarray[np.uint8_t, ndim=1] bs = np.zeros([4], dtype=np.uint8)
    cdef np.ndarray[np.uint8_t, ndim=2] colors = np.zeros([4, 4], dtype=np.uint8)

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


def process_image_74(np.ndarray[u8_t, ndim=3] image, f, np.int_t nx, np.int_t ny):
    cdef int yi = 0
    cdef int xi = 0

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


def process_image_77(np.ndarray[u8_t, ndim=3] image, f, np.int_t nx, np.int_t ny):
    cdef int yi = 0
    cdef int xi = 0

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


def process_image_80(np.ndarray[u8_t, ndim=3] image, f, np.int_t nx, np.int_t ny):
    cdef int yi = 0
    cdef int xi = 0

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


def process_image_83(np.ndarray[u8_t, ndim=3] image, f, np.int_t nx, np.int_t ny):
    cdef int yi = 0
    cdef int xi = 0

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


def process_image_cython(np.ndarray[u8_t, ndim=3] image, raw, np.int_t nx, np.int_t ny, np.int_t pixel_format):
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
