import os
import pickle
import io
import multiprocessing
import queue
import re
import json
import csv
import time
import sqlite3
import struct

from deca.file import ArchiveFile
from deca.vfs_db import VfsDatabase, VfsNode, propose_h4, propose_h6
from deca.game_info import GameInfo, game_info_load, GameInfoGZ, GameInfoGZB, GameInfoTHCOTW, GameInfoJC3, GameInfoJC4
from deca.errors import EDecaFileExists
from deca.ff_types import *
from deca.ff_txt import load_json
import deca.ff_rtpc
from deca.ff_adf import AdfDatabase, AdfTypeMissing, GdcArchiveEntry, TypeDef
from deca.ff_rtpc import Rtpc
from deca.ff_arc_tab import TabFileV3, TabFileV4
from deca.ff_sarc import FileSarc, EntrySarc
from deca.util import Logger, remove_prefix_if_present, remove_suffix_if_present
from deca.hash_jenkins import hash_little
from deca.ff_determine import determine_file_type_and_size
from deca.kaitai.gfx import Gfx


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


def run_mp_vfs_base(name, project_file, working_dir, q_in, q_out):
    p = MultiProcessVfsBase(name, project_file, working_dir, q_in, q_out)
    p.run()


class MultiProcessVfsBase:
    def __init__(self, name, project_file, working_dir, q_in: multiprocessing.Queue, q_out: multiprocessing.Queue, debug=False):
        self.name = name
        self.q_in = q_in
        self.q_out = q_out
        self.debug = debug

        self.vfs = VfsDatabase(project_file, working_dir, self)

        self.commands = {
            'process_archives_initial': lambda idxs: self.process_by_uid_wrapper(idxs, self.process_archives_initial),
            'process_adf_initial': lambda idxs: self.process_by_uid_wrapper(idxs, self.process_adf_initial),
            'process_rtpc_initial': lambda idxs: self.process_by_uid_wrapper(idxs, self.process_rtpc_initial),
            'process_gfx_initial': lambda idxs: self.process_by_uid_wrapper(idxs, self.process_gfx_initial),
            'process_txt_initial': lambda idxs: self.process_by_uid_wrapper(idxs, self.process_txt_initial),
            'process_vhash_final': lambda idxs: self.process_by_vhash_wrapper(idxs, self.process_vhash_final),
        }

    def send(self, cmd, *params):
        self.q_out.put_nowait((self.name, cmd, params, ))

    def log(self, msg):
        self.send('log', msg)

    def trace(self, msg):
        self.send('trace', msg)

    def run(self):
        keep_running = True
        while keep_running:
            try:
                cmd = self.q_in.get(block=True, timeout=1.0)
                params = cmd[1]
                cmd = cmd[0]

                if cmd is not None:
                    if self.debug:
                        self.log('Processing Command "{}({})"'.format(cmd, len(params)))

                    if cmd == 'exit':
                        keep_running = False
                    else:
                        self.process_command(cmd, params)
                        self.send('cmd_done', cmd)
            except queue.Empty:
                pass
            except Exception as e:
                print('Exception: {}'.format(e))

        self.send('process_done')

    def process_command(self, cmd, params):
        command = self.commands.get(cmd, None)
        if command is None:
            raise NotImplementedError(f'Command not implemented: {cmd}')
        command(*params)

    def process_wrapper(self, indexes, loop, iter):
        nodes_to_add = []
        nodes_to_update = []
        hash4_to_add = []  # hash, string, src, possible_ftypes
        hash6_to_add = []  # hash, string, src
        n_indexes = len(indexes)

        adf_db = AdfDatabase()
        adf_db.load_from_database(self.vfs)

        loop(indexes, iter, adf_db, nodes_to_add, nodes_to_update, hash4_to_add, hash6_to_add)

        n_nodes_to_add = len(nodes_to_add)
        if n_nodes_to_add > 0:
            self.log('Determining file types: {} nodes'.format(len(nodes_to_add)))
            for ii, node in enumerate(nodes_to_add):
                self.send('status', ii + n_indexes, n_nodes_to_add + n_indexes)
                self.vfs.determine_ftype(node)

            self.send('status', n_nodes_to_add + n_indexes, n_nodes_to_add + n_indexes)

            self.log('DATABASE: Inserting {} nodes'.format(len(nodes_to_add)))
            self.vfs.node_add_many(nodes_to_add)

        if len(nodes_to_update) > 0:
            self.log('DATABASE: Updating {} nodes'.format(len(nodes_to_update)))
            self.vfs.node_update_many(nodes_to_update)

        hash4_to_add = list(set(hash4_to_add))
        if len(hash4_to_add) > 0:
            self.log('DATABASE: Inserting {} hash 4 strings'.format(len(hash4_to_add)))
            self.vfs.hash4_add_many(hash4_to_add)

        hash6_to_add = list(set(hash6_to_add))
        if len(hash6_to_add) > 0:
            self.log('DATABASE: Inserting {} hash 6 strings'.format(len(hash6_to_add)))
            self.vfs.hash6_add_many(hash6_to_add)

        self.log('DATABASE: Saving ADF Types')
        adf_db.save_to_database(self.vfs)

    def loop_node_by_uid(self, indexes, iter, adf_db, nodes_to_add, nodes_to_update, hash4_to_add, hash6_to_add):
        n_indexes = len(indexes)
        for i, index in enumerate(indexes):
            self.send('status', i, n_indexes)

            node = self.vfs.node_where_uid(index)
            if node.is_valid():
                updated = iter(node, i, n_indexes, adf_db, nodes_to_add, nodes_to_update, hash4_to_add, hash6_to_add)

                if updated:
                    nodes_to_update.append(node)

        self.send('status', n_indexes, n_indexes)

    def process_by_uid_wrapper(self, indexes, func):
        self.process_wrapper(indexes, self.loop_node_by_uid, func)

    def loop_vhash(self, vhashes, iter, adf_db, nodes_to_add, nodes_to_update, hash4_to_add, hash6_to_add):
        n_indexes = len(vhashes)
        for i, vhash in enumerate(vhashes):
            self.send('status', i, n_indexes)
            iter(vhash, i, n_indexes, adf_db, nodes_to_add, nodes_to_update, hash4_to_add, hash6_to_add)

        self.send('status', n_indexes, n_indexes)

    def process_by_vhash_wrapper(self, indexes, func):
        self.process_wrapper(indexes, self.loop_vhash, func)

    def process_archives_initial(
            self, node, i, n_indexes, adf_db, nodes_to_add, nodes_to_update, hash4_to_add, hash6_to_add):
        debug = False
        ver = self.vfs.game_info.archive_version

        if node.ftype == FTYPE_EXE:
            node.processed = True
            adf_db.extract_types_from_exe(node.pvpath)

        elif node.ftype == FTYPE_ARC:
            # here we add the tab file as a child of the ARC, a trick to make it work with our data model
            node.processed = True
            tab_path = os.path.splitext(node.pvpath)
            tab_path = tab_path[0] + '.tab'
            cnode = VfsNode(ftype=FTYPE_TAB, pvpath=tab_path, pid=node.uid, level=node.level)
            nodes_to_add.append(cnode)
        elif node.ftype == FTYPE_TAB:
            if debug:
                self.log('Processing TAB: {}'.format(node.pvpath))
            node.processed = True
            with ArchiveFile(open(node.pvpath, 'rb'), debug=debug) as f:
                if 3 == ver:
                    tab_file = TabFileV3()
                elif 4 == ver:
                    tab_file = TabFileV4()
                else:
                    raise NotImplementedError('Unknown TAB file version {}'.format(ver))

                tab_file.deserialize(f)

                for i in range(len(tab_file.file_table)):
                    te = tab_file.file_table[i]
                    cnode = VfsNode(
                        vhash=te.hashname, pid=node.uid, level=node.level + 1, index=i,
                        offset=te.offset, size_c=te.size_c, size_u=te.size_u)
                    nodes_to_add.append(cnode)

        elif node.ftype == FTYPE_SARC:
            node.processed = True
            sarc_file = FileSarc()
            sarc_file.header_deserialize(self.vfs.file_obj_from(node))

            for se in sarc_file.entries:
                se: EntrySarc = se
                offset = se.offset
                if offset == 0:
                    offset = None  # sarc files with zero offset are not in file, but reference hash value
                cnode = VfsNode(
                    vhash=se.vhash, pid=node.uid, level=node.level + 1, index=se.index,
                    offset=offset, size_c=se.length, size_u=se.length, vpath=se.vpath,
                    sarc_ext_hash=se.file_extention_hash)

                nodes_to_add.append(cnode)
                propose_h4(hash4_to_add, cnode.vpath, node)

        elif node.vhash == deca.hash_jenkins.hash_little(b'gdc/global.gdcc'):
            # special case starting point for runtime
            node.processed = True
            adf = adf_db.read_node(self.vfs, node)

            cnode_name = b'gdc/global.gdc.DECA'
            cnode = VfsNode(
                vhash=deca.hash_jenkins.hash_little(cnode_name),
                vpath=cnode_name,
                ftype=FTYPE_GDCBODY, pid=node.uid, level=node.level,
                offset=adf.table_instance[0].offset,
                size_c=adf.table_instance[0].size,
                size_u=adf.table_instance[0].size)
            nodes_to_add.append(cnode)

        elif node.ftype in {FTYPE_GDCBODY}:
            pnode = self.vfs.node_where_uid(node.pid)
            adf = adf_db.read_node(self.vfs, pnode)

            for entry in adf.table_instance_values[0]:
                if isinstance(entry, GdcArchiveEntry):
                    # self.logger.log('GDCC: {:08X} {}'.format(entry.vpath_hash, entry.vpath))
                    adf_type = entry.adf_type_hash
                    ftype = None
                    if adf_type is not None:
                        ftype = FTYPE_ADF_BARE
                        # self.logger.log('ADF_BARE: Need Type: {:08x} {}'.format(adf_type, entry.vpath))
                    cnode = VfsNode(
                        vhash=entry.vpath_hash, pid=node.uid, level=node.level + 1, index=entry.index,
                        offset=entry.offset, size_c=entry.size, size_u=entry.size, vpath=entry.vpath,
                        ftype=ftype, adf_type=adf_type)
                    nodes_to_add.append(cnode)
                    propose_h4(hash4_to_add, cnode.vpath, node)

        elif node.sarc_type == 0xb4c9109e or (
                node.vpath is not None and node.vpath.endswith(b'.resourcebundle')):
            node.processed = True
            with ArchiveFile(self.vfs.file_obj_from(node)) as f:
                index = 0
                while f.tell() < node.size_u:
                    vhash = f.read_u32()
                    ext_hash = f.read_u32()
                    size = f.read_u32()
                    offset = f.tell()
                    buffer = f.read(size)

                    cnode = VfsNode(
                        vhash=vhash, pid=node.uid, level=node.level + 1, index=index,
                        offset=offset, size_c=size, size_u=size,
                        sarc_ext_hash=ext_hash)
                    index += 1

                    nodes_to_add.append(cnode)

        else:
            pass

        updated = node.processed
        return updated

    def process_adf_initial(
            self, node: VfsNode, i, n_indexes, adf_db, nodes_to_add, nodes_to_update, hash4_to_add, hash6_to_add):
        updated = False
        try:
            adf = adf_db.read_node(self.vfs, node)

            for sh in adf.table_stringhash:
                vhash = hash_little(sh.value)
                propose_h4(hash4_to_add, sh.value, node)

                if vhash != sh.value_hash:
                    # this is a 6 byte hash
                    propose_h6(hash6_to_add, sh.value, node)

                rp = remove_prefix_if_present(b'intermediate/', sh.value)
                if rp is not None:
                    propose_h4(hash4_to_add, rp, node)

                rp = remove_suffix_if_present(b'.stop', sh.value)
                if rp is None:
                    rp = remove_suffix_if_present(b'.play', sh.value)

                if rp is not None:
                    # self.logger.log('Found possible wavc file from: {}'.format(sh.value))
                    for lng in language_codes:
                        fn = b'sound/dialogue/' + lng.encode('ascii') + b'/' + rp + b'.wavc'
                        propose_h4(hash4_to_add, fn, node, possible_ftypes=[FTYPE_FSB5C])

            for sh in adf.found_strings:
                propose_h4(hash4_to_add, sh, node)
                rp = remove_prefix_if_present(b'intermediate/', sh)
                if rp is not None:
                    propose_h4(hash4_to_add, rp, node)

            for sh in adf.table_name:
                propose_h4(hash4_to_add, sh[1], node, is_field_name=1)

            if len(adf.table_instance_values) > 0 and \
                    adf.table_instance_values[0] is not None and \
                    isinstance(adf.table_instance_values[0], dict):
                obj0 = adf.table_instance_values[0]

                fns = []
                # self name patch files
                if 'PatchLod' in obj0 and 'PatchPositionX' in obj0 and 'PatchPositionZ' in obj0:
                    for world in self.vfs.game_info.worlds:
                        fn = world + 'terrain/hp/patches/patch_{:02d}_{:02d}_{:02d}.streampatch'.format(
                            obj0['PatchLod'], obj0['PatchPositionX'], obj0['PatchPositionZ'])
                        fns.append(fn)
                    fn = 'terrain/jc3/patches/patch_{:02d}_{:02d}_{:02d}.streampatch'.format(
                        obj0['PatchLod'], obj0['PatchPositionX'], obj0['PatchPositionZ'])
                    fns.append(fn)

                # self name environc files
                if adf.table_instance[0].name == b'environ':
                    fn = 'environment/weather/{}.environc'.format(obj0['Name'].decode('utf-8'))
                    fns.append(fn)
                    fn = 'environment/{}.environc'.format(obj0['Name'].decode('utf-8'))
                    fns.append(fn)

                found_any = False
                for fn in fns:
                    if node.vhash == hash_little(fn):
                        if node.vpath is None:
                            node.vpath = fn
                            updated = True
                        propose_h4(hash4_to_add, fn, node, possible_ftypes=[FTYPE_ADF, FTYPE_ADF_BARE])
                        found_any = True

                if len(fns) > 0 and not found_any:
                    self.log('COULD NOT MATCH GENERATED FILE NAME {:08X} {}'.format(node.vhash, fns[0]))

            # for ientry in adf.table_typedef:
            #     adf_type_hash = ientry.type_hash
            #     ev = map_adftype_usage.get(adf_type_hash, set())
            #     ev.add(node.uid)
            #     map_adftype_usage[adf_type_hash] = ev
            #     if ientry.type_hash not in map_typedefs:
            #         map_typedefs[ientry.type_hash] = ientry

        except AdfTypeMissing as ae:
            print('Missing Type {:08x} in {:08X} {} {}'.format(
                ae.type_id, node.vhash, node.vpath, node.pvpath))

        return updated

    def process_rtpc_initial(
            self, node: VfsNode, i, n_indexes, adf_db, nodes_to_add, nodes_to_update, hash4_to_add, hash6_to_add):
        updated = False
        # try:
        with self.vfs.file_obj_from(node) as f:
            buf = f.read(node.size_u)

        rtpc = Rtpc()
        with io.BytesIO(buf) as f:
            rtpc.deserialize(f)

        rnodelist = [rtpc.root_node]

        while len(rnodelist) > 0:
            rnode = rnodelist.pop(0)

            for c in rnode.child_table:
                rnodelist.append(c)

            for p in rnode.prop_table:
                if p.type == deca.ff_rtpc.PropType.type_str.value:
                    s = p.data
                    propose_h4(hash4_to_add, s, node)

                    fn, ext = os.path.splitext(s)
                    if ext in {b'.tga', b'.dds'}:
                        propose_h4(hash4_to_add, fn + b'.ddsc', node, possible_ftypes=[FTYPE_AVTX, FTYPE_DDS])
                    elif ext == b'.skeleton':
                        propose_h4(hash4_to_add, fn + b'.bsk', node, possible_ftypes=[FTYPE_TAG0])
                    elif ext == b'.ragdoll':
                        propose_h4(hash4_to_add, fn + b'.brd', node, possible_ftypes=[FTYPE_TAG0])
                        propose_h4(hash4_to_add, fn + b'.ragdolsettingsc', node, possible_ftypes=[FTYPE_ADF])
                    elif ext == b'.al':
                        propose_h4(hash4_to_add, fn + b'.afsmb', node, possible_ftypes=[FTYPE_RTPC])
                        propose_h4(hash4_to_add, fn + b'.asb', node, possible_ftypes=[FTYPE_RTPC])
                    elif ext == b'.model_xml':
                        propose_h4(hash4_to_add, fn + b'.model_xmlc', node)
                        propose_h4(hash4_to_add, fn + b'.model.xml', node)
                        propose_h4(hash4_to_add, fn + b'.model.xmlc', node)
                        propose_h4(hash4_to_add, fn + b'.xml', node)
                        propose_h4(hash4_to_add, fn + b'.xmlc', node)
                        propose_h4(hash4_to_add, fn + b'.modelc', node)
                    elif len(ext) > 0:
                        propose_h4(hash4_to_add, s + b'c', node, possible_ftypes=[FTYPE_ADF])

        return updated

    def process_gfx_initial(
            self, node: VfsNode, i, n_indexes, adf_db, nodes_to_add, nodes_to_update, hash4_to_add, hash6_to_add):
        updated = False
        with self.vfs.file_obj_from(node) as f:
            buffer = f.read(node.size_u)

        gfx = Gfx.from_bytes(buffer)

        image_tags = {Gfx.TagType.gfx_define_external_image, Gfx.TagType.gfx_define_external_image2}
        for tag in gfx.zlib_body.tags:
            if Gfx.TagType.gfx_exporter_info == tag.record_header.tag_type:
                propose_h4(hash4_to_add, f'ui/{tag.tag_body.name}.gfx', node, possible_ftypes=[FTYPE_GFX])
                for ii in range(255):
                    fn = 'ui/{}_i{:x}.ddsc'.format(tag.tag_body.name, ii)
                    propose_h4(hash4_to_add, fn, node, possible_ftypes=[FTYPE_AVTX, FTYPE_DDS])

            elif tag.record_header.tag_type in image_tags:
                fn = tag.tag_body.file_name
                fn = os.path.basename(fn)
                fn, ext = os.path.splitext(fn)
                fn = f'ui/{fn}.ddsc'
                propose_h4(hash4_to_add, fn, node, possible_ftypes=[FTYPE_AVTX, FTYPE_DDS])

            elif Gfx.TagType.import_assets2 == tag.record_header.tag_type:
                fn = tag.tag_body.url
                fn = os.path.basename(fn)
                fn, ext = os.path.splitext(fn)
                propose_h4(hash4_to_add, f'ui/{tag.tag_body.url}', node, possible_ftypes=[FTYPE_GFX])
                propose_h4(hash4_to_add, f'ui/{fn}.gfx', node, possible_ftypes=[FTYPE_GFX])

        return updated

    def process_txt_initial(
            self, node: VfsNode, i, n_indexes, adf_db, nodes_to_add, nodes_to_update, hash4_to_add, hash6_to_add):
        updated = False

        with self.vfs.file_obj_from(node) as f:
            buffer = f.read(node.size_u)

        json = load_json(buffer)

        # Parse {"0":[]. "1":[]}
        if isinstance(json, dict) and '0' in json and '1' in json:
            for k, v in json.items():
                for item in v:
                    propose_h4(hash4_to_add, item, node)

        return updated

    def process_vhash_final(
            self, vhash, i, n_indexes, adf_db, nodes_to_add, nodes_to_update, hash4_to_add, hash6_to_add):
        nodes = self.vfs.nodes_where_vhash(vhash)
        hash4 = self.vfs.hash4_where_vhash_select_all(vhash)

        missed_vpaths = set()
        h4ref_map = {}
        for rowid, vhash, vpath in hash4:
            missed_vpaths.add(vpath)
            h4ref_map[rowid] = self.vfs.hash4_references_where_h4rowid_select_all(rowid)

        # h4rowid, src_node, is_adf_field_name, used_at_runtime, possible_ftypes in h4ref

        if len(nodes) > 0:
            for node in nodes:
                if node.is_valid():
                    updated = False

                    if node.ftype is None:
                        ftype_int = ftype_list[FTYPE_NO_TYPE]
                    else:
                        ftype_int = ftype_list[node.ftype]

                    for rowid, vhash, vpath in hash4:
                        h4ref = h4ref_map[rowid]

                        if node.vpath is None:
                            for _, src_node, _, _, possible_ftypes in h4ref:
                                if possible_ftypes is None or possible_ftypes == 0:
                                    possible_ftypes = ftype_list[FTYPE_ANY_TYPE]

                                if (ftype_int & possible_ftypes) != 0:
                                    self.trace('vpath:add  {} {:08X} {} {} {}'.format(
                                        vpath, vhash, src_node, possible_ftypes, node.ftype))
                                    node.vpath = vpath
                                    updated = True
                                    break
                                else:
                                    self.log('vpath:skip {} {:08X} {} {} {}'.format(
                                        vpath, vhash, src_node, possible_ftypes, node.ftype))

                        if node.vpath == vpath:
                            for _, _, _, used_at_runtime, _ in h4ref:
                                if used_at_runtime:
                                    node.used_at_runtime_depth = 0
                                    updated = True
                                    break

                    if node.ftype is None and node.vpath is not None:
                        file, ext = os.path.splitext(node.vpath)
                        if ext[0:4] == b'.atx':
                            node.ftype = FTYPE_ATX
                            updated = True
                        elif ext == b'.hmddsc':
                            node.ftype = FTYPE_HMDDSC
                            updated = True

                    missed_vpaths.discard(node.vpath)

                    if updated:
                        nodes_to_update.append(node)

        for vpath in missed_vpaths:
            vhash = hash_little(vpath)
            self.trace('vpath:miss {} {:08X}'.format(vpath, vhash))

        # found_vpaths = list(found_vpaths)
        # found_vpaths.sort()
        # with open(self.working_dir + 'found_vpaths.txt', 'a') as f:
        #     for vp in found_vpaths:
        #         f.write('{}\n'.format(vp.decode('utf-8')))

        #         for s in ss:
        #             hid = hash_little(s)
        #             if hid in self.hash_present:
        #                 if hid in self.map_hash_to_vpath:
        #                     if s != self.map_hash_to_vpath[hid]:
        #                         self.logger.trace('HASH CONFLICT STRINGS: {:08X}: {} != {}'.format(hid, self.map_hash_to_vpath[hid], s))
        #                         self.hash_bad[hid] = (self.map_hash_to_vpath[hid], s)
        #                 else:
        #                     if dump_found_paths:
        #                         f.write('{:08X}\t{}\n'.format(hid, s))
        #                     self.map_hash_to_vpath[hid] = s
        #                     self.map_vpath_to_hash[s] = hid
        #                     found = found + 1
        #
        # self.logger.log('fill in v_paths, mark extensions identified files as ftype')
        #
        # self.logger.log('PROCESS BASELINE VNODE INFORMATION')
        # for idx in range(len(self.table_vfsnode)):
        #     node = self.table_vfsnode[idx]
        #     if node.is_valid() and node.vhash is not None:
        #         hid = node.vhash
        #         if node.vpath is not None:
        #             if hid in self.map_hash_to_vpath:
        #                 if self.map_hash_to_vpath[hid] != node.vpath:
        #                     self.logger.trace('HASH CONFLICT ARCHIVE: {:08X}: {} != {}'.format(hid, self.map_hash_to_vpath[hid], node.vpath))
        #                     self.hash_bad[hid] = (self.map_hash_to_vpath[hid], node.vpath)
        #             else:
        #                 self.map_hash_to_vpath[hid] = node.vpath
        #                 self.map_vpath_to_hash[node.vpath] = hid
        # self.logger.log('PROCESS BASELINE VNODE INFORMATION: found {} hashes, {} mapped'.format(len(self.hash_present), len(self.map_hash_to_vpath)))
        #
        # for idx in range(len(self.table_vfsnode)):
        #     node = self.table_vfsnode[idx]
        #     if node.is_valid() and node.vhash is not None and node.vpath is None:
        #         if node.vhash in self.map_hash_to_vpath:
        #             node.vpath = self.map_hash_to_vpath[node.vhash]
        #
        #     if node.is_valid() and node.vhash is not None:
        #         if node.ftype not in {FTYPE_ARC, FTYPE_TAB}:
        #             if node.vhash in self.map_hash_to_vpath:
        #                 self.hash_map_present.add(node.vhash)
        #             else:
        #                 self.hash_map_missing.add(node.vhash)
        #
        #     if node.is_valid() and node.vpath is not None:
        #         if os.path.splitext(node.vpath)[1][0:4] == b'.atx':
        #             if node.ftype is not None:
        #                 raise Exception('ATX marked as non ATX: {}'.format(node.vpath))
        #             node.ftype = FTYPE_ATX
        #
        #         lst = self.map_vpath_to_vfsnodes.get(node.vpath, [])
        #         if len(lst) > 0 and lst[0].offset is None:  # Do not let symlink be first is list # TODO Sort by accessibility
        #             lst = [node] + lst
        #         else:
        #             lst.append(node)
        #         self.map_vpath_to_vfsnodes[node.vpath] = lst

