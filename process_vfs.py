import sys
import os
import argparse
import pickle
from deca.ff_vfs import VfsStructure, VfsNode
from deca.ff_types import *
import PySide2
from PySide2.QtCore import QAbstractTableModel, QAbstractItemModel, QModelIndex, Qt, Slot, QSortFilterProxyModel
from PySide2.QtGui import QColor
from PySide2.QtWidgets import \
    QAction, QApplication, QHeaderView, QMainWindow, QSizePolicy, QTableView, QWidget, QVBoxLayout, QHBoxLayout, \
    QTabWidget, QTreeView, QTextEdit, QPushButton
from deca_gui_viewer_adf import DataViewerAdf
from deca_gui_viewer_rtpc import DataViewerRtpc
from deca_gui_viewer_image import DataViewerImage
from deca_gui_viewer_raw import DataViewerRaw
from deca_gui_viewer_text import DataViewerText
from deca_gui_viewer_sarc import DataViewerSarc
from deca.ff_avtx import Ddsc

prefix_in = '/home/krys/prj/as_games/gz/archives_win64/'
working_dir = './work/gz/'
ver = 3
debug = False

vfs_global = None


# ********************
# IDX, TYPE, HASH, USIZE, CSIZE, VPATH
class VfsNodeTableModel(QAbstractTableModel):
    def __init__(self, vfs=None, show_mapped=True):
        QAbstractTableModel.__init__(self)
        self.vfs = vfs
        self.show_mapped = show_mapped
        self.table = self.vfs.table_vfsnode

        if not show_mapped:
            self.table = [v for v in self.table if v.v_path is None and v.p_path is None and v.ftype not in {FTYPE_TAB, FTYPE_ARC}]

        self.remap = None
        self.remap_uid = None
        self.remap_pid = None
        self.remap_type = None
        self.remap_hash = None
        self.column_ids = ["Index", "PIDX", "Type", "Hash", "Size_U", "Size_C", "Path"]

    def sort(self, column: int, order: PySide2.QtCore.Qt.SortOrder):
        # if self.remap_uid is None:
        #     rm = list(range(len(self.vfs.table_vfsnode)))
        #     self.remap_uid = rm
        #
        # if column == 0:  # IDX
        #     self.remap = self.remap_uid
        # elif column == 1:  # PIDX
        #     if self.remap_pid is None:
        #         rm = list(range(len(self.vfs.table_vfsnode)))
        #         rm.sort(key=lambda v: self.vfs.table_vfsnode[v].pid)
        #         self.remap_pid = rm
        #     self.remap = self.remap_pid
        # elif column == 2:  # Type
        #     if self.remap_type is None:
        #         rm = list(range(len(self.vfs.table_vfsnode)))
        #         rm.sort(key=lambda v: self.vfs.table_vfsnode[v].file_type())
        #         self.remap_type = rm
        #     self.remap = self.remap_type
        # elif column == 3:  # Hash
        #     if self.remap_hash is None:
        #         rm = list(range(len(self.vfs.table_vfsnode)))
        #         rm.sort(key=lambda v: self.vfs.table_vfsnode[v].hashid)
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
        return len(self.table)

    def columnCount(self, parent=QModelIndex()):
        return 7

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
            node : VfsNode = self.table[row]
            if node is None:
                return 'NA'
            else:
                if column == 0:
                    return '{}'.format(node.uid)
                elif column == 1:
                    return '{}'.format(node.pid)
                elif column == 2:
                    return '{}'.format(node.file_type())
                elif column == 3:
                    if node.hashid is None:
                        return ''
                    else:
                        return '{:08X}'.format(node.hashid)
                elif column == 4:
                    return '{}'.format(node.size_u)
                elif column == 5:
                    return '{}'.format(node.size_c)
                elif column == 6:
                    if node.v_path is not None:
                        return 'V: {}'.format(node.v_path.decode('utf-8'))
                    elif node.p_path is not None:
                        return 'P: {}'.format(node.p_path)
                    else:
                        return ''

        elif role == Qt.BackgroundRole:
            node = self.table[row]
            if column == 1 and node.is_valid() and node.ftype in {FTYPE_AVTX, FTYPE_SARC, FTYPE_AAF, FTYPE_TAB, FTYPE_ARC}:
                return QColor(Qt.green)
            elif column == 6 and node.is_valid() and node.used_at_runtime:
                return QColor(Qt.green)

        elif role == Qt.TextAlignmentRole:
            if column == 6:
                return Qt.AlignLeft
            else:
                return Qt.AlignRight

        return None


