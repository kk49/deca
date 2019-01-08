from deca.file import ArchiveFile
import deca.dxgi
import io
import time
import numpy as np
from PIL import Image


class DecaImage:
    def __init__(self, sx=None, sy=None, depth_cnt=None, depth_idx=None, pixel_format=None, itype=None, data=None):
        self.size_x = sx
        self.size_y = sy
        self.depth_cnt = depth_cnt
        self.depth_idx = depth_idx
        self.pixel_format = pixel_format
        self.itype = itype
        self.data = data


class Ddsc:
    def __init__(self):
        self.mips = None

    def load_bmp(self, f):
        im = Image.open(f)
        im.convert('RGBA')
        self.mips = [DecaImage(sx=im.size[0], sy=im.size[1], itype='bmp', data=np.array(im))]

    def load_dds(self, f):
        im = Image.open(f)
        im.convert('RGBA')
        self.mips = [DecaImage(sx=im.size[0], sy=im.size[1], itype='dds', data=np.array(im))]

    def load_ddsc(self, f):
        header = f.read(128)
        fh = ArchiveFile(io.BytesIO(header))

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

        nx = nx0
        ny = ny0
        self.mips = []
        for i in range(full_mip_count):
            for j in range(depth):
                self.mips.append(DecaImage(sx=nx, sy=ny, depth_cnt=depth, depth_idx=j, pixel_format=pixel_format, itype='missing'))

            nx = nx // 2
            ny = ny // 2

        for midx in range((full_mip_count - mip_count) * depth, full_mip_count * depth):
            mip = self.mips[midx]
            pixel_format = mip.pixel_format
            nx = mip.size_x
            ny = mip.size_y
            if nx == 0 or ny == 0:
                break
            nxm = max(4, nx)
            nym = max(4, ny)
            raw_size = deca.dxgi.raw_data_size(pixel_format, nx, ny)
            # print('Loading Data: {}'.format(raw_size))
            raw_data = f.read(raw_size)
            if len(raw_data) < raw_size:
                raise Exception('Ddsc::load_ddsc: Not Enough Data')
            inp = np.zeros((nym, nxm, 4), dtype=np.uint8)
            # print('Process Data: {}'.format(mip))
            t0 = time.time()
            deca.dxgi.process_image(inp, raw_data, nx, ny, pixel_format)
            # inp = inp[0:ny, 0:nx, :]  # TODO Qt cannot display 2x2 for some reason
            if ny < nym or nx < nxm:
                inp[ny:, :, :] = 0
                inp[:, nx:, :] = 0
            t1 = time.time()
            # print('Execute time: {} s'.format(t1 - t0))
            mip.itype = 'ddsc'
            mip.data = inp

    def load_atx(self, f):
        first_loaded = 0
        while first_loaded < len(self.mips):
            if self.mips[first_loaded].data is None:
                first_loaded = first_loaded + 1
            else:
                break

        for midx in range(first_loaded - 1, -1, -1):
            mip = self.mips[midx]
            pixel_format = mip.pixel_format
            nx = mip.size_x
            ny = mip.size_y
            if nx == 0 or ny == 0:
                break
            nxm = max(4, nx)
            nym = max(4, ny)
            raw_size = deca.dxgi.raw_data_size(pixel_format, nx, ny)
            # print('Loading Data: {}'.format(raw_size))
            raw_data = f.read(raw_size)
            raw_data_size = len(raw_data)
            if raw_data_size == 0:
                break  # Ran out of data probably because more data is in another atx
            if raw_data_size < raw_size:
                raise Exception('Ddsc::load_atx: Not Enough Data')
            inp = np.zeros((nym, nxm, 4), dtype=np.uint8)
            # print('Process Data: {}'.format(mip))
            t0 = time.time()
            deca.dxgi.process_image(inp, raw_data, nx, ny, pixel_format)
            t1 = time.time()
            # print('Execute time: {} s'.format(t1 - t0))

            mip.itype = 'atx'
            mip.data = inp


# if dump:
#     im = PIL.Image.fromarray(inp)
#     fns = os.path.split(in_file)
#     ifn = fns[1]
#     fns = fns[0].split('/')
#     # print(fns)
#     if no_header:
#         impath = image_dump + 'raw_images/{:08x}/'.format(file_sz)
#     else:
#         impath = image_dump + '{:02d}/'.format(pixel_format)
#     impath = impath + '/'.join(fns[3:]) + '/'
#     imfn = impath + ifn + '.{:04d}x{:04d}.png'.format(fl[1], fl[2])
#     # print(imfn)
#     os.makedirs(impath, exist_ok=True)
#     if not os.path.isfile(imfn):
#         im.save(imfn)
# else:
#     plt.figure()
#     plt.imshow(inp, interpolation='none')
#     plt.show()

