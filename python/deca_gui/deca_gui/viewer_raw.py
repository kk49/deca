from .viewer import *
from .viewer_text import DataViewerText

MAX_DISPLAY_LINES = 1024 * 1024


class DataViewerRaw(DataViewerText):
    def __init__(self):
        super().__init__()

    def vnode_process(self, vfs: VfsProcessor, vnode: VfsNode):
        with vfs.file_obj_from(vnode) as f:
            buf = f.read(vnode.size_u)

        line_len = 16

        header0 = ' '.join(['{:02x}'.format(i) for i in range(line_len)])
        header1 = '-'.join(['--' for i in range(line_len)])

        def clean(v):
            if 0x20 <= v <= 0x7f:
                return chr(v)
            else:
                return '░'

        ss = [
            header0,
            header1
        ]

        n = len(buf)
        for i in range(0, n, line_len):
            if i >= MAX_DISPLAY_LINES:
                break

            ep = min(n, i + line_len)
            lb = buf[i:ep]

            lbc = [clean(v) for v in lb]

            ls = ' '.join(['{:02X}'.format(v) for v in lb])
            if line_len > len(lb):
                ls += ' ' + ' '.join(['  ' for i in range(line_len - len(lb))])
            ls += ' | '
            ls += ''.join(lbc)

            ss.append(ls)

        self.content_set(ss)
