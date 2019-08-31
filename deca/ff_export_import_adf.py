from .ff_adf import *
from .xlsxwriter_hack import DecaWorkBook
from .ff_adf_amf import AABB
from .ff_adf_amg_gltf import DecaGltf, DecaGltfNode
from .vfs_db import VfsStructure, VfsNode


def adf_export_xlsx_0x0b73315d(adf, vfs: VfsStructure, node: VfsNode, export_path, allow_overwrite):
    fn = export_path + '.xlsx'

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


def adf_export_amf_model_0xf7c20a69(adf, vfs: VfsStructure, node: VfsNode, export_path, allow_overwrite):
    gltf = DecaGltf(vfs, export_path)
    for lod in range(1):
        gltf.gltf_create(lod)
        with gltf.n_objects():
            gltf.export_modelc(node.vpath, None)
        gltf.gltf_save()


def adf_export_mdic_0xb5b062f1(adf, vfs: VfsStructure, node: VfsNode, export_path, allow_overwrite):
    mdic = adf.table_instance_values[0]
    models = [list(vfs.map_hash_to_vpath.get(m, [None]))[0] for m in mdic['Models']]
    instances = mdic['Instances']
    lod = 0
    gltf = DecaGltf(vfs, export_path)
    gltf.gltf_create(lod)

    aabb = None
    with gltf.n_world() as n_world:
        with DecaGltfNode(gltf, name=os.path.basename(node.vpath)):
            aabb = AABB(all6=mdic['AABB']).union(aabb)
            for instance in instances:
                transform = instance['Transform']
                model_index = instance['ModelIndex']
                model = models[model_index]
                if model is None:
                    vfs.logger.log('Missing model 0x{:08x}'.format(model_index))
                else:
                    gltf.export_modelc(model, transform)
        n_world.translation = list(-aabb.mid())

    gltf.gltf_save()


def adf_export_multi(vfs: VfsStructure, vpaths, root_export_path, allow_overwrite=False):
    pass


def adf_export(vfs: VfsStructure, node: VfsNode, export_path, allow_overwrite=False):
    adf = adf_node_read(vfs, node)
    if adf is not None:
        if len(adf.table_instance) == 1:
            if adf.table_instance[0].type_hash == 0x0B73315D:
                adf_export_xlsx_0x0b73315d(adf, vfs, node, export_path, allow_overwrite)
            elif adf.table_instance[0].type_hash == 0xf7c20a69:  # AmfModel
                adf_export_amf_model_0xf7c20a69(adf, vfs, node, export_path, allow_overwrite)
            elif adf.table_instance[0].type_hash == 0xb5b062f1:  # mdic
                adf_export_mdic_0xb5b062f1(adf, vfs, node, export_path, allow_overwrite)
            else:
                fn = export_path + '.txt'

                if not allow_overwrite and os.path.exists(fn):
                    raise EDecaFileExists(fn)

                s = adf.dump_to_string()

                with open(fn, 'wt') as f:
                    f.write(s)
