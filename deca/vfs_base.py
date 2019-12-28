import os

from deca.hash_jenkins import hash_little
from deca.file import ArchiveFile, SubsetFile
from deca.ff_types import *
from deca.ff_determine import determine_file_type_and_size
from deca.game_info import GameInfo
from deca.ff_aaf import extract_aaf


class VfsPathNode:
    def __init__(self, vpath):
        self.vpath = vpath
        self.vhash = None
        self.vfsnodes = []
        self.src = []  # [[SARC, vfsnode], [RTPC, vfsnode], [ADF, vfsnode], [GUESS], ]
        self.used_at_runtime = False
        self.possible_ftypes = set()


class VfsPathMap:
    def __init__(self, logger):
        self.logger = logger
        self.nodes = {}

    def merge(self, other):
        for k, v in other.nodes.items():
            v2 = self.nodes.get(k, VfsPathNode(k))

            if v2.vhash is None:
                v2.vhash = v.vhash
            elif v.vhash is not None:
                if v.vhash != v2.vhash:
                    raise Exception('merge: {}: hash mismatch {} != {}'.format(k, v.vhash, v2.vhash))

            v2.vfsnodes = v2.vfsnodes + v.vfsnodes
            v2.src = v2.src + v.src
            v2.used_at_runtime = v2.used_at_runtime or v.used_at_runtime
            for kf in v.possible_ftypes:
                v2.possible_ftypes.add(kf)

            self.nodes[k] = v2

    def propose(self, vpath, src, used_at_runtime=False, vnode=None, possible_ftypes=FTYPE_ANY_TYPE):
        """
        Add proposed vpath to map
        :param vpath: string representing vpath
        :param src: currently a vaguely formated list of information about where the vpath came from # TODO
        :param used_at_runtime: bool that indicates if this usage is known to be used by the executable gotten from procmon
        :param vnode: include vnode if the vnode was explicitly labeled, like in a sarc
        :param possible_ftypes: Value, or [Value] of file types that are expect to be connected to vpath
        :return: VpatjInference object
        """

        if isinstance(vpath, str):
            vpath = vpath.encode('ascii', 'ignore')
        elif isinstance(vpath, bytes):
            try:
                vpath.decode('utf-8')
            except UnicodeDecodeError:
                self.logger.log('propose: BAD STRING NOT UTF-8 {}'.format(vpath))
                return None
        else:
            self.logger.log('propose: BAD STRING {}'.format(vpath))
            return None

        vpath = vpath.replace(b'\\\\', b'/').replace(b'\\', b'/')

        if vpath in self.nodes:
            iv = self.nodes[vpath]
        else:
            iv = VfsPathNode(vpath)
            iv.vhash = hash_little(vpath)

        iv.used_at_runtime = iv.used_at_runtime or used_at_runtime

        if vnode is not None:
            if vnode.offset is None:
                iv.vfsnodes.append(vnode)
            else:
                iv.vfsnodes = [vnode] + iv.vfsnodes

        if src is not None:
            iv.src.append(src)

        if isinstance(possible_ftypes, list):
            for pf in possible_ftypes:
                iv.possible_ftypes.add(pf)
        elif possible_ftypes is not None:
            iv.possible_ftypes.add(possible_ftypes)

        self.nodes[vpath] = iv

        return iv


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
        self.children = set()
        self.used_at_runtime_depth = used_at_runtime_depth
        self.processed = processed

    def file_type(self):
        if self.is_compressed:
            return self.ftype + '.z'
        else:
            return self.ftype

    def is_valid(self):
        return self.uid is not None and self.uid != 0

    def used_depth_set(self, v):
        if self.used_at_runtime_depth is None or self.used_at_runtime_depth > v:
            self.used_at_runtime_depth = v
            for ch in self.children:
                ch.used_depth_set(v+1)

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


class VfsBase:
    def __init__(self, game_info: GameInfo, working_dir, logger):
        self.game_info = game_info

        self.worlds = ['', 'worlds/base/']
        for widx in range(8):
            self.worlds.append('worlds/world{}/'.format(widx))

        self.working_dir = working_dir
        self.logger = logger

        # basic node tracking
        self.uid = 0
        self.table_vfsnode = [VfsNode()]
        self.map_uid_to_vfsnode = {}  # TODO currently redundant, may always be

        # tracking node hashs
        self.map_hash_to_vnodes = {}
        self.hash_present = set()

        # track info from ADFs
        self.map_name_usage = {}
        self.map_vhash_usage = {}
        self.map_adftype_usage = {}
        self.adf_missing_types = {}

        # track possible vpaths
        self.possible_vpath_map = VfsPathMap(self.logger)

        # results from connecting vpaths to vfsnodes
        self.hash_map_present = set()
        self.hash_map_missing = set()
        self.hash_map_conflict = set()
        self.map_hash_to_vpath = {}
        self.map_vpath_to_vfsnodes = {}

    def logger_set(self, logger):
        self.logger = logger

    def file_obj_from(self, node: VfsNode, mode='rb'):
        if node.ftype == FTYPE_ARC:
            return open(node.pvpath, mode)
        elif node.ftype == FTYPE_TAB:
            return self.file_obj_from(self.table_vfsnode[node.pid])
        elif node.is_compressed:
            cache_dir = self.working_dir + '__CACHE__/'
            os.makedirs(cache_dir, exist_ok=True)
            file_name = cache_dir + '{:08X}.dat'.format(node.vhash)
            if not os.path.isfile(file_name):
                pnode = self.table_vfsnode[node.pid]
                with ArchiveFile(self.file_obj_from(pnode, mode)) as pf:
                    pf.seek(node.offset)
                    extract_aaf(pf, file_name)
            return open(file_name, mode)
        elif node.ftype == FTYPE_ADF_BARE:
            pnode = self.table_vfsnode[node.pid]
            return self.file_obj_from(pnode, mode)
        elif node.pid is not None:
            pnode = self.table_vfsnode[node.pid]
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
                node.ftype = 'symlink'
            else:
                with self.file_obj_from(node) as f:
                    node.ftype, node.size_u = determine_file_type_and_size(f, node.size_c)

        if node.ftype is FTYPE_AAF:
            node.is_compressed = True
            with self.file_obj_from(node) as f:
                node.ftype, node.size_u = determine_file_type_and_size(f, node.size_u)

    def node_add(self, node: VfsNode):
        self.uid = self.uid + 1
        node.uid = self.uid

        self.table_vfsnode.append(node)
        self.map_uid_to_vfsnode[node.uid] = node
        self.determine_ftype(node)

        if node.is_valid():
            if node.vhash is not None:
                self.hash_present.add(node.vhash)
                vl = self.map_hash_to_vnodes.get(node.vhash, [])
                if node.offset is None:
                    vl.append(node)  # put symlinks at end
                else:
                    vl = [node] + vl  # put real files up front
                self.map_hash_to_vnodes[node.vhash] = vl

            if node.pid is not None:
                pnode = self.table_vfsnode[node.pid]
                pnode.children.add(node)
                if pnode.used_at_runtime_depth is not None and \
                   (node.used_at_runtime_depth is None or node.used_at_runtime_depth > (1+pnode.used_at_runtime_depth)):
                    node.used_depth_set(pnode.used_at_runtime_depth + 1)

        return node


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