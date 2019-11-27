import os
import io
import time
import pprint
import numpy as np
from PIL import Image
from deca.file import ArchiveFile
from deca.errors import *
from deca.ff_types import *
import deca.dxgi


class DecaImage:
    def __init__(
            self, sx=None, sy=None, depth_cnt=None, depth_idx=None, pixel_format=None,
            itype=None, data=None, raw_data=None, filename=None):
        self.size_x = sx
        self.size_y = sy
        self.depth_cnt = depth_cnt
        self.depth_idx = depth_idx
        self.pixel_format = pixel_format
        self.itype = itype
        self.data = data
        self.raw_data = raw_data
        self.filename = filename

    def pil_image(self):
        return Image.fromarray(self.data)


class Ddsc:
    def __init__(self):
        self.header_buffer = None
        self.magic = None
        self.version = None
        self.unknown = None
        self.dim = None
        self.pixel_format = None
        self.nx0 = None
        self.ny0 = None
        self.depth = None
        self.flags = None
        self.full_mip_count = None
        self.mip_count = None
        self.mips = None

    def load_bmp(self, f, filename=None):
        im = Image.open(f)
        im.convert('RGBA')
        self.mips = [DecaImage(sx=im.size[0], sy=im.size[1], itype='bmp', data=np.array(im), filename=filename)]

    def load_ddsc(self, f, filename=None, save_raw_data=False):
        header = f.read(128)
        self.header_buffer = header

        fh = ArchiveFile(io.BytesIO(header))

        self.unknown = []
        self.magic = fh.read_u32()
        self.version = fh.read_u16()
        self.unknown.append(fh.read_u8())
        self.dim = fh.read_u8()
        self.pixel_format = fh.read_u32()
        self.nx0 = fh.read_u16()
        self.ny0 = fh.read_u16()
        self.depth = fh.read_u16()
        self.flags = fh.read_u16()
        self.full_mip_count = fh.read_u8()
        self.mip_count = fh.read_u8()
        self.unknown.append(fh.read_u16())
        while fh.tell() < 128:
            self.unknown.append(fh.read_u32())

        # print('Compression Format: {}'.format(self.pixel_format))

        nx = self.nx0
        ny = self.ny0
        self.mips = []
        for i in range(self.full_mip_count):
            for j in range(self.depth):
                self.mips.append(DecaImage(
                    sx=nx, sy=ny, depth_cnt=self.depth, depth_idx=j, pixel_format=self.pixel_format, itype='missing'))

            nx = nx // 2
            ny = ny // 2

        for midx in range((self.full_mip_count - self.mip_count) * self.depth, self.full_mip_count * self.depth):
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
            # t0 = time.time()
            deca.dxgi.process_image(inp, raw_data, nx, ny, pixel_format)
            # inp = inp[0:ny, 0:nx, :]  # TODO Qt cannot display 2x2 for some reason
            if ny < nym or nx < nxm:
                inp[ny:, :, :] = 0
                inp[:, nx:, :] = 0
            # t1 = time.time()
            # print('Execute time: {} s'.format(t1 - t0))
            mip.itype = 'ddsc'
            mip.data = inp
            mip.filename = filename

            if save_raw_data:
                mip.raw_data = raw_data

    def load_atx(self, f, filename=None, save_raw_data=False):
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
            # t0 = time.time()
            deca.dxgi.process_image(inp, raw_data, nx, ny, pixel_format)
            # t1 = time.time()
            # print('Execute time: {} s'.format(t1 - t0))

            mip.itype = 'atx'
            mip.data = inp
            mip.filename = filename

            if save_raw_data:
                mip.raw_data = raw_data

    def load_ddsc_atx(self, files, save_raw_data=False):
        self.load_ddsc(files[0][1], filename=files[0][0], save_raw_data=save_raw_data)
        for finfo in files[1:]:
            self.load_atx(finfo[1], filename=finfo[0], save_raw_data=save_raw_data)

    def load_dds(self, f):
        im = Image.open(f)
        im.convert('RGBA')
        self.mips = [DecaImage(sx=im.size[0], sy=im.size[1], itype='dds', data=np.array(im))]

    def load_dds_new(self, f, load_raw_data=False):
        if isinstance(f, str) or isinstance(f, bytes):
            with ArchiveFile(open(f, 'rb')) as f:
                return self.load_dds_new(f, load_raw_data=load_raw_data)
        else:
            magic = f.read(4)

            if magic != b'DDS ':
                raise EDecaIncorrectFileFormat('load_dds')

            # DDS_HEADER
            header = {}
            header['dwSize'] = f.read_u32()
            header['dwFlags'] = f.read_u32()
            header['dwHeight'] = f.read_u32()
            header['dwWidth'] = f.read_u32()
            header['dwPitchOrLinearSize'] = f.read_u32()
            header['dwDepth'] = f.read_u32()
            header['dwMipMapCount'] = f.read_u32()

            header['dwReserved1'] = []
            for i in range(11):
                header['dwReserved1'].append(f.read_u32())

            # PIXEL_FORMAT
            pixel_format = {}
            pixel_format['dwSize'] = f.read_u32()
            pixel_format['dwFlags'] = f.read_u32()
            pixel_format['dwFourCC'] = f.read(4)
            pixel_format['dwRGBBitCount'] = f.read_u32()
            pixel_format['dwRBitMask'] = f.read_u32()
            pixel_format['dwGBitMask'] = f.read_u32()
            pixel_format['dwBBitMask'] = f.read_u32()
            pixel_format['dwABitMask'] = f.read_u32()

            # DDS_HEADER continued
            header['ddspf'] = pixel_format
            header['dwCaps'] = f.read_u32()
            header['dwCaps2'] = f.read_u32()
            header['dwCaps3'] = f.read_u32()
            header['dwCaps4'] = f.read_u32()
            header['dwReserved2'] = f.read_u32()

            # DDS_HEADER_DXT10
            header_dxt10 = {}
            if header['ddspf']['dwFourCC'] == b'DX10':
                header_dxt10['dxgiFormat'] = f.read_u32()
                header_dxt10['resourceDimension'] = f.read_u32()
                header_dxt10['miscFlag'] = f.read_u32()
                header_dxt10['arraySize'] = f.read_u32()
                header_dxt10['miscFlags2'] = f.read_u32()

            pprint.pprint(header)
            pprint.pprint(header_dxt10)


            '''
            DDSD_CAPS;          Required in every .dds file.	0x1
            DDSD_HEIGHT;        Required in every .dds file.	0x2
            DDSD_WIDTH;         Required in every .dds file.	0x4
            DDSD_PITCH;         Required when pitch is provided for an uncompressed texture.	0x8
            DDSD_PIXELFORMAT;   Required in every .dds file.	0x1000
            DDSD_MIPMAPCOUNT;   Required in a mipmapped texture.	0x20000
            DDSD_LINEARSIZE;    Required when pitch is provided for a compressed texture.	0x80000
            DDSD_DEPTH;         Required in a depth texture.	0x800000
            '''
            dwFlagsTest = [
                [0x1, 'DDSD_CAPS'],
                [0x2, 'DDSD_HEIGHT'],
                [0x4, 'DDSD_WIDTH'],
                [0x8, 'DDSD_PITCH'],
                [0x1000, 'DDSD_PIXELFORMAT'],
                [0x20000, 'DDSD_MIPMAPCOUNT'],
                [0x80000, 'DDSD_LINEARSIZE'],
                [0x800000, 'DDSD_DEPTH'],
            ]
            dwFlags = header['dwFlags']
            for test in dwFlagsTest:
                if 0 != dwFlags & test[0]:
                    print('dwFlags: {}'.format(test[1]))

            '''
            DDSCAPS_COMPLEX	Optional; 0x8
                must be used on any file that contains more than one surface (a mipmap, a cubic environment map, or 
                mipmapped volume texture).
            DDSCAPS_MIPMAP	Optional; 0x400000
                should be used for a mipmap.	
            DDSCAPS_TEXTURE	Required; 0x1000
            '''
            dwCapsTest = [
                [0x8, 'DDSCAPS_COMPLEX'],
                [0x400000, 'DDSCAPS_MIPMAP'],
                [0x1000, 'DDSCAPS_TEXTURE'],
            ]
            dwCaps = header['dwCaps']
            for test in dwCapsTest:
                if 0 != dwCaps & test[0]:
                    print('dwCaps: {}'.format(test[1]))

            '''
            DDSCAPS2_CUBEMAP	Required for a cube map.	0x200
            DDSCAPS2_CUBEMAP_POSITIVEX	Required when these surfaces are stored in a cube map.	0x400
            DDSCAPS2_CUBEMAP_NEGATIVEX	Required when these surfaces are stored in a cube map.	0x800
            DDSCAPS2_CUBEMAP_POSITIVEY	Required when these surfaces are stored in a cube map.	0x1000
            DDSCAPS2_CUBEMAP_NEGATIVEY	Required when these surfaces are stored in a cube map.	0x2000
            DDSCAPS2_CUBEMAP_POSITIVEZ	Required when these surfaces are stored in a cube map.	0x4000
            DDSCAPS2_CUBEMAP_NEGATIVEZ	Required when these surfaces are stored in a cube map.	0x8000
            DDSCAPS2_VOLUME	Required for a volume texture.	0x200000
            '''
            dwCaps2Test = [
                [0x200, 'DDSCAPS2_CUBEMAP'],
                [0x400, 'DDSCAPS2_CUBEMAP_POSITIVEX'],
                [0x800, 'DDSCAPS2_CUBEMAP_NEGATIVEX'],
                [0x1000, 'DDSCAPS2_CUBEMAP_POSITIVEY'],
                [0x2000, 'DDSCAPS2_CUBEMAP_NEGATIVEY'],
                [0x4000, 'DDSCAPS2_CUBEMAP_POSITIVEZ'],
                [0x8000, 'DDSCAPS2_CUBEMAP_NEGATIVEZ'],
                [0x200000, 'DDSCAPS2_VOLUME'],
            ]
            dwCaps2 = header['dwCaps2']
            for test in dwCaps2Test:
                if 0 != dwCaps2 & test[0]:
                    print('dwCaps2: {}'.format(test[1]))

            '''
            DDPF_ALPHAPIXELS	Texture contains alpha data; dwRGBAlphaBitMask contains valid data.	0x1
            DDPF_ALPHA	Used in some older DDS files for alpha channel only uncompressed data (dwRGBBitCount contains 
                the alpha channel bitcount; dwABitMask contains valid data)	0x2
            DDPF_FOURCC	Texture contains compressed RGB data; dwFourCC contains valid data.	0x4
            DDPF_RGB	Texture contains uncompressed RGB data; dwRGBBitCount and the RGB masks 
                (dwRBitMask, dwGBitMask, dwBBitMask) contain valid data.	0x40
            DDPF_YUV	Used in some older DDS files for YUV uncompressed data (dwRGBBitCount contains the YUV bit count; 
                dwRBitMask contains the Y mask, dwGBitMask contains the U mask, dwBBitMask contains the V mask)	0x200
            DDPF_LUMINANCE	Used in some older DDS files for single channel color uncompressed data (dwRGBBitCount 
                contains the luminance channel bit count; dwRBitMask contains the channel mask). Can be combined with 
                DDPF_ALPHAPIXELS for a two channel DDS file.	0x20000
            '''
            dwPFFlagsTest = [
                [0x1, 'DDPF_ALPHAPIXELS'],
                [0x2, 'DDPF_ALPHA'],
                [0x4, 'DDPF_FOURCC'],
                [0x40, 'DDPF_RGB'],
                [0x200, 'DDPF_YUV'],
                [0x20000, 'DDPF_LUMINANCE'],
            ]
            dwPFFlags = header['ddspf']['dwFlags']
            for test in dwPFFlagsTest:
                if 0 != dwPFFlags & test[0]:
                    print('dwPFFlags: {}'.format(test[1]))


