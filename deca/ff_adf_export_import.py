import pprint
from deca.ff_adf import *
from deca.xlsxwriter_hack import DecaWorkBook
from deca.ff_adf_amg_gltf import DecaGltf


def adf_export(vfs, node, export_path, allow_overwrite=False):
    adf = adf_node_read(vfs, node)
    if adf is not None:
        if len(adf.table_instance) == 1:
            if adf.table_instance[0].type_hash == 0x0B73315D:
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
            elif adf.table_instance[0].type_hash == 0xf7c20a69:  # AmfModel
                gltf = DecaGltf(vfs, export_path)
                for lod in range(1):
                    gltf.gltf_create(lod)
                    gltf.export_modelc(node.vpath, None)
                    gltf.gltf_save()
            elif adf.table_instance[0].type_hash == 0xb5b062f1:  # mdic
                mdic = adf.table_instance_values[0]
                models = [list(vfs.map_hash_to_vpath.get(m, [None]))[0] for m in mdic['Models']]
                instances = mdic['Instances']
                lod = 0
                gltf = DecaGltf(vfs, export_path)
                gltf.gltf_create(lod)
                aabb = mdic['AABB']
                x = (aabb[0] + aabb[3]) / 2
                y = (aabb[1] + aabb[4]) / 2
                z = (aabb[2] + aabb[5]) / 2
                for instance in instances:
                    transform = instance['Transform']
                    transform[12] -= x
                    transform[13] -= y
                    transform[14] -= z
                    model_index = instance['ModelIndex']
                    model = models[model_index]
                    if model is None:
                        vfs.logger.log('Missing model 0x{:08x}'.format(model_index))
                    else:
                        gltf.export_modelc(model, transform)
                gltf.gltf_save()

            else:
                fn = export_path + '.txt'

                if not allow_overwrite and os.path.exists(fn):
                    raise EDecaFileExists(fn)

                s = adf.dump_to_string()

                with open(fn, 'wt') as f:
                    f.write(s)
