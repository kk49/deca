from deca.errors import EDecaOutOfData
from deca.ff_types import *
from .file import ArchiveFile


def tab_file_load(filename, ver):
    with ArchiveFile(open(filename, 'rb')) as f:
        magic = f.read(4)
        ver_0 = f.read_u16()
        ver_1 = f.read_u16()
        ver_2 = f.read_u32()

        assert magic == b'TAB\x00'
        if 3 == ver:
            assert ver_0 == 2, f"ver_0 = {ver_0}"
            assert ver_1 == 1, f"ver_1 = {ver_1}"
            assert ver_2 in {2048, 4096}, f"ver_2 = {ver_2}"
            tab_file = TabFileV3()
        elif 4 == ver:
            assert ver_0 == 2, f"ver_0 = {ver_0}"
            assert ver_1 == 1, f"ver_1 = {ver_1}"
            assert ver_2 == 4096, f"ver_2 = {ver_2}"
            tab_file = TabFileV4()
        elif 5 == ver:
            assert ver_0 == 3, f"ver_0 = {ver_0}"
            assert ver_1 == 1, f"ver_1 = {ver_1}"
            assert ver_2 == 4096, f"ver_2 = {ver_2}"
            tab_file = TabFileV5()
        else:
            raise NotImplementedError('Unknown TAB file version {}'.format(ver))

    with ArchiveFile(open(filename, 'rb')) as f:
        tab_file.deserialize(f)

    return tab_file


class TabFileBase:
    def __init__(self):
        self.unk = []
        self.magic = None
        self.file_version = None
        self.file_table = None
        self.file_hash_map = None
        self.file_block_table = None

    def deserialize(self, f):
        raise NotImplementedError('Interface Class')

    def serialize(self, f):
        raise NotImplementedError('Interface Class')


class TabFileV3(TabFileBase):
    def __init__(self):
        TabFileBase.__init__(self)

    def deserialize(self, f):
        self.magic = f.read(4)
        self.unk += [f.read_u16()]
        self.unk += [f.read_u16()]
        self.unk += [f.read_u32()]

        # print(self.magic, self.unk)

        self.file_table = []
        self.file_hash_map = {}
        entry = TabEntryFileV3()
        while entry.deserialize(f):
            self.file_table.append(entry)
            self.file_hash_map[entry.hashname] = entry
            entry = TabEntryFileV3()

        return True

    def serialize(self, f):
        raise NotImplementedError('Interface Class')


def process_file_blocks(file_table, file_block_table):
    # give each file entry its info about its file blocks
    no_block = [0xffffffff, 0xffffffff]
    fbt = [None] * len(file_block_table)
    for i, fte in enumerate(file_table):
        fbi = fte.file_block_index
        if file_block_table[fbi] != no_block:
            fte.file_block_table = []
            d_count = 0
            while d_count < fte.size_c:
                fb = file_block_table[fbi]
                sc = fb[0]
                assert fbt[fbi] is None  # make sure we are not clobbering other files
                fbt[fbi] = i
                d_count += sc
                fbi += 1
                fte.file_block_table.append(fb)
            assert d_count == fte.size_c


class TabFileV4(TabFileBase):
    def __init__(self):
        TabFileBase.__init__(self)

    def deserialize(self, f):
        self.magic = f.read(4)
        self.file_version = f.read_u16()  # just cause 4 was still 2, rage 2 is 3
        self.unk += [f.read_u16()]
        self.unk += [f.read_u32()]
        self.unk += [f.read_u32()]
        self.unk += [f.read_u32()]
        self.unk += [f.read_u32()]

        t1_len = f.read_u32()

        t1 = []
        for i in range(t1_len):
            len_c = f.read_u32()
            len_u = f.read_u32()
            t1.append([len_c, len_u])
        self.file_block_table = t1

        self.file_table = []
        self.file_hash_map = {}
        entry = TabEntryFileV4()
        while entry.deserialize(f):
            self.file_table.append(entry)
            self.file_hash_map[entry.hashname] = entry
            entry = TabEntryFileV4()

        process_file_blocks(self.file_table, self.file_block_table)

        return True

    def serialize(self, f):
        raise NotImplementedError('Interface Class')


