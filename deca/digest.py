import os
import sys
import io
import openpyxl

from .file import ArchiveFile
from .db_core import VfsDatabase, VfsNode
from .ff_adf import AdfDatabase
from .export_import_adf import adf_export_xlsx_0x0b73315d
from .util import make_dir_for_file


def process_translation_adf(vfs: VfsDatabase, adf_db: AdfDatabase, node: VfsNode):
    adf = adf_db.read_node(vfs, node)

    txt_buffer = adf.table_instance_values[0]['Text']
    txt_buffer = [(t + 256) % 256 for t in txt_buffer]
    txt_buffer = bytearray(txt_buffer)

    tr = {}
    with ArchiveFile(io.BytesIO(txt_buffer)) as tf:
        for prs in adf.table_instance_values[0]['SortedPairs']:
            tf.seek(prs['TextOffset'])
            text = tf.read_strz().decode('utf-8')
            tf.seek(prs['NameOffset'])
            name = tf.read_strz().decode('utf-8')
            tr[name] = text

    if sys.platform == 'linux':
        debug_file = os.path.join(vfs.working_dir, 'text_debug.txt')
        make_dir_for_file(debug_file)
        with open(debug_file, 'w') as dt:
            for k, v in tr.items():
                buf = '{}\t{}\n'.format(k, v.replace('\n', '<br>').replace('"', '&quot;'))
                dt.write(buf)

    return tr


def process_codex_adf(vfs: VfsDatabase, adf_db: AdfDatabase, node: VfsNode, export_path='./digest/'):
    codex_fn = adf_export_xlsx_0x0b73315d(vfs, adf_db, node, export_path=export_path, allow_overwrite=True)
    codex_wb = openpyxl.load_workbook(filename=codex_fn)

    cat_id = []
    cat_name = []
    for col in codex_wb['CollectableCategories'].columns:
        c = [v.value for v in col]
        if c[0] == 'id':
            cat_id = c[1:]
        elif c[0] == 'name':
            cat_name = c[1:]

    codex_id = []
    codex_name = []
    codex_desc = []
    codex_icon = []
    codex_category = []
    for col in codex_wb['Collectables'].columns:
        c = [v.value for v in col]
        if c[0] == 'id':
            codex_id = c[1:]
        elif c[0] == 'name':
            codex_name = c[1:]
        elif c[0] == 'description':
            codex_desc = c[1:]
        elif c[0] == 'icon':
            codex_icon = c[1:]
        elif c[0] == 'collection_id':
            codex_category = c[1:]

    categories = dict(zip(cat_id, cat_name))

    codex = {}
    for cid, name, desc, icon, category in zip(codex_id, codex_name, codex_desc, codex_icon, codex_category):
        if cid is not None:
            codex[cid] = (name, desc, icon, category)

    return categories, codex

