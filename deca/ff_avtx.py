from deca.file import ArchiveFile
import deca.dxgi
import io
import time
import numpy as np


class Ddsc:
    def __init__(self):
        self.mips = None
        self.mips_params = None

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
        self.mips_params = []
        self.mips = []
        for i in range(full_mip_count):
            self.mips_params.append([pixel_format, nx, ny])
            self.mips.append([max(4, ny), max(4, nx), 'missing', None])
            nx = nx // 2
            ny = ny // 2

        for midx in range(full_mip_count - mip_count, full_mip_count):
            fl = self.mips_params[midx]
            pixel_format = fl[0]
            nx = fl[1]
            ny = fl[2]
            if nx == 0 or ny == 0:
                break
            nxm = max(4, nx)
            nym = max(4, ny)
            raw_size = deca.dxgi.raw_data_size(pixel_format, nx, ny)
            print('Loading Data: {}'.format(raw_size))
            raw_data = f.read(raw_size)
            if len(raw_data) < raw_size:
                raise Exception('Ddsc::load_ddsc: Not Enough Data')
            inp = np.zeros((nym, nxm, 4), dtype=np.uint8)
            print('Process Data: {}'.format(fl))
            t0 = time.time()
            deca.dxgi.process_image(inp, raw_data, nx, ny, pixel_format)
            t1 = time.time()
            print('Execute time: {} s'.format(t1 - t0))

            self.mips[midx] = [nym, nxm, 'ddsc', inp]

    def load_atx(self, f):
        first_loaded = 0
        while first_loaded < len(self.mips):
            if self.mips[first_loaded][3] is None:
                first_loaded = first_loaded + 1
            else:
                break

        for midx in range(first_loaded - 1, -1, -1):
            fl = self.mips_params[midx]
            pixel_format = fl[0]
            nx = fl[1]
            ny = fl[2]
            if nx == 0 or ny == 0:
                break
            nxm = max(4, nx)
            nym = max(4, ny)
            raw_size = deca.dxgi.raw_data_size(pixel_format, nx, ny)
            print('Loading Data: {}'.format(raw_size))
            raw_data = f.read(raw_size)
            raw_data_size = len(raw_data)
            if raw_data_size == 0:
                break  # Ran out of data probably because more data is in another atx
            if raw_data_size < raw_size:
                raise Exception('Ddsc::load_atx: Not Enough Data')
            inp = np.zeros((nym, nxm, 4), dtype=np.uint8)
            print('Process Data: {}'.format(fl))
            t0 = time.time()
            deca.dxgi.process_image(inp, raw_data, nx, ny, pixel_format)
            t1 = time.time()
            print('Execute time: {} s'.format(t1 - t0))

            self.mips[midx] = [nym, nxm, 'atx', inp]


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

