import numpy as np
import struct
import io
from deca.file import ArchiveFile
from deca.ff_vfs import *


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


def determine_file_type(f, file_size):
    start_pos = f.tell()
    magic = f.read(32)

    ftype = None
    if b' FDA' == magic[0:4]:
        ftype = FTYPE_ADF
    elif b'AVTX' == magic[0:4]:
        ftype = FTYPE_AVTX
    elif b'AAF' == magic[0:3].upper():
        ftype = FTYPE_AAF
    elif b'SARC' == magic[4:8]:
        ftype = FTYPE_SARC
    elif b'DDS ' == magic[0:4]:
        ftype = FTYPE_DDS
    elif b'RTPC' == magic[0:4]:
        ftype = 'RTPC'
    elif b'CFX' == magic[0:3]:
        ftype = 'CFX'
    elif b'RIFF' == magic[0:4]:
        ftype = 'RIFF'
    elif b'OggS' == magic[0:4]:
        ftype = 'OGG'
    elif b'BM6' == magic[0:3]:
        ftype = 'BM6'
    elif b'BM8' == magic[0:3]:
        ftype = 'BM8'
    elif b'TAG0' == magic[4:8]:
        ftype = 'TAG0'
    elif b'FSB5' == magic[16:20]:
        ftype = 'lFSB5'
    elif file_size in raw_image_size:
        ftype = FTYPE_NHAVTX

    # need to inspect file structure
    if ftype is None:  # OBC files with (u32)4, (u32)cnt, f32 *
        fm = ArchiveFile(f)
        fm.seek(start_pos)
        ver = fm.read_u32()
        cnt = fm.read_u32()
        if ver == 4 and cnt * 80 + 8 == file_size:
            ftype = FTYPE_OBC

    if ftype is None:  # text file of some sort only text bytes, json, xml, ...
        fm.seek(start_pos)
        counts = file_stats(fm, file_size)
        all_sum = np.sum(counts)
        pri_sum = np.sum(counts[[9, 10, 13] + list(range(20, 128))])
        if all_sum == pri_sum:
            ftype = FTYPE_TXT

    return ftype
