import os
import sys
import struct
import re
from deca.file import ArchiveFile

root_path = sys.argv[1]
in_file = sys.argv[2]

# root_path = '/home/krys/prj/deca/test/jc4/'
# in_file = 'test/jc4/out/test/game0/691DB0D0.sarc'

out_path = root_path + 'files/'
fn_good = root_path + 'files_good.txt'
fn_bad = root_path + 'files_bad.txt'

hash_list_file = root_path + 'hash_list.txt'
hash_list_prefix = root_path + 'out'

"""
krys@krysl001:~/prj/gz_hack/tab_arc/out$ find -type f > ../hash_list.txt
"""

with open(hash_list_file, 'r') as f:
    hash_list = f.readlines()

hdict = {}
for ele in hash_list:
    if '\n' == ele[-1]:
        ele = ele[:-1]
    ele = hash_list_prefix + ele[1:]
    mr = re.match('.*/([^\.]+)\..*', ele)
    if mr is None:
        raise Exception('MISSING HASH {}'.format(ele))
    else:
        hashv = int(mr[1], base=16)
        if hashv in hdict:
            raise Exception('HASH ALREADY FOUND {}'.format(ele))
        else:
            hdict[hashv] = ele

print('Processing sarc file {}'.format(in_file))
with open(fn_good, 'a') as fng:
    with open(fn_bad, 'a') as fnb:
        with ArchiveFile(open(in_file, 'rb')) as f:
            version = f.read_u32()
            magic = f.read(4)
            ver2 = f.read_u32()
            dir_block_len = f.read_u32()

            buf = f.read(dir_block_len)
            string_len = struct.unpack('I', buf[0:4])[0]
            strings = buf[4:(4+string_len)]
            strings = strings.split(b'\00')
            if strings[-1] == '':
                strings = strings[:-1]

            buf = buf[(4 + string_len):]

            fdir = []
            width = 20
            for i in range(len(strings)):
                line = buf[(i*width):((i+1)*width)]
                if len(line) == width:
                    v = struct.unpack('IIIII', line)
                    v = [x for x in v]

                    offset = v[1]
                    length = v[2]
                    hashv = v[3]

                    fn = strings[i].split(b'/')
                    fn = [t.decode("utf-8") for t in fn]
                    dpath = out_path + os.path.join(*fn[0:-1])
                    fpath = out_path + os.path.join(*fn)
                    os.makedirs(dpath, exist_ok=True)

                    if offset == 0:
                        if os.path.isfile(fpath):
                            fng.write('{}\n'.format([strings[i].decode("utf-8"), in_file] + v))
                        else:
                            if hashv in hdict:
                                os.rename(hdict[hashv],fpath)
                                fng.write('{}\n'.format([strings[i].decode("utf-8"), in_file] + v))
                            else:
                                fnb.write('{:08x} {} {}\n'.format(hashv,length,strings[i].decode("utf-8")))
                    else:
                        if not os.path.isfile(fpath):
                            f.seek(offset)
                            cbuf = f.read(length)
                            with open(fpath, 'wb') as fo:
                                fo.write(cbuf)

                        if hashv in hdict:
                            hfn = hdict[hashv]
                            if os.path.isfile(hfn) and os.path.isfile(fpath):
                                if os.stat(hfn).st_size == os.stat(fpath).st_size:
                                    print('File {} found in TAB/ARC, sizes match, delete hash version'.format(strings[i].decode("utf-8")))
                                    os.remove(hfn)
                                else:
                                    print('File {} found in TAB/ARC, size do not match'.format(strings[i].decode("utf-8")))
                        fng.write('{}\n'.format([strings[i].decode("utf-8"), in_file] + v))

    # dump_block(buf,20)
    # dump_block(buf,20,'IIIII')

    # print(strings)
    # print(len(strings))
    #
    # print(len(buf))
    # dread(f, 4)
    # dread(f, 4)
    # dread(f, 4)
    # dread(f, 4)


    # strings_len = struct.unpack('I', f.read(4))[0]
    # print(t0, t1, strings_len)
    #
    # strings = f.read(strings_len)
    # strings = strings.split('\00')
    #
    # print(strings)
    #
    # t2 = struct.unpack('I', f.read(4))[0]
    # t3 = struct.unpack('I', f.read(4))[0]
    # t4 = struct.unpack('I', f.read(4))[0]
    # print(t2, t3, t4)

    # aic = f.read(8+16+4)
    # uncompressed_length = struct.unpack('I', f.read(4))[0]  # uncompressed length, whole file
    # section_size = struct.unpack('I', f.read(4))[0]  # uncompress length, max any section?
    # section_count = struct.unpack('I', f.read(4))[0]  # section count? Normally 1 (2-5 found), number of 32MiB blocks?
    #
    # with open(in_file + '.dat','wb') as fo:
    #     for i in range(section_count):
    #         section_start = f.tell()
    #         section_compressed_length = struct.unpack('I', f.read(4))[0]  # compressed length no including padding
    #         section_uncompressed_length = struct.unpack('I', f.read(4))[0]  # full length?
    #         section_length_with_header = struct.unpack('I', f.read(4))[0]  # padded length + 16
    #         magic_ewam = f.read(4)                         # 'EWAM'
    #         buf = f.read(section_compressed_length)
    #         obuf = zlib.decompress(buf,-15)
    #         fo.write(obuf)
    #         f.seek(section_length_with_header + section_start)
    #         # print(section_compressed_length, section_uncompressed_length, section_length_with_header, magic_ewam)
    #         if len(obuf) != section_uncompressed_length:
    #             raise Exception('Uncompress Failed {}'.format(in_file))

    # print(magic, version, uncompressed_length, section_size, section_count, in_file)


