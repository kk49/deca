import os
from .db_core import VfsDatabase, VfsNode
from .util import make_dir_for_file


def node_export_fsb5c_processed(
        vfs: VfsDatabase,
        node: VfsNode,
        extract_dir,
        allow_overwrite=False
):
    with vfs.file_obj_from(node) as f:
        buffer = f.read(node.size_u)

    # TODO hack just trim 16 byte header
    buffer = buffer[16:]

    if node.v_path is None:
        ofile = extract_dir + '{:08X}.dat.DECA.fsb'.format(node.v_hash)
    else:
        ofile = extract_dir + '{}.DECA.fsb'.format(node.v_path.decode('utf-8'))

    vfs.logger.log('Exporting {}'.format(ofile))

    make_dir_for_file(ofile)

    if allow_overwrite or not os.path.isfile(ofile):
        with open(ofile, 'wb') as fo:
            fo.write(buffer)