def image_load(vfs, vnode, save_raw_data=False):
    if vnode.ftype == FTYPE_BMP:
        f_ddsc = vfs.file_obj_from(vnode)
        ddsc = Ddsc()
        ddsc.load_bmp(f_ddsc)
    elif vnode.ftype == FTYPE_DDS:
        f_ddsc = vfs.file_obj_from(vnode)
        ddsc = Ddsc()
        ddsc.load_dds(f_ddsc)
    elif vnode.ftype in {FTYPE_AVTX, FTYPE_ATX, FTYPE_HMDDSC}:
        if vnode.vpath is None:
            f_ddsc = vfs.file_obj_from(vnode)
            ddsc = Ddsc()
            ddsc.load_ddsc(f_ddsc)
        else:
            filename = os.path.splitext(vnode.vpath)
            if len(filename[1]) == 0 and vnode.ftype == FTYPE_AVTX:
                filename_ddsc = vnode.vpath
            else:
                filename_ddsc = filename[0] + b'.ddsc'

            if filename_ddsc in vfs.map_vpath_to_vfsnodes:
                extras = [b'.hmddsc']
                for i in range(1, 16):
                    extras.append('.atx{}'.format(i).encode('ascii'))

                files = []
                files.append([
                    filename_ddsc,
                    vfs.file_obj_from(vfs.map_vpath_to_vfsnodes[filename_ddsc][0]),
                ])
                for extra in extras:
                    filename_atx = filename[0] + extra
                    if filename_atx in vfs.map_vpath_to_vfsnodes:
                        files.append([
                            filename_atx,
                            vfs.file_obj_from(vfs.map_vpath_to_vfsnodes[filename_atx][0]),
                        ])
                ddsc = Ddsc()
                ddsc.load_ddsc_atx(files, save_raw_data=save_raw_data)
            else:
                raise EDecaFileMissing('File {} is missing.'.format(filename_ddsc))
    return ddsc


