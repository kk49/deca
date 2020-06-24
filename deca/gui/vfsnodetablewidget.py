from typing import Optional
from deca.gui.vfs_widgets import used_color_calc
from deca.db_processor import VfsNode
from deca.db_view import VfsView
from deca.ff_types import *
import PySide2
from PySide2.QtCore import QAbstractTableModel, QModelIndex, Qt, Signal
from PySide2.QtGui import QColor
from PySide2.QtWidgets import QHeaderView, QSizePolicy, QTableView, QWidget, QHBoxLayout


class VfsNodeTableModel(QAbstractTableModel):
    vfs_changed_signal = Signal()

    def __init__(self, *args, **kwargs):
        QAbstractTableModel.__init__(self, *args, **kwargs)
        self.vfs_view: Optional[VfsView] = None
        self.show_all = True
        self.uid_table = None

        self.remap = None
        self.remap_uid = None
        self.remap_pid = None
        self.remap_type = None
        self.remap_hash = None
        self.column_ids = ["Index", "PIDX", "Type", "Sub Type", "Hash", "EXT_hash", "Size_U", "Size_C", "Path"]

        self.vfs_changed_signal.connect(self.update_model)

    def vfs_view_get(self):
        return self.vfs_view

    def vfs_view_set(self, vfs_view: VfsView):
        if self.vfs_view != vfs_view:
            if self.vfs_view is not None:
                self.vfs_view.signal_visible_changed.disconnect(self)
                self.vfs_view = None

            self.vfs_view = vfs_view
            self.vfs_view.signal_visible_changed.connect(self, lambda x: x.vfs_changed_signal.emit())
            self.vfs_changed_signal.emit()

    def update_model(self):
        self.beginResetModel()

        if self.show_all:
            self.uid_table = list(self.vfs_view.nodes_visible_uids_get())
        else:
            self.uid_table = list(self.vfs_view.nodes_visible_uids_no_vpath_get())
        self.uid_table.sort()

        self.endResetModel()

    def sort(self, column: int, order: PySide2.QtCore.Qt.SortOrder):
        # if self.remap_uid is None:
        #     rm = list(range(len(self.vfs_view.table_vfsnode)))
        #     self.remap_uid = rm
        #
        # if column == 0:  # IDX
        #     self.remap = self.remap_uid
        # elif column == 1:  # PIDX
        #     if self.remap_pid is None:
        #         rm = list(range(len(self.vfs_view.table_vfsnode)))
        #         rm.sort(key=lambda v: self.vfs_view.table_vfsnode[v].pid)
        #         self.remap_pid = rm
        #     self.remap = self.remap_pid
        # elif column == 2:  # Type
        #     if self.remap_type is None:
        #         rm = list(range(len(self.vfs_view.table_vfsnode)))
        #         rm.sort(key=lambda v: self.vfs_view.table_vfsnode[v].file_type)
        #         self.remap_type = rm
        #     self.remap = self.remap_type
        # elif column == 3:  # Hash
        #     if self.remap_hash is None:
        #         rm = list(range(len(self.vfs_view.table_vfsnode)))
        #         rm.sort(key=lambda v: self.vfs_view.table_vfsnode[v].hashid)
        #         self.remap_hash = rm
        #     self.remap = self.remap_hash
        # else:
        #     self.remap = self.remap_uid
        #     print('Unhandled Sort {}'.format(self.column_ids[column]))
        #
        # if self.remap is not None:
        #     if order == Qt.AscendingOrder:
        #         pass
        #     else:
        #         self.remap = self.remap[::-1]
        pass

    def rowCount(self, parent=QModelIndex()):
        if self.uid_table is None:
            return 0
        else:
            return len(self.uid_table)

    def columnCount(self, parent=QModelIndex()):
        return 9

    def headerData(self, section, orientation, role):
        if role != Qt.DisplayRole:
            return None
        if orientation == Qt.Horizontal:
            return self.column_ids[section]
        else:
            return None

    def data(self, index, role=Qt.DisplayRole):
        column = index.column()
        row = index.row()

        if self.remap is not None:
            row = self.remap[row]

        if role == Qt.DisplayRole:
            uid = self.uid_table[row]
            node: VfsNode = self.vfs_view.node_where_uid(uid)
            if node is None:
                return 'NA'
            else:
                if column == 0:
                    return '{}'.format(node.uid)
                elif column == 1:
                    return '{}'.format(node.pid)
                elif column == 2:
                    return '{}'.format(node.file_type)
                elif column == 3:
                    if node.file_sub_type is None:
                        return ''
                    elif node.file_type in {FTYPE_ADF0, FTYPE_ADF, FTYPE_ADF_BARE}:
                        return '{:08x}'.format(node.file_sub_type)
                    else:
                        return '{}'.format(node.file_sub_type)
                elif column == 4:
                    return node.v_hash_to_str()
                elif column == 5:
                    if node.ext_hash is None:
                        return ''
                    else:
                        return '{:08X}'.format(node.ext_hash)
                elif column == 6:
                    return '{}'.format(node.size_u)
                elif column == 7:
                    return '{}'.format(node.size_c)
                elif column == 8:
                    if node.v_path is not None:
                        return 'V: {}'.format(node.v_path.decode('utf-8'))
                    elif node.p_path is not None:
                        return 'P: {}'.format(node.p_path)
                    else:
                        return ''

        elif role == Qt.BackgroundRole:
            uid = self.uid_table[row]
            node: VfsNode = self.vfs_view.node_where_uid(uid)
            if node.is_valid():
                if column == 8:
                    if node.used_at_runtime_depth is not None:
                        return used_color_calc(node.used_at_runtime_depth)
                    elif column == 3:
                        if node.file_sub_type is not None and \
                                node.file_type in {FTYPE_ADF0, FTYPE_ADF, FTYPE_ADF_BARE} and \
                                node.file_sub_type not in self.adf_db.type_map_def:
                            return QColor(Qt.red)

        elif role == Qt.TextAlignmentRole:
            if column == 8:
                return Qt.AlignLeft
            else:
                return Qt.AlignRight

        return None


