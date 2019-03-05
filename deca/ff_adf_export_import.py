from deca.ff_adf import *
from deca.hash_jenkins import hash_little
import xlsxwriter


def adf_export(adf: Adf, export_path):
    if len(adf.table_instance) == 1:
        if adf.table_instance[0].type_hash == 0x0B73315D:
            fn = export_path + '.xlsx'

            src = adf.table_instance_values[0]
            book = xlsxwriter.Workbook(fn)

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
                name_short = '{:08x}'.format(hash_little(name))
                cellindex = srcw['CellIndex']
                worksheet = book.add_worksheet(name_short)
                worksheet.write_string(0, 0, name.decode('utf-8'))
                for i in range(rows):
                    for j in range(cols):
                        r = i
                        c = j + 1

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
                                pass
                                # worksheet.write_string(r, c, 'Missing BoolData {}'.format(didx), cell_format=cell_format)
                        elif ctype == 1:
                            if didx < len(src['StringData']):
                                worksheet.write_string(r, c, src['StringData'][didx].decode('utf-8'), cell_format=cell_format)
                            else:
                                pass
                                # worksheet.write_string(r, c, 'Missing StringData {}'.format(didx), cell_format=cell_format)
                        elif ctype == 2:
                            if didx < len(src['ValueData']):
                                worksheet.write_number(r, c, src['ValueData'][didx], cell_format=cell_format)
                            else:
                                pass
                                # worksheet.write_string(r, c, 'Missing ValueData {}'.format(didx), cell_format=cell_format)
                        else:
                            raise NotImplemented('Unhandled Cell Type {}'.format(ctype))

            book.close()
