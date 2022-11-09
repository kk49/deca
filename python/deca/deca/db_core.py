import os
import io
import sqlite3
import pickle
import re
import zstandard as zstd
import zlib
import numpy as np
from typing import List

from deca.util import common_prefix
from deca.errors import *
from deca.file import ArchiveFile, SubsetFile
from deca.ff_types import *
from deca.ff_aaf import extract_aaf
from deca.decompress import DecompressorOodleLZ
from deca.game_info import game_info_load
from deca.hashes import hash32_func, hash48_func, hash64_func, hash_all_func
from deca.ff_gtoc import GtocArchiveEntry, GtocFileEntry
from deca.db_types import *
from deca.db_cross_game import DbCrossGame

dumped_cache_dir = False

language_codes = [
    'bra',  # Brazil
    'chi',  # Chinese
    'eng',  # English
    'fre',  # French
    'ger',  # German
    'ita',  # Italy
    'jap',  # Japanese
    'mex',  # Mexico
    'pol',  # Polish
    'rus',  # Russian
    'sch',  # Simplified Chinese
    'spa',  # Spanish
    'swe',  # Swedish
]


def format_hash32(v_hash):
    if v_hash is None:
        return v_hash
    return '{:08x}'.format(np.uint64(v_hash))


def format_hash48(v_hash):
    if v_hash is None:
        return v_hash
    return '{:012x}'.format(np.uint64(v_hash))


def format_hash64(v_hash):
    if v_hash is None:
        return v_hash
    return '{:016x}'.format(np.uint64(v_hash))


class VfsNode:
    __slots__ = (
        'uid',
        'v_hash',
        'v_path',
        'p_path',
        'file_type',
        'file_sub_type',
        'ext_hash',
        'content_hash',
        'magic',
        'pid',
        'index',
        'offset',
        'size_c',
        'size_u',
        '_blocks',
        'flags',
        'used_at_runtime_depth',
    )

    def __init__(
            self, uid=None, file_type=None,
            v_hash=None, p_path=None, v_path=None,
            pid=None, index=None,
            offset=None, size_c=None, size_u=None,
            file_sub_type=None, ext_hash=None,
            content_hash=None,
            magic=None,
            is_processed_file_raw_no_name=False,
            is_processed_file_raw_with_name=False,
            is_processed_file_type=False,
            is_processed_file_specific=False,
            is_temporary_file=False,
            compression_type=0,
            compression_flag=0,
            blocks=None,
            flags=None,
            used_at_runtime_depth=None,
            v_hash_type=node_flag_v_hash_type_4,
    ):
        self.uid = uid
        self.v_hash = v_hash
        self.v_path = v_path
        self.p_path = p_path
        self.file_type = file_type
        self.file_sub_type = file_sub_type
        self.ext_hash = ext_hash
        self.content_hash = content_hash
        self.magic = magic

        self.pid = pid
        self.index = index  # index in parent
        self.offset = offset  # offset in parent
        self.size_c = size_c  # compressed size in client
        self.size_u = size_u  # extracted size

        self._blocks = blocks

        if flags is None:
            self.flags = 0
            self.flags |= (compression_type << node_flag_compression_type_shift) & node_flag_compression_type_mask
            self.flags |= (compression_flag << node_flag_compression_flag_shift) & node_flag_compression_flag_mask
            if is_processed_file_raw_no_name:
                self.flags = self.flags | node_flag_processed_file_raw_no_name
            if is_processed_file_raw_with_name:
                self.flags = self.flags | node_flag_processed_file_raw_with_name
            if is_processed_file_type:
                self.flags = self.flags | node_flag_processed_file_type
            if is_processed_file_specific:
                self.flags = self.flags | node_flag_processed_file_specific
            if is_temporary_file:
                self.flags = self.flags | node_flag_temporary_file

            self.flags = (self.flags & ~node_flag_v_hash_type_mask) | v_hash_type

            # make sure type and flag was saved properly
            assert self.compression_type_get() == compression_type
            assert self.compression_flag_get() == compression_flag
        else:
            self.flags = flags

        self.used_at_runtime_depth = used_at_runtime_depth

    def flags_get(self, bit):
        return (self.flags & bit) == bit

    def flags_set_value(self, bit, value):
        if value:
            value = bit
        else:
            value = 0
        self.flags = (self.flags & ~bit) | value

    def flags_set(self, bit):
        self.flags_set_value(bit, True)

    def flags_clear(self, bit):
        self.flags_set_value(bit, False)

    def compression_type_get(self):
        return (self.flags & node_flag_compression_type_mask) >> node_flag_compression_type_shift

    def compression_type_set(self, value):
        self.flags = \
            (self.flags & ~node_flag_compression_type_mask) | \
            ((value << node_flag_compression_type_shift) & node_flag_compression_type_mask)

    def compression_flag_get(self):
        return (self.flags & node_flag_compression_flag_mask) >> node_flag_compression_flag_shift

    def compression_flag_set(self, value):
        self.flags = \
            (self.flags & ~node_flag_compression_flag_mask) | \
            ((value << node_flag_compression_flag_shift) & node_flag_compression_flag_mask)

    def temporary_file_get(self):
        return self.flags_get(node_flag_temporary_file)

    def temporary_file_set(self, value):
        self.flags_set_value(node_flag_temporary_file, value)

    def is_valid(self):
        return self.uid is not None and self.uid != 0

    def __str__(self):
        info = []
        if self.file_type is not None:
            info.append('ft:{}'.format(self.file_type))
        if self.v_hash is not None:
            info.append('h:{}'.format(self.v_hash_to_str()))
        if self.v_path is not None:
            info.append('v:{}'.format(self.v_path))
        if self.p_path is not None:
            info.append('p:{}'.format(self.p_path))
        if len(info) == 0:
            info.append('child({},{})'.format(self.pid, self.index))
        return ' '.join(info)

    def v_hash_to_str(self):
        hash_type = self.flags & node_flag_v_hash_type_mask
        if hash_type == node_flag_v_hash_type_4:
            return format_hash32(self.v_hash)
        elif hash_type == node_flag_v_hash_type_6:
            return format_hash48(self.v_hash)
        elif hash_type == node_flag_v_hash_type_8:
            return format_hash64(self.v_hash)
        else:
            raise NotImplementedError('hash_type not handled: {:016x}'.format(np.uint64(self.flags)))

    def blocks_raw(self):
        if not self._blocks:
            return None

        return self._blocks

    def blocks_get(self, vfs):
        vfs: VfsDatabase

        if self._blocks is None:
            self._blocks = vfs.blocks_where_node_id(self.uid)

            if self._blocks is None:
                self._blocks = False

        if not self._blocks:
            return [(self.offset, self.size_c, self.size_u)]

        return self._blocks