class VfsNodeTableWidget(QWidget):
    def __init__(self, vfs_view, *args, **kwargs):
        QWidget.__init__(self, *args, **kwargs)

        self.vnode_2click_selected = None

        # Getting the Model
        self.model = VfsNodeTableModel()

        # Creating a QTableView
        self.table_view = QTableView()
        self.table_view.clicked.connect(self.clicked)
        self.table_view.doubleClicked.connect(self.double_clicked)
        font = self.table_view.font()
        font.setPointSize(8)
        self.table_view.setFont(font)
        # self.table_view.setSortingEnabled(True)
        self.table_view.setModel(self.model)

        # QTableView Headers
        self.horizontal_header = self.table_view.horizontalHeader()
        self.vertical_header = self.table_view.verticalHeader()
        self.horizontal_header.setSectionResizeMode(QHeaderView.Interactive)
        self.vertical_header.setSectionResizeMode(QHeaderView.Interactive)
        self.horizontal_header.setStretchLastSection(True)

        # QWidget Layout
        self.main_layout = QHBoxLayout()
        size = QSizePolicy(QSizePolicy.Preferred, QSizePolicy.Preferred)

        # Left layout
        size.setHorizontalStretch(1)
        self.table_view.setSizePolicy(size)
        self.main_layout.addWidget(self.table_view)

        # Set the layout to the QWidget
        self.setLayout(self.main_layout)

        self.model.vfs_view_set(vfs_view)

    def show_all_set(self, v):
        self.model.show_all = v

    def vfs_view_get(self):
        return self.model.vfs_view_get()

    def clicked(self, index):
        if index.isValid():
            if self.model.vfs_view is not None:
                items = list(set([self.model.uid_table[idx.row()] for idx in self.table_view.selectedIndexes()]))
                items = [self.model.vfs_view.node_where_uid(i) for i in items]
                self.model.vfs_view.paths_set(items)

    def double_clicked(self, index):
        if index.isValid():
            if self.vnode_2click_selected is not None:
                item = self.model.uid_table[index.row()]
                item = self.model.vfs_view.node_where_uid(item)
                self.vnode_2click_selected(item)
