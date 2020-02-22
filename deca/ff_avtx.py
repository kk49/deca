import os
import io
import pprint
import numpy as np
from PIL import Image
from .file import ArchiveFile
from .errors import *
from .ff_types import *
from .vfs_db import VfsDatabase, VfsNode
from .util import make_dir_for_file
from .dxgi_types import *

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


class DdImageHeader:
    def __init__(self):
        self.header_buffer = None
        self.dds_header = DdsHeader()
        self.dds_header_dxt10 = DdsHeaderDxt10()

        self.magic = None
        self.version = None
        self.unknown0 = None
        self.flags = 0
        self.mip_count = None
        self.unknown1 = None
        self.unknown2 = None
        self.unknown3 = None
        self.size_header = None
        self.size_body = None
        self.unknown = None

    def dump(self):
        print(f'magic: {self.magic}')
        print(f'version: {self.version}')
        print(f'UNKNOWN0: {self.unknown0}')
        print(f'flags: {self.flags}')
        print(f'mip_count: {self.mip_count}')
        print(f'UNKNOWN1: {self.unknown1}')
        print(f'UNKNOWN2: {self.unknown2}')
        print(f'UNKNOWN3: {self.unknown3}')
        print(f'size_header: {self.size_header}')
        print(f'size_body: {self.size_body}')
        print(f'UNKNOWN: {self.unknown}')

        ddsc_flags = [
            [0x40, "DDSC_CUBEMAP"],
        ]
        flags = self.flags
        for test in ddsc_flags:
            if 0 != flags & test[0]:
                print(f'flags: {test[1]}')
            flags = flags & (~test[0])

        print(f'flags: leftover: {flags}')

        pprint.pprint(self.dds_header)
        pprint.pprint(self.dds_header_dxt10)

        print('--- dwFlags')
        for test in dwFlagsTest:
            if 0 != self.dds_header.dwFlags & test[0]:
                print('dwFlags: {}'.format(test[1]))

        print('--- dwCaps')
        for test in dwCapsTest:
            if 0 != self.dds_header.dwCaps & test[0]:
                print('dwCaps: {}'.format(test[1]))

        print('--- dwCaps2')
        for test in dwCaps2Test:
            if 0 != self.dds_header.dwCaps2 & test[0]:
                print('dwCaps2: {}'.format(test[1]))

        print('--- dwPFFlags')
        for test in dwPFFlagsTest:
            if 0 != self.dds_header.ddspf.dwFlags & test[0]:
                print('dwPFFlags: {}'.format(test[1]))

    def deserialize_ddsc(self, buffer):
        with ArchiveFile(io.BytesIO(buffer)) as fh:
            self.magic = fh.read(4)
            self.version = fh.read_u16()
            self.unknown0 = fh.read_u8()

            self.dds_header.dwSize = 124
            self.dds_header.ddspf.dwSize = 32
            self.dds_header.ddspf.dwFourCC = b'DX10'
            self.dds_header.ddspf.dwFlags |= DDPF_FOURCC
            self.dds_header_dxt10.miscFlag = 0
            self.dds_header_dxt10.arraySize = 1
            self.dds_header_dxt10.miscFlags2 = 0

            self.dds_header_dxt10.resourceDimension = fh.read_u8() + 1
            self.dds_header_dxt10.dxgiFormat = fh.read_u32()

            # [0x8, 'DDSD_PITCH'],
            # [0x80000, 'DDSD_LINEARSIZE'],

            self.dds_header.dwWidth = fh.read_u16()
            self.dds_header.dwHeight = fh.read_u16()
            self.dds_header.dwDepth = fh.read_u16()
            self.flags = fh.read_u16()
            self.dds_header.dwMipMapCount = fh.read_u8()
            self.mip_count = fh.read_u8()
            self.unknown1 = fh.read_u16()
            self.unknown2 = fh.read_u32()
            self.unknown3 = fh.read_u32()
            self.size_header = fh.read_u32()
            self.size_body = fh.read_u32()
            self.unknown = []
            while fh.tell() < 128:
                self.unknown.append(fh.read_u32())

            self.dds_header.dwFlags |= DDSD_CAPS
            self.dds_header.dwFlags |= DDSD_HEIGHT
            self.dds_header.dwFlags |= DDSD_WIDTH
            self.dds_header.dwFlags |= DDSD_PIXELFORMAT
            self.dds_header.dwFlags |= DDSD_MIPMAPCOUNT
            self.dds_header.dwFlags |= DDSD_DEPTH

            self.dds_header.dwCaps |= DDSCAPS_TEXTURE
            if self.dds_header.dwMipMapCount > 1:
                self.dds_header.dwCaps |= DDSCAPS_COMPLEX
                self.dds_header.dwCaps |= DDSCAPS_MIPMAP

            if self.flags & 0x40:
                self.dds_header.dwCaps |= DDSCAPS_COMPLEX
                self.dds_header.dwCaps2 |= DDS_CUBEMAP_ALLFACES | DDSCAPS2_CUBEMAP

        self.dump()

    def deserialize_dds(self, f, convert_to_dx10=True):
        self.magic = f.read(4)

        if self.magic != b'DDS ':
            raise EDecaIncorrectFileFormat('deserialize_dds')

        # DDS_HEADER
        self.dds_header.dwSize = f.read_u32()
        self.dds_header.dwFlags = f.read_u32()
        self.dds_header.dwHeight = f.read_u32()
        self.dds_header.dwWidth = f.read_u32()
        self.dds_header.dwPitchOrLinearSize = f.read_u32()
        self.dds_header.dwDepth = f.read_u32()
        self.dds_header.dwMipMapCount = f.read_u32()

        self.dds_header.dwReserved1 = []
        for i in range(11):
            self.dds_header.dwReserved1.append(f.read_u32())

        # PIXEL_FORMAT
        self.dds_header.ddspf.dwSize = f.read_u32()
        self.dds_header.ddspf.dwFlags = f.read_u32()
        self.dds_header.ddspf.dwFourCC = f.read(4)
        self.dds_header.ddspf.dwRGBBitCount = f.read_u32()
        self.dds_header.ddspf.dwRBitMask = f.read_u32()
        self.dds_header.ddspf.dwGBitMask = f.read_u32()
        self.dds_header.ddspf.dwBBitMask = f.read_u32()
        self.dds_header.ddspf.dwABitMask = f.read_u32()

        # DDS_HEADER continued
        self.dds_header.dwCaps = f.read_u32()
        self.dds_header.dwCaps2 = f.read_u32()
        self.dds_header.dwCaps3 = f.read_u32()
        self.dds_header.dwCaps4 = f.read_u32()
        self.dds_header.dwReserved2 = f.read_u32()

        # DDS_HEADER_DXT10
        four_cc = self.dds_header.ddspf.dwFourCC
        dw_four_cc = struct.unpack('I', four_cc)[0]
        dxgi_format = dw_four_cc_convert.get(dw_four_cc, dw_four_cc_convert.get(four_cc, None))

        if self.dds_header.ddspf.dwFourCC == b'DX10':
            self.dds_header_dxt10.dxgiFormat = f.read_u32()
            self.dds_header_dxt10.resourceDimension = f.read_u32()
            self.dds_header_dxt10.miscFlag = f.read_u32()
            self.dds_header_dxt10.arraySize = f.read_u32()
            self.dds_header_dxt10.miscFlags2 = f.read_u32()
        elif convert_to_dx10 and dxgi_format is not None:
            self.dds_header.ddspf.dwFourCC = b'DX10'
            self.dds_header_dxt10.dxgiFormat = dxgi_format
            self.dds_header_dxt10.arraySize = 1  # TODO assume array size of one
            if self.dds_header.dwCaps2 & DDSCAPS2_VOLUME != 0:
                self.dds_header_dxt10.resourceDimension = 3 + 1
            else:
                # TODO assuming 2d texture
                self.dds_header_dxt10.resourceDimension = 2 + 1

            # self.dds_header_dxt10.miscFlag = 0
            # self.dds_header_dxt10.arraySize = 1
            # self.dds_header_dxt10.miscFlags2 = 0

        self.mip_count = self.dds_header.dwMipMapCount

        self.dump()