class VfsNodeTableWidget(QWidget):
    def __init__(self, vfs, show_mapped):
        QWidget.__init__(self)

        self.vnode_selected = None

        # Getting the Model
        self.model = VfsNodeTableModel(vfs, show_mapped=show_mapped)

        # Creating a QTableView
        self.table_view = QTableView()
        self.table_view.doubleClicked.connect(self.double_clicked)
        font = self.table_view.font()
        font.setPointSize(8)
        self.table_view.setFont(font)
        self.table_view.setSortingEnabled(True)
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

    def double_clicked(self, index):
        if index.isValid():
            if self.vnode_selected is not None:
                self.vnode_selected(self.model.table[index.row()])


class VfsDirLeaf(object):
    def __init__(self, name, vnodes):
        self.name = name
        self.parent = None
        self.row = 0
        self.vnodes = vnodes

    def child_count(self):
        return 0


class VfsDirBranch(object):
    def __init__(self, name):
        self.name = name
        self.parent = None
        self.row = 0
        self.children = []
        self.child_name_map = {}

    def child_count(self):
        return len(self.children)

    def child_add(self, c):
        if c.name in self.child_name_map:
            return self.children[self.child_name_map[c.name]]
        else:
            c.parent = self
            c.row = len(self.children)
            self.child_name_map[c.name] = c.row
            self.children.append(c)
            return c


class VfsDirModel(QAbstractItemModel):
    def __init__(self, vfs=None):
        QAbstractItemModel.__init__(self)
        self.vfs = vfs
        self.root_node = None
        self.n_rows = 0
        self.n_cols = 0
        self.items_build()

    def items_build(self):
        self.beginResetModel()
        self.root_node = None
        self.root_node = VfsDirBranch(b'/')

        keys = list(self.vfs.map_vpath_to_vfsnodes.keys())
        keys.sort()
        for v_path in keys:
            vnodes = self.vfs.map_vpath_to_vfsnodes[v_path]
            if len(vnodes) > 0 and v_path is not None:
                if v_path.find(b'\\') >= 0:
                    print('WINDOWS PATH {}'.format(v_path))
                    path = v_path.split(b'\\')
                else:
                    path = v_path.split(b'/')
                name = path[-1]
                path = path[0:-1]
                cnode = self.root_node
                for p in path:
                    cnode = cnode.child_add(VfsDirBranch(p))

                cnode.child_add(VfsDirLeaf(name, vnodes))

        self.endResetModel()

    def parent(self, index):
        if not index.isValid():
            return QModelIndex()

        node = index.internalPointer()
        if node.parent is None:
            return QModelIndex()
        else:
            return self.createIndex(node.parent.row, 0, node.parent)

    def index(self, row, column, parent):
        if not parent.isValid():
            return self.createIndex(row, column, self.root_node)

        parent_node = parent.internalPointer()
        return self.createIndex(row, column, parent_node.children[row])

    def rowCount(self, parent):
        if not parent.isValid():
            return 1
        node = parent.internalPointer()
        return node.child_count()

    def columnCount(self, parent):
        return 7

    def headerData(self, section, orientation, role):
        if orientation == Qt.Horizontal and role == Qt.DisplayRole:
            return ("Path", "Index", "Type", "Hash", "Size_U", "Size_C", "Used")[section]
        else:
            return None

    def data(self, index, role):
        if not index.isValid():
            return None
        node = index.internalPointer()
        column = index.column()
        if role == Qt.DisplayRole:
            if column == 0:
                return node.name.decode('utf-8')
            elif isinstance(node, VfsDirLeaf):
                vnode : VfsNode = node.vnodes[0]
                if column == 1:
                    return '{}'.format(vnode.uid)
                elif column == 2:
                    return '{}'.format(vnode.file_type())
                elif column == 3:
                    if vnode.hashid is None:
                        return ''
                    else:
                        return '{:08X}'.format(vnode.hashid)
                elif column == 4:
                    return '{}'.format(vnode.size_u)
                elif column == 5:
                    return '{}'.format(vnode.size_c)
                elif column == 6:
                    return '{}'.format(vnode.used_at_runtime)
        elif role == Qt.BackgroundColorRole:
            if isinstance(node, VfsDirLeaf):
                vnode : VfsNode = node.vnodes[0]
                if column == 6 and vnode.used_at_runtime:
                    return QColor(Qt.green)
        return None


