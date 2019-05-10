import sys
import os
import re
import argparse
import pickle
from deca.errors import *
from deca.ff_vfs import vfs_structure_prep, vfs_structure_open, VfsStructure, VfsNode
from deca.ff_types import *
from deca.builder import Builder
from deca.util import Logger
from deca.game_info import GameInfoGZ, GameInfoGZB, GameInfoTHCOTW, GameInfoJC3
from deca.gui.viewer_adf import DataViewerAdf
from deca.gui.viewer_rtpc import DataViewerRtpc
from deca.gui.viewer_image import DataViewerImage
from deca.gui.viewer_raw import DataViewerRaw
from deca.gui.viewer_text import DataViewerText
from deca.gui.viewer_sarc import DataViewerSarc
from deca.cmds.tool_make_web_map import tool_make_web_map
import PySide2
from PySide2.QtCore import \
    QAbstractTableModel, QAbstractItemModel, QModelIndex, Qt, Slot, QSortFilterProxyModel, QRegExp
from PySide2.QtGui import \
    QColor, QFont
from PySide2.QtWidgets import \
    QAction, QApplication, QHeaderView, QMainWindow, QSizePolicy, QTableView, QWidget, QVBoxLayout, QHBoxLayout, \
    QTabWidget, QTreeView, QTextEdit, QLineEdit, QPushButton, QMessageBox, QFileDialog, QLabel


# from PySide2.QtWebEngineWidgets import QWebEngineView


def used_color_calc(level):
    return QColor(0x00, max(0x10, 0xff - 0x20 * level), 0x00, 0xff)


class VfsNodeTableModel(QAbstractTableModel):
    def __init__(self, show_mapped=True):
        QAbstractTableModel.__init__(self)
        self.vfs = None
        self.show_mapped = show_mapped
        self.table = None

        self.remap = None
        self.remap_uid = None
        self.remap_pid = None
        self.remap_type = None
        self.remap_hash = None
        self.column_ids = ["Index", "PIDX", "Type", "Hash", "SARC_Type", "ADF_type", "Size_U", "Size_C", "Path"]

    def vfs_set(self, vfs):
        self.beginResetModel()
        self.vfs = vfs
        self.table = self.vfs.table_vfsnode
        if not self.show_mapped:
            self.table = [v for v in self.table if
                          v.vpath is None and v.pvpath is None and v.ftype not in {FTYPE_TAB, FTYPE_ARC}]
        self.endResetModel()

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
        if self.table is None:
            return 0
        else:
            return len(self.table)

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
            node: VfsNode = self.table[row]
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
                    if node.vhash is None:
                        return ''
                    else:
                        return '{:08X}'.format(node.vhash)
                elif column == 4:
                    if node.sarc_type is None:
                        return ''
                    else:
                        return '{:08X}'.format(node.sarc_type)
                elif column == 5:
                    if node.adf_type is None:
                        return ''
                    else:
                        return '{:08X}'.format(node.adf_type)
                elif column == 6:
                    return '{}'.format(node.size_u)
                elif column == 7:
                    return '{}'.format(node.size_c)
                elif column == 8:
                    if node.vpath is not None:
                        return 'V: {}'.format(node.vpath.decode('utf-8'))
                    elif node.pvpath is not None:
                        return 'P: {}'.format(node.pvpath)
                    else:
                        return ''

        elif role == Qt.BackgroundRole:
            node = self.table[row]
            if node.is_valid():
                if column == 8:
                    if node.used_at_runtime_depth is not None:
                        return used_color_calc(node.used_at_runtime_depth)
                elif column == 5:
                    if node.adf_type is not None and node.adf_type not in self.vfs.map_adftypes:
                        return QColor(Qt.red)

        elif role == Qt.TextAlignmentRole:
            if column == 8:
                return Qt.AlignLeft
            else:
                return Qt.AlignRight

        return None


class VfsNodeTableWidget(QWidget):
    def __init__(self, show_mapped):
        QWidget.__init__(self)

        self.vnode_1click_selected = None
        self.vnode_2click_selected = None

        # Getting the Model
        self.model = VfsNodeTableModel(show_mapped=show_mapped)

        # Creating a QTableView
        self.table_view = QTableView()
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

    def vfs_set(self, vfs):
        self.model.vfs_set(vfs)

    def double_clicked(self, index):
        if index.isValid():
            if self.vnode_2click_selected is not None:
                self.vnode_2click_selected(self.model.table[index.row()])