def image_export(vfs, node, extract_dir, export_raw, export_processed, allow_overwrite=False):
    existing_files = []
    ddsc = image_load(vfs, node, save_raw_data=True)

    if ddsc is not None:
        multifile = node.ftype in {FTYPE_AVTX, FTYPE_ATX, FTYPE_HMDDSC}

        if export_raw or not multifile:
            if multifile:
                cnodes = [mip.filename for mip in ddsc.mips]
                cnodes = set(cnodes)
                cnodes = [vfs.map_vpath_to_vfsnodes[cnode][0] for cnode in cnodes]
            else:
                cnodes = [node]

            for cnode in cnodes:
                if cnode.vpath is None:
                    ofile = extract_dir + '{:08X}.dat'.format(cnode.vhash)
                else:
                    ofile = extract_dir + '{}'.format(cnode.vpath.decode('utf-8'))

                ofiledir = os.path.dirname(ofile)
                os.makedirs(ofiledir, exist_ok=True)

                if not allow_overwrite  and os.path.isfile(ofile):
                    existing_files.append(ofile)
                else:
                    with open(ofile, 'wb') as fo:
                        with vfs.file_obj_from(cnode) as fi:
                            buffer = fi.read(cnode.size_u)
                            fo.write(buffer)

        if export_processed and multifile:
            if node.vpath is None:
                ofile = extract_dir + '{:08X}.dat'.format(node.vhash)
            else:
                ofile = extract_dir + '{}'.format(node.vpath.decode('utf-8'))

            ofiledir = os.path.dirname(ofile)
            os.makedirs(ofiledir, exist_ok=True)

            ofile = os.path.splitext(ofile)[0]
            ofile = ofile + '.ddsc'

            # export to reference png file
            ofile_img = ofile + '.REFERENCE_ONLY.png'
            if not allow_overwrite and os.path.isfile(ofile_img):
                existing_files.append(ofile_img)
            else:
                for i in range(len(ddsc.mips)):
                    if ddsc.mips[i].data is not None:
                        npimp = ddsc.mips[i].pil_image()
                        break
                npimp.save(ofile_img)

            # export dds with all mip levels
            ofile_img = ofile + '.dds'
            if not allow_overwrite and os.path.isfile(ofile_img):
                existing_files.append(ofile_img)
            else:
                flags = 0
                flags = flags | 0x1         # DDSD_CAPS
                flags = flags | 0x2         # DDSD_HEIGHT
                flags = flags | 0x4         # DDSD_WIDTH
                # flags = flags | 0x8         # DDSD_PITCH
                flags = flags | 0x1000      # DDSD_PIXELFORMAT
                flags = flags | 0x20000     # DDSD_MIPMAPCOUNT
                flags = flags | 0x80000     # DDSD_LINEARSIZE

                dwCaps1 = 0x8 | 0x1000 | 0x400000
                dwCaps2 = 0
                resourceDimension = 3

                if ddsc.depth > 1:
                    flags = flags | 0x800000        # DDSD_DEPTH
                    dwCaps2 = dwCaps2 | 0x200000
                    resourceDimension = 4

                with ArchiveFile(open(ofile_img, 'wb')) as f:
                    # magic word
                    f.write(b'DDS ')
                    # DDS_HEADER
                    f.write_u32(124)            # dwSize
                    f.write_u32(flags)          # dwFlags
                    f.write_u32(ddsc.ny0)       # dwHeight
                    f.write_u32(ddsc.nx0)       # dwWidth
                    f.write_u32(len(ddsc.mips[0].raw_data))  # dwPitchOrLinearSize
                    f.write_u32(ddsc.depth)     # dwDepth
                    f.write_u32(ddsc.full_mip_count)  # dwMipMapCount
                    for i in range(11):
                        f.write_u32(0)  # dwReserved1

                    # PIXEL_FORMAT
                    DDPF_FOURCC = 0x4
                    f.write_u32(32)  # DWORD dwSize
                    f.write_u32(DDPF_FOURCC)  # DWORD dwFlags
                    f.write(b'DX10')  # DWORD dwFourCC
                    f.write_u32(0)  # DWORD dwRGBBitCount
                    f.write_u32(0)  # DWORD dwRBitMask
                    f.write_u32(0)  # DWORD dwGBitMask
                    f.write_u32(0)  # DWORD dwBBitMask
                    f.write_u32(0)  # DWORD dwABitMask

                    # DDS_HEADER, cont...
                    f.write_u32(dwCaps1)          # dwCaps
                    f.write_u32(dwCaps2)          # dwCaps2
                    f.write_u32(0)          # dwCaps3
                    f.write_u32(0)          # dwCaps4
                    f.write_u32(0)          # dwReserved2

                    # DDS_HEADER_DXT10
                    f.write_u32(ddsc.pixel_format)  # DXGI_FORMAT              dxgiFormat;
                    f.write_u32(resourceDimension)  # D3D10_RESOURCE_DIMENSION resourceDimension;
                    f.write_u32(0)  # UINT                     miscFlag;
                    f.write_u32(1)  # UINT                     arraySize;
                    f.write_u32(0)  # UINT                     miscFlags2;

                    for mip in ddsc.mips:
                        f.write(mip.raw_data)

        # raise exception if any files could not be overwritten
        if len(existing_files) > 0:
            raise EDecaFileExists(existing_files)


