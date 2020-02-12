import re
from deca.gui.vfs_widgets import used_color_calc
from deca.vfs_db import VfsDatabase
from deca.vfs_processor import VfsNode
from deca.ff_adf import AdfDatabase
from PySide2.QtCore import QAbstractItemModel, QModelIndex, Qt, QSortFilterProxyModel
from PySide2.QtGui import QColor
from PySide2.QtWidgets import QHeaderView, QSizePolicy, QWidget, QHBoxLayout, QTreeView, QAbstractItemView


class VfsDirLeaf(object):
    def __init__(self, name, uid):
        self.name = name
        self.parent = None
        self.row = 0
        self.uid = uid

    def v_path(self):
        pn = b''
        if self.parent is not None:
            pn = self.parent.v_path(True)
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

    def v_path(self, child_called=False):
        s = ''
        if self.parent is not None:
            s = self.parent.v_path(True)
            s = s + self.name + '/'
        if not child_called:
            s = s + r'%'
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
        self.adf_db = None
        self.root_node = None
        self.n_rows = 0
        self.n_cols = 0

    def vfs_set(self, vfs: VfsDatabase):
        self.beginResetModel()
        self.vfs = vfs
        self.adf_db = AdfDatabase(vfs)

        vpaths = self.vfs.nodes_select_vpath_uid_where_vpath_not_null_type_not_symlink()
        vpaths.sort()
        vpaths = dict(vpaths)

        self.root_node = None
        self.root_node = VfsDirBranch('/')
        for v_path, uid in vpaths.items():
            if v_path.find('\\') >= 0:
                print(f'GUI: Warning: Windows Path {v_path}')
                path = v_path.split('\\')
            else:
                path = v_path.split('/')

            name = path[-1]
            path = path[0:-1]
            cnode = self.root_node
            for p in path:
                cnode = cnode.child_add(VfsDirBranch(p))

            cnode.child_add(VfsDirLeaf(name, uid))

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
            return ("Path", "Index", "Type", "Hash", "EXT_Hash", "ADF_Type", "Size_U", "Size_C", "Used_Depth")[section]
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
                return node.name
            elif isinstance(node, VfsDirLeaf):
                uid = node.uid
                vnode: VfsNode = self.vfs.node_where_uid(uid)
                if column == 1:
                    return '{}'.format(vnode.uid)
                elif column == 2:
                    return '{}'.format(vnode.file_type)
                elif column == 3:
                    if vnode.v_hash is None:
                        return ''
                    else:
                        return '{:08X}'.format(vnode.v_hash)
                elif column == 4:
                    if vnode.ext_hash is None:
                        return ''
                    else:
                        return '{:08x}'.format(vnode.ext_hash)
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
                uid = node.uid
                vnode: VfsNode = self.vfs.node_where_uid(uid)
                if column == 8:
                    if vnode.used_at_runtime_depth is not None:
                        return used_color_calc(vnode.used_at_runtime_depth)
                elif column == 5:
                    if vnode.adf_type is not None and vnode.adf_type not in self.adf_db.type_map_def:
                        return QColor(Qt.red)
        return None


class DecaSortFilterProxyModel(QSortFilterProxyModel):
    def __init__(self, *args, **kwargs):
        QSortFilterProxyModel.__init__(self, *args, **kwargs)
        self.filter_expr = re.compile('.*')
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
            vis = self.filter_expr.match(tnode.name) is not None

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
    def __init__(self, *args, **kwargs):
        QWidget.__init__(self, *args, **kwargs)

        self.vnode_selection_changed = None
        self.vnode_2click_selected = None

        # Getting the Model
        self.source_model = VfsDirModel()

        # prepare filter
        self.proxy_model = DecaSortFilterProxyModel(self)

        # Creating a QTableView
        self.view = QTreeView()
        self.view.doubleClicked.connect(self.double_clicked)
        self.view.clicked.connect(self.clicked)
        self.view.setSelectionBehavior(QAbstractItemView.SelectRows)
        self.view.setSelectionMode(QAbstractItemView.ExtendedSelection)

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
            if self.vnode_selection_changed is not None:
                items = self.view.selectedIndexes()
                items = [self.proxy_model.mapToSource(idx) for idx in items]
                items = list(set([idx.internalPointer() for idx in items]))
                items = [idx.v_path() for idx in items if isinstance(idx, VfsDirLeaf) or isinstance(idx, VfsDirBranch)]
                self.vnode_selection_changed(items)

    def double_clicked(self, index):
        if index.isValid():
            index = self.proxy_model.mapToSource(index)
            tnode = index.internalPointer()
            if isinstance(tnode, VfsDirLeaf) and self.vnode_2click_selected is not None:
                uid = tnode.uid
                item = self.source_model.vfs.node_where_uid(uid)
                self.vnode_2click_selected(item)

    def filter_vfspath_set(self, expr):
        # self.proxy_model.setFilterRegExp(QRegExp(expr, Qt.CaseInsensitive, QRegExp.RegExp))
        # self.proxy_model.setFilterKeyColumn(0)
        self.proxy_model.filter_set(expr)
