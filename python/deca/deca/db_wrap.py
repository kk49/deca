import os
from .db_core import VfsDatabase, VfsNode, GtocArchiveEntry
from .db_cross_game import DbCrossGame
from .ff_adf import AdfDatabase
from .ff_types import *
from .db_types import *
from .ff_determine import determine_file_type_and_size
from .file import ArchiveFile


def determine_file_type_by_name(vfs: VfsDatabase, node: VfsNode):
    if node.file_type is None:
        if node.offset is None:
            node.file_type = FTYPE_SYMLINK
        else:
            filename = None
            if node.v_path is not None:
                filename = node.v_path
            elif node.p_path is not None:
                filename = node.p_path

            if filename is not None:
                file, ext = os.path.splitext(filename)
                if ext.startswith(b'.atx'):
                    node.file_type = FTYPE_ATX
                elif ext == b'.hmddsc':
                    node.file_type = FTYPE_HMDDSC

            if node.file_type is None:
                hash32 = None
                hash64 = None
                string = node.v_path
                if vfs.game_info.file_hash_size == 4:
                    hash32 = node.v_hash
                elif vfs.game_info.file_hash_size == 8:
                    hash64 = node.v_hash
                else:
                    raise NotImplementedError(f'process_garc: Hash size of {vfs.game_info.file_hash_size} not handled')

                # find possible hash strings for node
                hash_strings = vfs.hash_string_match(hash32=hash32, hash64=hash64, string=string)

                gtoc_archives = []
                for rowid, string, hash32, hash48, hash64, ext_hash32 in hash_strings:
                    results = vfs.gtoc_archive_where_hash32_magic(path_hash32=hash32, magic=node.magic)
                    gtoc_archives = gtoc_archives + results

                if len(gtoc_archives) == 1:
                    node.file_type = FTYPE_GARC
                # elif len(gtoc_archives) == 0:
                #     print('No gtoc archives found for {} {} {}'.format(node.uid, node.v_hash_to_str(), node.v_path))
                # else:
                #     print('TOO MANY!!! {} gtoc archives found for {} {} {}'.format(len(gtoc_archives), node.uid, node.v_hash_to_str(), node.v_path))


def determine_file_type(vfs: VfsDatabase, node: VfsNode):
    if node.file_type is None:
        if node.offset is None:
            node.file_type = FTYPE_SYMLINK
        else:
            if node.compression_type_get() in {compression_v4_01_zlib, compression_v4_03_zstd, compression_v4_04_oo}:
                # todo special case for jc4 /rage2 compression needs to be cleaned up
                with vfs.file_obj_from(node) as f:
                    node.file_type, _, node.magic, node.file_sub_type = \
                        determine_file_type_and_size(f, node.size_u)
            else:
                fin = vfs.file_obj_from(node)
                if fin is None:
                    node.file_type = FTYPE_NOT_HANDLED
                else:
                    with fin as f:
                        node.file_type, node.size_u, node.magic, node.file_sub_type = \
                            determine_file_type_and_size(f, node.size_c)

    if node.file_type == FTYPE_AAF:
        node.compression_type_set(compression_v3_zlib)
        with vfs.file_obj_from(node) as f:
            node.file_type, node.size_u, node.magic, node.file_sub_type = \
                determine_file_type_and_size(f, node.size_u)

    if node.file_type == FTYPE_ADF0:
        with ArchiveFile(vfs.file_obj_from(node)) as f:
            _ = f.read_u32()  # magic
            adf_type = f.read_u32()
        node.file_sub_type = adf_type


