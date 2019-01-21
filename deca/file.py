import struct


class SubsetFile:
    def __init__(self, f, size):
        self.f = f
        self.f0 = f
        self.bpos = f.tell()
        self.epos = self.bpos + size

    def __enter__(self):
        self.f = self.f0.__enter__()
        return self

    def __exit__(self, t, value, traceback):
        self.f0.__exit__(t, value, traceback)

    def seek(self, pos):
        npos = self.bpos + pos
        if npos > self.epos:
            raise Exception('Seek Beyond End Of File')
        return self.f.seek(npos)

    def tell(self):
        return self.f.tell() - self.bpos

    def read(self, n):
        bpos = self.f.tell()
        epos = bpos + n
        epos = min(epos, self.epos)
        return self.f.read(epos - bpos)

    def write(self, blk):
        bpos = self.f.tell()
        epos = bpos + len(blk)
        if epos > self.epos:
            raise Exception('Write Beyond End Of File')
        return self.f.write(blk)


class ArchiveFile:
    def __init__(self, f, debug=False, endian=None):
        self.f0 = f
        self.f = f
        self.debug = debug

    def __enter__(self):
        self.f = self.f0.__enter__()
        return self

    def __exit__(self, t, value, traceback):
        self.f0.__exit__(t, value, traceback)

    def seek(self, pos):
        return self.f.seek(pos)

    def tell(self):
        return self.f.tell()

    def read(self, n):
        return self.f.read(n)

    def write(self, blk):
        return self.f.write(blk)

    def read_strz(self, delim=b'\00'):
        r = b''
        while True:
            v = self.f.read(1)
            if len(v) == 0:
                break
            elif v == delim:
                break
            else:
                r = r + v
        return r

    def read_base(self, fmt, elen, n):
        if n is None:
            buf = self.f.read(elen)
            if len(buf) != elen:
                return None
            v = struct.unpack(fmt, buf)[0]
        else:
            buf = self.f.read(elen * n)
            if len(buf) != elen * n:
                return None
            v = struct.unpack(fmt * n, buf)

        if self.debug:
            vs = ['{:02x}'.format(t) for t in buf]
            vs = ''.join(vs)
            print('{} {}'.format(vs, v))

        return v

    def read_c8(self, n=None):
        return self.read_base('c', 1, n)

    def read_strl_u32(self, n=None):
        if n is None:
            sz = self.read_u32()
            return self.read_strl(sz)
        else:
            sl = []
            for i in range(n):
                sl.append(self.read_strl_u32())
            return sl

    def read_strl(self, n=None):
        v = self.read_base('c', 1, n)
        return b''.join(v)

    def read_s8(self, n=None):
        return self.read_base('b', 1, n)

    def read_u8(self, n=None):
        return self.read_base('B', 1, n)

    def read_s16(self, n=None):
        return self.read_base('h', 2, n)

    def read_u16(self, n=None):
        return self.read_base('H', 2, n)

    def read_s32(self, n=None):
        return self.read_base('i', 4, n)

    def read_u32(self, n=None):
        return self.read_base('I', 4, n)

    def read_s64(self, n=None):
        return self.read_base('q', 8, n)

    def read_u64(self, n=None):
        return self.read_base('Q', 8, n)

    def read_f32(self, n=None):
        return self.read_base('f', 4, n)

    def read_f64(self, n=None):
        return self.read_base('d', 8, n)

    def write_base(self, fmt, elen, v):
        if isinstance(v, list) or isinstance(v, tuple):
            buf = struct.pack(fmt * len(v), *v)
            self.f.write(buf)
        else:
            buf = struct.pack(fmt, v)
            self.f.write(buf)

        if self.debug:
            vs = ['{:02x}'.format(t) for t in buf]
            vs = ''.join(vs)
            print('{} {}'.format(vs, v))

        return None

    def write_c8(self, v):
        return self.write_base('c', 1, v)

    def write_strl(self, v):
        return self.write_base('c', 1, v)

    def write_s8(self, v):
        return self.write_base('b', 1, v)

    def write_u8(self, v):
        return self.write_base('B', 1, v)

    def write_s16(self, v):
        return self.write_base('h', 2, v)

    def write_u16(self, v):
        return self.write_base('H', 2, v)

    def write_s32(self, v):
        return self.write_base('i', 4, v)

    def write_u32(self, v):
        return self.write_base('I', 4, v)

    def write_s64(self, v):
        return self.write_base('q', 8, v)

    def write_u64(self, v):
        return self.write_base('Q', 8, v)

    def write_f32(self, v):
        return self.write_base('f', 4, v)

    def write_f64(self, v):
        return self.write_base('d', 8, v)
