from .viewer import *
from PySide2.QtWidgets import QSizePolicy,  QVBoxLayout, QTextEdit
from PySide2.QtGui import QFont


class DataViewerInfo(DataViewer):
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

    def _dump_ancestors(self, vfs, vhash, indent=0):
        sbuf = ''
        # if vhash is not None:
        #     vpaths = list(vfs.map_hash_to_vpath[vhash])
        #     vnodes = vfs.map_vpath_to_vfsnodes[vpaths[0]]
        #     for vnode in vnodes:
        #         sbuf += '\n' + '  ' * indent
        #         sbuf += '0x{:08x}: "{}" "{}"'.format(vhash, vnode.vpath, vnode.pvpath)
        #         sbuf += self._dump_ancestors(vfs, vfs.table_vfsnode[vnode.pid].vhash, indent + 1)
        return sbuf

    def vnode_process(self, vfs: VfsProcessor, vnode: VfsNode):
        sbuf = self._dump_ancestors(vfs, vnode.vhash, 0)

        self.text_box.setText(sbuf)
