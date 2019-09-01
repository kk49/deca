import re
from typing import List
from .ff_adf import *
from .xlsxwriter_hack import DecaWorkBook
from .ff_adf_amf import AABB
from .ff_adf_amg_gltf import DecaGltf, DecaGltfNode, Deca3dMatrix
from .vfs_db import VfsStructure, VfsNode


def generate_export_file_path(vfs, export_path, vnode):
    if vnode.vpath is None:
        ofile = os.path.join(export_path, '{:08X}.dat'.format(vnode.vhash))
    else:
        ofile = os.path.join(export_path, '{}'.format(vnode.vpath.decode('utf-8')))
    vfs.logger.log('Exporting {}'.format(ofile))
    ofiledir = os.path.dirname(ofile)
    os.makedirs(ofiledir, exist_ok=True)

    return ofile


def adf_export_xlsx_0x0b73315d(vfs: VfsStructure, vnode: VfsNode, export_path, allow_overwrite):
    ofile = generate_export_file_path(vfs, export_path, vnode)
    fn = ofile + '.xlsx'

    adf = adf_node_read(vfs, vnode)

    if not allow_overwrite and os.path.exists(fn):
        raise EDecaFileExists(fn)

    src = adf.table_instance_values[0]
    book = DecaWorkBook(fn)

    cell_formats = []
    for att in src['Attribute']:
        fg_color = src['ColorData'][att['FGColorIndex'] - 1]
        bg_color = src['ColorData'][att['BGColorIndex'] - 1]
        fmt = book.add_format()
        # fmt.set_bg_color('#{:06X}'.format(bg_color))
        # fmt.set_font_color('#{:06X}'.format(fg_color))
        cell_formats.append(fmt)

    for srcw in src['Sheet']:
        cols = srcw['Cols']
        rows = srcw['Rows']
        name = srcw['Name']
        cellindex = srcw['CellIndex']
        worksheet = book.add_worksheet(name.decode('utf-8'))
        for i in range(rows):
            for j in range(cols):
                r = i
                c = j

                cidx = cellindex[j + cols * i]
                cdata = src['Cell'][cidx]

                ctype = cdata['Type']
                didx = cdata['DataIndex']
                aidx = cdata['AttributeIndex']
                cell_format = cell_formats[aidx]
                if ctype == 0:
                    if didx < len(src['BoolData']):
                        worksheet.write_boolean(r, c, src['BoolData'][didx], cell_format=cell_format)
                    else:
                        # worksheet.write_string(r, c, 'Missing BoolData {}'.format(didx), cell_format=cell_format)
                        pass
                elif ctype == 1:
                    if didx < len(src['StringData']):
                        worksheet.write_string(r, c, src['StringData'][didx].decode('utf-8'), cell_format=cell_format)
                    else:
                        # worksheet.write_string(r, c, 'Missing StringData {}'.format(didx), cell_format=cell_format)
                        pass
                elif ctype == 2:
                    if didx < len(src['ValueData']):
                        worksheet.write_number(r, c, src['ValueData'][didx], cell_format=cell_format)
                    else:
                        # worksheet.write_string(r, c, 'Missing ValueData {}'.format(didx), cell_format=cell_format)
                        pass
                else:
                    raise NotImplemented('Unhandled Cell Type {}'.format(ctype))

    book.close()


def adf_export_amf_model_0xf7c20a69(vfs: VfsStructure, vnode: VfsNode, export_path, allow_overwrite, save_to_one_dir=True):
    vfs.logger.log('Exporting {}: Started'.format(vnode.vpath.decode('utf-8')))
    gltf = DecaGltf(vfs, export_path, vnode.vpath.decode('utf-8'), save_to_one_dir=save_to_one_dir)

    with gltf.scene():
        with DecaGltfNode(gltf, name=os.path.basename(vnode.vpath)):
            gltf.export_modelc(vnode.vpath, None)

    gltf.gltf_save()
    vfs.logger.log('Exporting {}: Complete'.format(vnode.vpath.decode('utf-8')))


def adf_export_mdic_0xb5b062f1(vfs: VfsStructure, vnode: VfsNode, export_path, allow_overwrite, save_to_one_dir=True):
    vfs.logger.log('Exporting {}: Started'.format(vnode.vpath.decode('utf-8')))
    gltf = DecaGltf(vfs, export_path, vnode.vpath.decode('utf-8'), save_to_one_dir=save_to_one_dir)

    with gltf.scene():
        adf = adf_node_read(vfs, vnode)
        mdic = adf.table_instance_values[0]
        models = [list(vfs.map_hash_to_vpath.get(m, [None]))[0] for m in mdic['Models']]
        instances = mdic['Instances']
        aabb = AABB(all6=mdic['AABB'])
        mid = aabb.mid()
        with DecaGltfNode(gltf, name=os.path.basename(vnode.vpath)) as mdic_node:
            mdic_node.translation = list(mid)
            for instance in instances:
                transform = Deca3dMatrix(col_major=instance['Transform'])
                transform.translate(-mid)
                model_index = instance['ModelIndex']
                model = models[model_index]
                if model is None:
                    vfs.logger.log('Missing model 0x{:08x}'.format(model_index))
                else:
                    gltf.export_modelc(model, transform)

    gltf.gltf_save()
    vfs.logger.log('Exporting {}: Complete'.format(vnode.vpath.decode('utf-8')))


def adf_export_node(vfs: VfsStructure, vnode: VfsNode, export_path, allow_overwrite=False, save_to_one_dir=True):
    adf = adf_node_read(vfs, vnode)
    if adf is not None:
        if len(adf.table_instance) == 1:
            if adf.table_instance[0].type_hash == 0x0B73315D:
                adf_export_xlsx_0x0b73315d(vfs, vnode, export_path, allow_overwrite)
            elif adf.table_instance[0].type_hash == 0xf7c20a69:  # AmfModel
                adf_export_amf_model_0xf7c20a69(vfs, vnode, export_path, allow_overwrite, save_to_one_dir=save_to_one_dir)
            elif adf.table_instance[0].type_hash == 0xb5b062f1:  # mdic
                adf_export_mdic_0xb5b062f1(vfs, vnode, export_path, allow_overwrite, save_to_one_dir=save_to_one_dir)
            else:
                fn = export_path + '.txt'

                if not allow_overwrite and os.path.exists(fn):
                    raise EDecaFileExists(fn)

                s = adf.dump_to_string()

                with open(fn, 'wt') as f:
                    f.write(s)


def adf_export(vfs: VfsStructure, vnodes: List[VfsNode], export_path, allow_overwrite=False, save_to_one_dir=True):
    # export other files
    for vnode in vnodes:
        try:
            adf_export_node(vfs, vnode, export_path, allow_overwrite=allow_overwrite, save_to_one_dir=save_to_one_dir)
        except EDecaFileExists as e:
            vfs.logger.log(
                'WARNING: Extraction failed overwrite disabled and {} exists, skipping'.format(e.args[0]))