class VfsDirWidget(QWidget):
    def __init__(self, vfs):
        QWidget.__init__(self)

        self.vnode_selected = None

        # Getting the Model
        self.model = VfsDirModel(vfs)

        # Creating a QTableView
        self.view = QTreeView()
        self.view.doubleClicked.connect(self.double_clicked)
        font = self.view.font()
        font.setPointSize(8)
        self.view.setFont(font)
        # self.view.setSortingEnabled(True)
        self.view.setModel(self.model)

        # # QTableView Headers
        self.header = self.view.header()
        self.header.setSectionResizeMode(QHeaderView.ResizeToContents)
        self.header.setStretchLastSection(True)

        size = QSizePolicy(QSizePolicy.Preferred, QSizePolicy.Preferred)
        size.setHorizontalStretch(1)
        self.view.setSizePolicy(size)

        self.main_layout = QHBoxLayout()
        self.main_layout.addWidget(self.view)
        self.setLayout(self.main_layout)

    def double_clicked(self, index):
        if index.isValid():
            tnode = index.internalPointer()
            if isinstance(tnode, VfsDirLeaf) and self.vnode_selected is not None:
                self.vnode_selected(tnode.vnodes[0])


class DataViewWidget(QWidget):
    def __init__(self, vfs):
        QWidget.__init__(self)
        self.vfs = vfs

        self.tab_raw = DataViewerRaw()
        self.tab_text = DataViewerText()
        self.tab_sarc = DataViewerSarc()
        self.tab_image = DataViewerImage()
        self.tab_adf = DataViewerAdf()
        self.tab_rtpc = DataViewerRtpc()

        self.tab_widget = QTabWidget()
        self.tab_raw_index = self.tab_widget.addTab(self.tab_raw, 'Raw/Hex')
        self.tab_text_index = self.tab_widget.addTab(self.tab_text, 'Text')
        self.tab_sarc_index = self.tab_widget.addTab(self.tab_sarc, 'SARC')
        self.tab_image_index = self.tab_widget.addTab(self.tab_image, 'Image')
        self.tab_adf_index = self.tab_widget.addTab(self.tab_adf, 'ADF')
        self.tab_rtpc_index = self.tab_widget.addTab(self.tab_rtpc, 'RTPC')

        size = QSizePolicy(QSizePolicy.Preferred, QSizePolicy.Preferred)
        size.setVerticalStretch(1)
        self.tab_widget.setSizePolicy(size)

        self.main_layout = QVBoxLayout()
        self.main_layout.addWidget(self.tab_widget)
        self.setLayout(self.main_layout)

    def vnode_selected(self, vnode: VfsNode):
        print('DataViewWidget:vnode_selected: {}'.format(vnode))

        self.tab_widget.setTabEnabled(self.tab_raw_index, True)
        self.tab_raw.vnode_process(self.vfs, vnode)

        if vnode.ftype == FTYPE_TXT:
            self.tab_text.vnode_process(self.vfs, vnode)
            self.tab_widget.setTabEnabled(self.tab_text_index, True)
            self.tab_widget.setTabEnabled(self.tab_sarc_index, False)
            self.tab_widget.setTabEnabled(self.tab_image_index, False)
            self.tab_widget.setTabEnabled(self.tab_adf_index, False)
            self.tab_widget.setTabEnabled(self.tab_rtpc_index, False)
            self.tab_widget.setCurrentIndex(self.tab_text_index)
        elif vnode.ftype == FTYPE_SARC:
            self.tab_sarc.vnode_process(self.vfs, vnode)
            self.tab_widget.setTabEnabled(self.tab_text_index, False)
            self.tab_widget.setTabEnabled(self.tab_sarc_index, True)
            self.tab_widget.setTabEnabled(self.tab_image_index, False)
            self.tab_widget.setTabEnabled(self.tab_adf_index, False)
            self.tab_widget.setTabEnabled(self.tab_rtpc_index, False)
            self.tab_widget.setCurrentIndex(self.tab_sarc_index)
        elif vnode.ftype in {FTYPE_AVTX, FTYPE_ATX, FTYPE_DDS, FTYPE_BMP}:
            self.tab_image.vnode_process(self.vfs, vnode)
            self.tab_widget.setTabEnabled(self.tab_text_index, False)
            self.tab_widget.setTabEnabled(self.tab_sarc_index, False)
            self.tab_widget.setTabEnabled(self.tab_image_index, True)
            self.tab_widget.setTabEnabled(self.tab_adf_index, False)
            self.tab_widget.setTabEnabled(self.tab_rtpc_index, False)
            self.tab_widget.setCurrentIndex(self.tab_image_index)
        elif vnode.ftype == FTYPE_ADF:
            self.tab_adf.vnode_process(self.vfs, vnode)
            self.tab_widget.setTabEnabled(self.tab_text_index, False)
            self.tab_widget.setTabEnabled(self.tab_sarc_index, False)
            self.tab_widget.setTabEnabled(self.tab_image_index, False)
            self.tab_widget.setTabEnabled(self.tab_adf_index, True)
            self.tab_widget.setTabEnabled(self.tab_rtpc_index, False)
            self.tab_widget.setCurrentIndex(self.tab_adf_index)
        elif vnode.ftype == FTYPE_RTPC:
            self.tab_rtpc.vnode_process(self.vfs, vnode)
            self.tab_widget.setTabEnabled(self.tab_text_index, False)
            self.tab_widget.setTabEnabled(self.tab_sarc_index, False)
            self.tab_widget.setTabEnabled(self.tab_image_index, False)
            self.tab_widget.setTabEnabled(self.tab_adf_index, False)
            self.tab_widget.setTabEnabled(self.tab_rtpc_index, True)
            self.tab_widget.setCurrentIndex(self.tab_rtpc_index)
        else:
            self.tab_widget.setTabEnabled(self.tab_text_index, False)
            self.tab_widget.setTabEnabled(self.tab_sarc_index, False)
            self.tab_widget.setTabEnabled(self.tab_image_index, False)
            self.tab_widget.setTabEnabled(self.tab_adf_index, False)
            self.tab_widget.setTabEnabled(self.tab_rtpc_index, False)
            self.tab_widget.setCurrentIndex(self.tab_raw_index)


