from deca_gui_viewer import *
from deca.ff_sarc import FileSarc
from PySide2.QtWidgets import QSizePolicy,  QVBoxLayout, QTextEdit


class DataViewerSarc(DataViewer):
    def __init__(self):
        DataViewer.__init__(self)

        self.text_box = QTextEdit()
        size = QSizePolicy(QSizePolicy.Preferred, QSizePolicy.Preferred)
        self.text_box.setSizePolicy(size)

        self.main_layout = QVBoxLayout()
        self.main_layout.addWidget(self.text_box)
        self.setLayout(self.main_layout)

    def vnode_process(self, vfs: VfsStructure, vnode: VfsNode):
        sarc_file = FileSarc()
        sarc_file.deserialize(vfs.file_obj_from(vnode))
        sbuf = sarc_file.dump_str()
        self.text_box.setText(sbuf)


