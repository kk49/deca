import numpy as np
import struct
import io
from deca.file import ArchiveFile
from deca.ff_aaf import load_aaf_header
from deca.ff_types import *


# guess type
raw_image_size = {
    0x1000000: '',
    0x800000: '',
    0x400000: '',
    0x280000: '',
    0x200000: '',
    0x140000: '',
    0x100000: '',
    0xa0000: '',
    0x80000: '',
    0x40000: '',
    0x20000: '',
}


def file_stats(f, file_size):
    # TODO handle huge file size
    counts = np.zeros((256,), dtype=np.uint32)
    buf = f.read(file_size)
    buf = bytearray(buf)
    cnt = np.bincount(buf, minlength=256)
    counts = counts + cnt
    return counts


def determine_file_type_and_size(f, file_size):
    start_pos = f.tell()
    magic = f.read(32)

    ftype = None
    fsize = file_size
    if b' FDA' == magic[0:4]:
        ftype = FTYPE_ADF
    elif b'AVTX' == magic[0:4]:
        ftype = FTYPE_AVTX
    elif b'AAF' == magic[0:3].upper():
        ftype = FTYPE_AAF
        f.seek(start_pos)
        aafh = load_aaf_header(f)
        fsize = aafh.size_u
    elif b'SARC' == magic[4:8]:
        ftype = FTYPE_SARC
    elif b'DDS ' == magic[0:4]:
        ftype = FTYPE_DDS
    elif b'RTPC' == magic[0:4]:
        ftype = FTYPE_RTPC
    elif b'CFX' == magic[0:3]:
        ftype = 'CFX'
    elif b'RIFF' == magic[0:4]:
        ftype = 'RIFF'
    elif b'OggS' == magic[0:4]:
        ftype = 'OGG'
    elif b'BM6' == magic[0:3]:
        ftype = FTYPE_BMP
    elif b'BM8' == magic[0:3]:
        ftype = FTYPE_BMP
    elif b'TAG0' == magic[4:8]:
        ftype = FTYPE_TAG0
    elif b'FSB5' == magic[16:20]:
        ftype = FTYPE_LFSB5
    elif b'\x57\xE0\xE0\x57\x10\xC0\xC0\x10' == magic[0:8]:
        ftype = FTYPE_H2014
    elif b'MDI\x00' == magic[0:4]:
        ftype = FTYPE_MDI
    elif b'PFX\x00' == magic[0:4]:
        ftype = FTYPE_PFX
    # ATX file format was a guess by size
    # elif file_size in raw_image_size:
    #     ftype = FTYPE_ATX

    # need to inspect file structure

    if ftype is None:  # OBC files with (u32)4, (u32)count , 80 * count bytes, something to do with areas on the map? object placement?
        fm = ArchiveFile(f)
        fm.seek(start_pos)
        ver = fm.read_u32()
        cnt = fm.read_u32()
        if ver == 4 and cnt * 80 + 8 == file_size:
            ftype = FTYPE_OBC

    if ftype is None:  # text file only contains text bytes, json, xml, ...
        fm.seek(start_pos)
        counts = file_stats(fm, file_size)
        all_sum = np.sum(counts)
        pri_sum = np.sum(counts[[9, 10, 13] + list(range(20, 128))])
        if all_sum == pri_sum:
            ftype = FTYPE_TXT

    return ftype, fsize
