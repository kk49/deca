from .viewer import *
from ..ff_types import FTYPE_ADF_BARE, FTYPE_ADF
from ..file import ArchiveFile
from ..ff_adf import load_adf, load_adf_bare
from PySide2.QtWidgets import QSizePolicy,  QVBoxLayout, QTextEdit
from PySide2.QtGui import QFont


class DataViewerAdf(DataViewer):
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

    def vnode_process(self, vfs: VfsStructure, vnode: VfsNode):
        buffer = b''
        with ArchiveFile(vfs.file_obj_from(vnode)) as f:
            while True:
                v = f.read(16*1024*1024)
                if len(v) == 0:
                    break
                buffer = buffer + v

        sbuf = ''
        if vnode.ftype == FTYPE_ADF_BARE:
            obj = load_adf_bare(buffer, vnode.adf_type, vnode.offset, vnode.size_u, vfs.map_adftypes)
            if obj is None:
                sbuf = 'ADF_BARE: Missing ADF_TYPE {:08x}'.format(vnode.adf_type)
            else:
                sbuf = obj.dump_to_string()
        else:
            obj = load_adf(buffer)
            if obj is not None:
                sbuf = obj.dump_to_string()
        self.text_box.setText(sbuf)


