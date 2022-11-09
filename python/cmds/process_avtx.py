import os
import io
import sys
import matplotlib.pyplot as plt
import numpy as np
import PIL
import datetime
import time
import deca.dxgi
from deca.file import ArchiveFile


# TODO when dumping, run through other mip levels, to check for too much or too little data
# TODO add option to delete dst file on exception to clean up partially working loader
# TODO place all mip levels on same image, just 1.5 to 2.0 times the size?


if len(sys.argv) < 2:
    in_file = './test/gz/files/models/characters/machines/scout/textures/scout_01_dif.ddsc'
else:
    in_file = sys.argv[1]

dump = False
image_dump = './test/gz/images/'
error_log = './test/gz/error.txt'

# with open(error_log, 'a') as ef:
#     ef.write('{}: {}: {}\n'.format(datetime.datetime.now(), in_file, 'START'))


try:
    file_sz = os.stat(in_file).st_size

    # guess type
    file_data_layout_db = {
        0x1000000: [[71, 8192, 4096]],
        0x800000: [[71, 4096, 4096]],
        0x400000: [[71, 4096, 2048]],
        0x280000: [[71, 512 * 4, 640 * 4]],
        0x200000: [[71, 512 * 4, 512 * 4]],
        0x150000: [[83, 512 * 1, 512 * 1+128], [83, 512 * 2, 512 * 2 + 256]],
        0x140000: [[71, 512 * 4, 320 * 4]],
        0x100000: [[71, 512 * 4, 256 * 4]],
        0xa0000: [[71, 256 * 2, 256 * 2], [71, 256 * 4, 256 * 4]],
        0x80000: [[71, 256 * 4, 256 * 4]],
        0x40000: [[71, 256 * 4, 128 * 4]],
        0x20000: [[71, 128 * 4, 128 * 4]],
        # 0x8000: [[83, 128 * 2, 128 * 1]],
    }

    with ArchiveFile(open(in_file, 'rb')) as f0:
        no_header = file_sz in file_data_layout_db
        if not no_header:
            file_sz = file_sz - 128
            header = f0.read(128)
            fh = ArchiveFile(io.BytesIO(header))

            p = 0
            magic = fh.read_u32()
            version = fh.read_u16()
            d = fh.read_u8()
            dim = fh.read_u8()
            pixel_format = fh.read_u32()
            nx0 = fh.read_u16()
            ny0 = fh.read_u16()
            depth = fh.read_u16()
            flags = fh.read_u16()
            full_mip_count = fh.read_u8()
            mip_count = fh.read_u8()
            d = fh.read_u16()
            while fh.tell() < 128:
                d = fh.read_u32()

            nx = nx0 >> (full_mip_count - mip_count)
            ny = ny0 >> (full_mip_count - mip_count)
            file_layout = []
            for i in range(mip_count):
                file_layout.append([pixel_format, nx, ny])
                nx = nx // 2
                ny = ny // 2
        else:
            file_layout = file_data_layout_db[file_sz]

        expected_sz = 0
        for fl in file_layout:
            expected_sz += deca.dxgi.raw_data_size(fl[0], fl[1], fl[2])
        # if file_sz != expected_sz:
        #     raise Exception('File Size Does Not Match: {}'.format(in_file))

        for fl in file_layout:
            print(fl)

        for fl in file_layout:
            pixel_format = fl[0]
            nx = fl[1]
            ny = fl[2]
            if nx == 0 or ny == 0:
                break
            nxm = max(4, nx)
            nym = max(4, ny)
            raw_size = deca.dxgi.raw_data_size(pixel_format, nx, ny)
            print('Loading Data: {}'.format(raw_size))
            raw_data = f0.read(raw_size)
            inp = np.zeros((nym, nxm, 4), dtype=np.uint8)
            print('Process Data: {}'.format(fl))
            t0 = time.time()
            deca.dxgi.process_image(inp, raw_data, nx, ny, pixel_format)
            t1 = time.time()
            print('Execute time: {} s'.format(t1 - t0))
            if dump:
                im = PIL.Image.fromarray(inp)
                fns = os.path.split(in_file)
                ifn = fns[1]
                fns = fns[0].split('/')
                # print(fns)
                if no_header:
                    impath = image_dump + 'raw_images/{:08x}/'.format(file_sz)
                else:
                    impath = image_dump + '{:02d}/'.format(pixel_format)
                impath = impath + '/'.join(fns[3:]) + '/'
                imfn = impath + ifn + '.{:04d}x{:04d}.png'.format(fl[1], fl[2])
                # print(imfn)
                os.makedirs(impath, exist_ok=True)
                if not os.path.isfile(imfn):
                    im.save(imfn)
            else:
                plt.figure()
                plt.imshow(inp, interpolation='none')
                plt.show()
except:
    t, v, tb = sys.exc_info()
    em = '{}: {}: {}: {}\n'.format(datetime.datetime.now(), in_file, t, v)
    print(em)
    with open(error_log, 'a') as ef:
        ef.write(em)
    raise

'''
00000000  41 56 54 58 01 00 00 02  47 00 00 00 00 01 00 01  |AVTX....G.......|
00000010  01 00 00 00 09 09 00 00  00 00 00 00 00 00 00 00  |................|
00000020  80 00 00 00 b8 aa 00 00  10 00 00 00 00 00 00 00  |................|
00000030  00 00 00 00 00 00 00 00  00 00 00 00 00 00 00 00  |................|
00000040  00 00 00 00 00 00 00 00  00 00 00 00 00 00 00 00  |................|
00000050  00 00 00 00 00 00 00 00  00 00 00 00 00 00 00 00  |................|
00000060  00 00 00 00 00 00 00 00  00 00 00 00 00 00 00 00  |................|
00000070  00 00 00 00 00 00 00 00  00 00 00 00 00 00 00 00  |................|
00000080  ff 7b 1f 84 aa aa aa aa  ff 7b 1f 84 aa aa aa aa  |.{.......{......|
00000090  ff 7b 1f 84 aa aa aa aa  ff 7b 1f 84 aa aa aa aa  |.{.......{......|
000000a0  ff 7b 1f 84 aa aa aa aa  ff 7b 1f 84 aa aa aa aa  |.{.......{......|
000000b0  ff 7b 1f 84 aa aa aa aa  ff 7b 1f 84 aa aa aa aa  |.{.......{......|
000000c0  ff 7b 1f 84 aa aa aa aa  ff 7b 1f 84 aa aa aa aa  |.{.......{......|

'''