class VfsDirLeaf(object):
    def __init__(self, name, vnodes):
        self.name = name
        self.parent = None
        self.row = 0
        self.vnodes = vnodes

    def vpath(self):
        pn = b''
        if self.parent is not None:
            pn = self.parent.vpath(True)
        return pn + self.name

    def child_count(self):
        return 0


class VfsDirBranch(object):
    def __init__(self, name):
        self.name = name
        self.parent = None
        self.row = 0
        self.children = []
        self.child_name_map = {}

    def vpath(self, child_called=False):
        s = b''
        if self.parent is not None:
            s = self.parent.vpath(True)
            s = s + self.name + b'/'
        if not child_called:
            s = s + b'.*'
        return s

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
    def __init__(self):
        QAbstractItemModel.__init__(self)
        self.vfs = None
        self.root_node = None
        self.n_rows = 0
        self.n_cols = 0

    def vfs_set(self, vfs):
        self.beginResetModel()
        self.vfs = vfs
        self.root_node = None
        self.root_node = VfsDirBranch(b'/')

        keys = list(self.vfs.map_vpath_to_vfsnodes.keys())
        keys.sort()
        for vpath in keys:
            vnodes = self.vfs.map_vpath_to_vfsnodes[vpath]
            if len(vnodes) > 0 and vpath is not None:
                if vpath.find(b'\\') >= 0:
                    print('WINDOWS PATH {}'.format(vpath))
                    path = vpath.split(b'\\')
                else:
                    path = vpath.split(b'/')
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
        if node is None or node.parent is None:
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
        if node is None:
            return 0

        return node.child_count()

    def columnCount(self, parent):
        return 9

    def headerData(self, section, orientation, role):
        if orientation == Qt.Horizontal and role == Qt.DisplayRole:
            return ("Path", "Index", "Type", "Hash", "SARC_Type", "ADF_Type", "Size_U", "Size_C", "Used_Depth")[section]
        else:
            return None

    def data(self, index, role):
        if not index.isValid():
            return None
        node = index.internalPointer()
        if node is None:
            return None
        column = index.column()
        if role == Qt.DisplayRole:
            if column == 0:
                return node.name.decode('utf-8')
            elif isinstance(node, VfsDirLeaf):
                vnode: VfsNode = node.vnodes[0]
                if column == 1:
                    return '{}'.format(vnode.uid)
                elif column == 2:
                    return '{}'.format(vnode.file_type())
                elif column == 3:
                    if vnode.vhash is None:
                        return ''
                    else:
                        return '{:08X}'.format(vnode.vhash)
                elif column == 4:
                    if vnode.sarc_type is None:
                        return ''
                    else:
                        return '{:08x}'.format(vnode.sarc_type)
                elif column == 5:
                    if vnode.adf_type is None:
                        return ''
                    else:
                        return '{:08x}'.format(vnode.adf_type)
                elif column == 6:
                    return '{}'.format(vnode.size_u)
                elif column == 7:
                    return '{}'.format(vnode.size_c)
                elif column == 8:
                    return '{}'.format(vnode.used_at_runtime_depth)
        elif role == Qt.BackgroundColorRole:
            if isinstance(node, VfsDirLeaf):
                vnode: VfsNode = node.vnodes[0]
                if column == 8:
                    if vnode.used_at_runtime_depth is not None:
                        return used_color_calc(vnode.used_at_runtime_depth)
                elif column == 5:
                    if vnode.adf_type is not None and vnode.adf_type not in self.vfs.map_adftypes:
                        return QColor(Qt.red)
        return None


class DecaSortFilterProxyModel(QSortFilterProxyModel):
    def __init__(self, *args, **kwargs):
        QSortFilterProxyModel.__init__(self, *args, **kwargs)
        self.filter_expr = '.*'
        self.vis_map = {}

    def check_node(self, index):
        if index in self.vis_map:
            return self.vis_map[index]

        tnode = index.internalPointer()
        vis = False
        if isinstance(tnode, VfsDirBranch):
            for r in range(self.sourceModel().rowCount(index)):
                cindex = self.sourceModel().index(r, 0, index)
                vis = vis | self.check_node(cindex)

        elif isinstance(tnode, VfsDirLeaf):
            vis = self.filter_expr.match(tnode.name.decode('utf-8')) is not None

        self.vis_map[index] = vis

        return vis

    def filter_set(self, expr):
        self.beginResetModel()
        try:
            self.filter_expr = re.compile(expr)
        except Exception as err:
            self.filter_expr = re.compile('')

        self.vis_map = {}
        if self.sourceModel() is not None:
            self.check_node(self.sourceModel().index(0, 0, QModelIndex()))
        self.endResetModel()

    def filterAcceptsRow(self, source_row: int, source_parent):
        index = self.sourceModel().index(source_row, 0, source_parent)
        return self.check_node(index)


