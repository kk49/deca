from .viewer import *
from ..ff_sarc import FileSarc
from PySide2.QtCore import Signal
from PySide2.QtWidgets import QSizePolicy,  QVBoxLayout, QTextEdit, QPushButton, QHBoxLayout
from PySide2.QtGui import QFont


class DataViewerSarc(DataViewer):
    signal_archive_open = Signal(VfsNode)

    def __init__(self):
        DataViewer.__init__(self)

        self.vnode = None

        self.text_box = QTextEdit()
        self.text_box.setReadOnly(True)
        font = QFont("Courier", 8)
        self.text_box.setFont(font)
        self.text_box.setLineWrapMode(QTextEdit.LineWrapMode.NoWrap)
        size = QSizePolicy(QSizePolicy.Preferred, QSizePolicy.Preferred)
        self.text_box.setSizePolicy(size)

        self.bttn_open_archive = QPushButton()
        self.bttn_open_archive.setObjectName('bttn_open_archive')
        self.bttn_open_archive.setText('Open Archive')
        self.bttn_open_archive.clicked.connect(self.open_archive)

        self.cmd_layout = QHBoxLayout()
        self.cmd_layout.addWidget(self.bttn_open_archive)

        self.main_layout = QVBoxLayout()
        self.main_layout.addLayout(self.cmd_layout)
        self.main_layout.addWidget(self.text_box)
        self.setLayout(self.main_layout)

    def vnode_process(self, vfs: VfsProcessor, vnode: VfsNode):
        self.vnode = vnode

        sarc_file = FileSarc()
        sarc_file.header_deserialize(vfs.file_obj_from(vnode))
        sbuf = sarc_file.dump_str()
        self.text_box.setText(sbuf)

    def open_archive(self):
        self.signal_archive_open.emit(self.vnode)
