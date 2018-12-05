import sys
import io
import os
from kkae.util import *

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
        self.value = dread_strz(f)
        self.value_hash = dread(f, 'I', 4)
        self.unknown = dread(f, 'I', 4)
        print(self.value, self.value_hash, self.unknown)


class MemberDef:
    def __init__(self):
        self.name = None
        self.type_hash = None
        self.size = None
        self.offset = None
        self.default_type = None
        self.default_value = None

    def deserialize(self, f, nt):
        self.name = nt[dread(f, 'q', 8)][1]
        self.type_hash = dread(f, 'I', 4)
        self.size = dread(f, 'I', 4)
        self.offset = dread(f, 'I', 4)
        self.default_type = dread(f, 'I', 4)
        self.default_value = dread(f, 'Q', 8)


class EnumDef:
    def __init__(self):
        self.name = None
        self.value = None

    def deserialize(self, f, nt):
        self.name = nt[dread(f, 'q', 8)][1]
        self.value = dread(f, 'I', 4)

        print(self.name, self.value)

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
        self.metatype = dread(f, 'I', 4)
        self.size = dread(f, 'I', 4)
        self.alignment = dread(f, 'I', 4)
        self.type_hash = dread(f, 'I', 4)
        self.name = nt[dread(f, 'q', 8)][1]
        self.flags = dread(f, 'I', 4)
        self.element_type_hash = dread(f, 'I', 4)
        self.element_length = dread(f, 'I', 4)

        if self.metatype == 0:  # Primative
            pass
        elif self.metatype == 1:  # Structure
            member_count = dread(f, 'I', 4)
            self.members = [MemberDef() for i in range(member_count)]
            for i in range(member_count):
                self.members[i].deserialize(f, nt)
        elif self.metatype == 2:  # Pointer
            count = dread(f, 'I', 4)
            if count != 0:
                print(count)
                raise Exception('Not Implemented')
        elif self.metatype == 3:  # Array
            count = dread(f, 'I', 4)
            if count != 0:
                print(count)
                raise Exception('Not Implemented')
        elif self.metatype == 4:  # Inline Array
            count = dread(f, 'I', 4)
            if count != 0:
                print(count)
                raise Exception('Not Implemented')
        elif self.metatype == 7:  # BitField
            count = dread(f, 'I', 4)
            if count != 0:
                print(count)
                raise Exception('Not Implemented')
        elif self.metatype == 8:  # Enumeration
            count = dread(f, 'I', 4)
            self.members = [EnumDef() for i in range(count)]
            for i in range(count):
                self.members[i].deserialize(f, nt)
        elif self.metatype == 9:  # String Hash
            count = dread(f, 'I', 4)
            if count != 0:
                print(count)
                raise Exception('Not Implemented')
        else:
            raise Exception('Unknown Typedef Type {}'.format(self.type))

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
        print('FP Begin:', f.tell())
        self.name_hash = dread(f, 'I', 4)
        self.type_hash = dread(f, 'I', 4)
        self.offset = dread(f, 'I', 4)
        self.size = dread(f, 'I', 4)
        self.name = nt[dread(f, 'Q', 8)][1]
        # print('{:08x}'.format(self.name_hash), '{:08x}'.format(self.type_hash), self.offset, self.size, self.name)
        print('FP End', f.tell())


if len(sys.argv) < 2:
    in_file = './files/models/manmade/collectibles/gnomes/gnomes_01_garden_01.meshc'
else:
    in_file = sys.argv[1]

file_sz = os.stat(in_file).st_size
print('file size: {}'.format(file_sz))

with open(in_file, 'rb') as f:
    header = f.read(0x40)
    dump_block(header, 0x10)

    fh = io.BytesIO(header)

    magic = dread(fh,'I',4)
    version = dread(fh,'I',4)

    instance_count = dread(fh,'I',4)
    instance_offset = dread(fh,'I',4)

    typedef_count = dread(fh,'I',4)
    typedef_offset = dread(fh,'I',4)

    stringhash_count = dread(fh,'I',4)
    stringhash_offset = dread(fh,'I',4)

    nametable_count = dread(fh,'I',4)
    nametable_offset = dread(fh,'I',4)

    total_size = dread(fh,'I',4)
    dread(fh,'I',4)

    dread(fh,'I',4)
    dread(fh,'I',4)
    dread(fh,'I',4)
    dread(fh,'I',4)

    #TODO COMMENT C-string

    # name table
    name_table = [[None, None] for i in range(nametable_count)]
    f.seek(nametable_offset)
    for i in range(nametable_count):
        name_table[i][0] = dread(f, 'B', 1)
    for i in range(nametable_count):
        name_table[i][1] = f.read(name_table[i][0] + 1)[0:-1]

    # string hash
    stringhash_table = [StringHash() for i in range(stringhash_count)]
    stringhash_map = {}
    f.seek(stringhash_offset)
    for i in range(stringhash_count):
        stringhash_table[i].deserialize(f, name_table)
        stringhash_map[stringhash_table[i].value_hash] = stringhash_table[i]

    # typedef
    typedef_table = [TypeDef() for i in range(typedef_count)]
    typedef_map = {}
    f.seek(typedef_offset)
    for i in range(typedef_count):
        typedef_table[i].deserialize(f, name_table)
        typedef_map[typedef_table[i].type_hash] = typedef_table[i]

    print(typedef_map)

    # instance
    instance_table = [Instance() for i in range(instance_count)]
    instance_map = {}
    f.seek(instance_offset)
    for i in range(instance_count):
        instance_table[i].deserialize(f, name_table)
        instance_map[instance_table[i].name_hash] = instance_table[i]

print('--------name_table')
for i in range(len(name_table)):
    print(i, name_table[i][1])

print('--------string_hash')
for v in stringhash_map.items():
    print('{:08x}'.format(v[0]), v[1].value)

print('--------typedefs')
for v in typedef_map.items():
    print('{:08x}'.format(v[0]), v[1].name)

print('--------instances')
for v in instance_map.items():
    print('{:08x}'.format(v[0]), '{:08x}'.format(v[1].type_hash), v[1].name)
