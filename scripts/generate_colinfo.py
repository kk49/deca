import json

fn = './loc.json'

with open(fn, 'r') as f:
    data = json.load(f)

ctypes = [
    ('dala', True),
    ('gnome', True),
    ('mixtape', True),
    ('blueprint', True),
    ('location', False),
]
for ctypeinfo in ctypes:
    ctype = ctypeinfo[0]
    do_location = ctypeinfo[1]
    sd = {}
    for c in data:
        props = c['properties']
        if props['collectable_id'].find(ctype) >= 0:
            sd[props['collectable_id']] = [props['collectable_name_tr'], props['collectable_desc_tr'], props['position']]

    sn = list(sd.keys())
    sn.sort()

    print()
    print('{| class = "article-table"')
    print('!Name')
    print('!Description')
    if do_location:
        print('!Location')
    for n in sn:
        desc = sd[n][1]
        desc = desc.replace('\n', '<br/>')
        desc = desc.replace('|', ' ')
        print('|-')
        print('|{}'.format(sd[n][0]))
        print('|{}'.format(desc))
        if do_location:
            print('| {:.1f}, {:.1f}'.format(sd[n][2][0], sd[n][2][2]))
    print('|}')
