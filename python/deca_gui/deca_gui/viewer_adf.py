from .viewer import *
from deca.ff_adf import EDecaMissingAdfType, AdfDatabase
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

    def vnode_process(self, vfs: VfsProcessor, vnode: VfsNode):
        adf_db = AdfDatabase(vfs)

        try:
            obj = adf_db.read_node(vfs, vnode)
            sbuf = obj.dump_to_string(vfs)
        except EDecaMissingAdfType as e:
            sbuf = 'Missing ADF_TYPE {:08x} in parsing of type {:08x}'.format(e.type_id, vnode.file_sub_type)

        self.text_box.setText(sbuf)