class VfsDirWidget(QWidget):
    def __init__(self):
        QWidget.__init__(self)

        self.vnode_1click_selected = None
        self.vnode_2click_selected = None

        # Getting the Model
        self.source_model = VfsDirModel()

        # prepare filter
        self.proxy_model = DecaSortFilterProxyModel(self)

        # Creating a QTableView
        self.view = QTreeView()
        self.view.doubleClicked.connect(self.double_clicked)
        self.view.clicked.connect(self.clicked)

        font = self.view.font()
        font.setPointSize(8)
        self.view.setFont(font)
        # self.view.setSortingEnabled(True)
        self.view.setModel(self.proxy_model)

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

        self.filter_vfspath_set('.*')

    def vfs_set(self, vfs):
        self.source_model.vfs_set(vfs)
        self.proxy_model.setSourceModel(self.source_model)

    def clicked(self, index):
        if index.isValid():
            index = self.proxy_model.mapToSource(index)
            tnode = index.internalPointer()
            if (isinstance(tnode, VfsDirLeaf) or isinstance(tnode, VfsDirBranch)) and self.vnode_1click_selected is not None:
                self.vnode_1click_selected(tnode.vpath())

    def double_clicked(self, index):
        if index.isValid():
            index = self.proxy_model.mapToSource(index)
            tnode = index.internalPointer()
            if isinstance(tnode, VfsDirLeaf) and self.vnode_2click_selected is not None:
                self.vnode_2click_selected(tnode.vnodes[0])

    def filter_vfspath_set(self, expr):
        # self.proxy_model.setFilterRegExp(QRegExp(expr, Qt.CaseInsensitive, QRegExp.RegExp))
        # self.proxy_model.setFilterKeyColumn(0)
        self.proxy_model.filter_set(expr)


class DataViewWidget(QWidget):
    def __init__(self):
        QWidget.__init__(self)
        self.vfs = None

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

    def vfs_set(self, vfs):
        self.vfs = vfs

    def vnode_1click_selected(self, vpath: str):
        print('DataViewWidget:vnode_1click_selected: {}'.format(vpath))

    def vnode_2click_selected(self, vnode: VfsNode):
        print('DataViewWidget:vnode_2click_selected: {}'.format(vnode))

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
        elif vnode.ftype in {FTYPE_AVTX, FTYPE_ATX, FTYPE_HMDDSC, FTYPE_DDS, FTYPE_BMP}:
            self.tab_image.vnode_process(self.vfs, vnode)
            self.tab_widget.setTabEnabled(self.tab_text_index, False)
            self.tab_widget.setTabEnabled(self.tab_sarc_index, False)
            self.tab_widget.setTabEnabled(self.tab_image_index, True)
            self.tab_widget.setTabEnabled(self.tab_adf_index, False)
            self.tab_widget.setTabEnabled(self.tab_rtpc_index, False)
            self.tab_widget.setCurrentIndex(self.tab_image_index)
        elif vnode.ftype in {FTYPE_ADF, FTYPE_ADF_BARE}:
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


