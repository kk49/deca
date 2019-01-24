import sys
import io
import os
from deca.errors import *
from deca.file import ArchiveFile, SubsetFile
from deca.util import dump_block
from pprint import pformat
from deca.hash_jenkins import hash_little

# https://github.com/tim42/gibbed-justcause3-tools-fork/blob/master/Gibbed.JustCause3.FileFormats/AdfFile.cs

# TODO first pass find types?
# TODO first pass find string hashes?
# TODO ./files/effects/vehicles/wheels/rear_snow.effc good for basic types


class AdfTypeMissing(Exception):
    def __init__(self, hashid, *args, **kwargs):
        Exception.__init__(self, *args, **kwargs)
        self.hashid = hashid


class GdcArchiveEntry:
    def __init__(self, index, offset, size, vpath_hash, filetype_hash, adf_type_hash, vpath):
        self.index = index
        self.offset = offset
        self.size = size
        self.vpath = vpath
        self.vpath_hash = vpath_hash
        self.filetype_hash = filetype_hash
        self.adf_type_hash = adf_type_hash

    def __repr__(self):
        str_vhash = ''
        if self.vpath_hash is not None:
            str_vhash = ' h:{:08X}'.format(self.vpath_hash)

        str_fthash = ''
        if self.filetype_hash is not None:
            str_fthash = ' ft:{:08x}'.format(self.filetype_hash)

        str_adfhash = ''
        if self.adf_type_hash is not None:
            str_adfhash = ' adf:{:08x}'.format(self.adf_type_hash)

        return 'i:{:4d} o:{:9d} s:{:9d}{}{}{} vp:{}'.format(
            self.index, self.offset, self.size, str_vhash, str_fthash, str_adfhash, self.vpath.decode('utf-8'))


class StringHash:
    def __init__(self):
        self.value = None
        self.value_hash = None
        self.unknown = None

    def deserialize(self, f, nt):
        self.value = f.read_strz()
        self.value_hash = f.read_u32()
        self.unknown = f.read_u32()

        # print(self.value, self.value_hash, self.unknown)


class MemberDef:
    def __init__(self):
        self.name = None
        self.type_hash = None
        self.size = None
        self.offset = None
        self.bit_offset = None
        self.default_type = None
        self.default_value = None

    def deserialize(self, f, nt):
        self.name = nt[f.read_u64()][1]
        self.type_hash = f.read_u32()
        self.size = f.read_u32()
        offset = f.read_u32()
        self.bit_offset = (offset >> 24) & 0xff
        self.offset = offset & 0x00ffffff
        self.default_type = f.read_u32()
        self.default_value = f.read_u64()


class EnumDef:
    def __init__(self):
        self.name = None
        self.value = None

    def deserialize(self, f, nt):
        self.name = nt[f.read_u64()][1]
        self.value = f.read_u32()

        # print(self.name, self.value)


'''
        public enum TypeDefinitionType : uint
        {
            Primitive = 0,
            Structure = 1,
            Pointer = 2,
            Array = 3,
            InlineArray = 4,
            String = 5,
            BitField = 7,
            Enumeration = 8,
            StringHash = 9,
        }
'''


