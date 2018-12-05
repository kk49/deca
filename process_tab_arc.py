import struct
import os
from deca.util import *
from deca.file import ArchiveFile

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
            magic = f.read(4)
            unk00 = f.read_u16()
            unk01 = f.read_u16()
            unk02 = f.read_u32()
            print(magic, unk00, unk01, unk02)
            fileList = []
            while True:
                tmp = f.read_u32()
                if tmp is None:
                    break
                hashedName = tmp
                fileOffset = f.read_u32()
                fileSize = f.read_u32()
                fileList.append((hashedName, fileOffset, fileSize))
                # print(hashedName, fileOffset, fileSize, fileOffset + fileSize)
        elif 4 == ver:
            magic = f.read(4)
            unk00 = f.read_u16()
            unk01 = f.read_u16()
            unk02 = f.read_u32()
            print(magic, unk00, unk01, unk02)
            f.seek(0x1f0)
            fileList = []
            while True:
                tmp = f.read_u32()
                if tmp is None:
                    break
                hashedName = tmp
                fileOffset = f.read_u32()
                fileSize = f.read_u32()
                d1 = f.read_u32()
                d2 = f.read_u16()
                d3 = f.read_u16()
                fileList.append((hashedName, fileOffset, fileSize, d1, d2, d3))
                print('{:08X}'.format(hashedName), fileOffset, fileSize, d1, d2, '{:04X}'.format(d3))

    k_buffer_size = 1024*1024
    with open(file_arc, 'rb') as fi:
        for i in range(len(fileList)):
            frec = fileList[i]
            print('Processing {} of {}: {}'.format(i+1, len(fileList), frec[2]))
            fo_name = outpath + '{:08X}.dat'.format(frec[0])
            with open(fo_name, 'wb') as fo:
                fi.seek(frec[1])
                flen = frec[2]
                first_block = True
                while flen > 0:
                    rlen = min(k_buffer_size, flen)
                    buf = fi.read(rlen)
                    fo.write(buf)
                    flen -= rlen

                    if first_block:
                        first_block = False
                        if len(frec) == 6:
                            print('{:08X}'.format(frec[0]), frec[1], frec[2], frec[3], frec[4], '{:04X}'.format(frec[5]))
                            dump_block(buf[0:16], 16, 'hex')
                            dump_block(buf[0:16], 16, 'char')






'''
struct tabFileEntry
{
   unsigned int m_hashedName;
   unsigned int m_fileOffset;
   unsigned int m_fileSize;
};

struct tab
{
   unsigned int m_magic;//"TAB "
   unsigned short m_unk00;//Probably version always 2
   unsigned short m_unk01;//Always 1?
   unsigned long  m_unk02;//Alignment?
   tabFileEntry[numFiles];
};
'''