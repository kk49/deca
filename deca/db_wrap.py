import os
from .vfs_db import VfsDatabase, node_flag_v_hash_type_8, node_flag_v_hash_type_6, GtocArchiveEntry
from .ff_adf import AdfDatabase
from .ff_types import *
from .db_types import *


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

    def extract_types_from_exe(self, exe_path):
        return self._adf_db.extract_types_from_exe(exe_path)

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        if exc_type is None and not self._drop_results:
            n_nodes_to_add = len(self._nodes_to_add)
            if n_nodes_to_add > 0:
                self.log('Determining file types: {} nodes'.format(len(self._nodes_to_add)))
                for ii, node in enumerate(self._nodes_to_add):
                    self.status(ii + self._index_offset, n_nodes_to_add + self._index_offset)
                    self._db.determine_file_type(node)

                self.status(n_nodes_to_add + self._index_offset, n_nodes_to_add + self._index_offset)

                self.log('DATABASE: Inserting {} nodes'.format(len(self._nodes_to_add)))
                self._db.nodes_add_many(self._nodes_to_add)

            if len(self._nodes_to_update) > 0:
                self.log('DATABASE: Updating {} nodes'.format(len(self._nodes_to_update)))
                self._db.node_update_many(self._nodes_to_update)

            hash_strings_to_add = list(set(self._string_hash_to_add))
            if len(hash_strings_to_add) > 0:
                self.log('DATABASE: Inserting {} hash strings'.format(len(hash_strings_to_add)))
                self._db.hash_string_add_many(hash_strings_to_add)

            if len(self._gtoc_archive_defs) > 0:
                self.log('DATABASE: Inserting {} gt0c archive definitions'.format(len(self._gtoc_archive_defs)))
                self._db.gtoc_archive_add_many(self._gtoc_archive_defs)

            self.log('DATABASE: Saving ADF Types: {} Types'.format(len(self._adf_db.type_map_def)))
            self._adf_db.save_to_database(self._db)

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

        # find substrings
        substrings = string.split(b',')
        for substring in substrings:
            if substring != string:
                self.propose_string(substring.strip(), parent_node, is_field_name, possible_file_types, used_at_runtime, fix_paths)

        return rec

    def gtoc_archive_add(self, archive):
        if isinstance(archive, GtocArchiveEntry):
            self._gtoc_archive_defs.append(archive)
        else:
            self._gtoc_archive_defs = self._gtoc_archive_defs + archive


