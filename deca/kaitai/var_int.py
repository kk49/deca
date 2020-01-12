# This is a generated file! Please edit source .ksy file and use kaitai-struct-compiler to rebuild

from pkg_resources import parse_version
from kaitaistruct import __version__ as ks_version, KaitaiStruct, KaitaiStream, BytesIO


if parse_version(ks_version) < parse_version('0.7'):
    raise Exception("Incompatible Kaitai Struct Python API: 0.7 or later is required, but you have %s" % (ks_version))

class VarInt(KaitaiStruct):
    """LIMITATIONS:
      Max number of bits is 32
    SWF has can have integers of variable bit lengths determined at runtime. This provides support for that
    """
    def __init__(self, raw, num_bits, is_signed, is_le, _io, _parent=None, _root=None):
        self._io = _io
        self._parent = _parent
        self._root = _root if _root else self
        self.raw = raw
        self.num_bits = num_bits
        self.is_signed = is_signed
        self.is_le = is_le
        self._read()

    def _read(self):
        self.raw = [None] * (self.num_bits)
        for i in range(self.num_bits):
            self.raw[i] = self._io.read_bits_int(1) != 0


    @property
    def value(self):
        if hasattr(self, '_m_value'):
            return self._m_value if hasattr(self, '_m_value') else None

        self._m_value = (((((((((((((((((((((((((((((((((((1 if  ((self.num_bits > 0) and (self.raw[0]))  else 0) << 0) | ((1 if  ((self.num_bits > 1) and (self.raw[1]))  else 0) << 1)) | ((1 if  ((self.num_bits > 2) and (self.raw[2]))  else 0) << 2)) | ((1 if  ((self.num_bits > 3) and (self.raw[3]))  else 0) << 3)) | ((1 if  ((self.num_bits > 4) and (self.raw[4]))  else 0) << 4)) | ((1 if  ((self.num_bits > 5) and (self.raw[5]))  else 0) << 5)) | ((1 if  ((self.num_bits > 6) and (self.raw[6]))  else 0) << 6)) | ((1 if  ((self.num_bits > 7) and (self.raw[7]))  else 0) << 7)) | ((1 if  ((self.num_bits > 8) and (self.raw[8]))  else 0) << 8)) | ((1 if  ((self.num_bits > 9) and (self.raw[9]))  else 0) << 9)) | ((1 if  ((self.num_bits > 10) and (self.raw[10]))  else 0) << 10)) | ((1 if  ((self.num_bits > 11) and (self.raw[11]))  else 0) << 11)) | ((1 if  ((self.num_bits > 12) and (self.raw[12]))  else 0) << 12)) | ((1 if  ((self.num_bits > 13) and (self.raw[13]))  else 0) << 13)) | ((1 if  ((self.num_bits > 14) and (self.raw[14]))  else 0) << 14)) | ((1 if  ((self.num_bits > 15) and (self.raw[15]))  else 0) << 15)) | ((1 if  ((self.num_bits > 16) and (self.raw[16]))  else 0) << 16)) | ((1 if  ((self.num_bits > 17) and (self.raw[17]))  else 0) << 17)) | ((1 if  ((self.num_bits > 18) and (self.raw[18]))  else 0) << 18)) | ((1 if  ((self.num_bits > 19) and (self.raw[19]))  else 0) << 19)) | ((1 if  ((self.num_bits > 20) and (self.raw[20]))  else 0) << 20)) | ((1 if  ((self.num_bits > 21) and (self.raw[21]))  else 0) << 21)) | ((1 if  ((self.num_bits > 22) and (self.raw[22]))  else 0) << 22)) | ((1 if  ((self.num_bits > 23) and (self.raw[23]))  else 0) << 23)) | ((1 if  ((self.num_bits > 24) and (self.raw[24]))  else 0) << 24)) | ((1 if  ((self.num_bits > 25) and (self.raw[25]))  else 0) << 25)) | ((1 if  ((self.num_bits > 26) and (self.raw[26]))  else 0) << 26)) | ((1 if  ((self.num_bits > 27) and (self.raw[27]))  else 0) << 27)) | ((1 if  ((self.num_bits > 28) and (self.raw[28]))  else 0) << 28)) | ((1 if  ((self.num_bits > 29) and (self.raw[29]))  else 0) << 29)) | ((1 if  ((self.num_bits > 30) and (self.raw[30]))  else 0) << 30)) | ((1 if  ((self.num_bits > 31) and (self.raw[31]))  else 0) << 31)) | ((-1 << self.num_bits) if  ((self.is_signed) and (self.raw[((self.num_bits - 1) if self.is_le else 0)]))  else 0)) if self.is_le else ((((((((((((((((((((((((((((((((((1 if  ((self.num_bits > 0) and (self.raw[0]))  else 0) << ((self.num_bits - 1) - 0)) | ((1 if  ((self.num_bits > 1) and (self.raw[1]))  else 0) << ((self.num_bits - 1) - 1))) | ((1 if  ((self.num_bits > 2) and (self.raw[2]))  else 0) << ((self.num_bits - 1) - 2))) | ((1 if  ((self.num_bits > 3) and (self.raw[3]))  else 0) << ((self.num_bits - 1) - 3))) | ((1 if  ((self.num_bits > 4) and (self.raw[4]))  else 0) << ((self.num_bits - 1) - 4))) | ((1 if  ((self.num_bits > 5) and (self.raw[5]))  else 0) << ((self.num_bits - 1) - 5))) | ((1 if  ((self.num_bits > 6) and (self.raw[6]))  else 0) << ((self.num_bits - 1) - 6))) | ((1 if  ((self.num_bits > 7) and (self.raw[7]))  else 0) << ((self.num_bits - 1) - 7))) | ((1 if  ((self.num_bits > 8) and (self.raw[8]))  else 0) << ((self.num_bits - 1) - 8))) | ((1 if  ((self.num_bits > 9) and (self.raw[9]))  else 0) << ((self.num_bits - 1) - 9))) | ((1 if  ((self.num_bits > 10) and (self.raw[10]))  else 0) << ((self.num_bits - 1) - 10))) | ((1 if  ((self.num_bits > 11) and (self.raw[11]))  else 0) << ((self.num_bits - 1) - 11))) | ((1 if  ((self.num_bits > 12) and (self.raw[12]))  else 0) << ((self.num_bits - 1) - 12))) | ((1 if  ((self.num_bits > 13) and (self.raw[13]))  else 0) << ((self.num_bits - 1) - 13))) | ((1 if  ((self.num_bits > 14) and (self.raw[14]))  else 0) << ((self.num_bits - 1) - 14))) | ((1 if  ((self.num_bits > 15) and (self.raw[15]))  else 0) << ((self.num_bits - 1) - 15))) | ((1 if  ((self.num_bits > 16) and (self.raw[16]))  else 0) << ((self.num_bits - 1) - 16))) | ((1 if  ((self.num_bits > 17) and (self.raw[17]))  else 0) << ((self.num_bits - 1) - 17))) | ((1 if  ((self.num_bits > 18) and (self.raw[18]))  else 0) << ((self.num_bits - 1) - 18))) | ((1 if  ((self.num_bits > 19) and (self.raw[19]))  else 0) << ((self.num_bits - 1) - 19))) | ((1 if  ((self.num_bits > 20) and (self.raw[20]))  else 0) << ((self.num_bits - 1) - 20))) | ((1 if  ((self.num_bits > 21) and (self.raw[21]))  else 0) << ((self.num_bits - 1) - 21))) | ((1 if  ((self.num_bits > 22) and (self.raw[22]))  else 0) << ((self.num_bits - 1) - 22))) | ((1 if  ((self.num_bits > 23) and (self.raw[23]))  else 0) << ((self.num_bits - 1) - 23))) | ((1 if  ((self.num_bits > 24) and (self.raw[24]))  else 0) << ((self.num_bits - 1) - 24))) | ((1 if  ((self.num_bits > 25) and (self.raw[25]))  else 0) << ((self.num_bits - 1) - 25))) | ((1 if  ((self.num_bits > 26) and (self.raw[26]))  else 0) << ((self.num_bits - 1) - 26))) | ((1 if  ((self.num_bits > 27) and (self.raw[27]))  else 0) << ((self.num_bits - 1) - 27))) | ((1 if  ((self.num_bits > 28) and (self.raw[28]))  else 0) << ((self.num_bits - 1) - 28))) | ((1 if  ((self.num_bits > 29) and (self.raw[29]))  else 0) << ((self.num_bits - 1) - 29))) | ((1 if  ((self.num_bits > 30) and (self.raw[30]))  else 0) << ((self.num_bits - 1) - 30))) | ((1 if  ((self.num_bits > 31) and (self.raw[31]))  else 0) << ((self.num_bits - 1) - 31))) | ((-1 << self.num_bits) if  ((self.is_signed) and (self.raw[((self.num_bits - 1) if self.is_le else 0)]))  else 0)))
        return self._m_value if hasattr(self, '_m_value') else None


