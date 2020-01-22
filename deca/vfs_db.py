import os
import io
import sqlite3
import pickle
import re

from deca.hash_jenkins import hash_little
from deca.file import ArchiveFile, SubsetFile
from deca.ff_types import *
from deca.ff_determine import determine_file_type_and_size
from deca.ff_aaf import extract_aaf
from deca.util import make_dir_for_file
from deca.game_info import game_info_load


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
    if isinstance(item, str):
        item = item.encode('ascii')
    reg = re.compile(expr)
    return reg.search(item) is not None


def to_bytes(s):
    if isinstance(s, str):
        s = s.encode('ascii', 'ignore')
    return s


def propose_h4(h4list, vpath, pnode, is_field_name=0, possible_ftypes=None, used_at_runtime=None):
    ptypes = 0

    if isinstance(vpath, str):
        vpath = vpath.encode('ascii', 'ignore')
    elif isinstance(vpath, bytes):
        try:
            vpath.decode('utf-8')
        except UnicodeDecodeError:
            # if logger is not None:
            #     logger.log('propose: BAD STRING NOT UTF-8 {}'.format(vpath))
            return None
    else:
        # if logger is not None:
        #     logger.log('propose: BAD STRING {}'.format(vpath))
        return None

    vpath = vpath.replace(b'\\\\', b'/').replace(b'\\', b'/')

    p = None
    if pnode is not None:
        p = pnode.uid

    if possible_ftypes is None:
        pass
    elif isinstance(possible_ftypes, list):
        for pt in possible_ftypes:
            ptypes = ptypes | ftype_list[pt]
    else:
        ptypes = ptypes | ftype_list[possible_ftypes]

    rec = (hash_little(vpath), vpath, p, is_field_name, used_at_runtime, ptypes)

    h4list.append(rec)

    return rec


def propose_h6(h6list, vpath, pnode):
    p = None
    if pnode is not None:
        p = pnode.uid

    rec = (hash_little(vpath), vpath, p)

    h6list.append(rec)

    return rec


class VfsNode:
    def __init__(
            self, uid=None, ftype=None, compressed=False,
            vhash=None, pvpath=None, vpath=None, pid=None, level=0, index=None, offset=None,
            size_c=None, size_u=None, processed=False, used_at_runtime_depth=None,
            adf_type=None, sarc_ext_hash=None):
        self.uid = uid
        self.ftype = ftype
        self.adf_type = adf_type
        self.sarc_type = sarc_ext_hash
        self.is_compressed = compressed
        self.vpath = vpath
        self.vhash = vhash
        self.pvpath = pvpath
        self.pid = pid
        self.level = level
        self.index = index  # index in parent
        self.offset = offset  # offset in parent
        self.size_c = size_c  # compressed size in client
        self.size_u = size_u  # extracted size
        self.used_at_runtime_depth = used_at_runtime_depth
        self.processed = processed

    def file_type(self):
        if self.is_compressed:
            return self.ftype + '.z'
        else:
            return self.ftype

    def is_valid(self):
        return self.uid is not None and self.uid != 0

    def __str__(self):
        info = []
        if self.ftype is not None:
            info.append('ft:{}'.format(self.file_type()))
        if self.vhash is not None:
            info.append('h:{:08X}'.format(self.vhash))
        if self.vpath is not None:
            info.append('v:{}'.format(self.vpath))
        if self.pvpath is not None:
            info.append('p:{}'.format(self.pvpath))
        if len(info) == 0:
            info.append('child({},{})'.format(self.pid, self.index))
        return ' '.join(info)


def db_to_vfs_node(v):
    # v = [int(v[0]), v[1], v[2], int(v[3]), v[4]] + [int(i) for i in v[5:]]
    node = VfsNode(
        uid=v[0], ftype=v[1], vpath=to_bytes(v[2]), vhash=v[3], pvpath=v[4],
        pid=v[5], index=v[6], level=v[7], compressed=v[8], offset=v[9],
        size_c=v[10], size_u=v[11], used_at_runtime_depth=v[12], adf_type=v[13], sarc_ext_hash=v[14],
        processed=v[15],
    )
    return node