class Widget(QWidget):
    def __init__(self, vfs):
        QWidget.__init__(self)
        self.vfs = vfs
        self.current_vnode = None

        # Create VFS Node table
        self.vfs_node_widget = VfsNodeTableWidget(self.vfs, show_mapped=True)
        self.vfs_node_widget.vnode_selected = self.vnode_selected
        # size = QSizePolicy(QSizePolicy.Preferred, QSizePolicy.Preferred)
        # size.setHorizontalStretch(1)
        # self.vfs_node_widget.setSizePolicy(size)

        # Create VFS Node table
        self.vfs_node_widget_non_mapped = VfsNodeTableWidget(self.vfs, show_mapped=False)
        self.vfs_node_widget_non_mapped.vnode_selected = self.vnode_selected
        # size = QSizePolicy(QSizePolicy.Preferred, QSizePolicy.Preferred)
        # size.setHorizontalStretch(1)
        # self.vfs_node_widget_non_mapped.setSizePolicy(size)

        # Create VFS dir table
        self.vfs_dir_widget = VfsDirWidget(self.vfs)
        self.vfs_dir_widget.vnode_selected = self.vnode_selected
        # size = QSizePolicy(QSizePolicy.Preferred, QSizePolicy.Preferred)
        # size.setHorizontalStretch(1)
        # self.vfs_dir_widget.setSizePolicy(size)

        self.nav_widget = QTabWidget()
        self.nav_widget.addTab(self.vfs_dir_widget, 'Directory')
        self.nav_widget.addTab(self.vfs_node_widget_non_mapped, 'Non-Mapped List')
        self.nav_widget.addTab(self.vfs_node_widget, 'Raw List')
        size = QSizePolicy(QSizePolicy.Preferred, QSizePolicy.Preferred)
        size.setHorizontalStretch(1)
        size.setVerticalStretch(1)
        self.nav_widget.setSizePolicy(size)
        # self.nav_widget.updateGeometry()

        self.bt_extract = QPushButton()
        self.bt_extract.setEnabled(False)
        self.bt_extract.setText('EXTRACT')
        self.bt_extract.clicked.connect(self.bt_extract_clicked)
        size = QSizePolicy(QSizePolicy.Fixed, QSizePolicy.Fixed)
        # size.setHorizontalStretch(0)
        # size.setVerticalStretch(0)
        # self.bt_extract.setSizePolicy(size)

        self.nav_layout = QVBoxLayout()
        self.nav_layout.addWidget(self.nav_widget)
        self.nav_layout.addWidget(self.bt_extract)

        # Creating Data View
        self.data_view = DataViewWidget(self.vfs)
        size = QSizePolicy(QSizePolicy.Preferred, QSizePolicy.Preferred)
        # size.setHorizontalStretch(1)
        self.data_view.setSizePolicy(size)
        # self.data_view.updateGeometry()

        # QWidget Layout
        self.main_layout = QHBoxLayout()
        self.main_layout.addLayout(self.nav_layout)
        self.main_layout.addWidget(self.data_view)
        self.setLayout(self.main_layout)
        self.updateGeometry()

    def vnode_selected(self, vnode: VfsNode):
        self.current_vnode = vnode
        self.data_view.vnode_selected(vnode)
        if self.current_vnode is not None:
            self.bt_extract.setText('EXTRACT: {}'.format(vnode.v_path))
            self.bt_extract.setEnabled(True)

    def bt_extract_clicked(self, checked):
        if self.current_vnode is not None:
            self.vfs.extract_node(self.current_vnode)


