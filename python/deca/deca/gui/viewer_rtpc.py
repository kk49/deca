from .viewer import *
from ..ff_rtpc import RtpcVisitorDumpToString
from PySide2.QtWidgets import QSizePolicy,  QVBoxLayout, QTextEdit
from PySide2.QtGui import QFont


class DataViewerRtpc(DataViewer):
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
            buffer = f.read(vnode.size_u)
        dump = RtpcVisitorDumpToString(vfs)
        dump.visit(buffer)
        sbuf = dump.result()
        self.text_box.setText(sbuf)
