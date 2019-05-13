from deca.vfs_db import VfsNode, VfsStructure
from PySide2.QtWidgets import QWidget


class DataViewer(QWidget):
    def __init__(self):
        QWidget.__init__(self)

    def vnode_process(self, vfs: VfsStructure, vnode: VfsNode):
        pass