core_nodes_definition = \
    '''
    CREATE TABLE IF NOT EXISTS "core_nodes" (
        "node_id" INTEGER NOT NULL UNIQUE,
        "flags" INTEGER,
        "parent_id" INTEGER,
        "parent_index" INTEGER,
        "parent_offset" INTEGER,
        "v_hash" INTEGER,
        "v_path" TEXT,
        "p_path" TEXT,
        "content_hash" TEXT,
        "magic" INTEGER,
        "file_type" TEXT,
        "ext_hash" INTEGER,
        "size_c" INTEGER,
        "size_u" INTEGER,
        "file_sub_type" INTEGER,
        "used_at_runtime_depth" INTEGER,
        PRIMARY KEY("node_id")
    )
    '''

core_nodes_update_all_where_node_id = \
    """
    UPDATE core_nodes SET
    flags=(?),
    parent_id=(?),
    parent_index=(?),
    parent_offset=(?),
    v_hash=(?),
    v_path=(?),
    p_path=(?),
    content_hash=(?),
    magic=(?),
    file_type=(?),
    ext_hash=(?),
    size_c=(?),
    size_u=(?),
    file_sub_type=(?),
    used_at_runtime_depth=(?)
    WHERE node_id=(?)
    """

core_nodes_field_count = 16

core_nodes_all_fields = '(' + ','.join(['?'] * core_nodes_field_count) + ')'


def db_to_vfs_node(v):
    node = VfsNode(
        uid=v[0],
        flags=v[1],
        pid=v[2],
        index=v[3],
        offset=v[4],
        v_hash=v[5],
        v_path=to_bytes(v[6]),
        p_path=to_str(v[7]),
        content_hash=to_str(v[8]),
        magic=v[9],
        file_type=to_str(v[10]),
        ext_hash=v[11],
        size_c=v[12],
        size_u=v[13],
        file_sub_type=v[14],
        used_at_runtime_depth=v[15],
    )
    return node


def db_from_vfs_node(node: VfsNode):
    v = (
        node.uid,
        node.flags,
        node.pid,
        node.index,
        node.offset,
        node.v_hash,
        to_str(node.v_path),
        to_str(node.p_path),
        to_str(node.content_hash),
        node.magic,
        to_str(node.file_type),
        node.ext_hash,
        node.size_c,
        node.size_u,
        node.file_sub_type,
        node.used_at_runtime_depth,
    )
    return v


# string references
ref_flag_is_defined = 1 << 0
ref_flag_is_referenced = 1 << 1
ref_flag_is_file_name = 1 << 2
ref_flag_is_field_name = 1 << 3


