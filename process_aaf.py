import os
import zlib
import sys
import struct

in_file = sys.argv[1]

with open(in_file,'rb') as f:
    magic = f.read(4)
    version = struct.unpack('I', f.read(4))[0]
    aic = f.read(8+16+4)
    uncompressed_length = struct.unpack('I', f.read(4))[0]  # uncompressed length, whole file
    section_size = struct.unpack('I', f.read(4))[0]  # uncompress length, max any section?
    section_count = struct.unpack('I', f.read(4))[0]  # section count? Normally 1 (2-5 found), number of 32MiB blocks?

    with open(in_file + '.dat', 'wb') as fo:
        for i in range(section_count):
            section_start = f.tell()
            section_compressed_length = struct.unpack('I', f.read(4))[0]  # compressed length no including padding
            section_uncompressed_length = struct.unpack('I', f.read(4))[0]  # full length?
            section_length_with_header = struct.unpack('I', f.read(4))[0]  # padded length + 16
            magic_ewam = f.read(4)                         # 'EWAM'
            buf = f.read(section_compressed_length)
            obuf = zlib.decompress(buf,-15)
            fo.write(obuf)
            f.seek(section_length_with_header + section_start)
            # print(section_compressed_length, section_uncompressed_length, section_length_with_header, magic_ewam)
            if len(obuf) != section_uncompressed_length:
                raise Exception('Uncompress Failed {}'.format(in_file))
os.remove(in_file)
    # print(magic, version, uncompressed_length, section_size, section_count, in_file)


"""
if section count == 1
tst1 == tst2 == tst5

if section count == 2

('AAF\x00', 1, 46634008, 33554432, 2, 21711492, 33554432, 21711520, 'EWAM', 28677744, 28677680, './out/initial/game1/488471E7.aaf')


"""

