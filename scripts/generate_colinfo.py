import re
from deca.db_core import VfsDatabase
from deca.db_processor import vfs_structure_open
from deca.ff_adf import AdfDatabase
from deca.digest import process_translation_adf, process_codex_adf

do_description = True

vfs: VfsDatabase = vfs_structure_open('/home/krys/prj/work/gz/project.json')
adf_db = AdfDatabase(vfs)

# load translation
vnode = vfs.nodes_where_match(v_path=b'text/master_eng.stringlookup')[0]
tr = process_translation_adf(vfs, adf_db, vnode)

# LOAD collectable codex information
vnode = vfs.nodes_where_match(v_path=b'settings/hp_settings/codex_data.bin')[0]
codex = process_codex_adf(vfs, adf_db, vnode)

# Load collectable info
vnode = vfs.nodes_where_match(v_path=b'global/collection.collectionc')[0]
adf = adf_db.read_node(vfs, vnode)

collectables = []
for v in adf.table_instance_values[0]['Collectibles']:
    obj_id = v['ID']
    cid = v['Name'].decode('utf-8')

    if cid in codex:
        name, desc, icon, cc = codex[cid]

        if name is None:
            print(f'MISSING: {cid}')
        else:
            if name not in tr:
                rx = re.compile(name)
                for k in tr.keys():
                    if rx.match(k) is not None:
                        name = k
                        break

            if desc not in tr:
                rx = re.compile(desc)
                for k in tr.keys():
                    if rx.match(k) is not None:
                        desc = k
                        break

            name = tr[name]
            desc = tr[desc]
            position = v['Position']

            obj = {
                'type': 'Feature',
                'properties': {
                    'type': 'collection.collectionc',
                    'uid': obj_id,
                    'uid_str': '0x{:012X}'.format(obj_id),
                    'collectable_id': cid,
                    'collectable_category': cc,
                    'collectable_name_tr': name,
                    'collectable_desc_tr': desc,
                    'position': position,
                },
            }
            collectables.append(obj)

collectibles_order = [
    ('souvenirs', True),
    ('gnomes', True),
    ('mixtapes', True),
    ('blueprints', True),
    ('location_lore', False),
    ('island01_audiologs', True),
    ('island01_biographies', True),
    ('island01_photos', True),
]


for ci in collectibles_order:
    category = ci[0]
    do_location = ci[1]
    sd = {}
    for c in collectables:
        props = c['properties']
        if category == props['collectable_category']:
            sd[props['collectable_id']] = [props['collectable_name_tr'], props['collectable_desc_tr'], props['position']]

    sn = list(sd.keys())
    sn.sort()

    print()
    print('{| class = "article-table"')
    print('!Name')
    if do_description:
        print('!Description')
    if do_location:
        print('!Location')
    for n in sn:
        desc = sd[n][1]
        desc = desc.replace('\n', '<br/>')
        desc = desc.replace('|', ' ')
        print('|-')
        print('|{}'.format(sd[n][0]))
        if do_description:
            print('|{}'.format(desc))
        if do_location:
            print('| {:.1f}, {:.1f}'.format(sd[n][2][0], sd[n][2][2]))
    print('|}')
