import os
import io
import sqlite3
import pickle
import re
import numpy as np
from typing import List

import deca.util
from deca.file import ArchiveFile, SubsetFile
from deca.ff_types import *
from deca.ff_determine import determine_file_type_and_size
from deca.ff_aaf import extract_aaf
from deca.decompress import DecompressorOodleLZ
from deca.util import make_dir_for_file
from deca.game_info import game_info_load
from deca.hashes import hash32_func, hash48_func, hash64_func, hash_all_func
from deca.ff_gtoc import GtocArchiveEntry, GtocFileEntry
from deca.db_types import *


language_codes = [
    'chi',  # Chinese
    'eng',  # English
    'fre',  # French
    'ger',  # German
    'jap',  # Japanese
    'pol',  # Polish
    'rus',  # Russian
    'sch',  # Simplified Chinese
    'spa',  # Spanish
    'swe',  # Swedish
]


def regexp(expr, item):
    if item is None or expr is None:
        return False
    if isinstance(expr, str):
        expr = expr.encode('ascii')
    if isinstance(item, str):
        item = item.encode('ascii')
    reg = re.compile(expr)
    return reg.search(item) is not None


def common_prefix(s0, s1):
    cnt = 0
    while len(s0) > cnt and len(s1) > cnt and s0[cnt] == s1[cnt]:
        cnt += 1
    return s0[:cnt], s0[cnt:], s1[cnt:]


compression_type_mask = 0xFF
compression_type_shift = 0
compression_flag_mask = 0xFF00
compression_flag_shift = 8
v_hash_type_mask = 0x0030000
v_hash_type_4 = 0x0010000
v_hash_type_6 = 0x0020000
v_hash_type_8 = 0x0030000
is_processed_file_mask = 1 << 20
is_temporary_file_mask = 1 << 21


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
        'adf_type',
        'ext_hash',
        'magic',
        'pid',
        'index',
        'offset',
        'size_c',
        'size_u',
        'blocks',
        'flags',
        'used_at_runtime_depth',
    )

    def __init__(
            self, uid=None, file_type=None,
            v_hash=None, p_path=None, v_path=None,
            pid=None, index=None,
            offset=None, size_c=None, size_u=None,
            adf_type=None, ext_hash=None, magic=None,
            is_processed_file=False,
            is_temporary_file=False,
            compression_type=0,
            compression_flag=0,
            blocks=None,
            flags=None,
            used_at_runtime_depth=None,
            v_hash_type=v_hash_type_4,
    ):
        self.uid = uid
        self.v_hash = v_hash
        self.v_path = v_path
        self.p_path = p_path
        self.file_type = file_type
        self.adf_type = adf_type
        self.ext_hash = ext_hash
        self.magic = magic

        self.pid = pid
        self.index = index  # index in parent
        self.offset = offset  # offset in parent
        self.size_c = size_c  # compressed size in client
        self.size_u = size_u  # extracted size

        self.blocks = blocks

        if flags is None:
            self.flags = 0
            self.flags |= (compression_type << compression_type_shift) & compression_type_mask
            self.flags |= (compression_flag << compression_flag_shift) & compression_flag_mask
            if is_processed_file:
                self.flags = self.flags | is_processed_file_mask
            if is_temporary_file:
                self.flags = self.flags | is_temporary_file_mask

            self.flags = (self.flags & ~v_hash_type_mask) | v_hash_type

            # make sure type and flag was saved properly
            assert self.compression_type_get() == compression_type
            assert self.compression_flag_get() == compression_flag
        else:
            self.flags = flags

        self.used_at_runtime_depth = used_at_runtime_depth

    def flags_get(self, bit):
        return (self.flags & bit) == bit

    def flags_set(self, bit, value):
        if value:
            value = bit
        else:
            value = 0
        self.flags = (self.flags & ~bit) | value

    def compression_type_get(self):
        return (self.flags & compression_type_mask) >> compression_type_shift

    def compression_type_set(self, value):
        self.flags = \
            (self.flags & ~compression_type_mask) | \
            ((value << compression_type_shift) & compression_type_mask)

    def compression_flag_get(self):
        return (self.flags & compression_flag_mask) >> compression_flag_shift

    def compression_flag_set(self, value):
        self.flags = \
            (self.flags & ~compression_flag_mask) | \
            ((value << compression_flag_shift) & compression_flag_mask)

    def processed_file_get(self):
        return self.flags_get(is_processed_file_mask)

    def processed_file_set(self, value):
        self.flags_set(is_processed_file_mask, value)

    def temporary_file_get(self):
        return self.flags_get(is_temporary_file_mask)

    def temporary_file_set(self, value):
        self.flags_set(is_temporary_file_mask, value)

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
        hash_type = self.flags & v_hash_type_mask
        if hash_type == v_hash_type_4:
            return format_hash32(self.v_hash)
        elif hash_type == v_hash_type_6:
            return format_hash48(self.v_hash)
        elif hash_type == v_hash_type_8:
            return format_hash64(self.v_hash)
        else:
            raise NotImplementedError('hash_type not handled: {:016x}'.format(np.uint64(self.flags)))


