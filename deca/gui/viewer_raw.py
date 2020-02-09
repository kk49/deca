from .viewer import *
from PySide2.QtWidgets import QSizePolicy, QVBoxLayout, QTextEdit
from PySide2.QtGui import QFont


class DataViewerRaw(DataViewer):
    def __init__(self):
        DataViewer.__init__(self)

        self.text_box = QTextEdit()
        self.text_box.setReadOnly(True)
        font = QFont("Courier", 8)
        self.text_box.setFont(font)
        self.text_box.setLineWrapMode(QTextEdit.LineWrapMode.NoWrap)

        size = QSizePolicy(QSizePolicy.Preferred, QSizePolicy.Preferred)
        self.text_box.setSizePolicy(size)

        self.main_layout = QVBoxLayout()
        self.main_layout.addWidget(self.text_box)
        self.setLayout(self.main_layout)

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

        ss = ''
        ss += header0 + '\n'
        ss += header1 + '\n'
        n = len(buf)
        max_pos = min(n, 1024 * line_len)
        for i in range(0, max_pos, line_len):
            ep = min(n, i + line_len)
            lb = buf[i:ep]

            lbc = [clean(v) for v in lb]

            ls = ' '.join(['{:02X}'.format(v) for v in lb])
            if line_len > len(lb):
                ls += ' ' + ' '.join(['  ' for i in range(line_len - len(lb))])
            ls += ' | '
            ls += ''.join(lbc)

            ss += ls + '\n'

        self.text_box.setText(ss)