class VfsDatabase(DbBase):
    def __init__(
            self, project_file, working_dir, logger,
            init_display=False,
            max_uncompressed_cache_size=(2 * 1024**3)
    ):
        super().__init__(os.path.join(working_dir, 'db', 'core.db'), logger)

        self.db_cg = DbCrossGame(os.path.abspath(os.path.join(working_dir, "..")), logger)

        self.project_file = project_file
        self.working_dir = working_dir
        self.game_info = game_info_load(project_file)
        self.decompress_oodle_lz = DecompressorOodleLZ(self.game_info.oo_decompress_dll)
        if 4 == self.game_info.file_hash_size:
            self.file_hash_db_id = 'hash32'
            self.file_hash = hash32_func
            self.file_hash_format = format_hash32
            self.file_hash_type = node_flag_v_hash_type_4
            self.ext_hash = hash32_func
        elif 8 == self.game_info.file_hash_size:
            self.file_hash_db_id = 'hash64'
            self.file_hash = hash64_func
            self.file_hash_format = format_hash64
            self.file_hash_type = node_flag_v_hash_type_8
            self.ext_hash = hash32_func
        else:
            raise NotImplementedError('File Hash Size of {} Not Implemented'.format(self.game_info.file_hash_size))

        os.makedirs(working_dir, exist_ok=True)

        if init_display:
            logger.log('OPENING: {} {}'.format(self.game_info.game_dir, working_dir))

        self._lookup_equipment_from_name = None
        self._lookup_equipment_from_hash = None
        self._lookup_translation_from_name = None
        self._lookup_note_from_file_path = None

        self.db_setup()

        # setup in memory uncompressed cache
        # self.uncompressed_cache_max_size = max_uncompressed_cache_size
        # self.uncompressed_cache_map = {}
        # self.uncompressed_cache_lru = []

    def shutdown(self):
        self.decompress_oodle_lz.shutdown()

    def db_reset(self):
        self.db_execute_one('DROP INDEX IF EXISTS index_core_node_blocks_node_id;')
        self.db_execute_one('DROP INDEX IF EXISTS index_core_nodes_v_path_to_vnode;')
        self.db_execute_one('DROP INDEX IF EXISTS index_core_nodes_v_hash_to_vnode;')

        self.db_execute_one('DROP INDEX IF EXISTS core_strings_hash32_asc;')
        self.db_execute_one('DROP INDEX IF EXISTS core_strings_hash48_asc;')
        self.db_execute_one('DROP INDEX IF EXISTS core_strings_hash64_asc;')
        self.db_execute_one('DROP INDEX IF EXISTS core_object_id_ref_id_asc;')
        self.db_execute_one('DROP INDEX IF EXISTS core_object_id_ref_id_asc;')
        self.db_execute_one('DROP INDEX IF EXISTS core_event_id_ref_id_asc;')
        self.db_execute_one('DROP INDEX IF EXISTS core_event_id_ref_ori_asc;')
        self.db_execute_one('DROP INDEX IF EXISTS core_gtoc_archive_path_hash32_asc;')
        self.db_execute_one('DROP INDEX IF EXISTS core_gtoc_archive_archive_magic_asc;')
        self.db_execute_one('DROP INDEX IF EXISTS core_gtoc_file_entry_row_id_asc;')
        self.db_execute_one('DROP INDEX IF EXISTS core_gtoc_file_entry_index_asc;')

        self.db_execute_one('DROP TABLE IF EXISTS core_node_blocks;')
        self.db_execute_one('DROP TABLE IF EXISTS core_nodes;')
        self.db_execute_one('DROP TABLE IF EXISTS core_string_references;')
        self.db_execute_one('DROP TABLE IF EXISTS core_strings;')
        self.db_execute_one('DROP TABLE IF EXISTS core_adf_types;')

        self.db_execute_one('DROP TABLE IF EXISTS core_objects;')
        self.db_execute_one('DROP TABLE IF EXISTS core_object_id_ref;')
        self.db_execute_one('DROP TABLE IF EXISTS core_event_id_ref;')
        self.db_execute_one('DROP TABLE IF EXISTS core_gtoc_archive_def;')
        self.db_execute_one('DROP TABLE IF EXISTS core_gtoc_file_entry;')

        self.db_execute_one('VACUUM;')

        self.db_conn.commit()

        self.db_changed_signal.call()

        self.db_setup()

    def db_setup(self):
        self.db_execute_one(core_nodes_definition)
        self.db_execute_one(
            '''
            CREATE INDEX IF NOT EXISTS "index_core_nodes_v_path_to_vnode" ON "core_nodes" ("v_path"	ASC);
            '''
        )
        self.db_execute_one(
            '''
            CREATE INDEX IF NOT EXISTS "index_core_nodes_v_hash_to_vnode" ON "core_nodes" ("v_hash"	ASC);
            '''
        )
        self.db_execute_one(
            '''
            CREATE INDEX IF NOT EXISTS "index_core_nodes_content_hash_to_vnode" ON "core_nodes" ("content_hash" ASC);
            '''
        )

        self.db_execute_one(
            '''
            CREATE TABLE IF NOT EXISTS "core_node_blocks" (
                "node_id" INTEGER,
                "block_index" INTEGER,
                "block_offset" INTEGER,
                "block_length_compressed" INTEGER,
                "block_length_uncompressed" INTEGER,
                PRIMARY KEY ("node_id", "block_index")
            );
            '''
        )
        self.db_execute_one(
            '''
            CREATE INDEX IF NOT EXISTS "index_core_node_blocks_node_id" ON "core_node_blocks" ("node_id" ASC);
            '''
        )

        self.db_execute_one(
            '''
            CREATE TABLE IF NOT EXISTS "core_strings" (
                "string" TEXT,
                "hash32" INTEGER NOT NULL,
                "hash48" INTEGER NOT NULL,
                "hash64" INTEGER NOT NULL,
                "ext_hash32" INTEGER NOT NULL,
                PRIMARY KEY ("string", "hash32", "hash48", "hash64", "ext_hash32")
            );
            '''
        )
        self.db_execute_one(
            '''
            CREATE INDEX IF NOT EXISTS "core_strings_hash32_asc" ON "core_strings" ("hash32"	ASC);
            '''
        )
        self.db_execute_one(
            '''
            CREATE INDEX IF NOT EXISTS "core_strings_hash48_asc" ON "core_strings" ("hash48"	ASC);
            '''
        )
        self.db_execute_one(
            '''
            CREATE INDEX IF NOT EXISTS "core_strings_hash64_asc" ON "core_strings" ("hash64"	ASC);
            '''
        )

        self.db_execute_one(
            '''
            CREATE TABLE IF NOT EXISTS "core_string_references" (
                "string_rowid" INTEGER NOT NULL,
                "node_id_src" INTEGER,
                "is_adf_field_name" INTEGER,
                "used_at_runtime" INTEGER,
                "possible_file_types" INTEGER,
                PRIMARY KEY ("string_rowid", "node_id_src", "is_adf_field_name", "used_at_runtime", "possible_file_types")
            );
            '''
        )

        self.db_execute_one(
            '''
            CREATE TABLE IF NOT EXISTS "core_objects" (
                "node_id_src" INTEGER NOT NULL,
                "offset" INTEGER NOT NULL, 
                "class_str_rowid" INTEGER,
                "name_str_rowid" INTEGER,
                "object_id" INTEGER,
                PRIMARY KEY ("node_id_src", "offset")
            );
            '''
        )

        self.db_execute_one(
            '''
            CREATE TABLE IF NOT EXISTS "core_object_id_ref" (
                "object_rowid" INTEGER NOT NULL,
                "id" INTEGER NOT NULL,
                "flags" INTEGER,
                PRIMARY KEY ("object_rowid", "id")
            );
            '''
        )
        self.db_execute_one(
            'CREATE INDEX IF NOT EXISTS "core_object_id_ref_id_asc" ON "core_object_id_ref" ("id" ASC);')
        self.db_execute_one(
            'CREATE INDEX IF NOT EXISTS "core_object_id_ref_ori_asc" ON "core_object_id_ref" ("object_rowid" ASC);')

        self.db_execute_one(
            '''
            CREATE TABLE IF NOT EXISTS "core_event_id_ref" (
                "object_rowid" INTEGER NOT NULL,
                "id" INTEGER NOT NULL,
                "flags" INTEGER,
                PRIMARY KEY ("object_rowid", "id")
            );
            '''
        )
        self.db_execute_one(
            'CREATE INDEX IF NOT EXISTS "core_event_id_ref_id_asc" ON "core_event_id_ref" ("id" ASC);')
        self.db_execute_one(
            'CREATE INDEX IF NOT EXISTS "core_event_id_ref_ori_asc" ON "core_event_id_ref" ("object_rowid" ASC);')

        self.db_execute_one(
            '''
            CREATE TABLE IF NOT EXISTS "core_adf_types" (
                "type_hash" INTEGER NOT NULL,
                "missing_in" INTEGER,
                "pickle" BLOB,
                PRIMARY KEY ("type_hash", "missing_in", "pickle")
            );
            '''
        )

        self.db_execute_one(
            '''
            CREATE TABLE IF NOT EXISTS "core_gtoc_archive_def" (
                "node_id_src" INTEGER NOT NULL,
                "path_hash32" INTEGER NOT NULL,
                "archive_magic" INTEGER NOT NULL,
                PRIMARY KEY ("node_id_src", "path_hash32", "archive_magic")
            );
            '''
        )
        self.db_execute_one(
            'CREATE INDEX IF NOT EXISTS "core_gtoc_archive_path_hash32_asc" ON "core_gtoc_archive_def" ("path_hash32" ASC)')
        self.db_execute_one(
            'CREATE INDEX IF NOT EXISTS "core_gtoc_archive_archive_magic_asc" ON "core_gtoc_archive_def" ("archive_magic" ASC)')

        self.db_execute_one(
            '''
            CREATE TABLE IF NOT EXISTS "core_gtoc_file_entry" (
                "def_rowid" INTEGER NOT NULL,
                "def_index" INTEGER NOT NULL,
                "offset" INTEGER,
                "file_size" INTEGER NOT NULL,
                "path_string_rowid" INTEGER NOT NULL,
                PRIMARY KEY ("def_rowid", "def_index")
            );
            '''
        )

        self.db_execute_one(
            'CREATE INDEX IF NOT EXISTS "core_gtoc_file_entry_row_id_asc" ON "core_gtoc_file_entry" ("def_rowid" ASC)')

        self.db_execute_one(
            'CREATE INDEX IF NOT EXISTS "core_gtoc_file_entry_index_asc" ON "core_gtoc_file_entry" ("def_index" ASC)')

        self.db_conn.commit()

        self.db_changed_signal.call()

    def blocks_where_node_id(self, node_id):
        blocks = self.db_query_all(
            "SELECT block_offset, block_length_compressed, block_length_uncompressed "
            "FROM core_node_blocks "
            "WHERE node_id == (?) "
            "ORDER BY block_index ASC",
            [node_id], dbg='blocks_where_node_id')

        if len(blocks) > 0:
            return blocks

        return None

    def node_where_uid(self, uid):
        r1 = self.db_query_one(
            "select * from core_nodes where node_id == (?)",
            [uid],
            dbg='node_where_uid')

        r1 = db_to_vfs_node(r1)
        return r1

    # def nodes_where_uid(self, uids):
    #     nodes = self.db_query_one(
    #         "select * from core_nodes where node_id in (?)",
    #         [uids],
    #         dbg='nodes_where_uid')
    #
    #     nodes = [db_to_vfs_node(node) for node in nodes]
    #     return nodes

    def nodes_where_match(
            self,
            v_hash=None,
            v_path=None,
            v_path_like=None,
            v_path_regexp=None,
            file_type=None,
            content_hash_empty=None,
            pid_in=None,
            uid_only=False,
            output=None):
        params = []
        wheres = []

        if v_hash is not None:
            params.append(v_hash)
            wheres.append('(v_hash == (?))')

        if v_path is not None:
            if isinstance(v_path, bytes):
                v_path = v_path.decode('utf-8')
            params.append(v_path)
            wheres.append('(v_path == (?))')

        if v_path_like is not None:
            if isinstance(v_path_like, bytes):
                v_path_like = v_path_like.decode('utf-8')
            params.append(v_path_like)
            wheres.append('(v_path LIKE (?))')

        if v_path_regexp is not None:
            if isinstance(v_path_regexp, bytes):
                v_path_regexp = v_path_regexp.decode('utf-8')
            params.append(v_path_regexp)
            wheres.append('(v_path REGEXP (?))')

        if file_type is not None:
            if isinstance(file_type, bytes):
                file_type = file_type.decode('utf-8')
            params.append(file_type)
            wheres.append('(file_type == (?))')

        if content_hash_empty is not None:
            if content_hash_empty:
                wheres.append('(content_hash IS NULL)')
            else:
                wheres.append('(content_hash IS NOT NULL)')

        if pid_in is not None:
            params.append(pid_in)
            wheres.append('(parent_id == (?))')

        if len(wheres) > 0:
            where_str = ' WHERE ' + wheres[0]
            for ws in wheres[1:]:
                where_str = where_str + ' AND ' + ws
        else:
            where_str = ''

        if output is not None:
            result_str = output
        elif uid_only:
            result_str = 'node_id'
        else:
            result_str = '*'

        if len(where_str) > 0:
            nodes = self.db_query_all(
                "SELECT " + result_str + " FROM core_nodes " + where_str, params, dbg='nodes_where_match')
        else:
            nodes = self.db_query_all(
                "SELECT " + result_str + " FROM core_nodes", dbg='nodes_where_match_all')

        # todo load blocks
        if output is not None:
            return nodes
        elif uid_only:
            return [v[0] for v in nodes]
        else:
            return [db_to_vfs_node(node) for node in nodes]

    def nodes_select_vpath_uid_where_vpath_not_null_type_check_symlink(self, is_symlink):
        if is_symlink:
            sym_check = "file_type == 'symlink'"
        else:
            sym_check = "file_type != 'symlink'"

        result = self.db_query_all(
            f"SELECT v_path, node_id FROM core_nodes WHERE v_path IS NOT NULL AND ({sym_check} OR file_type IS NULL)",
            dbg='nodes_select_vpath_uid_where_vpath_not_null_type_check_symlink')
        return result

    def nodes_where_unmapped_select_uid(self):
        result = self.db_query_all(
            "SELECT node_id FROM core_nodes WHERE (file_type is NULL or (file_type != (?) AND file_type != (?))) AND v_path IS NULL AND p_path IS NULL",
            [FTYPE_ARC, FTYPE_TAB], dbg='nodes_where_unmapped_select_uid')
        return [v[0] for v in result]

    def nodes_where_flag_select_uid(self, mask, value, dbg='nodes_where_flag_select_uid'):
        uids = self.db_query_all(
            "select node_id from core_nodes where flags & (?) == (?)", [mask, value], dbg=dbg)
        return [uid[0] for uid in uids]

    def nodes_where_temporary_select_uid(self, temporary):
        mask = node_flag_temporary_file
        if temporary:
            value = node_flag_temporary_file
        else:
            value = 0
        return self.nodes_where_flag_select_uid(mask, value, dbg='nodes_where_temporary_select_uid')

    def nodes_where_f_type_select_uid_v_hash_processed(
            self, file_type, flag=node_flag_processed_file_type, has_any_path=None):
        params = []
        wheres = []

        if file_type is None:
            wheres.append('(file_type is NULL)')
        else:
            params.append(file_type)
            wheres.append('(file_type == (?))')

        if has_any_path is None:
            pass
        else:
            if has_any_path:
                wheres.append('((v_path is NOT NULL) OR (p_path is NOT NULL))')
            else:
                wheres.append('((v_path is NULL) AND (p_path is NULL))')

        q_str = ' AND '.join(wheres)

        results = self.db_query_all(
            "SELECT node_id, v_hash, ((flags & (?)) == (?)) FROM core_nodes WHERE " + q_str,
            [flag, flag] + params,
            dbg='nodes_where_f_type_select_uid_v_hash_processed')

        return results

    def nodes_where_match_select_uid_v_hash_processed(self, flag=node_flag_processed_file_type, v_hash=None, ext_hash=None, suffix_like=None):
        params = []
        wheres = []

        if v_hash is not None:
            params.append(v_hash)
            wheres.append('(v_hash == (?))')

        if ext_hash is not None:
            params.append(ext_hash)
            wheres.append('(ext_hash == (?))')

        if suffix_like is not None:
            if isinstance(suffix_like, bytes):
                suffix_like = suffix_like.decode('utf-8')
            suffix_like = '%' + suffix_like

            params.append(suffix_like)
            wheres.append('(v_path LIKE (?))')

        if len(params) > 0:
            q_str = ' ' + ' AND '.join(wheres)
            q_str += ' AND '
        else:
            q_str = ''

        results = self.db_query_all(
            "SELECT node_id, v_hash, ((flags & (?)) == (?)) FROM core_nodes WHERE " + q_str + "(parent_offset not null)",
            [flag, flag] + params,
            dbg='nodes_where_match_select_uid_v_hash_processed')
        return results

    def nodes_select_distinct_vhash(self):
        result = self.db_query_all(
            "SELECT DISTINCT v_hash FROM core_nodes", dbg='nodes_select_distinct_vhash')
        result = [r[0] for r in result if r[0] is not None]
        return result

    def nodes_select_distinct_vpath(self):
        result = self.db_query_all(
            "SELECT DISTINCT v_path FROM core_nodes", dbg='nodes_select_distinct_vpath')
        result = [to_bytes(r[0]) for r in result if r[0] is not None]
        return result

    def nodes_select_distinct_vpath_content_hash(self):
        result = self.db_query_all(
            "SELECT DISTINCT v_path, content_hash FROM core_nodes", dbg='nodes_select_distinct_vpath_content_hash')
        result = [(to_str(r[0]), to_str(r[1])) for r in result if r[0] is not None]
        return result

    def nodes_select_distinct_vpath_where_vhash(self, v_hash):
        result = self.db_query_all(
            "SELECT DISTINCT v_path FROM core_nodes WHERE v_hash == (?)", [v_hash], dbg='nodes_select_distinct_vpath')
        result = [to_bytes(r[0]) for r in result if r[0] is not None]
        return result

    def hash_string_select_distinct_string(self):
        result = self.db_query_all(
            "SELECT DISTINCT string FROM core_strings", dbg='string_select_distinct_string')
        result = [to_bytes(r[0]) for r in result if r[0] is not None]
        return result

    def hash_string_match(self, hash32=None, hash48=None, hash64=None, ext_hash32=None, string=None, to_dict=False):

        params = []
        wheres = []
        if hash32 is not None:
            if hash32 & 0xFFFFFFFF != hash32:
                return []
            params.append(hash32)
            wheres.append('(hash32 == (?))')

        if hash48 is not None:
            if hash48 & 0xFFFFFFFFFFFF != hash48:
                return []
            params.append(hash48)
            wheres.append('(hash48 == (?))')

        if hash64 is not None:
            params.append(hash64)
            wheres.append('(hash64 == (?))')

        if ext_hash32 is not None:
            if ext_hash32 & 0xFFFFFFFF != ext_hash32:
                return []
            params.append(ext_hash32)
            wheres.append('(ext_hash32 == (?))')

        if string is not None:
            string = to_str(string)
            params.append(string)
            wheres.append('(string == (?))')

        if len(wheres) > 0:
            where_str = ' WHERE ' + wheres[0]
            for ws in wheres[1:]:
                where_str = where_str + ' AND ' + ws
        else:
            where_str = ''

        if params:
            result = self.db_query_all(
                "SELECT rowid, string , hash32, hash48, hash64, ext_hash32 FROM core_strings " + where_str,
                params,
                dbg='hash_string_match'
            )
        else:
            result = self.db_query_all(
                "SELECT rowid, string , hash32, hash48, hash64, ext_hash32 FROM core_strings",
                dbg='hash_string_match_all'
            )

        if to_dict:
            result = [(r[0], (to_bytes(r[1]), r[2], r[3], r[4], r[5])) for r in result]
            result = dict(result)
        else:
            result = [(r[0], to_bytes(r[1]), r[2], r[3], r[4], r[5]) for r in result]

        return result

    def hash_string_references_match(self, hash_row_id=None):

        params = []
        wheres = []

        if hash_row_id is not None:
            params.append(hash_row_id)
            wheres.append('(string_rowid == (?))')

        if len(wheres) > 0:
            where_str = ' WHERE ' + wheres[0]
            for ws in wheres[1:]:
                where_str = where_str + ' AND ' + ws
        else:
            where_str = ''

        if params:
            result = self.db_query_all(
                "SELECT * FROM core_string_references " + where_str,
                params,
                dbg='hash_string_references_match'
            )
        else:
            result = self.db_query_all(
                "SELECT * FROM core_string_references",
                dbg='hash_string_references_match_all'
            )

        return result

    def nodes_delete_where_uid(self, uids):
        self.db_execute_many(
            "DELETE FROM core_nodes WHERE node_id=(?)", uids, dbg='nodes_delete_where_uid'
        )
        self.db_conn.commit()

        self.db_changed_signal.call()

    def nodes_add_many(self, nodes):
        db_nodes = [db_from_vfs_node(node) for node in nodes]

        self.db_execute_many(
            f"insert into core_nodes values {core_nodes_all_fields}",
            db_nodes,
            dbg='nodes_add_many:insert_nodes'
        )
        self.db_conn.commit()

        blocks = []
        node: VfsNode
        for node in nodes:
            if node.blocks_raw():
                result = self.db_query_all(
                    "SELECT node_id FROM core_nodes WHERE parent_id=(?) and parent_index=(?)",
                    [node.pid, node.index],
                    dbg='nodes_add_many:select_nodes'
                )

                node.uid = result[0][0]

                for bi, block in enumerate(node.blocks_raw()):
                    blocks.append((node.uid, bi, block[0], block[1], block[2]))

        if blocks:
            self.db_execute_many(
                "insert into core_node_blocks values (?,?,?,?,?)",
                blocks,
                dbg='nodes_add_many:insert_blocks'
            )
            self.db_conn.commit()

        self.db_changed_signal.call()

    def node_update_many(self, nodes: set):
        db_nodes = [db_from_vfs_node(node) for node in nodes]
        db_nodes = [db_node[1:] + db_node[0:1] for db_node in db_nodes]
        self.db_execute_many(core_nodes_update_all_where_node_id, db_nodes, dbg='node_update_many')
        self.db_conn.commit()
        self.db_changed_signal.call()

    def hash_string_add_many_basic(self, hash_list):
        # (string, h4, h6, h8, ext_hash32)
        hash_list_str = [(to_str(h[0]), h[1], h[2], h[3], h[4]) for h in hash_list]
        hash_list_str_unique = list(set(hash_list_str))
        self.db_execute_many(
            "INSERT OR IGNORE INTO core_strings VALUES (?,?,?,?,?)",
            hash_list_str_unique,
            dbg='hash_string_add_many_basic:0:insert'
        )
        self.db_conn.commit()
        self.db_changed_signal.call()

        hash_list_map = {}
        str_to_row_map = {}
        for rec in hash_list_str_unique:
            result = self.db_query_all(
                "SELECT rowid FROM core_strings WHERE string=(?) and hash32=(?) and hash48=(?) and hash64=(?) and ext_hash32=(?)",
                rec,
                dbg='hash_string_add_many_basic:1:select')

            # we expect one and only one match for a hash+string
            assert len(result) == 1
            row_id = result[0][0]
            hash_list_map[rec] = row_id
            str_to_row_map[to_bytes(rec[0])] = row_id

        return hash_list_str, hash_list_map, str_to_row_map

    def hash_string_add_many(self, hash_list):
        # (h4, h6, h8, string, parent_uid, is_field_name, used_at_runtime, p_types)
        hash_list_str, hash_list_map, _ = self.hash_string_add_many_basic(hash_list)

        row_ids = [hash_list_map[rec] for rec in hash_list_str]
        ref_list = [(r, h[5], h[6], h[7], int(np.int64(np.uint64(h[8])))) for r, h in zip(row_ids, hash_list)]
        ref_list = list(set(ref_list))
        self.db_execute_many(
            "INSERT OR IGNORE INTO core_string_references VALUES (?,?,?,?,?)",
            ref_list,
            dbg='hash_string_add_many:0:insert')
        self.db_conn.commit()
        self.db_changed_signal.call()

    def object_info_add_many(self, objects):
        # uid(ROWID), src_node_id, offset, class_str(_rowid), name_str(_rowid), object_id

        # prepare strings
        class_strs = [class_str for _, _, _, class_str, _, _ in objects if class_str is not None]
        name_strs = [name_str for _, _, _, _, name_str, _ in objects if name_str is not None]
        str_set = set(class_strs + name_strs)
        str_lookup = {}
        for s in str_set:
            result = self.db_query_all(
                "SELECT rowid FROM core_strings WHERE string=(?)",
                (s,),
                dbg='object_info_add_many:0:select')

            str_lookup[s] = result[0][0]

        str_lookup[None] = None

        # insertion record
        object_insert = [
            (src_node_id, offset, str_lookup[class_str], str_lookup[name_str], object_id) for uid, src_node_id, offset, class_str, name_str, object_id in objects
        ]

        self.db_execute_many(
            "INSERT OR IGNORE INTO core_objects VALUES (?,?,?,?,?)",
            object_insert,
            dbg='object_info_add_many:1:insert'
        )
        self.db_conn.commit()
        self.db_changed_signal.call()

        # lookup records to get obj_rowids
        obj_rowids = {}
        for uid, src_node_id, offset, class_str, name_str, object_id in objects:
            result = self.db_query_all(
                "SELECT rowid FROM core_objects WHERE node_id_src=(?) AND offset=(?)",
                (src_node_id, offset),
                dbg='object_info_add_many:2:select')
            obj_rowids[uid] = result[0][0]

        return obj_rowids

    def object_id_refs_add_many(self, refs, obj_rowids):
        # object_rowid((src_node_id,offset)), id, flags
        records = [(obj_rowids[object_rowid], idd, flags) for object_rowid, idd, flags in refs]

        self.db_execute_many(
            "INSERT OR IGNORE INTO core_object_id_ref VALUES (?,?,?)",
            records,
            dbg='object_id_refs_add_many:0:insert'
        )
        self.db_conn.commit()
        self.db_changed_signal.call()

    def event_id_refs_add_many(self, refs, obj_rowids):
        # object_rowid((src_node_id,offset)), id, flags
        records = [(obj_rowids[object_rowid], idd, flags) for object_rowid, idd, flags in refs]

        self.db_execute_many(
            "INSERT OR IGNORE INTO core_event_id_ref VALUES (?,?,?)",
            records,
            dbg='event_id_refs_add_many:0:insert'
        )
        self.db_conn.commit()
        self.db_changed_signal.call()

    def gtoc_archive_add_many(self, archives: List[GtocArchiveEntry]):
        # write gtoc archive definitions
        a: GtocArchiveEntry
        entries = [(a.src_uid, a.path_hash32, a.archive_magic) for a in archives]
        self.db_execute_many(
            "INSERT OR IGNORE INTO core_gtoc_archive_def VALUES (?,?,?)",
            entries,
            dbg='gtoc_archive_add_many:0:insert'
        )
        self.db_conn.commit()

        # lookup gtoc archive definitions
        def_row_ids = []
        for entry in entries:
            result = self.db_query_all(
                "SELECT rowid FROM core_gtoc_archive_def WHERE (node_id_src=(?)) AND (path_hash32=(?)) AND (archive_magic=(?))",
                entry,
                dbg='gtoc_archive_add_many:1:select'
            )
            assert len(result) == 1
            def_row_ids.append(result[0][0])

        # add file entry strings and get hash string row id map
        file_entry_strings = set()
        a: GtocArchiveEntry
        for a in archives:
            fe: GtocFileEntry
            for fe in a.file_entries:
                file_entry_strings.add(fe.path)

        hash_list = [make_hash_string_tuple(s) for s in file_entry_strings]
        _, _, str_to_row_map = self.hash_string_add_many_basic(hash_list)

        # insert file entries into db
        all_file_entries = []
        archive: GtocArchiveEntry
        for def_row_id, archive in zip(def_row_ids, archives):
            # write gtoc file entry definition
            file_entry: GtocFileEntry
            for i, file_entry in enumerate(archive.file_entries):
                offset_in_archive = file_entry.offset_in_archive
                file_size = file_entry.file_size
                path = file_entry.path
                path_row_id = str_to_row_map[path]

                if offset_in_archive == 0:
                    offset_in_archive = None

                all_file_entries.append(
                    (def_row_id, i, offset_in_archive, file_size, path_row_id)
                )

        # write gtoc file entries
        self.db_execute_many(
            "INSERT OR IGNORE INTO core_gtoc_file_entry VALUES (?,?,?,?,?)",
            all_file_entries,
            dbg='gtoc_archive_add_many:2:insert'
        )
        self.db_conn.commit()
        self.db_changed_signal.call()

    def gtoc_archive_where_hash32_magic(self, path_hash32=None, magic=None):
        params = []
        wheres = []
        if path_hash32 is not None:
            if path_hash32 & 0xFFFFFFFF != path_hash32:
                return []
            params.append(path_hash32)
            wheres.append('(path_hash32 == (?))')

        if magic is not None:
            params.append(magic)
            wheres.append('(archive_magic == (?))')

        if len(wheres) > 0:
            where_str = ' WHERE ' + wheres[0]
            for ws in wheres[1:]:
                where_str = where_str + ' AND ' + ws
        else:
            where_str = ''

        if params:
            result = self.db_query_all(
                "SELECT rowid, node_id_src, path_hash32, archive_magic FROM core_gtoc_archive_def " + where_str,
                params,
                dbg='gtoc_archive_where_hash32_magic:0:select'
            )
        else:
            result = self.db_query_all(
                "SELECT rowid, node_id_src, path_hash32, archive_magic FROM core_gtoc_archive_def",
                dbg='gtoc_archive_where_hash32_magic:0:select_all'
            )

        archives = []
        for rowid, src_uid, path_hash32, archive_magic in result:
            archive = GtocArchiveEntry()
            archive.src_uid = src_uid
            archive.path_hash32 = path_hash32
            archive.archive_magic = archive_magic

            file_entry_db = self.db_query_all(
                """
                SELECT 
                    core_gtoc_file_entry.def_index, 
                    core_gtoc_file_entry.offset, 
                    core_gtoc_file_entry.file_size, 
                    core_strings.hash32, 
                    core_strings.ext_hash32, 
                    core_strings.string 
                FROM core_gtoc_file_entry
                INNER JOIN core_strings ON core_gtoc_file_entry.path_string_rowid=core_strings.ROWID
                WHERE def_rowid = (?)
                ORDER BY def_index ASC
                """,
                [rowid],
                dbg='gtoc_archive_where_hash32_magic:1:select'
            )

            file_entries = []
            for def_index, offset, file_size, fe_hash32, fe_ext_hash32, fe_string in file_entry_db:
                file_entry = GtocFileEntry()

                file_entry.offset_in_archive = offset
                file_entry.path_hash32 = fe_hash32
                file_entry.ext_hash32 = fe_ext_hash32
                file_entry.file_size = file_size
                file_entry.path = to_bytes(fe_string)

                file_entries.append(file_entry)

            archive.file_entries = file_entries

            archives.append(archive)
        '''
                    # find archive uid in db
            pid = archive.parent_uid
            path_hash32 = archive.path_hash32
            magic = archive.archive_magic

            file_entries = archive.file_entries
            file_entry: GtocFileEntry
            for file_entry in file_entries:
                offset_in_archive = file_entry.offset_in_archive
                path_hash32 = file_entry.path_hash32
                ext_hash32 = file_entry.ext_hash32
                file_size = file_entry.file_size
                path = file_entry.path
                path_hash = db.file_hash(path)

                if offset_in_archive == 0:
                    offset_in_archive = None

                child = VfsNode(
                    pid=pid,
                    offset=offset_in_archive,
                    size_c=file_size,
                    size_u=file_size,
                    v_path=path,
                    v_hash=path_hash,
                    ext_hash=ext_hash32,
                )

                db.node_add(child)
        '''
        return archives

    def adf_type_map_save(self, adf_map, adf_missing):
        adf_list = []

        for k, v in adf_map.items():
            with io.BytesIO() as f:
                pickle.dump(v, f)
                adf_list.append((k, 0, bytes(f.getbuffer())))

        for type_id, missing_in in adf_missing:
            adf_list.append((type_id, missing_in, bytes()))

        result = self.db_execute_many(
            "INSERT OR IGNORE INTO core_adf_types VALUES (?,?,?)", adf_list, dbg='adf_type_map_save')
        self.db_conn.commit()
        self.db_changed_signal.call()

    def adf_type_map_load(self):
        result = self.db_query_all("SELECT * FROM core_adf_types", dbg='adf_type_map_load')

        adf_map = {}
        adf_missing = set()
        for k, miss, b in result:
            if len(b) > 0:
                with io.BytesIO(b) as f:
                    v = pickle.load(f)
                adf_map[k] = v
            elif miss is not None and miss != 0:
                adf_missing.add((k, miss))
            else:
                raise NotImplemented(f'Unknown type record: {k}, {miss}, {b}')

        return adf_map, adf_missing

    def generate_cache_file_name(self, node: VfsNode):
        pid = node.pid
        parent_nodes = []
        parent_paths = []
        while pid is not None:
            parent_node = self.node_where_uid(pid)
            pid = parent_node.pid
            parent_nodes.append(parent_node)
            pp = None
            if parent_node.p_path is not None:
                prefix, end0, end1 = common_prefix(parent_node.p_path, self.game_info.game_dir)
                f, e = os.path.splitext(end0)
                if e != '.tab':
                    pp = end0
            else:
                pp = parent_node.v_hash_to_str() + '.dat'
            if pp is not None:
                parent_paths.append(pp)
        cache_dir = os.path.join(self.working_dir, '__CACHE__/', *parent_paths[::-1])
        file_name = os.path.join(cache_dir, node.v_hash_to_str() + '.dat')

        global dumped_cache_dir
        if not dumped_cache_dir:
            dumped_cache_dir = True
            self.logger.log(f'CACHE DIRECTORY -> {cache_dir}')

        return file_name

    def file_obj_from(self, node: VfsNode):
        compression_type = node.compression_type_get()

        if node.file_type == FTYPE_ARC:
            return open(node.p_path, 'rb')
        elif node.file_type == FTYPE_TAB:
            return self.file_obj_from(self.node_where_uid(node.pid))
        elif compression_type in {compression_v3_zlib}:
            file_name = self.generate_cache_file_name(node)
            if not os.path.isfile(file_name):
                parent_node = self.node_where_uid(node.pid)
                with ArchiveFile(self.file_obj_from(parent_node)) as pf:
                    pf.seek(node.offset)
                    buffer_in = pf.read(node.size_c)

                self.logger.log(f'B: id:{node.uid}, pid:{node.pid}, v:{node.v_path}, p:{node.p_path}, cs:{node.size_c}, us:{node.size_u}')
                buffer_out = extract_aaf(ArchiveFile(io.BytesIO(buffer_in)))
                self.logger.log(f'E: id:{node.uid}, pid:{node.pid}, v:{node.v_path}, p:{node.p_path}, cs:{node.size_c}, us:{node.size_u}')

                make_dir_for_file(file_name)
                with open(file_name, 'wb') as fo:
                    fo.write(buffer_out)

                return io.BytesIO(buffer_out)
            else:
                return open(file_name, 'rb')

        elif compression_type in {compression_v4_01_zlib, compression_v4_03_zstd, compression_v4_04_oo}:
            file_name = self.generate_cache_file_name(node)

            if not os.path.isfile(file_name):
                parent_node = self.node_where_uid(node.pid)
                make_dir_for_file(file_name)
                good_blocks = []
                bad_blocks = []
                buffer_out = b''

                blocks = node.blocks_get(self)

                with self.file_obj_from(parent_node) as f_in:
                    for bi, (block_offset, compressed_len, uncompressed_len) in enumerate(blocks):
                        f_in.seek(block_offset)
                        in_buffer = f_in.read(compressed_len)

                        if compression_type in {compression_v4_01_zlib}:
                            buffer_ret = zlib.decompress(in_buffer)
                            ret = len(buffer_ret)
                            # buffer_ret = in_buffer
                            # ret = compressed_len
                        elif compression_type in {compression_v4_03_zstd}:
                            dc = zstd.ZstdDecompressor()
                            buffer_ret = dc.decompress(in_buffer)
                            ret = len(buffer_ret)
                        else:
                            if compressed_len == uncompressed_len:
                                buffer_ret, ret = in_buffer, len(in_buffer)
                            else:
                                buffer_ret, ret = self.decompress_oodle_lz.decompress(
                                    in_buffer, compressed_len, uncompressed_len)

                        bb = (bi, ret, block_offset, compressed_len, uncompressed_len)
                        if ret == uncompressed_len:
                            good_blocks.append(bb)
                            buffer_out = buffer_out + buffer_ret
                        else:
                            bad_blocks.append(bb)
                            buffer_out = buffer_out + in_buffer

                with open(file_name, 'wb') as f_out:
                    f_out.write(buffer_out)

                all_blocks = good_blocks + bad_blocks
                all_blocks.sort()
                if bad_blocks:
                    label = 'BAAD'
                else:
                    label = 'GOOD'

                if bad_blocks:
                    self.logger.trace('{}: ct:{}, cf:{}, sc:{}, su:{}, bnn:{}, bl:{}, f:{}'.format(
                        label, node.compression_type_get(), node.compression_flag_get(), node.size_c, node.size_u,
                        len(blocks) > 0, all_blocks, file_name,
                    ))

                return io.BytesIO(buffer_out)
            else:
                return open(file_name, 'rb')

        elif compression_type != compression_00_none:
            self.logger.log(f'NOT IMPLEMENTED: COMPRESSION TYPE {compression_type}: B: id:{node.uid}, pid:{node.pid}, v:{node.v_path}, p:{node.p_path}, cs:{node.size_c}, us:{node.size_u}')
            raise EDecaUnknownCompressionType(compression_type)
        elif node.file_type == FTYPE_ADF_BARE:
            parent_node = self.node_where_uid(node.pid)
            return self.file_obj_from(parent_node)
        elif node.pid is not None:
            parent_node = self.node_where_uid(node.pid)
            pf = self.file_obj_from(parent_node)
            pf.seek(node.offset)
            pf = SubsetFile(pf, node.size_u)
            return pf
        elif node.p_path is not None:
            return open(node.p_path, 'rb')
        else:
            raise Exception('NOT IMPLEMENTED: DEFAULT')

    def lookup_equipment_from_name(self, name):
        if self._lookup_equipment_from_name is None:
            return None

        return self._lookup_equipment_from_name.get(name, None)

    def lookup_equipment_from_hash(self, name_hash):
        if self._lookup_equipment_from_hash is None:
            return None

        return self._lookup_equipment_from_hash.get(name_hash, None)

    def lookup_translation_from_name(self, name, default=None):
        if self._lookup_translation_from_name is None:
            return default

        return self._lookup_translation_from_name.get(name, default)

    def lookup_note_from_file_path(self, path):
        if self._lookup_note_from_file_path is None:
            return ''

        return self._lookup_note_from_file_path.get(path, '')

'''
--vfs-fs dropzone --vfs-archive patch_win64 --vfs-archive archives_win64 --vfs-fs .
'''

'''
tab/arc - file archive {hash, file}
aaf - compressed single file
sarc - file archive: {filename, hash, file}
avtx - directx image archives can contain multiple MIP levels
headerless-avtx - directx image archives with no header probably connected to avtx files can contain multiple MIP levels
adf - typed files with objects/type/...
'''
