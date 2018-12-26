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


class Instance:
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


class Adf:
    def __init__(self):
        self.table_name = []
        self.table_stringhash = []
        self.map_stringhash = {}
        self.table_typedef = []
        self.map_typedef = {}
        self.table_instance = []
        self.map_instance = {}

    def dump_to_string(self):
        sbuf = ''

        sbuf = sbuf + '--------name_table\n'
        for i in range(len(self.table_name)):
            sbuf = sbuf + 'name_table\t{}\t{}\n'.format(i, self.table_name[i][1].decode('utf-8'))

        sbuf = sbuf + '\n--------string_hash\n'
        for v in self.map_stringhash.items():
            sbuf = sbuf + 'string_hash\t{:08x}\t{}\n'.format(v[0], v[1].value)

        sbuf = sbuf + '\n--------typedefs\n'
        for v in self.map_typedef.items():
            sbuf = sbuf + 'typedefs\t{:08x}\t{}\n'.format(v[0], v[1].name.decode('utf-8'))

        sbuf = sbuf + '\n--------instances\n'
        for v in self.map_instance.items():
            sbuf = sbuf + 'instances\t{:08x}\t{:08x}\t{}\n'.format(v[0], v[1].type_hash, v[1].name.decode('utf-8'))

        return sbuf

    def deserialize(self, fp):
        header = fp.read(0x40)

        fh = ArchiveFile(io.BytesIO(header))

        if len(header) < 0x40:
            raise DecaErrorParse('File Too Short')

        magic = fh.read_strl(4)

        if magic != b' FDA':
            raise DecaErrorParse('Magic does not match')

        version = fh.read_u32()

        instance_count = fh.read_u32()
        instance_offset = fh.read_u32()

        typedef_count = fh.read_u32()
        typedef_offset = fh.read_u32()

        stringhash_count = fh.read_u32()
        stringhash_offset = fh.read_u32()

        nametable_count = fh.read_u32()
        nametable_offset = fh.read_u32()

        total_size = fh.read_u32()
        fh.read_u32()

        fh.read_u32()
        fh.read_u32()
        fh.read_u32()
        fh.read_u32()

        # TODO COMMENT C-string

        # name table
        self.table_name = [[None, None] for i in range(nametable_count)]
        fp.seek(nametable_offset)
        for i in range(nametable_count):
            self.table_name[i][0] = fp.read_u8()
        for i in range(nametable_count):
            self.table_name[i][1] = fp.read(self.table_name[i][0] + 1)[0:-1]

        # string hash
        self.table_stringhash = [StringHash() for i in range(stringhash_count)]
        self.map_stringhash = {}
        fp.seek(stringhash_offset)
        for i in range(stringhash_count):
            self.table_stringhash[i].deserialize(fp, self.table_name)
            self.map_stringhash[self.table_stringhash[i].value_hash] = self.table_stringhash[i]

        # typedef
        self.table_typedef = [TypeDef() for i in range(typedef_count)]
        self.map_typedef = {}
        fp.seek(typedef_offset)
        for i in range(typedef_count):
            self.table_typedef[i].deserialize(fp, self.table_name)
            self.map_typedef[self.table_typedef[i].type_hash] = self.table_typedef[i]

        # print(typedef_map)

        # instance
        self.table_instance = [Instance() for i in range(instance_count)]
        self.map_instance = {}
        fp.seek(instance_offset)
        for i in range(instance_count):
            self.table_instance[i].deserialize(fp, self.table_name)
            self.map_instance[self.table_instance[i].name_hash] = self.table_instance[i]


def load_adf(buffer):
    with ArchiveFile(io.BytesIO(buffer)) as fp:
        obj = Adf()
        try:
            obj.deserialize(fp)
            return obj
        except DecaErrorParse:
            return None
