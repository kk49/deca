from numba import njit
import numpy as np


@njit()
def process_image_94_95_96(image, buffer, n_buffer, nx, ny):
    '''

    :param image:
    :param buffer:
    :param n_buffer:
    :param nx:
    :param ny:
    :return:
    '''


    # num subsets, end point, component
    end_points = np.zeros((3, 2, 4), dtype=np.ubyte)
    indexes_primary = [0] * 16
    indexes_secondary = [0] * 16

    pos = 0
    bnx = max(1, nx // 4)
    bny = max(1, ny // 4)
    for yi in range(bny):
        for xi in range(bnx):
            ox = xi * 4
            oy = yi * 4
            for syi in range(4):
                for sxi in range(4):
                    image[oy + syi, ox + sxi, 0] = 0
                    image[oy + syi, ox + sxi, 1] = 0
                    image[oy + syi, ox + sxi, 2] = 0
                    image[oy + syi, ox + sxi, 3] = 0
            pos += 16