class MainWidget(QWidget):
    def __init__(self):
        QWidget.__init__(self)
        self.vfs = None
        self.builder = Builder()
        self.current_vnode = None
        self.current_vpath = None

        self.log_widget = QTextEdit()
        self.log_widget.setReadOnly(True)
        font = QFont("Courier", 8)
        self.log_widget.setFont(font)
        self.log_widget.setLineWrapMode(QTextEdit.LineWrapMode.NoWrap)
        size = QSizePolicy(QSizePolicy.Preferred, QSizePolicy.Preferred)
        self.log_widget.setSizePolicy(size)

        # Create VFS Node table
        self.vfs_node_widget = VfsNodeTableWidget(show_mapped=True)
        self.vfs_node_widget.vnode_1click_selected = self.vnode_1click_selected
        self.vfs_node_widget.vnode_2click_selected = self.vnode_2click_selected
        # size = QSizePolicy(QSizePolicy.Preferred, QSizePolicy.Preferred)
        # size.setHorizontalStretch(1)
        # self.vfs_node_widget.setSizePolicy(size)

        # Create VFS Node table
        self.vfs_node_widget_non_mapped = VfsNodeTableWidget(show_mapped=False)
        self.vfs_node_widget_non_mapped.vnode_1click_selected = self.vnode_1click_selected
        self.vfs_node_widget_non_mapped.vnode_2click_selected = self.vnode_2click_selected
        # size = QSizePolicy(QSizePolicy.Preferred, QSizePolicy.Preferred)
        # size.setHorizontalStretch(1)
        # self.vfs_node_widget_non_mapped.setSizePolicy(size)

        # Create VFS dir table
        self.vfs_dir_widget = VfsDirWidget()
        self.vfs_dir_widget.vnode_1click_selected = self.vnode_1click_selected
        self.vfs_dir_widget.vnode_2click_selected = self.vnode_2click_selected
        # size = QSizePolicy(QSizePolicy.Preferred, QSizePolicy.Preferred)
        # size.setHorizontalStretch(1)
        # self.vfs_dir_widget.setSizePolicy(size)

        # # Create map widget
        # self.web_map_widget = QWebEngineView(self)
        # self.web_map_widget.setUrl(working_dir + 'map/z0/index.html')
        # self.web_map_widget.show()

        self.nav_widget = QTabWidget()
        self.nav_widget.addTab(self.log_widget, 'Log')
        self.nav_widget.addTab(self.vfs_dir_widget, 'Directory')
        self.nav_widget.addTab(self.vfs_node_widget_non_mapped, 'Non-Mapped List')
        self.nav_widget.addTab(self.vfs_node_widget, 'Raw List')
        # self.nav_widget.addTab(self.web_map_widget, 'Map')
        size = QSizePolicy(QSizePolicy.Preferred, QSizePolicy.Preferred)
        size.setHorizontalStretch(1)
        size.setVerticalStretch(1)
        self.nav_widget.setSizePolicy(size)
        # self.nav_widget.updateGeometry()

        # filter
        self.filter_label = QLabel()
        self.filter_label.setText('Filter (Python Expression Syntax)')

        self.filter_edit = QLineEdit()
        self.filter_edit.setText('.*')
        self.filter_edit.textChanged.connect(self.filter_text_changed)

        filter_layout = QHBoxLayout()
        filter_layout.addWidget(self.filter_label)
        filter_layout.addWidget(self.filter_edit)

        self.bt_extract = QPushButton()
        self.bt_extract.setEnabled(False)
        self.bt_extract.setText('EXTRACT')
        self.bt_extract.clicked.connect(self.bt_extract_clicked)
        size = QSizePolicy(QSizePolicy.Fixed, QSizePolicy.Fixed)
        # size.setHorizontalStretch(0)
        # size.setVerticalStretch(0)
        # self.bt_extract.setSizePolicy(size)

        self.bt_prep_mod = QPushButton()
        self.bt_prep_mod.setEnabled(False)
        self.bt_prep_mod.setText('PREP MOD')
        self.bt_prep_mod.clicked.connect(self.bt_prep_mod_clicked)
        size = QSizePolicy(QSizePolicy.Fixed, QSizePolicy.Fixed)

        self.bt_mod_build = QPushButton()
        # self.bt_mod_build.setEnabled(False)
        self.bt_mod_build.setText('BUILD MOD')
        self.bt_mod_build.clicked.connect(self.bt_mod_build_clicked)
        size = QSizePolicy(QSizePolicy.Fixed, QSizePolicy.Fixed)

        self.nav_layout = QVBoxLayout()
        self.nav_layout.addWidget(self.nav_widget)
        self.nav_layout.addLayout(filter_layout)
        self.nav_layout.addWidget(self.bt_extract)
        self.nav_layout.addWidget(self.bt_prep_mod)
        self.nav_layout.addWidget(self.bt_mod_build)

        # Creating Data View
        self.data_view = DataViewWidget()
        size = QSizePolicy(QSizePolicy.Preferred, QSizePolicy.Preferred)
        # size.setHorizontalStretch(1)
        self.data_view.setSizePolicy(size)
        # self.data_view.updateGeometry()

        # QWidget Layout
        self.main_layout = QHBoxLayout()
        self.main_layout.addLayout(self.nav_layout, stretch=1)
        self.main_layout.addWidget(self.data_view, stretch=1)
        self.setLayout(self.main_layout)
        self.updateGeometry()

    def vfs_set(self, vfs):
        self.vfs = vfs
        self.vfs_node_widget.vfs_set(self.vfs)
        self.vfs_node_widget_non_mapped.vfs_set(self.vfs)
        self.vfs_dir_widget.vfs_set(self.vfs)
        self.data_view.vfs_set(self.vfs)

    def error_dialog(self, s):
        msg = QMessageBox()
        msg.setIcon(QMessageBox.Warning)

        msg.setWindowTitle("DECA: ERROR")
        msg.setText(s)
        # msg.setInformativeText("This is additional information")
        # msg.setDetailedText("The details are as follows:")
        msg.setStandardButtons(QMessageBox.Ok)
        retval = msg.exec_()

    def dialog_good(self, s):
        msg = QMessageBox()
        msg.setIcon(QMessageBox.Information)

        msg.setWindowTitle("DECA")
        msg.setText(s)
        # msg.setInformativeText("This is additional information")
        # msg.setDetailedText("The details are as follows:")
        msg.setStandardButtons(QMessageBox.Ok)
        retval = msg.exec_()

    def vnode_1click_selected(self, vpath: str):
        self.current_vpath = vpath
        self.data_view.vnode_1click_selected(vpath)
        if self.current_vpath is not None:
            self.bt_extract.setText('EXTRACT: {}'.format(self.current_vpath))
            self.bt_extract.setEnabled(True)
            self.bt_prep_mod.setText('PREP MOD: {}'.format(self.current_vpath))
            self.bt_prep_mod.setEnabled(True)

    def vnode_2click_selected(self, vnode: VfsNode):
        self.current_vnode = vnode
        self.data_view.vnode_2click_selected(vnode)
        # if self.current_vnode is not None:
        #     self.bt_extract.setText('EXTRACT: {}'.format(vnode.vpath))
        #     self.bt_extract.setEnabled(True)

    def bt_extract_clicked(self, checked):
        if self.current_vpath is not None:
            try:
                self.vfs.extract_nodes(self.current_vpath, self.vfs.working_dir + 'extracted/', False)
            except DecaFileExists as exce:
                self.error_dialog('Extacted Canceled: File Exists: {}'.format(exce.args))

    def bt_prep_mod_clicked(self, checked):
        if self.current_vpath is not None:
            try:
                self.vfs.extract_nodes(self.current_vpath, self.vfs.working_dir + 'mod/', True)
            except DecaFileExists as exce:
                self.error_dialog('Mod Prep Canceled: File Exists: {}'.format(exce.args))

    def bt_mod_build_clicked(self, checked):
        try:
            self.builder.build_dir(self.vfs, self.vfs.working_dir + 'mod/', self.vfs.working_dir + 'build/')
            self.dialog_good('BUILD SUCCESS')
        except DecaFileExists as exce:
            self.error_dialog('Build Failed: File Exists: {}'.format(exce.args))
        except EDecaBuildError as exce:
            self.error_dialog('Build Failed: {}'.format(exce.args))

    def filter_text_changed(self):
        txt = self.filter_edit.text()
        if len(txt) == 0:
            txt = '.*'
        self.vfs_dir_widget.filter_vfspath_set(txt)