class TypeDef:
    def __init__(self):
        self.metatype = None
        self.size = None
        self.alignment = None
        self.type_hash = None
        self.name = None
        self.flags = None
        self.element_type_hash = None
        self.element_length = None
        self.members = None

    def deserialize(self, f, nt):
        self.metatype = f.read_u32()
        self.size = f.read_u32()
        self.alignment = f.read_u32()
        self.type_hash = f.read_u32()
        self.name = nt[f.read_u64()][1]
        self.flags = f.read_u32()
        self.element_type_hash = f.read_u32()
        self.element_length = f.read_u32()

        if self.metatype == 0:  # Primative
            pass
        elif self.metatype == 1:  # Structure
            member_count = f.read_u32()
            self.members = [MemberDef() for i in range(member_count)]
            for i in range(member_count):
                self.members[i].deserialize(f, nt)
        elif self.metatype == 2:  # Pointer
            count = f.read_u32()
            if count != 0:
                raise Exception('Not Implemented: count == {}'.format(count))
        elif self.metatype == 3:  # Array
            count = f.read_u32()
            if count != 0:
                # raise Exception('Not Implemented: count == {}'.format(count))
                print('Not Implemented: count == {}'.format(count))
        elif self.metatype == 4:  # Inline Array
            count = f.read_u32()
            if count != 0:
                raise Exception('Not Implemented: count == {}'.format(count))
        elif self.metatype == 7:  # BitField
            count = f.read_u32()
            if count != 0:
                raise Exception('Not Implemented: count == {}'.format(count))
        elif self.metatype == 8:  # Enumeration
            count = f.read_u32()
            self.members = [EnumDef() for i in range(count)]
            for i in range(count):
                self.members[i].deserialize(f, nt)
        elif self.metatype == 9:  # String Hash
            count = f.read_u32()
            if count != 0:
                raise Exception('Not Implemented: count == {}'.format(count))
        else:
            raise Exception('Unknown Typedef Type {}'.format(self.metatype))


    # def read(self, type_systems, f):
    #     if self.metatype == 0:  # Primative
    #         pass
    #     elif self.metatype == 1:  # Structure
    #         v = {}
    #         for m in self.members:
    #             v[m.name] = m.read(type_systems, f)
    #         return v
    #     elif self.metatype == 2:  # Pointer
    #         raise Exception('Not Implement')
    #     elif self.metatype == 3:  # Array
    #         raise Exception('Not Implement')
    #     elif self.metatype == 4:  # Inline Array
    #         raise Exception('Not Implement')
    #     elif self.metatype == 7:  # BitField
    #         raise Exception('Not Implement')
    #     elif self.metatype == 8:  # Enumeration
    #         raise Exception('Not Implement')
    #     elif self.metatype == 9:  # String Hash
    #         raise Exception('Not Implement')
    #     else:
    #         raise Exception('Unknown Typedef Type {}'.format(self.metatype))


'''
 public uint NameHash;
            public uint TypeHash;
            public uint Offset;
            public uint Size;
            public string Name;
            public MemoryStream Data; // instance data (from offset to offset+size)
            public List<InstanceMemberInfo> Members; // members of instance info
            public TypeDefinition Type;
            public int InlineArrayIndex; // The index of the member after which to put the inline array
            public uint MinInlineArraySize; // I don't like this, but that's the only solution for some ADF files...

'''


class InstanceEntry:
    def __init__(self):
        self.name_hash = None
        self.type_hash = None
        self.offset = None
        self.size = None
        self.name = None

    def deserialize(self, f, nt):
        # print('FP Begin:', f.tell())
        self.name_hash = f.read_u32()
        self.type_hash = f.read_u32()
        self.offset = f.read_u32()
        self.size = f.read_u32()
        self.name = nt[f.read_u64()][1]
        # print('{:08x}'.format(self.name_hash), '{:08x}'.format(self.type_hash), self.offset, self.size, self.name)
        # print('FP End', f.tell())

    # def read(self, type_systems, f):
    #     if self.type_hash not in type_systems:
    #         raise AdfTypeMissing(self.type_hash)
    #     td = type_systems[self.type_hash]
    #     f.seek(self.offset)
    #     v = td.read(type_systems, f)
    #     return v


MetaTypeString = ['Primative', 'Structure', 'Pointer', 'Array', 'InlineArray', 'String', '6', 'BitField', 'Enumeration', 'StringHash']


