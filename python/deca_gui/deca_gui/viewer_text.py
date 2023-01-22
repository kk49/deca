from .viewer import *
from deca.file import ArchiveFile
from PySide2.QtCore import QStringListModel
from PySide2.QtGui import QFont, QKeyEvent, QKeySequence, QGuiApplication
from PySide2.QtWidgets import QSizePolicy, QVBoxLayout, QListView, QAbstractItemView
import io


class DecaListView(QListView):
    def keyPressEvent(self, event: QKeyEvent) -> None:
        if event.matches(QKeySequence.Copy):
            idxs = self.selectedIndexes()
            ss = ""
            for idx in idxs:
                s = self.model().data(idx)
                ss += s + "\n"

            QGuiApplication.clipboard().setText(ss)
        else:
            return super().keyPressEvent(event)


class DataViewerText(DataViewer):
    def __init__(self):
        super().__init__()

        self.list_view = DecaListView()
        self.list_view.setViewMode(QListView.ViewMode.ListMode)
        self.list_view.setEditTriggers(QAbstractItemView.NoEditTriggers)
        self.list_view.setSelectionMode(QAbstractItemView.ExtendedSelection)

        font = QFont("Courier", 8)
        self.list_view.setFont(font)

        size = QSizePolicy(QSizePolicy.Preferred, QSizePolicy.Preferred)
        self.list_view.setSizePolicy(size)

        self.main_layout = QVBoxLayout()
        self.main_layout.addWidget(self.list_view)
        self.setLayout(self.main_layout)

    def content_set(self, s):
        if isinstance(s, str):
            with io.StringIO(s) as f:
                ss = f.readlines()
        else:
            ss = s

        ss = [s.rstrip() for s in ss]

        model = QStringListModel(ss)

        self.list_view.setModel(model)

    def vnode_process(self, vfs: VfsProcessor, vnode: VfsNode):
        with ArchiveFile(vfs.file_obj_from(vnode)) as f:
            buf = f.read(vnode.size_u)

        self.content_set(buf.decode('utf-8'))
