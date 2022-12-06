from .ff_adf import *
from .xlsxwriter_hack import DecaWorkBook
from .ff_adf_amf import AABB
from .ff_adf_amf_gltf import DecaGltf, DecaGltfNode, Deca3dMatrix
from .db_core import VfsDatabase, VfsNode


def generate_export_file_path(vfs: VfsDatabase, export_path, vnode: VfsNode, note):
    if vnode.v_path is None:
        ofile = os.path.join(export_path, '{:08X}.dat'.format(vnode.v_hash))
    else:
        ofile = os.path.join(export_path, '{}'.format(vnode.v_path.decode('utf-8')))

    if vnode.file_type == FTYPE_ADF_BARE:
        ofile = ofile + '.gdcc'

    vfs.logger.log('Exporting{}: {}'.format(note, ofile))
    ofiledir = os.path.dirname(ofile)
    os.makedirs(ofiledir, exist_ok=True)

    return ofile


def adf_export_xlsx_0x0b73315d(
        vfs: VfsDatabase,
        adf_db: AdfDatabase,
        vnode: VfsNode,
        export_path,
        allow_overwrite
):
    ofile = generate_export_file_path(vfs, export_path, vnode, ' as XLSX')
    fn = ofile + '.xlsx'

    adf = adf_db.read_node(vfs, vnode)

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
                    worksheet.write_string(r, c, f'DECA: ERROR: cell_type = {ctype}, data_index = {didx}, attr_index = {aidx}')
                    # raise NotImplementedError('Unhandled Cell Type {}'.format(ctype))

    book.close()

    return fn


def adf_export_amf_model_0xf7c20a69(
        vfs: VfsDatabase,
        adf_db: AdfDatabase,
        vnode: VfsNode,
        export_path,
        allow_overwrite,
        save_to_one_dir,
        include_skeleton,
        texture_format,
):
    vfs.logger.log('Exporting {}: Started'.format(vnode.v_path.decode('utf-8')))
    gltf = DecaGltf(
        vfs, export_path, vnode.v_path.decode('utf-8'),
        save_to_one_dir=save_to_one_dir, include_skeleton=include_skeleton, texture_format=texture_format)

    with gltf.scene():
        with DecaGltfNode(gltf, name=os.path.basename(vnode.v_path)):
            gltf.export_modelc(vnode.v_path, None)

    gltf.gltf_save()
    vfs.logger.log('Exporting {}: Complete'.format(vnode.v_path.decode('utf-8')))


def adf_export_mdic_0xb5b062f1(
        vfs: VfsDatabase,
        adf_db: AdfDatabase,
        vnode: VfsNode,
        export_path,
        allow_overwrite,
        save_to_one_dir,
        include_skeleton,
        texture_format,
):
    vfs.logger.log('Exporting {}: Started'.format(vnode.v_path.decode('utf-8')))
    gltf = DecaGltf(
        vfs, export_path, vnode.v_path.decode('utf-8'),
        save_to_one_dir=save_to_one_dir, include_skeleton=include_skeleton, texture_format=texture_format)

    with gltf.scene():
        adf = adf_db.read_node(vfs, vnode)
        mdic = adf.table_instance_values[0]
        models = []
        for m in mdic['Models']:
            vpaths = vfs.nodes_select_distinct_vpath_where_vhash(m)
            if vpaths:
                v_path = vpaths[0]
            else:
                v_path = None
            models.append(v_path)
        instances = mdic['Instances']
        aabb = AABB(all6=mdic['AABB'])
        mid = aabb.mid()
        with DecaGltfNode(gltf, name=os.path.basename(vnode.v_path)) as mdic_node:
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
    vfs.logger.log('Exporting {}: Complete'.format(vnode.v_path.decode('utf-8')))


def adf_export_mdic_0x9111dc0(
        vfs: VfsDatabase,
        adf_db: AdfDatabase,
        vnode: VfsNode,
        export_path,
        allow_overwrite,
        save_to_one_dir,
        include_skeleton,
        texture_format,
):
    vfs.logger.log('Exporting {}: Started'.format(vnode.v_path.decode('utf-8')))
    gltf = DecaGltf(
        vfs, export_path, vnode.v_path.decode('utf-8'),
        save_to_one_dir=save_to_one_dir, include_skeleton=include_skeleton, texture_format=texture_format)

    with gltf.scene():
        adf = adf_db.read_node(vfs, vnode)
        mdic = adf.table_instance_values[0]
        models = []
        for m in mdic['Models']:
            v_path = None
            v_paths = vfs.hash_string_match(hash32=m)
            if len(v_paths) > 0:
                v_path = v_paths[0][1]
            models.append(v_path)
        instances = mdic['Instances']
        aabb = AABB(all6=mdic['AABB'])
        mid = aabb.mid()
        with DecaGltfNode(gltf, name=os.path.basename(vnode.v_path)) as mdic_node:
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
    vfs.logger.log('Exporting {}: Complete'.format(vnode.v_path.decode('utf-8')))


def node_export_adf_gltf(
        vfs: VfsDatabase,
        adf_db: AdfDatabase,
        vnode: VfsNode,
        export_path,
        allow_overwrite,
        save_to_one_dir,
        include_skeleton,
        texture_format,
):
    adf = adf_db.read_node(vfs, vnode)
    if adf is not None:
        if len(adf.table_instance) == 1:
            if adf.table_instance[0].type_hash == 0xf7c20a69:  # AmfModel
                adf_export_amf_model_0xf7c20a69(
                    vfs, adf_db, vnode, export_path, allow_overwrite,
                    save_to_one_dir=save_to_one_dir, include_skeleton=include_skeleton, texture_format=texture_format)
            elif adf.table_instance[0].type_hash == 0xb5b062f1:  # mdic
                adf_export_mdic_0xb5b062f1(
                    vfs, adf_db, vnode, export_path, allow_overwrite,
                    save_to_one_dir=save_to_one_dir, include_skeleton=include_skeleton, texture_format=texture_format)
            elif adf.table_instance[0].type_hash == 0x9111DC10:  # mdic
                adf_export_mdic_0x9111dc0(
                    vfs, adf_db, vnode, export_path, allow_overwrite,
                    save_to_one_dir=save_to_one_dir, include_skeleton=include_skeleton, texture_format=texture_format)


def node_export_adf_processed(
        vfs: VfsDatabase,
        adf_db: AdfDatabase,
        vnode: VfsNode,
        export_path,
        allow_overwrite=False
):
    adf = adf_db.read_node(vfs, vnode)
    if adf is not None:
        if len(adf.table_instance) == 1:
            if adf.table_instance[0].type_hash == 0x0B73315D:
                adf_export_xlsx_0x0b73315d(vfs, adf_db, vnode, export_path, allow_overwrite)


def node_export_adf_text(
        vfs: VfsDatabase,
        adf_db: AdfDatabase,
        vnode: VfsNode,
        export_path,
        allow_overwrite=False
):
    adf = adf_db.read_node(vfs, vnode)

    fn = generate_export_file_path(vfs, export_path, vnode, ' as Text') + '.txt'

    if not allow_overwrite and os.path.exists(fn):
        raise EDecaFileExists(fn)

    s = adf.dump_to_string(vfs)

    fn_dir = os.path.dirname(fn)
    os.makedirs(fn_dir, exist_ok=True)

    with open(fn, 'wt', encoding='utf-8') as f:
        f.write(s)

