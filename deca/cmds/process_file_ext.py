import os
import sys
import numpy as np
from deca.file import ArchiveFile

paths = [sys.argv[1]]


def file_stats(filename):
    counts = np.zeros((256,), dtype=np.uint32)
    with open(filename, 'rb') as f:
        buf = f.read(1024*1024)
        buf = bytearray(buf)
        cnt = np.bincount(buf, minlength=256)
        counts = counts + cnt
    return counts


while len(paths) > 0:
    path = paths.pop(-1)
    # print(path)
    if os.path.isdir(path):
        path = path + '/'
        files = os.listdir(path)
        for file in files:
            ffn = path + file
            paths.append(ffn)
    elif path[-3:].lower() == 'dat':
        with ArchiveFile(open(path, 'rb')) as f:
            magic = f.read(8)
            f.seek(0)
            magic_long = f.read(32)
        if False:
            None
        # elif b' fda' == magic[0:4].lower():
        #     os.rename(path, path[0:-4] + '.adf')
        elif b'SARC' == magic[4:8]:
            os.rename(path, path[0:-4] + '.sarc')
        elif b'aaf' == magic[0:3].lower():
            os.rename(path, path[0:-4] + '.aaf')
        elif b'avtx' == magic[0:4].lower():
            os.rename(path, path[0:-4] + '.avtx')
        # elif b'riff' == magic[0:4].lower():
        #     os.rename(path, path[0:-4] + '.riff')
        # elif b'dds ' == magic[0:4].lower():
        #     os.rename(path, path[0:-4] + '.dds')
        # elif b'BM' == magic[0:2]:
        #     os.rename(path, path[0:-4] + '.bmp')
        # elif b'OggS' == magic[0:4]:
        #     os.rename(path, path[0:-4] + '.ogg')
        # elif b'{'[0] == magic[0] or b'['[0] == magic[0]:
        #     counts = file_stats(path)
        #     all_sum = np.sum(counts)
        #     pri_sum = np.sum(counts[[9, 10, 13] + list(range(20,128))])
        #     if all_sum == pri_sum:
        #         os.rename(path, path[0:-4] + '.json')
        # elif b'<'[0] == magic[0]:
        #     counts = file_stats(path)
        #     all_sum = np.sum(counts)
        #     pri_sum = np.sum(counts[[9, 10, 13] + list(range(20, 128))])
        #     if all_sum == pri_sum:
        #         os.rename(path, path[0:-4] + '.xml')
        else:
            magic_ba = bytearray(magic_long)
            magic_hex = ['{:02x}'.format(v) for v in magic_ba]
            magic_hex = ''.join(magic_hex)
            magic_str = magic_ba
            for i in range(len(magic_str)):
                if magic_str[i] < 32 or magic_str[i] >= 127:
                    magic_str[i] = ord('.')
            magic_str = magic_str.decode('utf-8')
            file_size = os.stat(path).st_size
            line = '{}\t{}\t0x{:08x}\th{}\t{}'.format(path, file_size, file_size, magic_hex, magic_str)
            print(line)
