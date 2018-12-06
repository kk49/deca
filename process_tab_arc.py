import os
import sys
from deca.util import *
from deca.file import ArchiveFile
from deca.ff_arc_tab import TabFileV3, TabFileV4
import zlib
import lzma

if len(sys.argv) > 3:
    ver = int(sys.argv[1])
    prefix_in = sys.argv[2]
    prefix_out = sys.argv[3]
else:
    prefix_in = '/home/krys/prj/gz/archives_win64/'
    prefix_out = './test/gz/out/'
    ver = 3
    # prefix_in = '/home/krys/prj/jc4/archives_win64/'
    # prefix_out = './test/jc4/out/'
    # ver = 4

debug = False

input_files = []

cats = os.listdir(prefix_in)

for cat in cats:
    fcat = prefix_in + cat
    print(fcat)
    if os.path.isdir(fcat):
        fcat = fcat + '/'
        files = os.listdir(fcat)
        for file in files:
            if 'tab' == file[-3:]:
                input_files.append((cat, file[0:-4]))

for ta_file in input_files:
    outpath = prefix_out + ta_file[0] + '/' + ta_file[1] + '/'
    os.makedirs(outpath, exist_ok=True)
    inpath = prefix_in + ta_file[0] + '/' + ta_file[1]

    file_tab = inpath + '.tab'
    file_arc = inpath + '.arc'

    with ArchiveFile(open(file_tab, 'rb'), debug=debug) as f:
        if 3 == ver:
            tab_file = TabFileV3()
        elif 4 == ver:
            tab_file = TabFileV4()

        tab_file.deserialize(f)

    k_buffer_size = 1024*1024
    with open(file_arc, 'rb') as fi:
        for i in range(len(tab_file.file_table)):
            frec = tab_file.file_table[i]
            print('Processing {} of {}: {}'.format(i+1, len(tab_file.file_table), frec.debug()))

            fo_name = outpath + '{:08X}.dat'.format(frec.hashname)
            with open(fo_name, 'wb') as fo:
                fi.seek(frec.offset)
                len_c = frec.size_c
                len_u = frec.size_u
                for bi in frec.file_block_table:
                    buf = fi.read(bi[0])
                    if bi[0] != bi[1]:
                        ibuf = buf
                        with open(fo_name + '.{:08x}-{:08x}.compress'.format(bi[0],bi[1]), 'wb') as fd:
                            fd.write(ibuf)
                        buf = ibuf
                        # buf = lzma.decompress(ibuf, format=lzma.FORMAT_RAW, filters=[{'id': lzma.FILTER_LZMA2}])
                        # if len(buf) != bi[1]:
                        #     raise Exception('Parse Error')
                    fo.write(buf)
                    len_c -= bi[0]
                    len_u -= bi[1]

            if len_c != 0:
                raise Exception('Parse Error')
            if len_u != 0:
                raise Exception('Parse Error')