def dump_type(type_id, type_map, offset=0):
    prim_types = {
        0x580D0A62: 'sint08',
        0x0ca2821d: 'uint08',
        0xD13FCF93: 'sint16',
        0x86d152bd: 'uint16',
        0x192fe633: 'sint32',
        0x075e4e4f: 'uint32',
        0xAF41354F: 'sint64',
        0xA139E01F: 'uint64',
        0x7515a207: 'float',
        0xC609F663: 'double',
        0x8955583e: 'name',
    }

    if type_id in prim_types:
        return '{}PrimType: {}\n'.format(' ' * offset, prim_types[type_id])

    if type_id not in type_map:
        return '{}UNKNOWN TYPE: {:08x}\n'.format(' ' * offset, type_id)
        # raise AdfTypeMissing(type_id)
    type_def = type_map[type_id]

    space = ' ' * offset
    sbuf = space + MetaTypeString[type_def.metatype] +'\n'
    if type_def.metatype == 0:  # Primative
        pass
    elif type_def.metatype == 1:  # Structure
        for m in type_def.members:
            sbuf = sbuf + '{}{} o:{}({:08x})[{}] s:{} t:{:08x} dt:{:08x} dv:{:016x}\n'.format(' ' * (offset + 2), m.name.decode('utf-8'), m.offset, m.offset, m.bit_offset, m.size, m.type_hash, m.default_type, m.default_value)
            sbuf = sbuf + dump_type(m.type_hash, type_map, offset + 4)
    elif type_def.metatype == 2:  # Pointer
        pass
    elif type_def.metatype == 3:  # Array
        sbuf = sbuf + '{}Length: {}\n'.format(' ' * (offset + 2), type_def.element_length)
        sbuf = sbuf + dump_type(type_def.element_type_hash, type_map, offset+2)
    elif type_def.metatype == 4:  # Inline Array
        sbuf = sbuf + '{}Length: {}\n'.format(' ' * (offset + 2), type_def.element_length)
        sbuf = sbuf + dump_type(type_def.element_type_hash, type_map, offset+2)
    elif type_def.metatype == 7:  # BitField
        pass
    elif type_def.metatype == 8:  # Enumeration
        pass
    elif type_def.metatype == 9:  # String Hash
        pass
    else:
        raise Exception('Unknown Typedef Type {}'.format(type_def.metatype))
    return sbuf


typedef_s8 = 0x580D0A62
typedef_u8 = 0x0ca2821d
typedef_s16 = 0xD13FCF93
typedef_u16 = 0x86d152bd
typedef_s32 = 0x192fe633
typedef_u32 = 0x075e4e4f
typedef_s64 = 0xAF41354F
typedef_u64 = 0xA139E01F
typedef_f32 = 0x7515a207
typedef_f64 = 0xC609F663

prim_types = {
    typedef_s8,
    typedef_u8,
    typedef_s16,
    typedef_u16,
    typedef_s32,
    typedef_u32,
    typedef_s64,
    typedef_u64,
    typedef_f32,
    typedef_f64,
}


