# This is a generated file! Please edit source .ksy file and use kaitai-struct-compiler to rebuild
# type: ignore

import kaitaistruct
from kaitaistruct import KaitaiStruct, KaitaiStream, BytesIO
from enum import IntEnum


if getattr(kaitaistruct, 'API_VERSION', (0, 9)) < (0, 11):
    raise Exception("Incompatible Kaitai Struct Python API: 0.11 or later is required, but you have %s" % (kaitaistruct.__version__))

class Rtpc(KaitaiStruct):

    class Variant(IntEnum):
        unassigned = 0
        uint32 = 1
        float = 2
        string = 3
        vec2 = 4
        vec3 = 5
        vec4 = 6
        matrix_3x3 = 7
        matrix_4x4 = 8
        uint32_array = 9
        float_array = 10
        byte_array = 11
        deprecated = 12
        object_id = 13
        event = 14
        total = 15
    def __init__(self, _io, _parent=None, _root=None):
        self._io = _io
        self._parent = _parent
        self._root = _root if _root else self
        self._read()

    def _read(self):
        self.header = Rtpc.RtpcHeader(self._io, self, self._root)
        self.container = Rtpc.Container(self._io, self, self._root)

    class ContainerBody(KaitaiStruct):
        def __init__(self, property_count, container_count, _io, _parent=None, _root=None):
            self._io = _io
            self._parent = _parent
            self._root = _root if _root else self
            self.property_count = property_count
            self.container_count = container_count
            self._read()

        def _read(self):
            self.properties = []
            for i in range(self.property_count):
                self.properties.append(Rtpc.PropertyHeader(self._io, self, self._root))

            self.containers = []
            for i in range(self.container_count):
                self.containers.append(Rtpc.Container(self._io, self, self._root))

            self.valid_properties = self._io.read_u4le()


    class F4Array(KaitaiStruct):
        def __init__(self, _io, _parent=None, _root=None):
            self._io = _io
            self._parent = _parent
            self._root = _root if _root else self
            self._read()

        def _read(self):
            self.count = self._io.read_u4le()
            self.values = []
            for i in range(self.count):
                self.values.append(self._io.read_f4le())



    class PropertyHeader(KaitaiStruct):
        def __init__(self, _io, _parent=None, _root=None):
            self._io = _io
            self._parent = _parent
            self._root = _root if _root else self
            self._read()

        def _read(self):
            self.name_hash = self._io.read_u4le()
            self.raw_data = self._io.read_u4le()
            self.variant_type = KaitaiStream.resolve_enum(Rtpc.Variant, self._io.read_u1())

        @property
        def simple_f4(self):
            if hasattr(self, '_m_simple_f4'):
                return self._m_simple_f4

            self._m_simple_f4 = self.raw_data
            return getattr(self, '_m_simple_f4', None)

        @property
        def offset_value(self):
            if hasattr(self, '_m_offset_value'):
                return self._m_offset_value

            _pos = self._io.pos()
            self._io.seek(self.raw_data)
            _on = self.variant_type
            if _on == Rtpc.Variant.string:
                self._m_offset_value = Rtpc.String(self._io, self, self._root)
            elif _on == Rtpc.Variant.uint32_array:
                self._m_offset_value = Rtpc.U4Array(self._io, self, self._root)
            elif _on == Rtpc.Variant.matrix_4x4:
                self._m_offset_value = Rtpc.F4ArrayParam(16, self._io, self, self._root)
            elif _on == Rtpc.Variant.vec4:
                self._m_offset_value = Rtpc.F4ArrayParam(4, self._io, self, self._root)
            elif _on == Rtpc.Variant.vec3:
                self._m_offset_value = Rtpc.F4ArrayParam(3, self._io, self, self._root)
            elif _on == Rtpc.Variant.deprecated:
                self._m_offset_value = Rtpc.Unassigned(self._io, self, self._root)
            elif _on == Rtpc.Variant.uint32:
                self._m_offset_value = Rtpc.MU4(self._io, self, self._root)
            elif _on == Rtpc.Variant.float:
                self._m_offset_value = Rtpc.MF4(self._io, self, self._root)
            elif _on == Rtpc.Variant.byte_array:
                self._m_offset_value = Rtpc.ByteArray(self._io, self, self._root)
            elif _on == Rtpc.Variant.matrix_3x3:
                self._m_offset_value = Rtpc.F4ArrayParam(9, self._io, self, self._root)
            elif _on == Rtpc.Variant.total:
                self._m_offset_value = Rtpc.Unassigned(self._io, self, self._root)
            elif _on == Rtpc.Variant.float_array:
                self._m_offset_value = Rtpc.F4Array(self._io, self, self._root)
            elif _on == Rtpc.Variant.vec2:
                self._m_offset_value = Rtpc.F4ArrayParam(2, self._io, self, self._root)
            elif _on == Rtpc.Variant.object_id:
                self._m_offset_value = Rtpc.ObjectId(self._io, self, self._root)
            elif _on == Rtpc.Variant.unassigned:
                self._m_offset_value = Rtpc.Unassigned(self._io, self, self._root)
            elif _on == Rtpc.Variant.event:
                self._m_offset_value = Rtpc.Event(self._io, self, self._root)
            else:
                self._m_offset_value = Rtpc.Unassigned(self._io, self, self._root)
            self._io.seek(_pos)
            return getattr(self, '_m_offset_value', None)


    class Event(KaitaiStruct):
        def __init__(self, _io, _parent=None, _root=None):
            self._io = _io
            self._parent = _parent
            self._root = _root if _root else self
            self._read()

        def _read(self):
            self.count = self._io.read_u4le()
            self.pair = []
            for i in range(self.count):
                self.pair.append(Rtpc.U32ArrayParam(2, self._io, self, self._root))



    class Unassigned(KaitaiStruct):
        def __init__(self, _io, _parent=None, _root=None):
            self._io = _io
            self._parent = _parent
            self._root = _root if _root else self
            self._read()

        def _read(self):
            pass


    class Container(KaitaiStruct):
        def __init__(self, _io, _parent=None, _root=None):
            self._io = _io
            self._parent = _parent
            self._root = _root if _root else self
            self._read()

        def _read(self):
            self.name_hash = self._io.read_u4le()
            self.offset = self._io.read_u4le()
            self.property_count = self._io.read_u2le()
            self.container_count = self._io.read_u2le()

        @property
        def body(self):
            if hasattr(self, '_m_body'):
                return self._m_body

            _pos = self._io.pos()
            self._io.seek(self.offset)
            self._m_body = Rtpc.ContainerBody(self.property_count, self.container_count, self._io, self, self._root)
            self._io.seek(_pos)
            return getattr(self, '_m_body', None)


    class String(KaitaiStruct):
        def __init__(self, _io, _parent=None, _root=None):
            self._io = _io
            self._parent = _parent
            self._root = _root if _root else self
            self._read()

        def _read(self):
            self.value = (self._io.read_bytes_term(0, False, True, True)).decode("UTF-8")


    class ByteArray(KaitaiStruct):
        def __init__(self, _io, _parent=None, _root=None):
            self._io = _io
            self._parent = _parent
            self._root = _root if _root else self
            self._read()

        def _read(self):
            self.count = self._io.read_u4le()
            self.values = self._io.read_bytes(self.count)


    class F4ArrayParam(KaitaiStruct):
        def __init__(self, count, _io, _parent=None, _root=None):
            self._io = _io
            self._parent = _parent
            self._root = _root if _root else self
            self.count = count
            self._read()

        def _read(self):
            self.values = []
            for i in range(self.count):
                self.values.append(self._io.read_f4le())



    class MU4(KaitaiStruct):
        def __init__(self, _io, _parent=None, _root=None):
            self._io = _io
            self._parent = _parent
            self._root = _root if _root else self
            self._read()

        def _read(self):
            pass


    class U4Array(KaitaiStruct):
        def __init__(self, _io, _parent=None, _root=None):
            self._io = _io
            self._parent = _parent
            self._root = _root if _root else self
            self._read()

        def _read(self):
            self.count = self._io.read_u4le()
            self.values = []
            for i in range(self.count):
                self.values.append(self._io.read_u4le())



    class MF4(KaitaiStruct):
        def __init__(self, _io, _parent=None, _root=None):
            self._io = _io
            self._parent = _parent
            self._root = _root if _root else self
            self._read()

        def _read(self):
            pass


    class U32ArrayParam(KaitaiStruct):
        def __init__(self, count, _io, _parent=None, _root=None):
            self._io = _io
            self._parent = _parent
            self._root = _root if _root else self
            self.count = count
            self._read()

        def _read(self):
            self.values = []
            for i in range(self.count):
                self.values.append(self._io.read_u4le())



    class RtpcHeader(KaitaiStruct):
        def __init__(self, _io, _parent=None, _root=None):
            self._io = _io
            self._parent = _parent
            self._root = _root if _root else self
            self._read()

        def _read(self):
            self.magic = self._io.read_bytes(4)
            if not self.magic == b"\x52\x54\x50\x43":
                raise kaitaistruct.ValidationNotEqualError(b"\x52\x54\x50\x43", self.magic, self._io, u"/types/rtpc_header/seq/0")
            self.version = self._io.read_u4le()


    class ObjectId(KaitaiStruct):
        def __init__(self, _io, _parent=None, _root=None):
            self._io = _io
            self._parent = _parent
            self._root = _root if _root else self
            self._read()

        def _read(self):
            self.oid = self._io.read_u8le()

        @property
        def user_data(self):
            """May need to reverse oid before & 255."""
            if hasattr(self, '_m_user_data'):
                return self._m_user_data

            self._m_user_data = (self.oid & 255)
            return getattr(self, '_m_user_data', None)