core_vnodes_definition = \
    '''
    CREATE TABLE IF NOT EXISTS "core_vnodes" (
        "uid" INTEGER NOT NULL UNIQUE,
        "flags" INTEGER,
        "parent_id" INTEGER,
        "index_in_parent" INTEGER,
        "offset" INTEGER,
        "v_hash" INTEGER,
        "v_path" TEXT,
        "p_path" TEXT,
        "magic" INTEGER,
        "file_type" TEXT,
        "ext_hash" INTEGER,
        "size_c" INTEGER,
        "size_u" INTEGER,
        "adf_type" INTEGER,
        "used_at_runtime_depth" INTEGER,
        PRIMARY KEY("uid")
    )
    '''

core_vnodes_update_all_where_uid = \
    """
    UPDATE core_vnodes SET 
    flags=(?),
    parent_id=(?),
    index_in_parent=(?),
    offset=(?),
    v_hash=(?),
    v_path=(?),
    p_path=(?),
    magic=(?),
    file_type=(?),
    ext_hash=(?),
    size_c=(?),
    size_u=(?),
    adf_type=(?),
    used_at_runtime_depth=(?)
    WHERE uid=(?)
    """

core_vnodes_field_count = 15

core_vnodes_all_fields = '(' + ','.join(['?'] * core_vnodes_field_count) + ')'


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
        magic=v[8],
        file_type=to_str(v[9]),
        ext_hash=v[10],
        size_c=v[11],
        size_u=v[12],
        adf_type=v[13],
        used_at_runtime_depth=v[14],
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
        node.magic,
        to_str(node.file_type),
        node.ext_hash,
        node.size_c,
        node.size_u,
        node.adf_type,
        node.used_at_runtime_depth,
    )
    return v


