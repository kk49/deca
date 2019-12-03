import os
import io
from deca.file import ArchiveFile


def process_translation_adf(vfs, f, sz):
    buffer = f.read(sz)
    adf = vfs.adf_db.load_adf(buffer)

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

    if os.path.exists(os.path.join('scratch', 'gz')):
        with open(os.path.join('scratch', 'gz', 'text_debug.txt'), 'w') as dt:
            for k, v in tr.items():
                dt.write('{}\t{}\n'.format(k, v.replace('\n', '<br>')))

    return tr
