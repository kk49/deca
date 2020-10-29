import sqlite3
import re
from deca.util import make_dir_for_file, DecaSignal
from deca.hashes import hash32_func, hash_all_func


node_flag_compression_type_mask = 0xFF
node_flag_compression_type_shift = 0
node_flag_compression_flag_mask = 0xFF00
node_flag_compression_flag_shift = 8
node_flag_v_hash_type_mask = 0x3 << 16
node_flag_v_hash_type_4 = 0x1 << 16
node_flag_v_hash_type_6 = 0x2 << 16
node_flag_v_hash_type_8 = 0x3 << 16

node_flag_temporary_file = 1 << 20
node_flag_processed_file_raw_no_name = 1 << 21
node_flag_processed_file_raw_with_name = 1 << 22
node_flag_processed_file_type = 1 << 23
node_flag_processed_file_specific = 1 << 24


def to_bytes(s):
    if isinstance(s, str):
        s = s.encode('ascii', 'ignore')
    return s


def to_str(s):
    if isinstance(s, bytes):
        s = s.decode('utf-8')
    return s


def make_hash_string_tuple(string):
    string = to_bytes(string)

    period_pos = string.rfind(b'.')

    if period_pos >= 0:
        ext_string = string[period_pos:]
    else:
        ext_string = b''

    ext_hash32 = hash32_func(ext_string)
    hash32, hash48, hash64 = hash_all_func(string)

    return string, hash32, hash48, hash64, ext_hash32


def regexp(expr, item):
    if item is None or expr is None:
        return False
    if isinstance(expr, str):
        expr = expr.encode('ascii')
    if isinstance(item, str):
        item = item.encode('ascii')
    reg = re.compile(expr)
    return reg.search(item) is not None


class DbBase:
    def __init__(self, db_filename, logger):
        self.logger = logger

        self.db_changed_signal = DecaSignal()

        # setup data base
        self.db_filename = db_filename
        make_dir_for_file(self.db_filename)

        self.db_conn = sqlite3.connect(self.db_filename)
        # self.db_conn.text_factory = bytes
        self.db_conn.create_function("REGEXP", 2, regexp)
        self.db_cur = self.db_conn.cursor()

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
