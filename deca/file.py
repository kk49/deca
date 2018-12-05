import struct


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

    def read_u16(self, n=None):
        return self.read_base('H', 2, n)

    def read_u32(self, n=None):
        return self.read_base('I', 4, n)