class Ddsc:
    def __init__(self):
        self.header_buffer = None
        self.header = DdImageHeader()
        self.mips = None

    def load_bmp(self, f, filename=None):
        im = Image.open(f)
        im.convert('RGBA')
        self.mips = [DecaImage(sx=im.size[0], sy=im.size[1], itype='bmp', data=np.array(im), filename=filename)]

    def load_mip(self, mip, f, filename, save_raw_data, is_atx=False):
        pixel_format = mip.pixel_format
        nx = mip.size_x
        ny = mip.size_y
        if nx == 0 or ny == 0:
            return False
        nxm = max(4, nx)
        nym = max(4, ny)
        raw_size = deca.dxgi.raw_data_size(pixel_format, nx, ny)
        # print('Loading Data: {}'.format(raw_size))
        raw_data = f.read(raw_size)
        raw_data_size = len(raw_data)

        if is_atx:
            if raw_data_size == 0:
                return False  # Ran out of data probably because more data is in another atx
            elif raw_data_size < raw_size:
                raise Exception('Ddsc::load_atx: Not Enough Data')
        else:
            if raw_data_size < raw_size:
                raise Exception('Ddsc::load_ddsc: Not Enough Data')

        if pixel_format in {10}:  # floating point components
            inp_f32 = np.zeros((nym, nxm, 4), dtype=np.float32)
            deca.dxgi.process_image(inp_f32, raw_data, nx, ny, pixel_format)
            mn = np.nanmin(inp_f32)
            mx = np.nanmax(inp_f32)
            s = 1.0 / (mx - mn)
            inp = ((inp_f32 - mn) * s * 255).astype(dtype=np.uint8)
        else:
            inp = np.zeros((nym, nxm, 4), dtype=np.uint8)
            deca.dxgi.process_image(inp, raw_data, nx, ny, pixel_format)

        # inp = inp[0:ny, 0:nx, :]  # TODO Qt cannot display 2x2 for some reason
        if ny < nym or nx < nxm:
            inp[ny:, :, :] = 0
            inp[:, nx:, :] = 0

        if is_atx:
            mip.itype = 'atx'
        else:
            mip.itype = 'ddsc'
        mip.data = inp
        mip.filename = filename

        if save_raw_data:
            mip.raw_data = raw_data

        return True

    def load_body(self, f, filename, save_raw_data):
        nx = self.header.dds_header.dwWidth
        ny = self.header.dds_header.dwHeight
        self.mips = []

        if self.header.dds_header.dwMipMapCount == 0:
            mip_map_count = 1
            mip_map_count_in_file = 1
        else:
            mip_map_count = self.header.dds_header.dwMipMapCount
            mip_map_count_in_file = self.header.mip_count

        depth = max(1, self.header.dds_header.dwDepth)

        for i in range(mip_map_count):
            for j in range(depth):
                self.mips.append(DecaImage(
                    sx=nx, sy=ny,
                    depth_cnt=depth, depth_idx=j,
                    pixel_format=self.header.dds_header_dxt10.dxgiFormat, itype='missing'))

            nx = nx // 2
            ny = ny // 2

        begin = (mip_map_count - mip_map_count_in_file) * depth
        end = mip_map_count * depth
        for midx in range(begin, end):
            mip = self.mips[midx]
            if not self.load_mip(mip, f, filename, save_raw_data):
                break

    def load_ddsc(self, f, filename=None, save_raw_data=False):
        header = f.read(128)
        self.header_buffer = header
        self.header.deserialize_ddsc(header)

        # print('Compression Format: {}'.format(self.pixel_format))
        self.load_body(f, filename, save_raw_data)

    def load_atx(self, f, filename=None, save_raw_data=False):
        first_loaded = 0
        while first_loaded < len(self.mips):
            if self.mips[first_loaded].data is None:
                first_loaded = first_loaded + 1
            else:
                break

        for midx in range(first_loaded - 1, -1, -1):
            mip = self.mips[midx]
            if not self.load_mip(mip, f, filename, save_raw_data, is_atx=True):
                break

    def load_ddsc_atx(self, files, save_raw_data=False):
        self.load_ddsc(files[0][1], filename=files[0][0], save_raw_data=save_raw_data)
        for finfo in files[1:]:
            self.load_atx(finfo[1], filename=finfo[0], save_raw_data=save_raw_data)

    def load_dds(self, f):
        im = Image.open(f)
        im.convert('RGBA')
        self.mips = [DecaImage(sx=im.size[0], sy=im.size[1], itype='dds', data=np.array(im))]

    def load_dds_new(self, f, filename=None, save_raw_data=False):
        if isinstance(f, str) or isinstance(f, bytes):
            with ArchiveFile(open(f, 'rb')) as f:
                return self.load_dds_new(f, filename=filename, save_raw_data=save_raw_data)
        else:
            self.header.deserialize_dds(f)
            self.load_body(f, filename, save_raw_data)


