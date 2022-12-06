from deca.file import ArchiveFile
from deca.hashes import hash32_func
from deca.util import align_to
import os
import numpy as np


class EntrySarc:
    def __init__(self, index=None, v_path=None):
        self.META_entry_ptr = None
        self.META_entry_offset_ptr = None
        self.META_entry_size_ptr = None
        self.index = index
        self.v_path = v_path
        self.string_offset = None
        self.offset = None
        self.length = None
        self.file_ext_hash = None
        self.v_hash = None
        self.is_symlink = None

    def deserialize_v2(self, f: ArchiveFile):
        self.META_entry_ptr = f.tell()
        self.v_path = f.read_strl_u32()  # string raw length in multiples of 4 bytes (based on theHunter:COTW)
        self.v_path = self.v_path.strip(b'\00')
        self.META_entry_offset_ptr = f.tell()
        self.offset = f.read_u32()
        self.META_entry_size_ptr = f.tell()
        self.length = f.read_u32()

        self.v_hash = hash32_func(self.v_path)
        self.is_symlink = self.offset == 0

    def serialize_v2(self, f: ArchiveFile):
        # prepare data that will be written, v_path should be a multiple of 4 in length
        v_path = self.v_path + b'\00' * (((len(self.v_path) + 3) // 4 * 4) - len(self.v_path))
        f.write_u32(len(v_path))
        f.write(v_path)

        f.write_u32(self.offset)

        f.write_u32(self.length)

    def deserialize_v3(self, f):
        self.META_entry_ptr = f.tell()
        self.string_offset = f.read_u32()
        self.META_entry_offset_ptr = f.tell()
        self.offset = f.read_u32()
        self.META_entry_size_ptr = f.tell()
        self.length = f.read_u32()
        self.v_hash = f.read_u32()
        self.file_ext_hash = f.read_u32()  # This has is the extension including the period

        self.is_symlink = self.offset == 0

        assert(self.v_hash == hash32_func(self.v_path))
        assert(self.file_ext_hash == hash32_func(os.path.splitext(self.v_path)[1]))

    def serialize_v3(self, f):
        # update entry based on v_path
        self.v_hash = hash32_func(self.v_path)
        self.file_ext_hash = hash32_func(os.path.splitext(self.v_path)[1])

        f.write_u32(self.string_offset)
        f.write_u32(self.offset)
        f.write_u32(self.length)
        f.write_u32(self.v_hash)
        f.write_u32(self.file_ext_hash)

    def __repr__(self):
        str_vhash = ''
        if self.v_hash is not None:
            str_vhash = ' h:{:08X}'.format(self.v_hash)

        str_fthash = ''
        if self.file_ext_hash is not None:
            str_fthash = ' ft:{:08X}'.format(self.file_ext_hash)

        return 'o:{:9d} s:{:9d}{}{} vp:{}'.format(
            self.offset, self.length, str_vhash, str_fthash, self.v_path.decode('utf-8'))

    def dump_str(self):
        return self.__repr__()


class FileSarc:
    def __init__(self):
        self.version = None
        self.magic = None
        self.ver2 = None
        self.dir_block_len = None
        self.strings0 = None
        self.strings = None
        self.entries = None
        self.entries_begin = None
        self.entries_end = None

    def header_deserialize(self, fin):
        with ArchiveFile(fin) as f:
            self.version = f.read_u32()
            self.magic = f.read(4)
            self.ver2 = f.read_u32()
            # assuming 16 byte boundry based on some some examples from theHunter:COTW
            self.dir_block_len = f.read_u32()

            assert(self.version == 4)
            assert(self.magic == b'SARC')
            assert(self.ver2 in {2, 3})

            self.entries = []

            if self.ver2 == 2:
                self.entries_begin = f.tell()
                end_pos = f.tell() + self.dir_block_len
                idx = 0
                while f.tell() + 12 <= end_pos:  # 12 is minimum length of v2 sarc entry and they pad with some zeros
                    entry = EntrySarc(idx)
                    entry.deserialize_v2(f)
                    self.entries.append(entry)
                    idx += 1

            elif self.ver2 == 3:
                string_len = f.read_u32()
                self.strings0 = f.read(string_len)
                self.strings = self.strings0.split(b'\00')
                self.strings = [s for s in self.strings if len(s) > 0]

                self.entries_begin = f.tell()
                self.entries = [EntrySarc(index=i, v_path=s) for i, s in enumerate(self.strings)]
                for ent in self.entries:
                    ent.deserialize_v3(f)

            else:
                raise NotImplementedError('FileSarc.header_deserialize: self.ver2 == {}'.format(self.ver2))

            self.entries_end = f.tell()

    def header_serialize(self, f):
        vpath_string = b''

        if self.ver2 == 2:
            # calculate dir block length
            dir_block_len = 0
            entry: EntrySarc
            for entry in self.entries:
                dir_block_len += 12 + align_to(len(entry.v_path), 4)
            dir_block_len = align_to(dir_block_len, 16)

        elif self.ver2 == 3:
            # calculate dir block length
            entry: EntrySarc
            for entry in self.entries:
                entry.string_offset = len(vpath_string)
                vpath_string = vpath_string + entry.v_path + b'\00'

            # vpath_string = vpath_string + b'\00'

            dir_block_len = 4 + len(vpath_string) + 20 * len(self.entries)
            dir_block_len = align_to(dir_block_len, 16)

        else:
            raise NotImplementedError('FileSarc.header_serialize: self.ver2 == {}'.format(self.ver2))

        data_write_pos = 16 + dir_block_len

        # determine offsets for files in sarc
        for entry in self.entries:
            sz = entry.length
            entry.offset = 0
            # figure out where data goes, take into account 32MB boundaries

            if not entry.is_symlink:
                # IMPORTANT SARCS apparently don't want data to cross 32MB boundary (maybe small boundary?)
                max_block_size = 32 * 1024 * 1024
                if sz > max_block_size:
                    raise NotImplementedError('Excessive file size: {}'.format(entry.v_path))

                block_pos_diff = \
                    np.floor((data_write_pos + sz) / max_block_size) - np.floor(data_write_pos / max_block_size)

                if block_pos_diff > 0:
                    # boundary crossed
                    data_write_pos = ((data_write_pos + max_block_size - 1) // max_block_size) * max_block_size

                entry.offset = data_write_pos
                data_write_pos = data_write_pos + sz
                data_write_pos = align_to(data_write_pos, 4)

        if self.ver2 == 2:
            f.write_u32(4)              # Version == 4 for supported sarc files
            f.write(b'SARC')            # Magic number/id
            f.write_u32(self.ver2)      # Subversion
            f.write_u32(dir_block_len)  # dir block length

            for entry in self.entries:
                entry.serialize_v2(f)

            # fill with zeros to data offset position
            f.write(b'\00' * (data_write_pos - f.tell()))

        elif self.ver2 == 3:
            f.write_u32(4)              # Version == 4 for supported sarc files
            f.write(b'SARC')            # Magic number/id
            f.write_u32(self.ver2)      # Subversion
            f.write_u32(dir_block_len)  # dir block length

            f.write_u32(len(vpath_string))
            f.write(vpath_string)
            for entry in self.entries:
                entry.serialize_v3(f)

            # fill with zeros to data offset position
            f.write(b'\00' * (data_write_pos - f.tell()))

        else:
            raise NotImplementedError('FileSarc.header_serialize: self.ver2 == {}'.format(self.ver2))

    def dump_str(self):
        sbuf = ''
        for ent in self.entries:
            sbuf = sbuf + ent.dump_str() + '\n'
        return sbuf
