from PySide2.QtCore import Signal
from PySide2.QtWidgets import QWidget
from deca.db_view import VfsView


class IVfsViewSrc(QWidget):
    signal_visible_changed = Signal(VfsView)
    signal_selection_changed = Signal(VfsView)

    def vfs_get(self):
        return None

    def vfs_view_get(self):
        return None

    def archive_open(self, selection):
        pass