def image_load(vfs: VfsDatabase, vnode: VfsNode, save_raw_data=False):
    if vnode.file_type == FTYPE_BMP:
        f_ddsc = vfs.file_obj_from(vnode)
        ddsc = Ddsc()
        ddsc.load_bmp(f_ddsc)

    elif vnode.file_type == FTYPE_DDS:
        # f_ddsc = vfs.file_obj_from(vnode)
        # ddsc = Ddsc()
        # ddsc.load_dds(f_ddsc)

        if vnode.v_path is None:
            filename = None
        else:
            filename = os.path.splitext(vnode.v_path)
        f_ddsc = vfs.file_obj_from(vnode)
        ddsc = Ddsc()
        ddsc.load_dds_new(ArchiveFile(f_ddsc), filename=filename, save_raw_data=save_raw_data)

    elif vnode.file_type in {FTYPE_AVTX, FTYPE_ATX, FTYPE_HMDDSC}:
        if vnode.v_path is None:
            f_ddsc = vfs.file_obj_from(vnode)
            ddsc = Ddsc()
            ddsc.load_ddsc(f_ddsc)
        else:
            filename = os.path.splitext(vnode.v_path)
            if len(filename[1]) == 0 and vnode.file_type == FTYPE_AVTX:
                filename_ddsc = vnode.v_path
            else:
                filename_ddsc = filename[0] + b'.ddsc'

            filename_ddsc_nodes = vfs.nodes_where_match(v_path=filename_ddsc)

            if filename_ddsc_nodes:
                extras = [b'.hmddsc']
                for i in range(1, 16):
                    extras.append('.atx{}'.format(i).encode('ascii'))

                files = []
                files.append([
                    filename_ddsc,
                    vfs.file_obj_from(filename_ddsc_nodes[0]),
                ])
                for extra in extras:
                    filename_atx = filename[0] + extra
                    filename_atx_nodes = vfs.nodes_where_match(v_path=filename_atx)
                    if filename_atx_nodes:
                        files.append([
                            filename_atx,
                            vfs.file_obj_from(filename_atx_nodes[0]),
                        ])
                ddsc = Ddsc()
                ddsc.load_ddsc_atx(files, save_raw_data=save_raw_data)
            else:
                raise EDecaFileMissing('File {} is missing.'.format(filename_ddsc))
    else:
        raise EDecaIncorrectFileFormat('Cannot handle format {} in {}'.format(vnode.file_type, vnode.v_path))

    return ddsc