def read_instance(f, type_id, map_typdef, map_stringhash, table_name, abs_offset, bit_offset=None, found_strings=None):
    if type_id == typedef_s8:
        v = f.read_s8()
    elif type_id == typedef_u8:
        v = f.read_u8()
    elif type_id == typedef_s16:
        v = f.read_s16()
    elif type_id == typedef_u16:
        v = f.read_u16()
    elif type_id == typedef_s32:
        v = f.read_s32()
    elif type_id == typedef_u32:
        v = f.read_u32()
    elif type_id == typedef_s64:
        v = f.read_s64()
    elif type_id == typedef_u64:
        v = f.read_u64()
    elif type_id == typedef_f32:
        v = f.read_f32()
    elif type_id == typedef_f64:
        v = f.read_f64()
    elif type_id == 0x8955583e:
        v = f.read_u64()
        opos = f.tell()
        offset = v & 0xffffffff
        f.seek(offset)
        # TODO Size may be needed for byte codes?
        # size = (v >> 32) & 0xffffffff
        # v = f.read_c8(size)
        # v = b''.join(v)
        v = f.read_strz()

        if found_strings is not None:
            found_strings.add(v)

        f.seek(opos)
    # TODO: optional type? this seems to be missing in some cases, i.e. the case of meshc files for CharacterMesh1UVMesh
    elif type_id == 0xdefe88ed:  # Optional value
        v0 = f.read_u32(4)
        if v0[0] == 0 or v0[2] == 0:
            v = None
        else:
            opos = f.tell()
            f.seek(v0[0])
            v = read_instance(f, v0[2], map_typdef, map_stringhash, table_name, abs_offset, found_strings=found_strings)
            f.seek(opos)
    elif type_id == 0x178842fe:  # gdc/global.gdcc
        # TODO this should probably be it's own file type and the adf should be considered a wrapper
        v = []
        while True:
            t = f.read_u8()
            if t is None:
                break
            v.append(t)
        v = bytearray(v)
        with ArchiveFile(io.BytesIO(v)) as gdf:
            count = gdf.read_u32(8)
            assert(count[0] == 32)
            assert(count[1] == 16)
            assert(count[2] == count[6])
            assert(count[3] == 0)
            # assert(count[4] == filesize +- k)
            assert(count[5] == 16)
            assert(count[6] == count[2])
            assert(count[7] == 0)
            dir_list = []
            for i in range(count[2]):
                d00_offset = gdf.read_u32()
                d04_unk = gdf.read_u32()
                d08_filetype_hash = gdf.read_u32()
                d12_unk = gdf.read_u32()
                d16_vpath_offset = gdf.read_u32()
                d20_unk = gdf.read_u32()
                d24_unk = gdf.read_u32()
                d28_unk = gdf.read_u32()
                assert(d04_unk == 16)
                assert(d12_unk == 0)
                assert(d20_unk == 16)
                assert(d24_unk == 0)
                assert(d28_unk == 0)
                entry = [d00_offset, d16_vpath_offset, d08_filetype_hash, d04_unk, d12_unk, d20_unk, d24_unk, d28_unk]
                dir_list.append(entry)

            dir_contents = []
            idx = 0
            for e1 in dir_list:
                # TODO something weird is going on with this second header, sometimes it makes sense, sometimes it may
                # have floats? or indicate that is should be 24 byte long?
                string_offset = e1[1]
                ftype_hash = e1[2]

                gdf.seek(string_offset)
                vpath = gdf.read_strz()
                vhash = hash_little(vpath)

                gdf.seek(e1[0])

                if ftype_hash in {0xD74CC4CB}:  # RTPC read directly
                    # TODO this follows the data structure for an array of some type, 0xD74CC4CB is probably it's hash
                    header2 = gdf.read_u32(4)
                    actual_offset = header2[0]
                    actual_size = header2[2]
                    adf_type_hash = None
                else:  #TODO current guess it that it is a bare ADF instance
                    header2 = gdf.read_u32(8)
                    actual_offset = e1[0]
                    actual_size = string_offset - actual_offset
                    adf_type_hash = ftype_hash

                gdf.seek(actual_offset)
                buf = gdf.read(actual_size)
                entry = GdcArchiveEntry(
                    index=idx,
                    offset=actual_offset + abs_offset,
                    size=actual_size,
                    vpath_hash=vhash,
                    filetype_hash=ftype_hash,
                    adf_type_hash=adf_type_hash,
                    vpath=vpath)
                dir_contents.append(entry)
                idx += 1
            v = dir_contents

    elif type_id == 0xb5b062f1:  # MDIC
        # TODO this should probably be it's own file type and the adf should be considered a wrapper
        v = []
        while True:
            t = f.read_u8()
            if t is None:
                break
            v.append(t)
        v = bytearray(v)
        # v = ['{:02x}'.format(v[i]) for i in range(len(v))]
    else:
        if type_id not in map_typdef:
            raise AdfTypeMissing(type_id)
        type_def = map_typdef[type_id]

        if type_def.metatype == 0:  # Primative
            raise AdfTypeMissing(type_id)
        elif type_def.metatype == 1:  # Structure
            v = {}
            p0 = f.tell()
            for m in type_def.members:
                f.seek(p0 + m.offset)
                nm = m.name.decode('utf-8')
                vt = read_instance(f, m.type_hash, map_typdef, map_stringhash, table_name, abs_offset, bit_offset=m.bit_offset, found_strings=found_strings)
                v[nm] = vt
                # print(nm, vt)
            p1 = f.tell()
            f.seek(p0 + type_def.size)
            # print(p0, p1, p1-p0, type_def.size)
        elif type_def.metatype == 2:  # Pointer
            v0 = f.read_u64()
            v = (v0, 'NOTE: {}: {:016x} to {:08x}'.format(type_def.name, v0, type_def.element_type_hash))
            # TODO sure how this is used yet, but it's used by effects so lower priority
            # raise AdfTypeMissing(type_id)
        elif type_def.metatype == 3:  # Array
            v0 = f.read_u32(4)
            opos = f.tell()

            offset = v0[0]
            flags = v0[1]
            length = v0[2]
            unknown = v0[3]
            align = None
            # aligning based on element size info
            # if type_def.element_type_hash not in prim_types:
            #     align = 4
            f.seek(offset)

            if type_def.element_type_hash == typedef_u8:
                # v = list(f.read_u8(length))
                v = f.read(length)
            elif type_def.element_type_hash == typedef_s8:
                # v = list(f.read_s8(length))
                v = f.read(length)
            elif type_def.element_type_hash == typedef_u16:
                v = list(f.read_u16(length))
            elif type_def.element_type_hash == typedef_s16:
                v = list(f.read_s16(length))
            elif type_def.element_type_hash == typedef_u32:
                v = list(f.read_u32(length))
            elif type_def.element_type_hash == typedef_s32:
                v = list(f.read_s32(length))
            elif type_def.element_type_hash == typedef_u64:
                v = list(f.read_u64(length))
            elif type_def.element_type_hash == typedef_s64:
                v = list(f.read_s64(length))
            elif type_def.element_type_hash == typedef_f32:
                v = list(f.read_f32(length))
            elif type_def.element_type_hash == typedef_f64:
                v = list(f.read_f64(length))
            else:
                # if length > 1000:
                #     print('OPTIMIZE {:08x}'.format(type_def.element_type_hash))
                v = [None] * length
                for i in range(length):
                    p0 = f.tell()
                    if align is not None:
                        nudge = (align - p0 % align) % align
                        f.seek(p0 + nudge)  # v0[0] offset ele 0, v0[1] stride?
                    v[i] = read_instance(f, type_def.element_type_hash, map_typdef, map_stringhash, table_name, abs_offset, found_strings=found_strings)
                    p1 = f.tell()
                    # print(p0, p1, p1-p0)
            f.seek(opos)
        elif type_def.metatype == 4:  # Inline Array
            v = [None] * type_def.element_length
            for i in range(type_def.element_length):
                v[i] = read_instance(f, type_def.element_type_hash, map_typdef, map_stringhash, table_name, abs_offset, found_strings=found_strings)
        elif type_def.metatype == 7:  # BitField
            if type_def.size == 1:
                v = f.read_u8()
            elif type_def.size == 2:
                v = f.read_u16()
            elif type_def.size == 4:
                v = f.read_u32()
            elif type_def.size == 8:
                v = f.read_u64()
            else:
                raise Exception('Unknown bitfield size')

            if bit_offset is None:
                raise Exception('Missing bit offset')
            v = (v >> bit_offset) & 1
        elif type_def.metatype == 8:  # Enumeration
            if type_def.size != 4:
                raise Exception('Unknown enum size')
            v = f.read_u32()
            if v < len(type_def.members):
                vs = type_def.members[v].name
            else:
                vs = None
            v = [v, vs]
        elif type_def.metatype == 9:  # String Hash
            if type_def.size == 4:
                v = f.read_u32()
                if v in map_stringhash:
                    v = map_stringhash[v].value
                elif v == 0xDEADBEEF:
                    v = b''
                else:
                    v = (v, 'MISSING_STRINGHASH {} 0x{:08x}'.format(type_def.size, v))
            elif type_def.size == 6:
                v0 = f.read_u32()
                v1 = f.read_u16()
                v = v1 << 32 | v0
                v = (v, 'OBJID {} 0x{:016x}'.format(type_def.size, v))
            elif type_def.size == 8:
                v = f.read_u64()
                v = (v, 'NOT EXPECTED {} 0x{:016x}'.format(type_def.size, v))
            else:
                v = f.read(type_def.size)
                v = (v, 'NOT EXPECTED {}'.format(type_def.size))

        else:
            raise Exception('Unknown Typedef Type {}'.format(type_def.metatype))

    return v