def db_from_vfs_node(node):
    v = (
        node.uid, node.ftype, node.vpath, node.vhash, node.pvpath,
        node.pid, node.index, node.level, node.is_compressed, node.offset,
        node.size_c, node.size_u, node.used_at_runtime_depth, node.adf_type, node.sarc_type,
        node.processed
    )
    return v


class VfsDatabase:
    def __init__(self, project_file, working_dir, logger, init_display=False):
        self.project_file = project_file
        self.working_dir = working_dir
        self.logger = logger
        self.game_info = game_info_load(project_file)

        os.makedirs(working_dir, exist_ok=True)

        if init_display:
            logger.log('OPENING: {} {}'.format(self.game_info.game_dir, working_dir))

        self.db_filename = os.path.join(self.working_dir, 'db', 'core.db')
        make_dir_for_file(self.db_filename)

        self.db_conn = sqlite3.connect(self.db_filename)
        self.db_conn.create_function("REGEXP", 2, regexp)
        self.db_cur = self.db_conn.cursor()

        self.db_setup()

        # track info from ADFs
        self.map_adftype_usage = {}
        self.adf_missing_types = {}

    def logger_set(self, logger):
        self.logger = logger

    def db_execute_one(self, stmt, params=None, dbg='db_execute_one'):
        if params is None:
            params = []

        while True:
            try:
                result = self.db_cur.execute(stmt, params)
                break
            except sqlite3.OperationalError as ex:
                self.logger.log(f'{dbg}: Waiting on database...')

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
                self.logger.log(f'{dbg}: Waiting on database...')

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
                self.logger.log(f'{dbg}: Waiting on database...')

        return result

    def db_reset(self):
        self.db_execute_one('DROP INDEX IF EXISTS core_vpath_to_vnode;')
        self.db_execute_one('DROP INDEX IF EXISTS core_vhash_to_vnode;')

        self.db_execute_one('DROP TABLE IF EXISTS core_vnodes;')
        self.db_execute_one('DROP TABLE IF EXISTS core_hash4;')
        self.db_execute_one('DROP TABLE IF EXISTS core_hash4_references;')
        self.db_execute_one('DROP TABLE IF EXISTS core_hash6;')
        self.db_execute_one('DROP TABLE IF EXISTS core_hash6_references;')
        self.db_execute_one('DROP TABLE IF EXISTS core_adf_types;')

        self.db_execute_one('VACUUM;')

        self.db_conn.commit()

        self.db_setup()

    def db_setup(self):
        self.db_execute_one(
            '''
            CREATE TABLE IF NOT EXISTS "core_vnodes" (
                "uid" INTEGER NOT NULL UNIQUE,
                "ftype" TEXT,
                "vpath" TEXT,
                "vpath_hash" INTEGER,
                "ppath" TEXT,
                "parent_id" INTEGER,
                "index_in_parent" INTEGER,
                "level" INTEGER,
                "is_compressed" INTEGER,
                "offset" INTEGER,
                "size_c" INTEGER,
                "size_u" INTEGER,
                "used_at_runtime_depth" INTEGER,
                "gdcc_adf_type" INTEGER,
                "ext_hash" INTEGER,
                "processed" INTEGER,
                PRIMARY KEY("uid")
            );
            '''
        )
        self.db_execute_one(
            '''
            CREATE TABLE IF NOT EXISTS "core_hash4" (
                "hash" INTEGER NOT NULL,
                "string" TEXT,
                PRIMARY KEY ("hash", "string")
            );
            '''
        )
        self.db_execute_one(
            '''
            CREATE TABLE IF NOT EXISTS "core_hash4_references" (
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
            CREATE TABLE IF NOT EXISTS "core_hash6" (
                "hash" INTEGER NOT NULL,
                "string" TEXT,
                PRIMARY KEY ("hash", "string")
            );
            '''
        )
        self.db_execute_one(
            '''
            CREATE TABLE IF NOT EXISTS "core_hash6_references" (
                "hash_row_id" INTEGER NOT NULL,
                "src_node" INTEGER,
                PRIMARY KEY ("hash_row_id", "src_node")
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
            CREATE INDEX IF NOT EXISTS "core_vpath_to_vnode" ON "core_vnodes" ("vpath"	ASC);
            '''
        )
        self.db_execute_one(
            '''
            CREATE INDEX IF NOT EXISTS "core_vhash_to_vnode" ON "core_vnodes" ("vpath_hash"	ASC);
            '''
        )

        self.db_conn.commit()

    def nodes_select_all(self):
        nodes = self.db_query_all(
            "select * from core_vnodes", dbg='nodes_select_uids')
        return [db_to_vfs_node(node) for node in nodes]

    def node_where_uid(self, uid):
        r1 = self.db_query_one(
            "select * from core_vnodes where uid == (?)", [uid], dbg='node_where_uid')
        r1 = db_to_vfs_node(r1)
        return r1

    def nodes_where_processed_select_uid(self, processed):
        uids = self.db_query_all(
            "select uid from core_vnodes where processed == (?)", [processed], dbg='nodes_where_processed_select_uid')
        return [uid[0] for uid in uids]

    def nodes_where_ftype_select_uid(self, ftype):
        uids = self.db_query_all(
            "select uid from core_vnodes where ftype == (?)", [ftype], dbg='nodes_where_ftype_select_uid')
        return [uid[0] for uid in uids]

    def nodes_where_vhash(self, vhash):
        nodes = self.db_query_all(
            "select * from core_vnodes where vpath_hash == (?)", [vhash], dbg='nodes_where_vhash')
        return [db_to_vfs_node(node) for node in nodes]

    def nodes_where_vpath(self, vpath):
        nodes = self.db_query_all(
            "select * from core_vnodes where vpath == (?)", [vpath], dbg='nodes_where_vpath')
        return [db_to_vfs_node(node) for node in nodes]

    def nodes_where_vpath_regex_2(self, regex_0, regex_1):
        nodes = self.db_query_all(
            "select * from core_vnodes where (vpath REGEXP (?)) AND (vpath REGEXP (?))",
            [regex_0, regex_1],
            dbg='nodes_where_vpath_regex_2'
        )
        return [db_to_vfs_node(node) for node in nodes]

    def nodes_select_distinct_vhash(self):
        result = self.db_query_all(
            "SELECT DISTINCT vpath_hash FROM core_vnodes", dbg='nodes_select_distinct_vhash')
        result = [r[0] for r in result if r[0] is not None]
        return result

    def nodes_select_distinct_vpath(self):
        result = self.db_query_all(
            "SELECT DISTINCT vpath FROM core_vnodes", dbg='nodes_select_distinct_vpath')
        result = [to_bytes(r[0]) for r in result if r[0] is not None]
        return result

    def nodes_select_distinct_vpath_where_vhash(self, vhash):
        result = self.db_query_all(
            "SELECT DISTINCT vpath FROM core_vnodes WHERE vpath_hash == (?)", [vhash], dbg='nodes_select_distinct_vpath')
        result = [to_bytes(r[0]) for r in result if r[0] is not None]
        return result

    def hash4_select_distinct_string(self):
        result = self.db_query_all(
            "SELECT DISTINCT string FROM core_hash4", dbg='hash4_select_distinct_string')
        result = [to_bytes(r[0]) for r in result if r[0] is not None]
        return result

    def hash4_select_all_to_dict(self):
        result = self.db_query_all(
            "SELECT rowid, hash, string FROM core_hash4", dbg='hash4_select_all_to_dict')
        result = [(r[0], (r[1], to_bytes(r[2]))) for r in result]
        result = dict(result)
        return result

    def hash4_where_vhash_select_all(self, vhash):
        result = self.db_query_all(
            "SELECT rowid, hash, string FROM core_hash4 WHERE hash == (?)", [vhash], dbg='hash4_where_vhash_select_all')
        return [(r[0], r[1], to_bytes(r[2])) for r in result]

    def hash4_references_select_all(self):
        result = self.db_query_all(
            "SELECT * FROM core_hash4_references", dbg='hash4_references_select_all')
        return result

    def hash4_references_where_h4rowid_select_all(self, rowid):
        result = self.db_query_all(
            "SELECT * FROM core_hash4_references WHERE hash_row_id == (?)", [rowid], dbg='hash4_references_where_h4rowid_select_all')
        return result

    def hash6_where_vhash_select_all(self, vhash):
        result = self.db_query_all(
            "SELECT rowid, hash, string FROM core_hash6 WHERE hash == (?)", [vhash], dbg='hash6_where_vhash_select_all')
        return [(r[0], r[1], to_bytes(r[2])) for r in result]

    def node_add_one(self, node: VfsNode):
        while True:
            try:
                result = self.db_cur.execute(
                    "insert into core_vnodes values (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)", db_from_vfs_node(node))
                break
            except sqlite3.OperationalError:
                self.logger.log('TIMEOUT: node_add_one: Waiting on database...')

        self.db_conn.commit()

        node.uid = result.lastrowid

        return node

    def node_add_many(self, nodes):
        db_nodes = [db_from_vfs_node(node) for node in nodes]

        while True:
            try:
                result = self.db_cur.executemany(
                    "insert into core_vnodes values (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)", db_nodes)
                break
            except sqlite3.OperationalError:
                self.logger.log('TIMEOUT: node_add_many: Waiting on database...')

        self.db_conn.commit()

    def node_update_many(self, nodes: list):
        db_nodes = [db_from_vfs_node(node) for node in nodes]
        db_nodes = [db_node[1:] + db_node[0:1] for db_node in db_nodes]
        while True:
            try:
                result = self.db_cur.executemany(
                    """
                    update core_vnodes set 
                    ftype=(?),
                    vpath=(?),
                    vpath_hash=(?),
                    ppath=(?),
                    parent_id=(?),
                    index_in_parent=(?),
                    level=(?),
                    is_compressed=(?),
                    offset=(?),
                    size_c=(?),
                    size_u=(?),
                    used_at_runtime_depth=(?),
                    gdcc_adf_type=(?),
                    ext_hash=(?),
                    processed=(?)
                    where uid=(?)
                    """, db_nodes)
                break
            except sqlite3.OperationalError:
                self.logger.log('TIMEOUT: node_update_many: Waiting on database...')
        self.db_conn.commit()

    def hash4_add_many(self, hash_list):
        hash_list_str = [(h[0], h[1]) for h in hash_list]

        hash_list_str_unique = list(set(hash_list_str))
        while True:
            try:
                result = self.db_cur.executemany(
                    "INSERT OR IGNORE INTO core_hash4 VALUES (?,?)", hash_list_str_unique)
                break
            except sqlite3.OperationalError:
                self.logger.log('TIMEOUT: hash4_add_many:insert:0: Waiting on database...')

        self.db_conn.commit()

        hash_list_map = {}
        for rec in hash_list_str_unique:
            while True:
                try:
                    result = self.db_cur.execute(
                        "SELECT rowid FROM core_hash4 WHERE hash==(?) and string==(?)", rec)
                    result = result.fetchall()
                    break
                except sqlite3.OperationalError as exc:
                    self.logger.log('TIMEOUT: hash4_add_many:select:0: Waiting on database...')

            # we expect one and only one match for a hash+string
            assert len(result) == 1
            row_id = result[0][0]
            hash_list_map[rec] = row_id

        row_ids = [hash_list_map[rec] for rec in hash_list_str]

        ref_list = [(r, h[2], h[3], h[4], h[5]) for r, h in zip(row_ids, hash_list)]
        ref_list = list(set(ref_list))
        while True:
            try:
                result = self.db_cur.executemany(
                    "INSERT OR IGNORE INTO core_hash4_references VALUES (?,?,?,?,?)", ref_list)
                break
            except sqlite3.OperationalError:
                self.logger.log('TIMEOUT: hash4_add_many:insert:1: Waiting on database...')

        self.db_conn.commit()

    def hash6_add_many(self, hash_list):
        hash_list_str = [(h[0], h[1]) for h in hash_list]

        hash_list_str_unique = list(set(hash_list_str))
        while True:
            try:
                result = self.db_cur.executemany(
                    "INSERT OR IGNORE INTO core_hash6 VALUES (?,?)", hash_list_str_unique)
                break
            except sqlite3.OperationalError:
                self.logger.log('TIMEOUT: hash6_add_many:insert:0: Waiting on database...')

        self.db_conn.commit()

        hash_list_map = {}
        for rec in hash_list_str_unique:
            while True:
                try:
                    result = self.db_cur.execute(
                        "SELECT rowid FROM core_hash6 WHERE hash==(?) and string==(?)", rec)
                    result = result.fetchall()
                    break
                except sqlite3.OperationalError as exc:
                    self.logger.log('TIMEOUT: hash6_add_many:select:0: Waiting on database...')

            # we expect one and only one match for a hash+string
            assert len(result) == 1
            row_id = result[0][0]
            hash_list_map[rec] = row_id

        row_ids = [hash_list_map[rec] for rec in hash_list_str]

        ref_list = [(r, h[2]) for r, h in zip(row_ids, hash_list)]
        ref_list = list(set(ref_list))
        while True:
            try:
                result = self.db_cur.executemany(
                    "INSERT OR IGNORE INTO core_hash6_references VALUES (?,?)", ref_list)
                break
            except sqlite3.OperationalError:
                self.logger.log('TIMEOUT: hash6_add_many:insert:1: Waiting on database...')

        self.db_conn.commit()

    def adf_type_map_save(self, adf_map, adf_missing):
        adf_list = []

        for k, v in adf_map.items():
            with io.BytesIO() as f:
                pickle.dump(v, f)
                adf_list.append((k, 0, bytes(f.getbuffer())))

        for type_id, missing_in in adf_missing:
            adf_list.append((type_id, missing_in, bytes()))

        while True:
            try:
                result = self.db_cur.executemany(
                    "INSERT OR IGNORE INTO core_adf_types VALUES (?,?,?)", adf_list)
                break
            except sqlite3.OperationalError:
                self.logger.log('TIMEOUT: adf_type_map_save: Waiting on database...')

        self.db_conn.commit()

    def adf_type_map_load(self):
        while True:
            try:
                result = self.db_cur.execute(
                    "select * from core_adf_types")
                result = result.fetchall()
                break
            except sqlite3.OperationalError:
                self.logger.log('TIMEOUT: adf_type_map_load: Waiting on database...')

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

    def file_obj_from(self, node: VfsNode, mode='rb'):
        if node.ftype == FTYPE_ARC:
            return open(node.pvpath, mode)
        elif node.ftype == FTYPE_TAB:
            return self.file_obj_from(self.node_where_uid(node.pid))
        elif node.is_compressed:
            cache_dir = self.working_dir + '__CACHE__/'
            os.makedirs(cache_dir, exist_ok=True)
            file_name = cache_dir + '{:08X}.dat'.format(node.vhash)
            if not os.path.isfile(file_name):
                pnode = self.node_where_uid(node.pid)
                with ArchiveFile(self.file_obj_from(pnode, mode)) as pf:
                    pf.seek(node.offset)
                    extract_aaf(pf, file_name)
            return open(file_name, mode)
        elif node.ftype == FTYPE_ADF_BARE:
            pnode = self.node_where_uid(node.pid)
            return self.file_obj_from(pnode, mode)
        elif node.pid is not None:
            pnode = self.node_where_uid(node.pid)
            pf = self.file_obj_from(pnode, mode)
            pf.seek(node.offset)
            pf = SubsetFile(pf, node.size_u)
            return pf
        elif node.pvpath is not None:
            return open(node.pvpath, mode)
        else:
            raise Exception('NOT IMPLEMENTED: DEFAULT')

    def determine_ftype(self, node: VfsNode):
        if node.ftype is None:
            node.is_compressed = False
            if node.offset is None:
                node.ftype = FTYPE_SYMLINK
            else:
                with self.file_obj_from(node) as f:
                    node.ftype, node.size_u = determine_file_type_and_size(f, node.size_c)

        if node.ftype is FTYPE_AAF:
            node.is_compressed = True
            with self.file_obj_from(node) as f:
                node.ftype, node.size_u = determine_file_type_and_size(f, node.size_u)



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

'''
VfsTable

uid : u64
ftype : u32
vhash : u32
pvpath : str
vpath : str
pid : u64
index : u64  # index in parent
offset : u64 # offset in parent
size_c : u64 # compressed size in client
size_u : u64 # extracted size

VfshashToNameMap
VfsNameToHashMap
'''