def ddsc_write_to_png(ddsc, output_file_name):
    image = None
    for i in range(len(ddsc.mips)):
        if ddsc.mips[i].data is not None:
            image = ddsc.mips[i].pil_image()
            break
    if image is None:
        raise EDecaIncorrectFileFormat('Could not find image data')

    image.save(output_file_name)


def ddsc_write_to_dds(ddsc, output_file_name):
    flags = 0
    flags = flags | 0x1  # DDSD_CAPS
    flags = flags | 0x2  # DDSD_HEIGHT
    flags = flags | 0x4  # DDSD_WIDTH
    # flags = flags | 0x8         # DDSD_PITCH
    flags = flags | 0x1000  # DDSD_PIXELFORMAT
    flags = flags | 0x20000  # DDSD_MIPMAPCOUNT
    flags = flags | 0x80000  # DDSD_LINEARSIZE

    dwCaps1 = 0x8 | 0x1000 | 0x400000
    dwCaps2 = 0
    resourceDimension = 3

    if ddsc.header.dds_header.dwDepth > 1:
        flags = flags | 0x800000  # DDSD_DEPTH
        dwCaps2 = dwCaps2 | 0x200000
        resourceDimension = 4

    with ArchiveFile(open(output_file_name, 'wb')) as f:
        # magic word
        f.write(b'DDS ')
        # DDS_HEADER
        f.write_u32(124)  # dwSize
        f.write_u32(flags)  # dwFlags
        f.write_u32(ddsc.header.dds_header.dwHeight)  # dwHeight
        f.write_u32(ddsc.header.dds_header.dwWidth)  # dwWidth
        f.write_u32(len(ddsc.mips[0].raw_data))  # dwPitchOrLinearSize
        f.write_u32(ddsc.header.dds_header.dwDepth)  # dwDepth
        f.write_u32(ddsc.header.dds_header.dwMipMapCount)  # dwMipMapCount
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
        f.write_u32(dwCaps1)  # dwCaps
        f.write_u32(dwCaps2)  # dwCaps2
        f.write_u32(0)  # dwCaps3
        f.write_u32(0)  # dwCaps4
        f.write_u32(0)  # dwReserved2

        # DDS_HEADER_DXT10
        f.write_u32(ddsc.header.dds_header_dxt10.dxgiFormat)  # DXGI_FORMAT              dxgiFormat;
        f.write_u32(resourceDimension)  # D3D10_RESOURCE_DIMENSION resourceDimension;
        f.write_u32(0)  # UINT                     miscFlag;
        f.write_u32(1)  # UINT                     arraySize;
        f.write_u32(0)  # UINT                     miscFlags2;

        for mip in ddsc.mips:
            f.write(mip.raw_data)


