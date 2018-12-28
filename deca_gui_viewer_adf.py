from deca_gui_viewer import *
from deca.file import ArchiveFile
from deca.ff_adf import load_adf
from PySide2.QtWidgets import QSizePolicy,  QVBoxLayout, QTextEdit


class DataViewerAdf(DataViewer):
    def __init__(self):
        DataViewer.__init__(self)

        self.text_box = QTextEdit()
        size = QSizePolicy(QSizePolicy.Preferred, QSizePolicy.Preferred)
        self.text_box.setSizePolicy(size)

        self.main_layout = QVBoxLayout()
        self.main_layout.addWidget(self.text_box)
        self.setLayout(self.main_layout)

    def vnode_process(self, vfs: VfsStructure, vnode: VfsNode):
        with ArchiveFile(vfs.file_obj_from(vnode)) as f:
            buffer = f.read(vnode.size_u)
        obj = load_adf(buffer)
        sbuf = ''
        if obj is not None:
            sbuf = obj.dump_to_string()
        self.text_box.setText(sbuf)