# ********************
class MainWindow(QMainWindow):
    def __init__(self):
        QMainWindow.__init__(self)
        self.vfs = None

        # Menu
        self.menu = self.menuBar()
        self.file_menu = self.menu.addMenu('File')
        self.edit_menu = self.menu.addMenu('Edit')
        self.tools_menu = self.menu.addMenu('Tools')

        self.action_project_new = QAction("&New Project...")
        self.action_project_new.triggered.connect(self.project_new)

        self.action_project_open = QAction("&Open Project...")
        self.action_project_open.triggered.connect(self.project_open)

        self.action_exit = QAction("E&xit", self)
        self.action_exit.setShortcut("Ctrl+Q")
        self.action_exit.triggered.connect(self.exit_app)

        self.action_make_web_map = QAction("Make &Web Map")
        self.action_make_web_map.triggered.connect(self.tool_make_web_map)

        self.file_menu.addAction(self.action_project_new)
        self.file_menu.addAction(self.action_project_open)
        self.file_menu.addAction(self.action_exit)
        self.tools_menu.addAction(self.action_make_web_map)

        # Status Bar
        self.status = self.statusBar()

        # # Window dimensions
        # geometry = app.desktop().availv_pableGeometry(self)
        # self.setFixedSize(geometry.width() * 0.8, geometry.height() * 0.7)

        self.main_widget = MainWidget()

        class WidgetLogger(Logger):
            def __init__(self, wdir, log_widget):
                Logger.__init__(self, wdir)
                self.log_widget = log_widget

            def log_base(self, level, s):
                msg = Logger.log_base(self, level, s)
                if level <= 0:
                    self.log_widget.append(msg)
                    self.log_widget.repaint()

        self.logger = WidgetLogger('./', self.main_widget.log_widget)

        self.setCentralWidget(self.main_widget)

    def vfs_set(self, vfs):
        self.vfs = vfs
        self.setWindowTitle(
            "deca GUI, Archive Version: {}, Archive: {}".format('TODO', vfs.game_info.game_dir))
        self.status.showMessage(
            "Data loaded and plotted: {}".format('hash_map_missing: {}'.format(len(vfs.hash_map_missing))))
        self.main_widget.vfs_set(vfs)

    @Slot()
    def project_new(self, checked):
        if os.name == 'nt':
            game_loc = 'C:/Program Files(x86)/Steam/steamapps/common/'
        else:
            game_loc = '../'

        filename = QFileDialog.getOpenFileName(self, 'Create Project ...', game_loc, 'Game EXE (*.exe *.EXE)')

        if filename is not None and len(filename[0]) > 0:
            exe_path = filename[0]
            game_dir, exe_name = os.path.split(exe_path)
            game_dir = os.path.join(game_dir, '')

            game_info = None
            if False:
                pass
            elif exe_name.find('GenerationZero') >= 0 and game_dir.find('BETA') >= 0:
                game_info = GameInfoGZB(game_dir, exe_name)
            elif exe_name.find('GenerationZero') >= 0:
                game_info = GameInfoGZ(game_dir, exe_name)
            elif exe_name.find('theHunterCotW') >= 0:
                game_info = GameInfoTHCOTW(game_dir, exe_name)
            elif exe_name.find('JustCause3') >= 0:
                game_info = GameInfoJC3(game_dir, exe_name)
            else:
                self.logger.log('Unknown Game {}'.format(filename))

            if game_info is not None:
                working_dir = '../work/{}/'.format(game_info.game_id)
                vfs = vfs_structure_prep(game_info, working_dir)  # , logger=self.logger)
                self.vfs_set(vfs)

        else:
            self.logger.log('Cannot Create {}'.format(filename))

    @Slot()
    def project_open(self, checked):
        filename = QFileDialog.getOpenFileName(self, 'Open Project ...', '../work', 'Project File (project.json)')
        if filename is not None and len(filename[0]) > 0:
            project_file = filename[0]
            # working_dir = './work/gzb/project.json'
            # working_dir = './work/hp/project.json'
            vfs = vfs_structure_open(project_file)  # , logger=self.logger)
            self.vfs_set(vfs)
        else:
            self.logger.log('Cannot Open {}'.format(filename))

    @Slot()
    def exit_app(self, checked):
        self.close()

    @Slot()
    def tool_make_web_map(self, checked):
        tool_make_web_map(self.vfs, self.vfs.working_dir, True)


