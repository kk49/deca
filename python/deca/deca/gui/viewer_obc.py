from .viewer import *
from ..ff_obc import Obc
from PySide2.QtWidgets import QSizePolicy,  QVBoxLayout, QTextEdit
from PySide2.QtGui import QFont


class DataViewerObc(DataViewer):
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
        obc = Obc()
        with vfs.file_obj_from(vnode) as f:
            obc.deserialize(f)
        sbuf = obc.dump_to_string(vfs)
        self.text_box.setText(sbuf)