class DbWrap:
    def __init__(self, db: VfsDatabase, logger=None, index_offset=0):
        self._db = db
        self._adf_db = AdfDatabase()
        self._logger = logger
        self._index_offset = index_offset
        self._drop_results = False
        self._nodes_to_add = []
        self._nodes_to_update = set()
        self._string_hash_to_add = []
        self._gtoc_archive_defs = []
        self._objects = []  # uid(ROWID), src_node_id, offset, class_str(_rowid), name_str(_rowid), object_id
        self._object_id_refs = []  # object_rowid((src_node_id,offset)), id, flags
        self._event_id_refs = []  # object_rowid((src_node_id,offset)), id, flags

        self._adf_db.load_from_database(self._db)

        self.file_hash_type = self._db.file_hash_type
        self.file_hash = self._db.file_hash

    def db(self) -> VfsDatabase:
        return self._db

    def log(self, msg):
        if self._logger is not None:
            self._logger.log(msg)

    def status(self, i, n):
        if self._logger is not None:
            self._logger.status(i, n)

    def index_offset_set(self, index_offset):
        self._index_offset = index_offset

    def node_read_adf(self, node):
        return self._adf_db.read_node(self._db, node)

    def process_adf_in_exe(self, exe_path, node_uid):
        return self._adf_db.process_adf_in_exe(exe_path, node_uid)

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        if exc_type is None and not self._drop_results:
            n_nodes_to_add = len(self._nodes_to_add)
            if n_nodes_to_add > 0:
                # self.log('Determining file types: {} nodes'.format(len(self._nodes_to_add)))
                # for ii, node in enumerate(self._nodes_to_add):
                #     self.status(ii + self._index_offset, n_nodes_to_add + self._index_offset)
                #     determine_file_type_by_name(self._db, node)
                #     determine_file_type(self._db, node)

                # self.status(n_nodes_to_add + self._index_offset, n_nodes_to_add + self._index_offset)

                self.log('DATABASE: Inserting {} nodes'.format(len(self._nodes_to_add)))
                self._db.nodes_add_many(self._nodes_to_add)

            if len(self._nodes_to_update) > 0:
                self.log('DATABASE: Updating {} nodes'.format(len(self._nodes_to_update)))
                self._db.node_update_many(self._nodes_to_update)

            hash_strings_to_add = list(set(self._string_hash_to_add))
            if len(hash_strings_to_add) > 0:
                self.log('DATABASE: Inserting {} hash strings'.format(len(hash_strings_to_add)))
                self._db.hash_string_add_many(hash_strings_to_add)

            hash_field_strings_to_add = [hs for hs in hash_strings_to_add if hs[-3]]
            if len(hash_field_strings_to_add) > 0:
                self.log('DATABASE: Inserting {} hash field strings'.format(len(hash_field_strings_to_add)))
                self._db.db_cg.hash_string_add_many(hash_field_strings_to_add)

            if len(self._gtoc_archive_defs) > 0:
                self.log('DATABASE: Inserting {} gt0c archive definitions'.format(len(self._gtoc_archive_defs)))
                self._db.gtoc_archive_add_many(self._gtoc_archive_defs)

            if self._adf_db.has_type_map_changed():
                self.log('DATABASE: Saving ADF Types: {} Types'.format(len(self._adf_db.type_map_def)))
                self._adf_db.save_to_database(self._db)

            if len(self._objects) > 0:
                self.log('DATABASE: Inserting {} objects'.format(len(self._objects)))
                obj_rowids = self._db.object_info_add_many(self._objects)

                if len(self._object_id_refs) > 0:
                    self.log('DATABASE: Inserting {} object id ref'.format(len(self._object_id_refs)))
                    self._db.object_id_refs_add_many(self._object_id_refs, obj_rowids)

                if len(self._event_id_refs) > 0:
                    self.log('DATABASE: Inserting {} event id refs'.format(len(self._event_id_refs)))
                    self._db.event_id_refs_add_many(self._event_id_refs, obj_rowids)

    def node_add(self, node):
        self._nodes_to_add.append(node)

    def node_update(self, node):
        self._nodes_to_update.add(node)

    def propose_string(
            self, string, parent_node=None, is_field_name=False, possible_file_types=None,
            used_at_runtime=None, fix_paths=True):
        p_types = 0

        if isinstance(string, str):
            string = string.encode('ascii', 'ignore')
        elif isinstance(string, bytes):
            try:
                string.decode('utf-8')
            except UnicodeDecodeError:
                # if logger is not None:
                #     logger.log('propose: BAD STRING NOT UTF-8 {}'.format(string))
                return None
        else:
            # if logger is not None:
            #     logger.log('propose: BAD STRING {}'.format(string))
            return None

        if fix_paths:
            string = string.replace(b'\\\\', b'/').replace(b'\\', b'/')

        parent_uid = None
        if parent_node is not None:
            parent_uid = parent_node.uid

        if possible_file_types is None:
            pass
        elif isinstance(possible_file_types, list):
            for pt in possible_file_types:
                p_types = p_types | ftype_list[pt]
        else:
            p_types = p_types | ftype_list[possible_file_types]

        hash_string_tuple = make_hash_string_tuple(string)

        rec = (*hash_string_tuple, parent_uid, is_field_name, used_at_runtime, p_types)

        self._string_hash_to_add.append(rec)

        # find substrings spliting on , and |
        substrings = [string]
        # TODO put b'/', b' ' back
        seps = [b',', b'|']
        for sep in seps:
            substrings_new = []
            for substring in substrings:
                substrings_new += substring.split(sep)
            substrings = substrings_new

        is_field_name = False  # for substrings to be possible field names
        for substring in substrings:
            if substring != string:
                self.propose_string(substring.strip(), parent_node, is_field_name, possible_file_types, used_at_runtime, fix_paths)

        return rec

    def gtoc_archive_add(self, archive):
        if isinstance(archive, GtocArchiveEntry):
            self._gtoc_archive_defs.append(archive)
        else:
            self._gtoc_archive_defs = self._gtoc_archive_defs + archive

    def object_add(self, src_node_id, offset, class_str, name_str, object_id):
        # uid(ROWID), src_node_id, offset, class_str(_rowid), name_str(_rowid), object_id
        obj_uid = len(self._objects)
        self._objects.append([obj_uid, src_node_id, offset, to_str(class_str), to_str(name_str), object_id])
        return obj_uid

    def object_id_ref_add(self, obj_uid, object_id, flags):
        # object_rowid((src_node_id,offset)), id, flags
        self._object_id_refs.append([obj_uid, object_id, flags])

    def event_id_ref_add(self, obj_uid, event_id, flags):
        # object_rowid((src_node_id,offset)), id, flags
        self._event_id_refs.append([obj_uid, event_id, flags])
