import sys

from deca.db_processor import vfs_structure_open, VfsProcessor
from deca.ff_adf import AdfDatabase
from deca.file import ArchiveFile
import os
import io
import zlib
import zstandard as zstd
import re
import json
import numpy as np


def main():
    fn = sys.argv[1]

    with open(fn, 'rb') as f:
        buf = f.read()

    for offset in range(0, len(buf), 2):
        try:
            tmp_buf_c = buf[offset:]
            tmp_buf_u = zlib.decompress(tmp_buf_c, -15)

            if len(tmp_buf_u) > 64:
                print(f"zlib: offset={offset}, sz={len(tmp_buf_u)}, {tmp_buf_u[0:4]}")
        except:
            pass



    for offset in range(0, len(buf), 2):
        try:
            tmp_buf_c = buf[offset:]
            dc = zstd.ZstdDecompressor()
            tmp_buf_u = dc.decompress(tmp_buf_c)

            if len(tmp_buf_u) > 64:
                print(f"zstd: offset={offset}, sz={len(tmp_buf_u)}, {tmp_buf_u[0:4]}")
        except:
            pass


if __name__ == "__main__":
    main()
