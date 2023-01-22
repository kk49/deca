from .viewer import *
from .viewer_text import DataViewerText
from deca.ff_obc import Obc
from PySide2.QtWidgets import QSizePolicy,  QVBoxLayout, QTextEdit
from PySide2.QtGui import QFont


class DataViewerObc(DataViewerText):
    def __init__(self):
        super().__init__()

    def vnode_process(self, vfs: VfsProcessor, vnode: VfsNode):
        obc = Obc()
        with vfs.file_obj_from(vnode) as f:
            obc.deserialize(f)
        sbuf = obc.dump_to_string(vfs)

        self.content_set(sbuf)