def image_import(vfs, node, ifile: str, opath: str):
    print('Importing Image: {}\n  input {}\n  opath {}'.format(node.vpath, ifile, opath))
    ddsc = image_load(vfs, node, save_raw_data=True)

    compiled_files = []
    if ddsc is not None:
        with open(ifile, 'rb') as file_in:
            dsc_header = file_in.read(37 * 4 - 5 * 4)  # skip dds header
            for mip in ddsc.mips:
                buffer = file_in.read(len(mip.raw_data))
                mip.raw_data = buffer

        out_vpaths = [mip.filename for mip in ddsc.mips]
        out_vpaths = set(out_vpaths)

        for vpath_out in out_vpaths:
            fout_name = os.path.join(opath, vpath_out.decode('utf-8'))

            with open(fout_name, 'wb') as file_out:
                if vpath_out.endswith(b'.ddsc'):
                    file_out.write(ddsc.header_buffer)
                    # DDSC files have high to low resolution
                    for mip_index in range(0, len(ddsc.mips)):
                        mip = ddsc.mips[mip_index]
                        if vpath_out == mip.filename:
                            file_out.write(mip.raw_data)
                else:
                    # HMDDSC ATX files have low to high resolution
                    for mip_index in range(len(ddsc.mips)-1, -1, -1):
                        mip = ddsc.mips[mip_index]
                        if vpath_out == mip.filename:
                            file_out.write(mip.raw_data)

            compiled_files.append((vpath_out, fout_name))

    return compiled_files

'''
typedef struct {
  DWORD           dwSize;
  DWORD           dwFlags;
  DWORD           dwHeight;
  DWORD           dwWidth;
  DWORD           dwPitchOrLinearSize;
  DWORD           dwDepth;
  DWORD           dwMipMapCount;
  DWORD           dwReserved1[11];
  DDS_PIXELFORMAT ddspf;
  DWORD           dwCaps;
  DWORD           dwCaps2;
  DWORD           dwCaps3;
  DWORD           dwCaps4;
  DWORD           dwReserved2;
} DDS_HEADER;

struct DDS_PIXELFORMAT {
  DWORD dwSize;
  DWORD dwFlags;
  DWORD dwFourCC;
  DWORD dwRGBBitCount;
  DWORD dwRBitMask;
  DWORD dwGBitMask;
  DWORD dwBBitMask;
  DWORD dwABitMask;
};

typedef struct {
  DXGI_FORMAT              dxgiFormat;
  D3D10_RESOURCE_DIMENSION resourceDimension;
  UINT                     miscFlag;
  UINT                     arraySize;
  UINT                     miscFlags2;
} DDS_HEADER_DXT10;

'''
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