def image_export(vfs: VfsDatabase, node: VfsNode, extract_dir, export_raw, export_processed, allow_overwrite=False):
    existing_files = []
    ddsc = image_load(vfs, node, save_raw_data=True)

    if ddsc is not None:
        multifile = node.file_type in {FTYPE_AVTX, FTYPE_ATX, FTYPE_HMDDSC}

        if export_raw or not multifile:
            if multifile:
                cnodes = [mip.filename for mip in ddsc.mips]
                cnodes = set(cnodes)
                cnodes = [vfs.nodes_where_match(v_path=cnode)[0] for cnode in cnodes]
            else:
                cnodes = [node]

            for cnode in cnodes:
                if cnode.v_path is None:
                    ofile = extract_dir + '{:08X}.dat'.format(cnode.v_hash)
                else:
                    ofile = extract_dir + '{}'.format(cnode.v_path.decode('utf-8'))

                make_dir_for_file(ofile)

                if not allow_overwrite and os.path.isfile(ofile):
                    existing_files.append(ofile)
                else:
                    with open(ofile, 'wb') as fo:
                        with vfs.file_obj_from(cnode) as fi:
                            buffer = fi.read(cnode.size_u)
                            fo.write(buffer)

        if export_processed and multifile:
            if node.v_path is None:
                ofile = extract_dir + '{:08X}.dat'.format(node.v_hash)
            else:
                ofile = extract_dir + '{}'.format(node.v_path.decode('utf-8'))

            make_dir_for_file(ofile)

            ofile = os.path.splitext(ofile)[0]
            ofile = ofile + '.ddsc'

            # export to reference png file
            ofile_img = ofile + '.DECA.REFERENCE.png'
            if not allow_overwrite and os.path.isfile(ofile_img):
                existing_files.append(ofile_img)
            else:
                ddsc_write_to_png(ddsc, ofile_img)

            # export dds with all mip levels
            ofile_img = ofile + '.dds'
            if not allow_overwrite and os.path.isfile(ofile_img):
                existing_files.append(ofile_img)
            else:
                ddsc_write_to_dds(ddsc, ofile_img)

        # raise exception if any files could not be overwritten
        if len(existing_files) > 0:
            raise EDecaFileExists(existing_files)


def image_import(vfs: VfsDatabase, node: VfsNode, ifile: str, opath: str):
    print('Importing Image: {}\n  input {}\n  opath {}'.format(node.v_path, ifile, opath))
    ddsc = image_load(vfs, node, save_raw_data=True)

    compiled_files = []
    if ddsc is not None:
        with ArchiveFile(open(ifile, 'rb')) as file_in:
            # dsc_header = file_in.read(37 * 4 - 5 * 4)  # skip dds header
            dsc_header = Ddsc()
            dsc_header.load_dds_new(file_in, True)
            for mip in ddsc.mips:
                buffer = file_in.read(len(mip.raw_data))
                mip.raw_data = buffer

        out_vpaths = [mip.filename for mip in ddsc.mips]
        out_vpaths = set(out_vpaths)

        for vpath_out in out_vpaths:
            fout_name = os.path.join(opath, vpath_out.decode('utf-8'))

            make_dir_for_file(fout_name)

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

