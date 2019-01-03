import sys
import io
import os
from deca.errors import *
from deca.file import ArchiveFile
from deca.util import dump_block

# https://github.com/tim42/gibbed-justcause3-tools-fork/blob/master/Gibbed.JustCause3.FileFormats/AdfFile.cs

# TODO first pass find types?
# TODO first pass find string hashes?
# TODO ./files/effects/vehicles/wheels/rear_snow.effc good for basic types


class AdfTypeMissing(Exception):
    def __init__(self, hashid, *args, **kwargs):
        Exception.__init__(self, *args, **kwargs)
        self.hashid = hashid


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
        self.default_type = None
        self.default_value = None

    def deserialize(self, f, nt):
        self.name = nt[f.read_u64()][1]
        self.type_hash = f.read_u32()
        self.size = f.read_u32()
        self.offset = f.read_u32()
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
            sbuf = sbuf + '{}{} o:{}({:08x}) s:{} t:{:08x} dt:{:08x} dv:{:016x}\n'.format(' ' * (offset + 2), m.name.decode('utf-8'), m.offset, m.offset, m.size, m.type_hash, m.default_type, m.default_value)
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


def read_instance(f, type_id, map_typdef, map_stringhash, table_name):
    if type_id == 0x580D0A62:
        v = f.read_s8()
    elif type_id == 0x0ca2821d:
        v = f.read_u8()
    elif type_id == 0xD13FCF93:
        v = f.read_s16()
    elif type_id == 0x86d152bd:
        v = f.read_u16()
    elif type_id == 0x192fe633:
        v = f.read_s32()
    elif type_id == 0x075e4e4f:
        v = f.read_u32()
    elif type_id == 0xAF41354F:
        v = f.read_s64()
    elif type_id == 0xA139E01F:
        v = f.read_u64()
    elif type_id == 0x7515a207:
        v = f.read_f32()
    elif type_id == 0xC609F663:
        v = f.read_f64()
    elif type_id == 0x8955583e:
        v = f.read_u64()
        v = table_name[v]
    else:
        if type_id not in map_typdef:
            raise AdfTypeMissing(type_id)
        type_def = map_typdef[type_id]

        if type_def.metatype == 0:  # Primative
            raise AdfTypeMissing(type_id)
        elif type_def.metatype == 1:  # Structure
            v = {}
            for m in type_def.members:
                v[m.name.decode('utf-8')] = read_instance(f, m.type_hash, map_typdef, map_stringhash, table_name)
        elif type_def.metatype == 2:  # Pointer
            raise AdfTypeMissing(type_id)
        elif type_def.metatype == 3:  # Array
            pos = f.tell()
            buf = f.read(128)
            f.seek(pos)
            l = f.read_u32()
            v = [None] * l
            for i in range(l):
                v[i] = read_instance(f, type_def.element_type_hash, map_typdef, map_stringhash, table_name)
            # raise AdfTypeMissing(type_id)
        elif type_def.metatype == 4:  # Inline Array
            v = [None] * type_def.element_length
            for i in range(type_def.element_length):
                v[i] = read_instance(f, type_def.element_type_hash, map_typdef, map_stringhash, table_name)
        elif type_def.metatype == 7:  # BitField
            raise AdfTypeMissing(type_id)
        elif type_def.metatype == 8:  # Enumeration
            raise AdfTypeMissing(type_id)
        elif type_def.metatype == 9:  # String Hash
            v = f.read_u32()
            v = map_stringhash[v].value
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

        self.comment = ''
        self.table_name = []
        self.table_stringhash = []
        self.map_stringhash = {}
        self.table_typedef = []
        self.map_typedef = {}
        self.table_instance = []
        self.map_instance = {}
        self.table_instance_value = []

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

        sbuf = sbuf + '\n--------comment\n'
        sbuf = sbuf + self.comment.decode('utf-8')

        sbuf = sbuf + '\n\n--------name_table\n'
        for i in range(len(self.table_name)):
            sbuf = sbuf + 'name_table\t{}\t{}\n'.format(i, self.table_name[i][1].decode('utf-8'))

        sbuf = sbuf + '\n--------string_hash\n'
        for v in self.map_stringhash.items():
            sbuf = sbuf + 'string_hash\t{:08x}\t{}\n'.format(v[0], v[1].value)

        sbuf = sbuf + '\n--------typedefs\n'
        for v in self.map_typedef.items():
            sbuf = sbuf + 'typedefs\t{:08x}\t{}\n'.format(v[0], v[1].name.decode('utf-8'))
            sbuf = sbuf + dump_type(v[0], self.map_typedef, 2)

        sbuf = sbuf + '\n--------instances\n'
        for v in self.map_instance.items():
            sbuf = sbuf + 'instances\t{:08x}\t{:08x}\t{}\t{}\t{}\t{:08x}-{:08x}\n'.format(v[0], v[1].type_hash, v[1].name.decode('utf-8'), v[1].offset, v[1].size, v[1].offset, v[1].offset + v[1].size)

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
        fh.read_u32()

        fh.read_u32()
        fh.read_u32()
        fh.read_u32()
        fh.read_u32()

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

        # self.table_instance_values = []
        # for ins in self.table_instance:
        #     fp.seek(ins.offset)
        #     v = read_instance(fp, ins.type_hash, self.map_typedef, self.map_stringhash, self.table_name)
        #     self.table_instance_values.append(v)


def load_adf(buffer):
    with ArchiveFile(io.BytesIO(buffer)) as fp:
        obj = Adf()
        try:
            obj.deserialize(fp)
            return obj
        except DecaErrorParse:
            return None