class VfsDatabase:
    def __init__(
            self, project_file, working_dir, logger,
            init_display=False,
            max_uncompressed_cache_size=(2 * 1024**3)
    ):
        self.project_file = project_file
        self.working_dir = working_dir
        self.logger = logger
        self.game_info = game_info_load(project_file)
        self.decompress_oodle_lz = DecompressorOodleLZ(self.game_info.oo_decompress_dll)
        if 4 == self.game_info.file_hash_size:
            self.file_hash_db_id = 'hash32'
            self.file_hash = hash32_func
            self.file_hash_format = format_hash32
            self.file_hash_type = v_hash_type_4
            self.ext_hash = hash32_func
        elif 8 == self.game_info.file_hash_size:
            self.file_hash_db_id = 'hash64'
            self.file_hash = hash64_func
            self.file_hash_format = format_hash64
            self.file_hash_type = v_hash_type_8
            self.ext_hash = hash32_func
        else:
            raise NotImplementedError('File Hash Size of {} Not Implemented'.format(self.game_info.file_hash_size))

        os.makedirs(working_dir, exist_ok=True)

        if init_display:
            logger.log('OPENING: {} {}'.format(self.game_info.game_dir, working_dir))

        # setup data base
        self.db_filename = os.path.join(self.working_dir, 'db', 'core.db')
        make_dir_for_file(self.db_filename)

        self.db_conn = sqlite3.connect(self.db_filename)
        # self.db_conn.text_factory = bytes
        self.db_conn.create_function("REGEXP", 2, regexp)
        self.db_cur = self.db_conn.cursor()

        self.db_setup()

        # setup in memory uncompressed cache
        # self.uncompressed_cache_max_size = max_uncompressed_cache_size
        # self.uncompressed_cache_map = {}
        # self.uncompressed_cache_lru = []

    def shutdown(self):
        self.decompress_oodle_lz.shutdown()

    def logger_set(self, logger):
        self.logger = logger

    def handle_exception(self, dbg, exc: sqlite3.OperationalError):
        if len(exc.args) == 1 and exc.args[0] == 'database is locked':
            self.logger.log(f'{dbg}: Waiting on database...')
        else:
            print(dbg, exc, exc.args)
            raise

    def db_execute_one(self, stmt, params=None, dbg='db_execute_one'):
        if params is None:
            params = []

        while True:
            try:
                result = self.db_cur.execute(stmt, params)
                break
            except sqlite3.OperationalError as exc:
                self.handle_exception(dbg, exc)

        return result

    def db_execute_many(self, stmt, params=None, dbg='db_execute_many'):
        if params is None:
            params = []

        while True:
            try:
                result = self.db_cur.executemany(stmt, params)
                break
            except sqlite3.OperationalError as exc:
                self.handle_exception(dbg, exc)

        return result

    def db_query_one(self, stmt, params=None, dbg='db_query_one'):
        if params is None:
            params = []

        while True:
            try:
                result = self.db_cur.execute(stmt, params)
                result = result.fetchone()
                break
            except sqlite3.OperationalError as exc:
                self.handle_exception(dbg, exc)

        return result

    def db_query_all(self, stmt, params=None, dbg='db_query_all'):
        if params is None:
            params = []

        while True:
            try:
                result = self.db_cur.execute(stmt, params)
                result = result.fetchall()
                break
            except sqlite3.OperationalError as exc:
                self.handle_exception(dbg, exc)

        return result

    def db_reset(self):
        self.db_execute_one('DROP INDEX IF EXISTS core_vnode_blocks_index_vnode_uid;')
        self.db_execute_one('DROP INDEX IF EXISTS core_vpath_to_vnode;')
        self.db_execute_one('DROP INDEX IF EXISTS core_vhash_to_vnode;')

        self.db_execute_one('DROP TABLE IF EXISTS core_vnode_blocks;')
        self.db_execute_one('DROP TABLE IF EXISTS core_vnodes;')
        self.db_execute_one('DROP TABLE IF EXISTS core_hash_strings;')
        self.db_execute_one('DROP TABLE IF EXISTS core_hash_string_references;')
        self.db_execute_one('DROP TABLE IF EXISTS core_adf_types;')

        self.db_execute_one('VACUUM;')

        self.db_conn.commit()

        self.db_setup()

    def db_setup(self):
        self.db_execute_one(core_vnodes_definition)
        self.db_execute_one(
            '''
            CREATE INDEX IF NOT EXISTS "core_vpath_to_vnode" ON "core_vnodes" ("v_path"	ASC);
            '''
        )
        self.db_execute_one(
            '''
            CREATE INDEX IF NOT EXISTS "core_vhash_to_vnode" ON "core_vnodes" ("v_hash"	ASC);
            '''
        )

        self.db_execute_one(
            '''
            CREATE TABLE IF NOT EXISTS "core_vnode_blocks" (
                "vnode_uid" INTEGER,
                "block_index" INTEGER,
                "block_offset" INTEGER,
                "block_length_compressed" INTEGER,
                "block_length_uncompressed" INTEGER,
                PRIMARY KEY ("vnode_uid", "block_index")
            );
            '''
        )
        self.db_execute_one(
            '''
            CREATE INDEX IF NOT EXISTS "core_vnode_blocks_index_vnode_uid" ON "core_vnode_blocks" ("vnode_uid" ASC);
            '''
        )

        self.db_execute_one(
            '''
            CREATE TABLE IF NOT EXISTS "core_hash_strings" (
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
            CREATE INDEX IF NOT EXISTS "core_hash32_asc" ON "core_hash_strings" ("hash32"	ASC);
            '''
        )
        self.db_execute_one(
            '''
            CREATE INDEX IF NOT EXISTS "core_hash48_asc" ON "core_hash_strings" ("hash48"	ASC);
            '''
        )
        self.db_execute_one(
            '''
            CREATE INDEX IF NOT EXISTS "core_hash64_asc" ON "core_hash_strings" ("hash64"	ASC);
            '''
        )

        self.db_execute_one(
            '''
            CREATE TABLE IF NOT EXISTS "core_hash_string_references" (
                "hash_row_id" INTEGER NOT NULL,
                "src_node" INTEGER,
                "is_adf_field_name" INTEGER,
                "used_at_runtime" INTEGER,
                "possible_file_types" INTEGER,
                PRIMARY KEY ("hash_row_id", "src_node", "is_adf_field_name", "used_at_runtime", "possible_file_types")
            );
            '''
        )

        self.db_execute_one(
            '''
            CREATE TABLE IF NOT EXISTS "core_adf_types" (
                "hash" INTEGER NOT NULL,
                "missing_in" INTEGER,
                "pickle" BLOB,
                PRIMARY KEY ("hash", "missing_in", "pickle")
            );
            '''
        )

        self.db_execute_one(
            '''
            CREATE TABLE IF NOT EXISTS "core_gtoc_archive_def" (
                "src_uid" INTEGER NOT NULL,
                "path_hash32" INTEGER NOT NULL,
                "archive_magic" INTEGER NOT NULL,
                PRIMARY KEY ("src_uid", "path_hash32", "archive_magic")
            );
            '''
        )
        self.db_execute_one(
            'CREATE INDEX IF NOT EXISTS "core_gtoc_archive_def_path_hash32_asc" ON "core_gtoc_archive_def" ("path_hash32" ASC)')
        self.db_execute_one(
            'CREATE INDEX IF NOT EXISTS "core_gtoc_archive_def_archive_magic_asc" ON "core_gtoc_archive_def" ("archive_magic" ASC)')

        self.db_execute_one(
            '''
            CREATE TABLE IF NOT EXISTS "core_gtoc_file_entry" (
                "def_row_id" INTEGER NOT NULL,
                "def_index" INTEGER NOT NULL,
                "offset" INTEGER,
                "file_size" INTEGER NOT NULL,
                "path_string_row_id" INTEGER NOT NULL,
                PRIMARY KEY ("def_row_id", "def_index")
            );
            '''
        )

        self.db_execute_one(
            'CREATE INDEX IF NOT EXISTS "core_gtoc_file_entry_def_row_id_asc" ON "core_gtoc_file_entry" ("def_row_id" ASC)')

        self.db_execute_one(
            'CREATE INDEX IF NOT EXISTS "core_gtoc_file_entry_def_index_asc" ON "core_gtoc_file_entry" ("def_index" ASC)')

        self.db_conn.commit()

    def node_where_uid(self, uid):
        r1 = self.db_query_one(
            "select * from core_vnodes where uid == (?)",
            [uid],
            dbg='node_where_uid')
        # todo load blocks
        r1 = db_to_vfs_node(r1)
        return r1

    def nodes_where_match(self, v_hash=None, v_path=None, v_path_like=None, v_path_regexp=None, uid_only=False):
        params = []
        wheres = []

        if v_hash is not None:
            params.append(v_hash)
            wheres.append('v_hash == (?)')

        if v_path is not None:
            if isinstance(v_path, bytes):
                v_path = v_path.decode('utf-8')
            params.append(v_path)
            wheres.append('v_path == (?)')

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

        if len(wheres) > 0:
            where_str = ' WHERE ' + wheres[0]
            for ws in wheres[1:]:
                where_str = where_str + ' AND ' + ws
        else:
            where_str = ''

        if uid_only:
            result_str = 'uid'
        else:
            result_str = '*'

        if params:
            nodes = self.db_query_all("SELECT " + result_str + " FROM core_vnodes " + where_str, params, dbg='nodes_where_match')
        else:
            nodes = self.db_query_all("SELECT " + result_str + " FROM core_vnodes", dbg='nodes_where_match_all')

        # todo load blocks
        if uid_only:
            return [v[0] for v in nodes]
        else:
            return [db_to_vfs_node(node) for node in nodes]

    def nodes_select_vpath_uid_where_vpath_not_null_type_not_symlink(self):
        result = self.db_query_all(
            "SELECT v_path, uid FROM core_vnodes WHERE v_path IS NOT NULL AND (file_type != 'symlink' OR file_type IS NULL)",
            dbg='nodes_select_vpath_uid_where_vpath_not_null_type_not_symlink')
        return result

    def nodes_where_unmapped_select_uid(self):
        result = self.db_query_all(
            "SELECT uid FROM core_vnodes WHERE (file_type is NULL or (file_type != (?) AND file_type != (?))) AND v_path IS NULL AND p_path IS NULL",
            [FTYPE_ARC, FTYPE_TAB], dbg='nodes_where_unmapped_select_uid')
        return [v[0] for v in result]

    def nodes_where_flag_select_uid(self, mask, value, dbg='nodes_where_flag_select_uid'):
        uids = self.db_query_all(
            "select uid from core_vnodes where flags & (?) == (?)", [mask, value], dbg=dbg)
        return [uid[0] for uid in uids]

    def nodes_where_processed_select_uid(self, processed):
        mask = is_processed_file_mask
        if processed:
            value = is_processed_file_mask
        else:
            value = 0
        return self.nodes_where_flag_select_uid(mask, value, dbg='nodes_where_processed_select_uid')

    def nodes_where_temporary_select_uid(self, temporary):
        mask = is_temporary_file_mask
        if temporary:
            value = is_temporary_file_mask
        else:
            value = 0
        return self.nodes_where_flag_select_uid(mask, value, dbg='nodes_where_temporary_select_uid')

    def nodes_where_f_type_select_uid_v_hash_processed(self, file_type):
        if file_type is None:
            results = self.db_query_all(
                "select uid, v_hash, ((flags & (?)) == (?)) from core_vnodes where file_type IS NULL",
                [is_processed_file_mask, is_processed_file_mask],
                dbg='nodes_where_f_type_select_uid_v_hash_processed')

        else:
            results = self.db_query_all(
                "select uid, v_hash, ((flags & (?)) == (?)) from core_vnodes where file_type == (?)",
                [is_processed_file_mask, is_processed_file_mask, file_type],
                dbg='nodes_where_f_type_select_uid_v_hash_processed')
        return results

    def nodes_where_v_hash_select_uid_v_hash_processed(self, v_hash):
        results = self.db_query_all(
            "select uid, v_hash, ((flags & (?)) == (?)) from core_vnodes where (v_hash == (?)) and (offset not null)",
            [is_processed_file_mask, is_processed_file_mask, v_hash],
            dbg='nodes_where_v_hash_select_uid_v_hash_processed')
        return results

    def nodes_where_ext_hash_select_uid_v_hash_processed(self, ext_hash):
        results = self.db_query_all(
            "select uid, v_hash, ((flags & (?)) == (?)) from core_vnodes where (ext_hash == (?)) and (offset not null)",
            [is_processed_file_mask, is_processed_file_mask, ext_hash],
            dbg='nodes_where_ext_hash_select_uid_v_hash_processed')
        return results

    def nodes_where_vpath_endswith_select_uid_v_hash_processed(self, suffix):
        if isinstance(suffix, bytes):
            suffix = suffix.decode('utf-8')
        suffix = '%' + suffix
        results = self.db_query_all(
            "select uid, v_hash, ((flags & (?)) == (?)) from core_vnodes where (v_path LIKE (?)) and (offset not null)",
            [is_processed_file_mask, is_processed_file_mask, suffix],
            dbg='nodes_where_vpath_endswith_select_uid_v_hash_processed')
        return results

    def nodes_select_distinct_vhash(self):
        result = self.db_query_all(
            "SELECT DISTINCT v_hash FROM core_vnodes", dbg='nodes_select_distinct_vhash')
        result = [r[0] for r in result if r[0] is not None]
        return result

    def nodes_select_distinct_vpath(self):
        result = self.db_query_all(
            "SELECT DISTINCT v_path FROM core_vnodes", dbg='nodes_select_distinct_vpath')
        result = [to_bytes(r[0]) for r in result if r[0] is not None]
        return result

    def nodes_select_distinct_vpath_where_vhash(self, v_hash):
        result = self.db_query_all(
            "SELECT DISTINCT v_path FROM core_vnodes WHERE v_hash == (?)", [v_hash], dbg='nodes_select_distinct_vpath')
        result = [to_bytes(r[0]) for r in result if r[0] is not None]
        return result

    def hash_string_select_distinct_string(self):
        result = self.db_query_all(
            "SELECT DISTINCT string FROM core_hash_strings", dbg='hash_string_select_distinct_string')
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
                "SELECT rowid, string , hash32, hash48, hash64, ext_hash32 FROM core_hash_strings " + where_str,
                params,
                dbg='hash_string_match'
            )
        else:
            result = self.db_query_all(
                "SELECT rowid, string , hash32, hash48, hash64, ext_hash32 FROM core_hash_strings",
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
            wheres.append('(hash_row_id == (?))')

        if len(wheres) > 0:
            where_str = ' WHERE ' + wheres[0]
            for ws in wheres[1:]:
                where_str = where_str + ' AND ' + ws
        else:
            where_str = ''

        if params:
            result = self.db_query_all(
                "SELECT * FROM core_hash_string_references " + where_str,
                params,
                dbg='hash_string_references_match'
            )
        else:
            result = self.db_query_all(
                "SELECT * FROM core_hash_string_references",
                dbg='hash_string_references_match_all'
            )

        return result

    def nodes_delete_where_uid(self, uids):
        self.db_execute_many(
            "DELETE FROM core_vnodes WHERE uid=(?)", uids, dbg='nodes_delete_where_uid'
        )
        self.db_conn.commit()

    def nodes_add_many(self, nodes):
        db_nodes = [db_from_vfs_node(node) for node in nodes]

        self.db_execute_many(
            f"insert into core_vnodes values {core_vnodes_all_fields}",
            db_nodes,
            dbg='nodes_add_many:insert_nodes'
        )
        self.db_conn.commit()

        blocks = []
        for node in nodes:
            if node.blocks:
                result = self.db_query_all(
                    "SELECT uid FROM core_vnodes WHERE parent_id=(?) and index_in_parent=(?)",
                    [node.pid, node.index],
                    dbg='nodes_add_many:select_nodes'
                )

                node.uid = result[0][0]

                for bi, block in enumerate(node.blocks):
                    blocks.append((node.uid, bi, block[0], block[1], block[2]))

        if blocks:
            self.db_execute_many(
                "insert into core_vnode_blocks values (?,?,?,?,?)",
                blocks,
                dbg='nodes_add_many:insert_blocks'
            )
            self.db_conn.commit()

    def node_update_many(self, nodes: set):
        db_nodes = [db_from_vfs_node(node) for node in nodes]
        db_nodes = [db_node[1:] + db_node[0:1] for db_node in db_nodes]
        self.db_execute_many(core_vnodes_update_all_where_uid, db_nodes, dbg='node_update_many')
        self.db_conn.commit()

    def hash_string_add_many_basic(self, hash_list):
        # (string, h4, h6, h8, ext_hash32)
        hash_list_str = [(to_str(h[0]), h[1], h[2], h[3], h[4]) for h in hash_list]
        hash_list_str_unique = list(set(hash_list_str))
        self.db_execute_many(
            "INSERT OR IGNORE INTO core_hash_strings VALUES (?,?,?,?,?)",
            hash_list_str_unique,
            dbg='hash_string_add_many_basic:0:insert'
        )
        self.db_conn.commit()

        hash_list_map = {}
        str_to_row_map = {}
        for rec in hash_list_str_unique:
            result = self.db_query_all(
                "SELECT rowid FROM core_hash_strings WHERE string=(?) and hash32=(?) and hash48=(?) and hash64=(?) and ext_hash32=(?)",
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
            "INSERT OR IGNORE INTO core_hash_string_references VALUES (?,?,?,?,?)",
            ref_list,
            dbg='hash_string_add_many:0:insert')
        self.db_conn.commit()

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
                "SELECT rowid FROM core_gtoc_archive_def WHERE (src_uid=(?)) AND (path_hash32=(?)) AND (archive_magic=(?))",
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
                "SELECT rowid, src_uid, path_hash32, archive_magic FROM core_gtoc_archive_def " + where_str,
                params,
                dbg='gtoc_archive_where_hash32_magic:0:select'
            )
        else:
            result = self.db_query_all(
                "SELECT rowid, src_uid, path_hash32, archive_magic FROM core_gtoc_archive_def",
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
                    core_hash_strings.hash32, 
                    core_hash_strings.ext_hash32, 
                    core_hash_strings.string 
                FROM core_gtoc_file_entry
                INNER JOIN core_hash_strings ON core_gtoc_file_entry.path_string_row_id=core_hash_strings.ROWID
                WHERE def_row_id = (?)
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

    def adf_type_map_load(self):
        result = self.db_query_all("SELECT * FROM core_adf_types", dbg='adf_type_map_load')

        adf_map = {}
        adf_missing = set()
        for k, miss, b in result:
            if len(b) > 0:
                with io.BytesIO(b) as f:
                    v = pickle.load(f)
                adf_map[k] = v
            elif miss is not None and miss != 1:
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
        return file_name

    def file_obj_from(self, node: VfsNode):
        compression_type = node.compression_type_get()

        if node.file_type == FTYPE_ARC:
            return open(node.p_path, 'rb')
        elif node.file_type == FTYPE_TAB:
            return self.file_obj_from(self.node_where_uid(node.pid))
        elif compression_v3_zlib == node.compression_type_get():
            file_name = self.generate_cache_file_name(node)
            if not os.path.isfile(file_name):
                parent_node = self.node_where_uid(node.pid)
                with ArchiveFile(self.file_obj_from(parent_node)) as pf:
                    pf.seek(node.offset)
                    buffer_in = pf.read(node.size_c)

                buffer_out = extract_aaf(ArchiveFile(io.BytesIO(buffer_in)))

                make_dir_for_file(file_name)
                with open(file_name, 'wb') as fo:
                    fo.write(buffer_out)

                return io.BytesIO(buffer_out)
            else:
                return open(file_name, 'rb')

        elif compression_type in {compression_v4_03_oo, compression_v4_04_oo}:
            file_name = self.generate_cache_file_name(node)

            if not os.path.isfile(file_name):
                parent_node = self.node_where_uid(node.pid)
                make_dir_for_file(file_name)
                good_blocks = []
                bad_blocks = []
                buffer_out = b''

                if node.blocks is None:
                    blocks = [(node.offset, node.size_c, node.size_u)]
                else:
                    blocks = node.blocks

                with self.file_obj_from(parent_node) as f_in:
                    for bi, (block_offset, compressed_len, uncompressed_len) in enumerate(blocks):
                        f_in.seek(block_offset)
                        in_buffer = f_in.read(compressed_len)
                        buffer_ret, ret = self.decompress_oodle_lz.decompress(in_buffer, compressed_len, uncompressed_len)
                        if ret == uncompressed_len:
                            good_blocks.append((bi, ret, block_offset, compressed_len, uncompressed_len))
                            buffer_out = buffer_out + buffer_ret
                        else:
                            bad_blocks.append((bi, ret, block_offset, compressed_len, uncompressed_len))
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
                        node.blocks is not None, all_blocks, file_name,
                    ))

                return io.BytesIO(buffer_out)
            else:
                return open(file_name, 'rb')

        elif compression_type != compression_00_none:
            raise Exception(f'NOT IMPLEMENTED: COMPRESSION TYPE {compression_type}')
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

    def determine_file_type(self, node: VfsNode):
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

                if node.compression_type_get() in {compression_v4_03_oo, compression_v4_04_oo}:
                    # todo special case for jc4 /rage2 compression needs to be cleaned up
                    with self.file_obj_from(node) as f:
                        node.file_type, _, node.magic = determine_file_type_and_size(f, node.size_u)
                else:
                    with self.file_obj_from(node) as f:
                        node.file_type, node.size_u, node.magic = determine_file_type_and_size(f, node.size_c)

        if node.file_type == FTYPE_AAF:
            node.compression_type_set(compression_v3_zlib)
            with self.file_obj_from(node) as f:
                node.file_type, node.size_u, node.magic = determine_file_type_and_size(f, node.size_u)

        if node.file_type == FTYPE_ADF0:
            with ArchiveFile(self.file_obj_from(node)) as f:
                _ = f.read_u32()  # magic
                adf_type = f.read_u32()
            node.adf_type = adf_type


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