def main():
    # options = argparse.ArgumentParser()
    # options.add_argument("-f", "--file", type=str, required=True)
    # args = options.parse_args()

    # Qt Application
    app = QApplication(sys.argv)

    window = MainWindow()

    window.show()

    app.exec_()

    needed = {
        0x0b73315d,
        0x536cdf14,
        0x5618735f,
        0x5b222c55,
        0x5db297db,
        0x6e9b42c0,
        0x7c962fa6,
        0x82d0bea7,
        0x904f4b40,
        0x90a5413e,
        0x9ebbfbef,
        0xa28fbf46,
        0xba23d341,
        0xbc425335,
        0xc402ec5d,
        0xc60e6202,
        0xd0f19cd8,
        0xeb42f07d,
        0xfb2226c6,
    }

    vfs = window.vfs
    prefix = './resources/adf'
    os.makedirs(prefix, exist_ok=True)
    for adft in needed:
        uids = vfs.map_adftype_usage.get(adft, set())
        for uid in uids:
            vnode = vfs.table_vfsnode[uid]
            with vfs.file_obj_from(vnode) as fi:
                buf = fi.read(vnode.size_u)
            fn = os.path.join(prefix, '{:08X}.full.adf'.format(adft))
            if not os.path.isfile(fn):
                with open(fn, 'wb') as fo:
                    fo.write(buf)
            break

    return window.vfs
