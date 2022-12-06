import datetime
import os
import struct
import weakref
import sys


class Logger:
    def __init__(self, working_dir):
        self.working_dir = working_dir

    def log_base(self, level, s):
        msg = '{}: {}'.format(datetime.datetime.now(), s)
        if self.working_dir is not None:
            with open(self.working_dir + 'log.txt', 'a') as f:
                f.write(msg + '\n')
                if level <= 2:
                    print(msg)

        return msg

    def error(self, s):
        self.log_base(0, s)

    def warning(self, s):
        self.log_base(1, s)

    def log(self, s):
        self.log_base(2, s)

    def trace(self, s):
        self.log_base(3, s)

    def debug(self, s):
        self.log_base(3, s)


class DecaSignal:
    def __init__(self):
        self.callbacks = set()

    def connect(self, obj, func):
        self.callbacks.add((weakref.ref(obj), func))

    def disconnect(self, obj):
        to_erase = []
        for i in self.callbacks:
            if i[0]() == obj:
                to_erase.append(i)

        for i in to_erase:
            self.callbacks.remove(i)

    def call(self, *params, **kwargs):
        to_erase = []
        callbacks = self.callbacks.copy()
        for i in callbacks:
            obj = i[0]()
            func = i[1]
            if obj is not None:
                func(obj, *params, **kwargs)
            else:
                to_erase.append(i)

        for i in to_erase:
            self.callbacks.remove(i)


def dump_line(line, width, fmt='hex'):
    if fmt == 'hex' or len(line) != width:
        line = ''.join(['{:02x}'.format(v) for v in bytearray(line)])
    elif fmt == 'char':
        line = ['{}'.format(chr(v)) for v in bytearray(line)]
    else:
        line = struct.unpack(fmt, line)
    return '{}'.format(line)


def dump_block(blk, width, fmt='hex'):
    for i in range((len(blk) + width - 1) // width):
        line = blk[(i * width):((i + 1) * width)]
        line = dump_line(line, width, fmt)
        print(line)


def remove_prefix_if_present(prefix, s):
    if s.find(prefix) == 0:
        return s[len(prefix):]
    else:
        return None


def remove_suffix_if_present(suffix, s):
    if s.endswith(suffix):
        return s[:-len(suffix)]
    else:
        return None


def common_prefix(s0, s1):
    cnt = 0
    while len(s0) > cnt and len(s1) > cnt and s0[cnt] == s1[cnt]:
        cnt += 1
    return s0[:cnt], s0[cnt:], s1[cnt:]


def align_to(v, boundry):
    return ((v + boundry - 1) // boundry) * boundry


def make_dir_for_file(fn):
    new_dir = os.path.dirname(fn)
    os.makedirs(new_dir, exist_ok=True)
    return new_dir


def to_unicode(s):
    if isinstance(s, bytes):
        s = s.decode('utf-8')

    return s


def deca_root():
    frozen = getattr(sys, 'frozen', False)
    if frozen and hasattr(sys, '_MEIPASS'):
        # print('running in a PyInstaller bundle')
        bundle_dir = sys._MEIPASS
    else:
        # print('running in a normal Python process')
        bundle_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..', '..'))

    # print(f"{__file__=}")
    # print(f"{bundle_dir=}")
    # print(f"{sys.argv[0]=}")
    # print(f"{sys.executable=}")
    # print(f"{os.getcwd()=}")
    # print(f"{frozen=}")

    return bundle_dir