# ********************
class MainWindow(QMainWindow):
    def __init__(self, widget, msg):
        QMainWindow.__init__(self)

        self.setWindowTitle("deca GUI, Archive Version: {}, Archive: {}".format(ver, prefix_in))

        # Menu
        self.menu = self.menuBar()
        self.file_menu = self.menu.addMenu("File")

        # Exit QAction
        exit_action = QAction("Exit", self)
        exit_action.setShortcut("Ctrl+Q")
        exit_action.triggered.connect(self.exit_app)

        self.file_menu.addAction(exit_action)

        # Status Bar
        self.status = self.statusBar()
        self.status.showMessage("Data loaded and plotted: {}".format(msg))

        # # Window dimensions
        # geometry = app.desktop().availableGeometry(self)
        # self.setFixedSize(geometry.width() * 0.8, geometry.height() * 0.7)

        self.setCentralWidget(widget)


    @Slot()
    def exit_app(self, checked):
        sys.exit()


if __name__ == "__main__":
    # options = argparse.ArgumentParser()
    # options.add_argument("-f", "--file", type=str, required=True)
    # args = options.parse_args()

    cache_file = working_dir + 'vfs_cache.pickle'
    if os.path.isfile(cache_file):
        with open(cache_file, 'rb') as f:
            vfs_global = pickle.load(f)
    else:
        vfs_global = VfsStructure(working_dir)
        vfs_global.load_from_archives(prefix_in, debug=debug)
        with open(cache_file, 'wb') as f:
            pickle.dump(vfs_global, f, protocol=pickle.HIGHEST_PROTOCOL)

    # Qt Application
    app = QApplication(sys.argv)

    widget = Widget(vfs_global)

    window = MainWindow(widget, 'hash_map_missing: {}'.format(len(vfs_global.hash_map_missing)))

    window.show()

    sys.exit(app.exec_())




