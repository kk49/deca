# This is a generated file! Please edit source .ksy file and use kaitai-struct-compiler to rebuild

from pkg_resources import parse_version
from kaitaistruct import __version__ as ks_version, KaitaiStruct, KaitaiStream, BytesIO


if parse_version(ks_version) < parse_version('0.7'):
    raise Exception("Incompatible Kaitai Struct Python API: 0.7 or later is required, but you have %s" % (ks_version))

class WorldBin(KaitaiStruct):
    """File format for older world.bin in APEX engine games, at least Generation Zero
    and theHunter:COTW. It seems like it's a weird inline RTPC file
    """
    def __init__(self, _io, _parent=None, _root=None):
        self._io = _io
        self._parent = _parent
        self._root = _root if _root else self
        self._read()

    def _read(self):
        self.header_ver_0 = self._io.read_u1()
        self.header_ver_1 = self._io.read_u2le()
        self.object_count = self._io.read_u2le()
        self.objects = [None] * (self.object_count)
        for i in range(self.object_count):
            self.objects[i] = self._root.Object(self._io, self, self._root)


    class Object(KaitaiStruct):
        def __init__(self, _io, _parent=None, _root=None):
            self._io = _io
            self._parent = _parent
            self._root = _root if _root else self
            self._read()

        def _read(self):
            self.name = self._io.read_u4le()
            self.unk0 = self._io.read_u1()
            self.unk1 = self._io.read_u2le()
            self.count = self._io.read_u2le()
            self.members = [None] * (self.count)
            for i in range(self.count):
                self.members[i] = self._root.Element(self._io, self, self._root)



    class Element(KaitaiStruct):
        def __init__(self, _io, _parent=None, _root=None):
            self._io = _io
            self._parent = _parent
            self._root = _root if _root else self
            self._read()

        def _read(self):
            self.name = self._io.read_u4le()
            self.type_id = self._io.read_u1()
            if self.type_id == 1:
                self.data_u4 = self._io.read_u4le()

            if self.type_id == 2:
                self.data_f4 = self._io.read_f4le()

            if self.type_id == 3:
                self.data_strn = self._root.Strn(self._io, self, self._root)

            if self.type_id == 5:
                self.data_vec3 = [None] * (3)
                for i in range(3):
                    self.data_vec3[i] = self._io.read_f4le()


            if self.type_id == 8:
                self.data_mat3x4 = self._root.Mat3x4(self._io, self, self._root)

            if self.type_id == 14:
                self.data_events = self._root.Events(self._io, self, self._root)



    class Vec3(KaitaiStruct):
        def __init__(self, _io, _parent=None, _root=None):
            self._io = _io
            self._parent = _parent
            self._root = _root if _root else self
            self._read()

        def _read(self):
            self.x = self._io.read_f4le()
            self.y = self._io.read_f4le()
            self.z = self._io.read_f4le()


    class Strn(KaitaiStruct):
        def __init__(self, _io, _parent=None, _root=None):
            self._io = _io
            self._parent = _parent
            self._root = _root if _root else self
            self._read()

        def _read(self):
            self.len = self._io.read_u2le()
            self.data = (self._io.read_bytes(self.len)).decode(u"ascii")


    class Events(KaitaiStruct):
        def __init__(self, _io, _parent=None, _root=None):
            self._io = _io
            self._parent = _parent
            self._root = _root if _root else self
            self._read()

        def _read(self):
            self.len = self._io.read_u4le()
            self.data = [None] * (self.len)
            for i in range(self.len):
                self.data[i] = self._io.read_u8le()



    class Mat3x4(KaitaiStruct):
        def __init__(self, _io, _parent=None, _root=None):
            self._io = _io
            self._parent = _parent
            self._root = _root if _root else self
            self._read()

        def _read(self):
            self.mat3x3 = [None] * (9)
            for i in range(9):
                self.mat3x3[i] = self._io.read_f4le()

            self.vec3 = [None] * (3)
            for i in range(3):
                self.vec3[i] = self._io.read_f4le()




