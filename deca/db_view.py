import re
from typing import TypeVar, Optional

from .util import DecaSignal, to_unicode, common_prefix
from .ff_types import *
from .db_core import VfsDatabase, VfsNode
from .ff_adf import AdfDatabase

NodeListElement = TypeVar('NodeListElement', str, bytes, VfsNode)


class VfsView:
    def __init__(self, *params, **kwargs):
        self._vfs: Optional[VfsDatabase] = None
        self._adf_db: Optional[AdfDatabase] = None
        self._vfs_view: Optional[VfsView] = None
        self.paths = None
        self.mask = None
        self.parent_id = None
        self._nodes_visible_dirty = True
        self._nodes_visible = []
        self._nodes_visible_uids = set()
        self._nodes_visible_uids_no_vpaths = set()
        self._nodes_selected_dirty = True
        self._nodes_selected = []
        self._nodes_selected_uids = set()
        self._nodes_selected_uids_no_vpaths = set()

        self.source_changed = True
        self.signal_visible_changed = DecaSignal()
        self.signal_selection_changed = DecaSignal()

        self.parent_id = kwargs.get('parent_id', None)

        if len(params) == 1:
            vfs_view = params[0]
            assert isinstance(vfs_view, VfsView)
            self._vfs_view = vfs_view
            self._vfs = vfs_view._vfs
            self._adf_db = vfs_view._adf_db
            self.paths = vfs_view.paths
            self.mask = vfs_view.mask
            vfs_view.signal_visible_changed.connect(self, lambda x: x.slot_visible_changed())
        elif len(params) == 3:
            vfs = params[0]
            assert isinstance(vfs, VfsDatabase)
            self._vfs_view = None
            self._vfs = vfs
            self._adf_db = AdfDatabase(vfs)
            self.paths = params[1]
            self.mask = params[2]
            vfs.db_changed_signal.connect(self, lambda x: x.slot_visible_changed())
        else:
            raise Exception('Incorrect Parameter count to VfsView')

    def vfs_view(self):
        return self._vfs_view

    def vfs(self):
        return self._vfs

    def adf_db(self):
        return self._adf_db

    def slot_visible_changed(self):
        print('VfsView.slot_visible_changed')
        self.source_changed = True
        self.signal_visible_changed.call()

    def mask_set(self, mask):
        print('VfsView.mask_set')
        self._nodes_visible_dirty = True
        self.mask = mask
        self.signal_visible_changed.call()

    def paths_count(self):
        if self.paths is None:
            return 0
        else:
            return len(self.paths)

    def paths_set(self, paths):
        self._nodes_selected_dirty = True
        self.paths = paths
        self.signal_selection_changed.call()

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

    def node_accumulate(self, nodes_map, nodes_uids, nodes_uids_no_vpath, mask=None, pid_in=None, id_pat=None):
        if isinstance(id_pat, VfsNode):
            nodes_all = [(id_pat.uid, id_pat.v_path, id_pat.file_type, id_pat.offset)]
        else:
            nodes_all = self.vfs().nodes_where_match(
                v_path_like=id_pat,
                pid_in=pid_in,
                output='node_id, v_path, file_type, parent_offset',
            )

        for uid, v_path, file_type, parent_offset in nodes_all:
            nodes_uids.add(uid)

            if v_path is None:
                nodes_uids_no_vpath.add(uid)
            else:
                v_path = to_unicode(v_path)

                lst0 = nodes_map.get(v_path, None)

                if lst0 is None:
                    lst = [[], []]
                else:
                    lst = lst0

                if file_type != FTYPE_SYMLINK and parent_offset is not None:
                    lst[0].append(uid)
                else:
                    lst[1].append(uid)

                if lst0 is None:
                    nodes_map[v_path] = lst

        mask_expr = re.compile(to_unicode(mask))
        to_erase = [vp for vp in nodes_map.keys() if mask_expr.match(vp) is None]
        for vp in to_erase:
            nodes_map.pop(vp)

    def node_update(self):
        selection_changed = False
        if self.source_changed:
            self._adf_db.load_from_database(self._vfs)
            self.source_changed = False
            self._nodes_visible_dirty = True
            self._nodes_selected_dirty = True
            selection_changed = True

        if self._nodes_visible_dirty:
            self.vfs().logger.log(f'Nodes Visible Begin')

            # visible nodes
            self._nodes_visible = {}
            self._nodes_visible_uids = set()
            self._nodes_visible_uids_no_vpaths = set()

            self.node_accumulate(
                self._nodes_visible, self._nodes_visible_uids, self._nodes_visible_uids_no_vpaths,
                mask=self.mask, pid_in=self.parent_id)

            self._nodes_visible_dirty = False
            self._nodes_selected_dirty = True
            selection_changed = True
            self.vfs().logger.log(f'Nodes Visible End')

        if self._nodes_selected_dirty:
            self.vfs().logger.log(f'Nodes Selected Begin')

            # selected nodes
            self._nodes_selected = {}
            self._nodes_selected_uids = set()
            self._nodes_selected_uids_no_vpaths = set()

            if self.paths is not None:
                for v in self.paths:
                    id_pat = v

                    if isinstance(id_pat, str):
                        id_pat = v.encode('ascii')

                    self.node_accumulate(
                        self._nodes_selected, self._nodes_selected_uids, self._nodes_selected_uids_no_vpaths,
                        mask=self.mask, pid_in=self.parent_id, id_pat=id_pat)

            self._nodes_selected_dirty = False
            self.vfs().logger.log(f'Nodes Selected End')

        if selection_changed:
            self.signal_selection_changed.call()

    def node_visible_count(self):
        self.node_update()
        return len(self._nodes_visible)

    def nodes_visible_map_get(self):
        self.node_update()
        return self._nodes_visible

    def nodes_visible_uids_get(self):
        self.node_update()
        return self._nodes_visible_uids

    def nodes_visible_uids_no_vpath_get(self):
        self.node_update()
        return self._nodes_visible_uids_no_vpaths

    def node_visible_has(self, uids):
        self.node_update()
        for uid in uids:
            if uid in self._nodes_visible_uids:
                return True
        return False

    def node_selected_count(self):
        self.node_update()
        return len(self._nodes_selected)

    def nodes_selected_get(self):
        self.node_update()
        return self._nodes_selected

    def nodes_selected_uids_get(self):
        self.node_update()
        return self._nodes_selected_uids

    def node_selected_has(self, uids):
        self.node_update()
        for uid in uids:
            if uid in self._nodes_selected_uids:
                return True
        return False

    def node_where_uid(self, uid):
        return self.vfs().node_where_uid(uid)

    def lookup_note_from_file_path(self, path):
        return self.vfs().lookup_note_from_file_path(path)

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
