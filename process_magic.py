import os
import numpy as np
import sys
from deca.file import ArchiveFile


def file_stats(filename):
    counts = np.zeros((256,),dtype=np.uint32)
    with open(filename, 'rb') as f:
        buf = f.read(1024*1024)
        buf = bytearray(buf)
        cnt = np.bincount(buf, minlength=256)
        counts = counts + cnt
    return counts


if len(sys.argv) > 1:
    paths = [sys.argv[i] for i in range(1, len(sys.argv))]
else:
    paths = ['./test/gz/out']

line = '{}\t{}\t{}\t{}\th{}'.format('path', 'ftype', 'file_size', 'file_size_hex', 'magic_hex')
print(line)

while len(paths) > 0:
    path = paths.pop(-1)
    # print(path)
    if os.path.isdir(path):
        path = path + '/'
        files = os.listdir(path)
        for file in files:
            ffn = path + file
            paths.append(ffn)
    else:
        file_size = os.stat(path).st_size
        with ArchiveFile(open(path, 'rb')) as f:
            magic = f.read(32)

        # guess type
        raw_image_size = {
            0x1000000: '',
            0x800000:  '',
            0x400000:  '',
            0x280000:  '',
            0x200000:  '',
            0x140000:  '',
            0x100000:  '',
            0xa0000:   '',
            0x80000:   '',
            0x40000:   '',
            0x20000:   '',
        }

        ftype = ''
        if b' FDA' == magic[0:4]:
            ftype = 'ADF'
        elif b'AVTX' == magic[0:4]:
            ftype = 'AVTX'
        elif b'RTPC' == magic[0:4]:
            ftype = 'RTPC'
        elif b'CFX' == magic[0:3]:
            ftype = 'CFX'
        elif b'RIFF' == magic[0:4]:
            ftype = 'RIFF'
        elif b'DDS ' == magic[0:4]:
            ftype = 'DDS'
        elif b'OggS' == magic[0:4]:
            ftype = 'DDS'
        elif b'BM6' == magic[0:3]:
            ftype = 'BM6'
        elif b'TAG0' == magic[4:8]:
            ftype = 'TAG0'
        elif b'SARC' == magic[4:8]:
            ftype = 'SARC'
        elif b'FSB5' == magic[16:20]:
            ftype = 'lFSB5'
        elif file_size in raw_image_size:
            ftype = 'raw_image'


        magic_ba = bytearray(magic)
        magic_hex = ['{:02x}'.format(v) for v in magic_ba]
        magic_hex = ''.join(magic_hex)
        magic_str = magic_ba
        for i in range(len(magic_str)):
            if magic_str[i] < 32 or magic_str[i] >= 127:
                magic_str[i] = ord('.')
        magic_str = magic_str.decode('utf-8')
        # line = '{}\t{}\t{}\t0x{:x}\th{}\t{}'.format(path, ftype, file_size, file_size, magic_hex, magic_str)
        line = '{}\t{}\t{}\t0x{:x}\th{}'.format(path, ftype, file_size, file_size, magic_hex)
        print(line)
