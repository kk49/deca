import os
import io
import sqlite3
import pickle
import re
import zstandard as zstd
import numpy as np
from typing import List

from deca.util import common_prefix
from deca.errors import *
from deca.file import ArchiveFile, SubsetFile
from deca.ff_types import *
from deca.ff_aaf import extract_aaf
from deca.decompress import DecompressorOodleLZ
from deca.util import make_dir_for_file, to_unicode, DecaSignal
from deca.game_info import game_info_load
from deca.hashes import hash32_func, hash48_func, hash64_func, hash_all_func
from deca.ff_gtoc import GtocArchiveEntry, GtocFileEntry
from deca.db_types import *


class DbCrossGame(DbBase):
    def __init__(self,  working_dir, logger):
        super().__init__(os.path.join(working_dir, 'cross_game.db'), logger)

        self.db_execute_one(
            '''
            CREATE TABLE IF NOT EXISTS "field_strings" (
                "string" TEXT,
                "hash32" INTEGER NOT NULL,
                "hash48" INTEGER NOT NULL,
                "hash64" INTEGER NOT NULL,
                "ext_hash32" INTEGER NOT NULL,
                PRIMARY KEY ("string", "hash32", "hash48", "hash64", "ext_hash32")
            );
            '''
        )

    def hash_string_add_many_basic(self, hash_list):
        # (string, h4, h6, h8, ext_hash32)
        hash_list_str = [(to_str(h[0]), h[1], h[2], h[3], h[4]) for h in hash_list]
        hash_list_str_unique = list(set(hash_list_str))
        self.db_execute_many(
            "INSERT OR IGNORE INTO field_strings VALUES (?,?,?,?,?)",
            hash_list_str_unique,
            dbg='hash_string_add_many_basic:0:insert'
        )
        self.db_conn.commit()
        self.db_changed_signal.call()

        hash_list_map = {}
        str_to_row_map = {}
        for rec in hash_list_str_unique:
            result = self.db_query_all(
                "SELECT rowid FROM field_strings WHERE string=(?) and hash32=(?) and hash48=(?) and hash64=(?) and ext_hash32=(?)",
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

        # row_ids = [hash_list_map[rec] for rec in hash_list_str]
        # ref_list = [(r, h[5], h[6], h[7], int(np.int64(np.uint64(h[8])))) for r, h in zip(row_ids, hash_list)]
        # ref_list = list(set(ref_list))
        # self.db_execute_many(
        #     "INSERT OR IGNORE INTO core_string_references VALUES (?,?,?,?,?)",
        #     ref_list,
        #     dbg='hash_string_add_many:0:insert')
        # self.db_conn.commit()
        # self.db_changed_signal.call()