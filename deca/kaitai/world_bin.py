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
        self.header_count = self._io.read_u2le()
        self.elements = []
        i = 0
        while not self._io.is_eof():
            self.elements.append(self._root.Element(self._io, self, self._root))
            i += 1


    class Mat12(KaitaiStruct):
        def __init__(self, _io, _parent=None, _root=None):
            self._io = _io
            self._parent = _parent
            self._root = _root if _root else self
            self._read()

        def _read(self):
            self.mat = [None] * (12)
            for i in range(12):
                self.mat[i] = self._io.read_f4le()



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
                self.data_01 = self._io.read_u4le()

            if self.type_id == 2:
                self.data_02 = self._io.read_f4le()

            if self.type_id == 3:
                self.data_03 = self._root.Strn(self._io, self, self._root)

            if self.type_id == 5:
                self.data_05 = self._root.Vec3(self._io, self, self._root)

            if self.type_id == 8:
                self.data_08 = self._root.Mat12(self._io, self, self._root)

            if self.type_id == 14:
                self.data_0e = self._root.Events(self._io, self, self._root)

            if self.type_id == 248:
                self.data_f8 = self._root.Vec3(self._io, self, self._root)



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



    class Type3(KaitaiStruct):
        def __init__(self, _io, _parent=None, _root=None):
            self._io = _io
            self._parent = _parent
            self._root = _root if _root else self
            self._read()

        def _read(self):
            self.type_id = self._io.read_u1()
            self.len = self._io.read_u2le()
            self.val = (self._io.read_bytes(self.len)).decode(u"ascii")