class TabFileV5(TabFileBase):
    def __init__(self):
        TabFileBase.__init__(self)

    def deserialize(self, f):
        self.magic = f.read(4)
        self.file_version = f.read_u16()  # 3
        self.unk += [f.read_u16()]  # 1
        self.unk += [f.read_u32()]  # 4096
        file_count = f.read_u32()
        block_count = f.read_u32()
        self.unk += [f.read_u32()]
        self.unk += [f.read_u32()]
        self.unk += [f.read_u32()]

        t1 = []
        for i in range(block_count):
            len_c = f.read_u32()
            len_u = f.read_u32()
            t1.append([len_c, len_u])
        self.file_block_table = t1

        self.file_table = []
        self.file_hash_map = {}
        for i in range(file_count):
            entry = TabEntryFileV5()
            entry.deserialize(f)
            self.file_table.append(entry)
            self.file_hash_map[entry.hashname] = entry

        process_file_blocks(self.file_table, self.file_block_table)

        return True

    def serialize(self, f):
        raise NotImplementedError('Interface Class')


class TabEntryFileBase:
    def __init__(self):
        self.hashname = None
        self.offset = None
        self.size_c = None
        self.size_u = None
        self.file_block_index = None
        self.compression_type = None
        self.compression_flags = None
        self.file_block_table = None

    def deserialize(self, f):
        raise NotImplementedError('Interface Class')

    def serialize(self, f):
        raise NotImplementedError('Interface Class')

    def debug(self):
        l = [self.offset, self.size_c, self.size_u]
        return [
            '{:08x}'.format(self.hashname),
            l,
            ['{:08x}'.format(v) for v in l],
            self.file_block_index,
            self.compression_type,
            self.compression_flags,
            self.file_block_table
        ]


class TabEntryFileV3(TabEntryFileBase):
    def __init__(self):
        TabEntryFileBase.__init__(self)

    def deserialize(self, f):
        try:
            self.hashname = f.read_u32(raise_on_no_data=True)
            self.offset = f.read_u32(raise_on_no_data=True)
            self.size_c = f.read_u32(raise_on_no_data=True)
            self.size_u = self.size_c
            self.compression_flags = 0
            if self.size_c == self.size_u:
                self.compression_type = compression_00_none
            else:
                self.compression_type = compression_v3_zlib

            if f.debug:
                self.debug()
        except EDecaOutOfData:
            return False

        return True

    def serialize(self, f):
        raise NotImplementedError('TODO')


class TabEntryFileV4(TabEntryFileBase):
    def __init__(self):
        TabEntryFileBase.__init__(self)

    def deserialize(self, f):
        try:
            self.hashname = f.read_u32(raise_on_no_data=True)
            self.offset = f.read_u32(raise_on_no_data=True)
            self.size_c = f.read_u32(raise_on_no_data=True)
            self.size_u = f.read_u32(raise_on_no_data=True)
            self.file_block_index = f.read_u16(raise_on_no_data=True)
            self.compression_type = f.read_u8(raise_on_no_data=True)
            self.compression_flags = f.read_u8(raise_on_no_data=True)

            if f.debug:
                print(self.debug())
        except EDecaOutOfData:
            return False

        return True

    def serialize(self, f):
        raise NotImplementedError('TODO')


class TabEntryFileV5(TabEntryFileBase):
    def __init__(self):
        TabEntryFileBase.__init__(self)

    def deserialize(self, f):
        try:
            self.hashname = f.read_s64(raise_on_no_data=True)  # s64 because python uses those for ints
            self.offset = f.read_u32(raise_on_no_data=True)
            self.size_c = f.read_u32(raise_on_no_data=True)
            self.size_u = f.read_u32(raise_on_no_data=True)
            self.file_block_index = f.read_u16(raise_on_no_data=True)
            self.compression_type = f.read_u8(raise_on_no_data=True)
            self.compression_flags = f.read_u8(raise_on_no_data=True)

            if f.debug:
                print(self.debug())
        except EDecaOutOfData:
            return False

        return True

    def serialize(self, f):
        raise NotImplementedError('TODO')