class Adf:
    def __init__(self):
        self.version = None
        self.instance_count = None
        self.instance_offset = None
        self.typedef_count = None
        self.typedef_offset = None
        self.stringhash_count = None
        self.stringhash_offset = None
        self.nametable_count = None
        self.nametable_offset = None
        self.total_size = None

        self.unknown = None

        self.comment = ''
        self.table_name = []
        self.table_stringhash = []
        self.map_stringhash = {}
        self.table_typedef = []
        self.map_typedef = {}
        self.table_instance = []
        self.map_instance = {}

        self.found_strings = set()
        self.table_instance_values = []

    def dump_to_string(self):
        sbuf = ''
        sbuf = sbuf + '--------header\n'
        sbuf = sbuf + '{}: {}\n'.format('version', self.version)
        sbuf = sbuf + '{}: {}\n'.format('instance_count', self.instance_count)
        sbuf = sbuf + '{}: {}\n'.format('instance_offset', self.instance_offset)
        sbuf = sbuf + '{}: {}\n'.format('typedef_count', self.typedef_count)
        sbuf = sbuf + '{}: {}\n'.format('typedef_offset', self.typedef_offset)
        sbuf = sbuf + '{}: {}\n'.format('stringhash_count', self.stringhash_count)
        sbuf = sbuf + '{}: {}\n'.format('stringhash_offset', self.stringhash_offset)
        sbuf = sbuf + '{}: {}\n'.format('nametable_count', self.nametable_count)
        sbuf = sbuf + '{}: {}\n'.format('nametable_offset', self.nametable_offset)
        sbuf = sbuf + '{}: {}\n'.format('total_size', self.total_size)
        for i in range(len(self.unknown)):
            sbuf = sbuf + 'Unknown[{0}]: {1} 0x{1:08x}\n'.format(i, self.unknown[i])

        sbuf = sbuf + '\n--------comment\n'
        sbuf = sbuf + self.comment.decode('utf-8')

        sbuf = sbuf + '\n\n--------name_table\n'
        # sbuf = sbuf + '  NOT CURRENTLY SHOWN\n'
        for i in range(len(self.table_name)):
            sbuf = sbuf + 'name_table\t{}\t{}\n'.format(i, self.table_name[i][1].decode('utf-8'))

        sbuf = sbuf + '\n--------string_hash\n'
        # sbuf = sbuf + '  NOT CURRENTLY SHOWN\n'
        for v in self.map_stringhash.items():
            sbuf = sbuf + 'string_hash\t{:08x}\t{}\n'.format(v[0], v[1].value)

        sbuf = sbuf + '\n--------typedefs\n'
        # sbuf = sbuf + '  NOT CURRENTLY SHOWN\n'
        for v in self.map_typedef.items():
            sbuf = sbuf + 'typedefs\t{:08x}\t{}\n'.format(v[0], v[1].name.decode('utf-8'))
            sbuf = sbuf + dump_type(v[0], self.map_typedef, 2)

        sbuf = sbuf + '\n--------instances\n'
        for info, v in zip(self.table_instance, self.table_instance_values):
            sbuf = sbuf + 'instances\t{:08x}\t{:08x}\t{}\t{}\t{}\t{:08x}-{:08x}\n'.format(
                info.name_hash,
                info.type_hash,
                info.name.decode('utf-8'),
                info.offset, info.size, info.offset, info.offset + info.size)

            sbuf = sbuf + pformat(v, width=1024) + '\n'

        return sbuf

    def deserialize(self, fp):
        header = fp.read(0x40)

        fh = ArchiveFile(io.BytesIO(header))

        if len(header) < 0x40:
            raise DecaErrorParse('File Too Short')

        magic = fh.read_strl(4)

        if magic != b' FDA':
            raise DecaErrorParse('Magic does not match')

        self.version = fh.read_u32()

        self.instance_count = fh.read_u32()
        self.instance_offset = fh.read_u32()

        self.typedef_count = fh.read_u32()
        self.typedef_offset = fh.read_u32()

        self.stringhash_count = fh.read_u32()
        self.stringhash_offset = fh.read_u32()

        self.nametable_count = fh.read_u32()
        self.nametable_offset = fh.read_u32()

        self.total_size = fh.read_u32()

        self.unknown = fh.read_u32(5)

        self.comment = fp.read_strz()

        # name table
        self.table_name = [[None, None] for i in range(self.nametable_count)]
        fp.seek(self.nametable_offset)
        for i in range(self.nametable_count):
            self.table_name[i][0] = fp.read_u8()
        for i in range(self.nametable_count):
            self.table_name[i][1] = fp.read(self.table_name[i][0] + 1)[0:-1]

        # string hash
        self.table_stringhash = [StringHash() for i in range(self.stringhash_count)]
        self.map_stringhash = {}
        fp.seek(self.stringhash_offset)
        for i in range(self.stringhash_count):
            self.table_stringhash[i].deserialize(fp, self.table_name)
            self.map_stringhash[self.table_stringhash[i].value_hash] = self.table_stringhash[i]

        # typedef
        self.table_typedef = [TypeDef() for i in range(self.typedef_count)]
        self.map_typedef = {}
        fp.seek(self.typedef_offset)
        for i in range(self.typedef_count):
            self.table_typedef[i].deserialize(fp, self.table_name)
            self.map_typedef[self.table_typedef[i].type_hash] = self.table_typedef[i]

        # print(typedef_map)

        # instance
        self.table_instance = [InstanceEntry() for i in range(self.instance_count)]
        self.map_instance = {}
        fp.seek(self.instance_offset)
        for i in range(self.instance_count):
            self.table_instance[i].deserialize(fp, self.table_name)
            self.map_instance[self.table_instance[i].name_hash] = self.table_instance[i]

        self.found_strings = set()
        self.table_instance_values = [None] * len(self.table_instance)
        for i in range(len(self.table_instance)):
            ins = self.table_instance[i]
            fp.seek(ins.offset)
            # try:
            buf = fp.read(ins.size)
            with ArchiveFile(io.BytesIO(buf)) as f:
                v = read_instance(f, ins.type_hash, self.map_typedef, self.map_stringhash, self.table_name, ins.offset, found_strings=self.found_strings)
                self.table_instance_values[i] = v
            # except AdfTypeMissing as ae:
            #     print('Missing HASHID {:08x}'.format(ae.hashid))
            # except Exception as exp:
            #     print(exp)


def load_adf(buffer):
    with ArchiveFile(io.BytesIO(buffer)) as fp:
        obj = Adf()
        try:
            obj.deserialize(fp)
            return obj
        except DecaErrorParse:
            return None


def load_adf_bare(buffer, adf_type):
    return None
