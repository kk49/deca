from typing import TypeVar, Optional

from .util import DecaSignal, to_unicode, common_prefix
from .ff_types import *
from .db_core import VfsDatabase, VfsNode
from .ff_adf import AdfDatabase

NodeListElement = TypeVar('NodeListElement', str, bytes, VfsNode)


class VfsView:
    def __init__(self, *params):
        self._vfs: Optional[VfsDatabase] = None
        self._adf_database: Optional[AdfDatabase] = None
        self._vfs_view: Optional[VfsView] = None
        self.paths = None
        self.mask = None
        self.archive_active = False
        self.archives = {}
        self.archive_uids = set()
        self.nodes_visible_dirty = True
        self.nodes_visible = []
        self.nodes_visible_uids = set()
        self.nodes_selected_dirty = True
        self.nodes_selected = []
        self.nodes_selected_uids = set()

        self.vfs_changed = True
        self.vfs_changed_signal = DecaSignal()

        if len(params) == 1:
            vfs_view = params[0]
            assert isinstance(vfs_view, VfsView)
            self._vfs_view = vfs_view
            self._vfs = vfs_view._vfs
            self._adf_database = vfs_view._adf_database
            self.paths = vfs_view.paths
            self.mask = vfs_view.mask
            vfs_view.vfs_changed_signal.connect(self, lambda x: x.vfs_changed_callback())
        elif len(params) == 3:
            vfs = params[0]
            assert isinstance(vfs, VfsDatabase)
            self._vfs_view = None
            self._vfs = vfs
            self._adf_database = AdfDatabase(vfs)
            self.paths = params[1]
            self.mask = params[2]
            vfs.db_changed_signal.connect(self, lambda x: x.vfs_changed_callback())
        else:
            raise Exception('Incorrect Parameter count to VfsView')

    def vfs_view(self):
        return self._vfs_view

    def vfs(self):
        return self._vfs

    def adf_database(self):
        return self._adf_database

    def vfs_changed_callback(self):
        self.vfs_changed = True
        self.vfs_changed_signal.call()
        print('VfsView.vfs_changed')

    def archive_active_get(self):
        return self.archive_active

    def archive_active_set(self, v):
        self.archive_active = v
        self.archive_update()
        self.nodes_visible_dirty = True

    def archive_update(self):
        if not self.archive_active:
            self.vfs().logger.log('Archives begin')
            self.archives = {}
            self.archive_uids = set()
            for path in self.paths:
                if isinstance(path, VfsNode):
                    nodes = [path]
                else:
                    nodes = self.vfs().nodes_where_match(v_path_like=path, file_type=FTYPE_SARC)
                for node in nodes:
                    self.archives[node.v_path] = node
                    self.archive_uids.add(node.uid)
            self.vfs().logger.log(f'Archives end count: {len(self.archives)}')

    def archive_count(self):
        return len(self.archives)

    def archive_summary_str(self):
        len_a = len(self.archives)
        if len_a == 0:
            return ''
        elif len_a == 1:
            return to_unicode(list(self.archives.keys())[0])
        else:
            return f'{len_a} Archives'

    def mask_set(self, mask):
        self.nodes_visible_dirty = True
        self.mask = mask

    def paths_count(self):
        if self.paths is None:
            return 0
        else:
            return len(self.paths)

    def paths_set(self, paths):
        self.nodes_selected_dirty = True
        self.paths = paths
        self.archive_update()

    def paths_summary_str(self):
        if self.paths_count() == 0:
            return ''
        elif self.paths_count() == 1:
            return to_unicode(self.paths[0])
        else:
            return '**MULTIPLE**'

    def common_prefix(self):
        path = self.paths[0]
        for p in self.paths:
            path, _, _ = common_prefix(path, p)

        return path

    def node_accumulate(self, nodes_visible, nodes_visible_uids, mask=None, pid_in=None, id_pat=None):
        if isinstance(id_pat, VfsNode):
            nodes_all = [id_pat]
        else:
            nodes_all = self.vfs().nodes_where_match(v_path_like=id_pat, v_path_regexp=mask, pid_in=pid_in)

        for node in nodes_all:
            nodes_visible_uids.add(node.uid)

            if node.v_path is None:
                vp = f'uid_{node.uid}'.encode('ascii')
            else:
                vp = node.v_path

            lst0 = nodes_visible.get(vp, None)

            if lst0 is None:
                lst = [[], []]
            else:
                lst = lst0

            if node.file_type != FTYPE_SYMLINK and node.offset is not None:
                lst[0].append(node)
            else:
                lst[1].append(node)

            if lst0 is None:
                nodes_visible[vp] = lst

    def node_update(self):
        if self.nodes_visible_dirty:
            pid_in = self.archive_uids
            if not self.archive_active:
                pid_in = set()

            # visible nodes
            self.nodes_visible = {}
            self.nodes_visible_uids = set()

            self.node_accumulate(self.nodes_visible, self.nodes_visible_uids, mask=self.mask, pid_in=pid_in)

            self.nodes_visible_dirty = False
            self.nodes_selected_dirty = True

        if self.nodes_selected_dirty:
            pid_in = self.archive_uids
            if not self.archive_active:
                pid_in = set()

            # selected nodes
            self.nodes_selected = {}
            self.nodes_selected_uids = set()

            if self.paths is not None:
                for v in self.paths:
                    id_pat = v

                    if isinstance(id_pat, str):
                        id_pat = v.encode('ascii')

                    self.node_accumulate(
                        self.nodes_selected, self.nodes_selected_uids, mask=self.mask, pid_in=pid_in, id_pat=id_pat)

            self.nodes_selected_dirty = False

    def node_visible_count(self):
        self.node_update()
        return len(self.nodes_visible)

    def nodes_visible_get(self):
        self.node_update()
        return self.nodes_visible

    def node_visible_has(self, uids):
        self.node_update()
        for uid in uids:
            if uid in self.nodes_visible_uids:
                return True
        return False

    def node_selected_count(self):
        self.node_update()
        return len(self.nodes_selected)

    def nodes_selected_get(self):
        self.node_update()
        return self.nodes_selected

    def node_selected_has(self, uids):
        self.node_update()
        for uid in uids:
            if uid in self.nodes_selected_uids:
                return True
        return False

    # def expand_vfs_paths(self):
    #     vos = []
    #
    #     for v in self.paths:
    #         id_pat = v
    #
    #         if isinstance(id_pat, str):
    #             id_pat = v.encode('ascii')
    #
    #         if isinstance(id_pat, bytes):
    #             nodes_all = self.vfs().nodes_where_match(v_path_like=id_pat, v_path_regexp=self.mask)
    #             nodes = []
    #             for node in nodes_all:
    #                 if node.file_type != FTYPE_SYMLINK and node.offset is not None:
    #                     nodes.append(node)
    #             nodes = dict([(n.v_path, n) for n in nodes])
    #             nodes = list(nodes.values())
    #             vos += nodes
    #         else:
    #             vos.append(v)
    #
    #     return vos

    # def find_vfs_node(self, v):
    #     node = None
    #     path = None
    #     if isinstance(v, bytes):
    #         path = v
    #     elif isinstance(v, VfsNode):
    #         node = v
    #     else:
    #         raise NotImplementedError('find_vfs_node: Could not extract {}'.format(v))
    #
    #     if path is not None:
    #         matching_nodes = self.vfs().nodes_where_match(v_path=path)
    #         node = None
    #         for matching_node in matching_nodes:
    #             if matching_node.offset is not None:
    #                 node = matching_node
    #                 break
    #         if node is None:
    #             raise EDecaFileMissing('find_vfs_node: Missing {}'.format(path.decode('utf-8')))
    #
    #     return node
