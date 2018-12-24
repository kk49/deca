import os
from deca.ff_aaf import extract_aaf
from deca.file import ArchiveFile

FTYPE_TABARC = 'tabarc'
FTYPE_AAF = 'aaf'
FTYPE_SARC = 'sarc'
FTYPE_AVTX = 'avtx'
FTYPE_NHAVTX = 'nh_avtx'
FTYPE_ADF = 'adf'
FTYPE_DDS = 'dds'
FTYPE_TXT = 'txt'
FTYPE_OBC = 'obc'


class VfsNode:
    def __init__(self, uid=None, ftype=None, hashid=None, p_path=None, v_path=None, pid=None, level=0, index=None, offset=None, size_c=None, size_u=None, processed=False):
        self.uid = uid
        self.ftype = ftype
        self.hashid = hashid
        self.p_path = p_path
        self.v_path = v_path
        self.pid = pid
        self.level = level
        self.index = index  # index in parent
        self.offset = offset  # offset in parent
        self.size_c = size_c  # compressed size in client
        self.size_u = size_u  # extracted size
        self.processed = processed

    def __str__(self):
        info = []
        if self.ftype is not None:
            info.append('ft:{}'.format(self.ftype))
        if self.hashid is not None:
            info.append('h:{:08X}'.format(self.hashid))
        if self.v_path is not None:
            info.append('v:{}'.format(self.v_path))
        if self.p_path is not None:
            info.append('p:{}'.format(self.p_path))
        if len(info) == 0:
            info.append('child({},{})'.format(self.pid, self.index))
        return ' '.join(info)


def file_obj_from(vfs_table, node: VfsNode, work_dir, mode='rb'):

    if node.ftype == FTYPE_TABARC:
        return open(node.p_path, mode)
    elif node.ftype == FTYPE_AAF:
        cache_dir = work_dir + '__CACHE__/'
        os.makedirs(cache_dir, exist_ok=True)
        file_name = cache_dir + '{:08X}.dat'.format(node.hashid)
        if not os.path.isfile(file_name):
            pnode = vfs_table[node.pid]
            with ArchiveFile(file_obj_from(vfs_table, pnode, work_dir, mode)) as pf:
                pf.seek(node.offset)
                extract_aaf(pf, file_name)
        return open(file_name, mode)
    elif node.pid is not None:
        pnode = vfs_table[node.pid]
        pf = file_obj_from(vfs_table, pnode, work_dir, mode)
        pf.seek(node.offset)
        return pf
    else:
        raise Exception('NOT IMPLEMENTED: DEFAULT')


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
hashid : u32
p_path : str
v_path : str
pid : u64
index : u64  # index in parent
offset : u64 # offset in parent
size_c : u64 # compressed size in client
size_u : u64 # extracted size

VfsHashToNameMap
VfsNameToHashMap
'''