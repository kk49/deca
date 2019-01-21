from deca.ff_vfs import vfs_structure_prep
from deca.ff_avtx import Ddsc
from deca.ff_rtpc import Rtpc, PropName, RtpcProperty, RtpcNode
from deca.ff_adf import load_adf
from deca.file import ArchiveFile
from PIL import Image
import numpy as np
import os
import json
import io
import matplotlib.pyplot as plt


def process_translation_adf(f, sz):
    buffer = f.read(sz)
    adf = load_adf(buffer)

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

    # with open('doc/text_debug.txt', 'w') as dt:
    #     for k, v in tr.items():
    #         dt.write('{}\t{}\n'.format(k, v))

    return tr


def tileset_make(img, tile_path, tile_size=256, max_zoom=-1):
    # save full image, mainly for debugging
    os.makedirs(tile_path, exist_ok=True)
    img.save(tile_path + '/full.png')

    # determine zoom levels
    sz = img.size
    max_width = max(*sz)
    zooms = 0
    w = tile_size
    while w <= max_width:
        zooms = zooms + 1
        w = w * 2

    # save tiles
    zimgs = [None] * zooms
    zimgs[-1] = img
    for z in range(zooms):
        zlevel = zooms - 1 - z
        zpath = tile_path + '/{}'.format(zlevel)
        print('Generate Zoom: {}'.format(zpath))

        # shrink image
        if zimgs[zlevel] is None:
            zimgs[zlevel] = zimgs[zlevel + 1].resize((sz[0] >> z, sz[1] >> z), Image.LANCZOS)

        if not os.path.isdir(zpath):
            for x in range(0, 2 ** zlevel):
                dpath = zpath + '/{}'.format(x)
                os.makedirs(dpath, exist_ok=True)
                for y in range(0, 2 ** zlevel):
                    fpath = dpath + '/{}.png'.format(y)
                    zimgs[zlevel].crop((x * tile_size, y * tile_size, (x + 1) * tile_size, (y + 1) * tile_size)).save(
                        fpath)

    for zlevel in range(zooms, max_zoom+1):
        width = tile_size >> (zlevel - (zooms-1))
        zpath = tile_path + '/{}'.format(zlevel)
        print('Generate Zoom: {}'.format(zpath))
        if not os.path.isdir(zpath):
            for x in range(0, 2 ** zlevel):
                dpath = zpath + '/{}'.format(x)
                os.makedirs(dpath, exist_ok=True)
                for y in range(0, 2 ** zlevel):
                    fpath = dpath + '/{}.png'.format(y)
                    zimgs[(zooms-1)].crop((x * width, y * width, (x + 1) * width, (y + 1) * width)).resize((tile_size, tile_size), Image.NEAREST).save(fpath)


def plugin_make_web_map(vfs, wdir):
    force_topo_tiles = False

    # BUILD topo map
    topo_dst_path = wdir + 'map/z0/tile_t'
    if not os.path.isdir(topo_dst_path) or force_topo_tiles:  # this is slow so only do it once
        # extract full res image
        ai = []
        for i in range(16):
            ai.append([None] * 16)
        for i in range(256):
            x = i % 16
            y = i // 16
            fn = 'textures/ui/map_reserve_0/zoom3/{}.ddsc'.format(i)
            fn = fn.encode('ascii')
            vnode = vfs.map_vpath_to_vfsnodes[fn][0]
            img = Ddsc()
            with vfs.file_obj_from(vnode) as f:
                img.load_ddsc(f)
            ai[y][x] = img.mips[0].data

        for i in range(16):
            ai[i] = np.hstack(ai[i])
        ai = np.vstack(ai)
        img = Image.fromarray(ai)

        tileset_make(img, topo_dst_path)

    # BUILD height map
    # extract full res image
    fn = b'terrain/global_heightfield.rawc'
    vnode = vfs.map_vpath_to_vfsnodes[fn][0]

    with vfs.file_obj_from(vnode) as f:
        buffer = f.read(1024 * 1024)

    aimg = np.frombuffer(buffer, count=512*512, dtype=np.float32)
    aimg = np.reshape(aimg, (512, 512))
    aimg = (aimg - aimg.min()) / (aimg.max() - aimg.min())

    # convert range of values to color map
    cm = plt.get_cmap('jet')
    cimg = cm(aimg)
    img = Image.fromarray((cimg[:, :, :3] * 255).astype(np.uint8))

    tileset_make(img, wdir + 'map/z0/tile_h')

    # BUILD water nvwaveworks map
    # extract full res image
    fn = b'terrain/water_nvwaveworks_mod.rawc'
    vnode = vfs.map_vpath_to_vfsnodes[fn][0]

    with vfs.file_obj_from(vnode) as f:
        buffer = f.read(1024 * 1024)

    aimg = np.frombuffer(buffer, count=1024*1024, dtype=np.uint8)
    aimg = np.flipud(np.reshape(aimg, (1024, 1024)).astype(dtype=np.float32))
    aimg = (aimg - aimg.min()) / (aimg.max() - aimg.min())

    # convert range of values to color map
    cm = plt.get_cmap('jet')
    cimg = cm(aimg)
    img = Image.fromarray((cimg[:, :, :3] * 255).astype(np.uint8))

    tileset_make(img, wdir + 'map/z0/tile_wn')

    # BUILD water gerstner map
    # extract full res image
    fn = b'terrain/water_gerstner_mod.rawc'
    vnode = vfs.map_vpath_to_vfsnodes[fn][0]

    with vfs.file_obj_from(vnode) as f:
        buffer = f.read(1024 * 1024)

    aimg = np.frombuffer(buffer, count=1024*1024, dtype=np.uint8)
    aimg = np.flipud(np.reshape(aimg, (1024, 1024)).astype(dtype=np.float32))
    aimg = (aimg - aimg.min()) / (aimg.max() - aimg.min())

    # convert range of values to color map
    cm = plt.get_cmap('jet')
    cimg = cm(aimg)
    img = Image.fromarray((cimg[:, :, :3] * 255).astype(np.uint8))

    tileset_make(img, wdir + 'map/z0/tile_wg')

    # TODO parse terrain/nv_water_cull_mask.rawc ? 1 bit per pixel 512x512 pixels
    fn = b'terrain/nv_water_cull_mask.rawc'
    vnode = vfs.map_vpath_to_vfsnodes[fn][0]

    with vfs.file_obj_from(vnode) as f:
        buffer = f.read(32 * 1024)

    aimg = np.frombuffer(buffer, count=32*1024, dtype=np.uint8)
    cimg = np.zeros((512, 512, 4), dtype=np.uint8)

    for r in range(512):
        rd = aimg[r*64:(r+1)*64]
        for c in range(64):
            for sc in range(8):
                if rd[c] & (0x80 >> sc) == 0:
                    cimg[r, c * 8 + sc, :] = [0, 0, 0, 0]
                else:
                    cimg[r, c*8 + sc, :] = [0xff, 0xff, 0xff, 0xff]
    cimg = np.flip(cimg, 0)
    img = Image.fromarray(cimg)

    tileset_make(img, wdir + 'map/z0/tile_wnm')

    tile_overlays = []

    for crit in ['dreadnought', 'harvester', 'hunter', 'scout', 'skirmisher']:
        for ctype, color in zip(['a', 'b', 'c'], [[255,0,0,255],[0,255,0,255],[0,0,255,255]]):
            tile_overlays.append([
                'settings/hp_settings/hp_ai_textures/spawn_maps/spawn_{}_{}.bmp_datac'.format(crit, ctype).encode('ascii'),
                'tile_spawn_{}_{}'.format(crit, ctype),
                color
            ])

    for tileo in tile_overlays:
        fn = tileo[0]
        vnode = vfs.map_vpath_to_vfsnodes[fn][0]

        with vfs.file_obj_from(vnode) as f:
            f.seek(vnode.size_u - 8192)
            buffer = f.read(8192)

        aimg = np.frombuffer(buffer, count=8 * 1024, dtype=np.uint8)
        cimg = np.zeros((512, 512, 4), dtype=np.uint8)

        for r in range(256):
            rd = aimg[r * 32:(r + 1) * 32]
            for c in range(32):
                for sc in range(8):
                    if rd[c] & (0x01 << sc) == 0:
                        cimg[128 + r, 128 + c * 8 + sc, :] = [0, 0, 0, 0]
                    else:
                        cimg[128 + r, 128 + c * 8 + sc, :] = tileo[2]
        # cimg = np.flip(cimg, 0)
        img = Image.fromarray(cimg)

        tileset_make(img, wdir + 'map/z0/{}'.format(tileo[1]))

    # load translation
    tr = {}
    # vnode = vfs.map_vpath_to_vfsnodes[b'text/master_eng.stringlookup'][0]
    # with vfs.file_obj_from(vnode, 'rb') as f:
    #     tr = process_translation_adf(f, vnode.size_u)

    # extract geometric features
    dst_x0 = 128
    dst_y0 = -128

    src_to_dst_x_scale = 128 / (16*1024)  # 180.0/(16*1024)
    src_to_dst_y_scale = -128 / (16*1024)  # -90.0/(16*1024)

    regions = []
    global_collectables = []
    pois = []

    vnode = vfs.map_vpath_to_vfsnodes[b'global/global.blo'][0]
    with vfs.file_obj_from(vnode, 'rb') as f:
        rtpc = Rtpc()
        rtpc.deserialize(f)
    chs = [rtpc.root_node]
    while len(chs) > 0:
        ch: RtpcNode = chs.pop(0)

        for c in ch.child_table:
            chs.append(c)

        # if k_class_name in ch.prop_map and ch.prop_map[k_class_name].data == b'CRegion':
        if PropName.CLASS_NAME in ch.prop_map:
            obj_type = ch.prop_map[PropName.CLASS_NAME].data.decode('utf-8')
            obj_id = ch.prop_map.get(PropName.INSTANCE_UID, RtpcProperty()).data
            comment = ch.prop_map.get(PropName.CLASS_COMMENT, RtpcProperty()).data.decode('utf-8')
            if obj_type == 'CRegion':
                rotpos_trans = ch.prop_map.get(PropName.ROTPOS_TRANSFORM, RtpcProperty()).data
                border = ch.prop_map[PropName.CREGION_BORDER].data
                if len(border) % 4 != 0:
                    raise Exception('Unexpected')

                if rotpos_trans is not None:
                    src_x0 = rotpos_trans[12]
                    src_y0 = rotpos_trans[14]
                else:
                    print('USING DEFAULT OFFSETS')
                    src_x0 = -7016.08642578125
                    src_y0 = -1591.216064453125

                coords = []
                for i in range(len(border) // 4):
                    x = (border[4*i + 0] + src_x0) * src_to_dst_x_scale + dst_x0
                    y = (border[4*i + 2] + src_y0) * src_to_dst_y_scale + dst_y0
                    coords.append([x, y])

                obj = {
                    'type': 'Feature',
                    'properties': {
                        'type': obj_type,
                        'uid': obj_id,
                        'uid_str': '0x{:012X}'.format(obj_id),
                        'comment': comment,
                    },
                    'geometry': {
                        'type': 'Polygon',
                        'coordinates': [coords]
                    },
                }
                regions.append(obj)

            elif obj_type == 'CCollectable':
                rotpos_trans = ch.prop_map.get(PropName.ROTPOS_TRANSFORM, RtpcProperty()).data

                if rotpos_trans is not None:
                    src_x0 = rotpos_trans[12]
                    src_y0 = rotpos_trans[14]
                else:
                    print('USING DEFAULT OFFSETS')
                    src_x0 = 0
                    src_y0 = 0

                x = (0 + src_x0) * src_to_dst_x_scale + dst_x0
                y = (0 + src_y0) * src_to_dst_y_scale + dst_y0
                coords = [x, y]

                obj = {
                    'type': 'Feature',
                    'properties': {
                        'type': obj_type,
                        'uid': obj_id,
                        'uid_str': '0x{:012X}'.format(obj_id),
                        'comment': comment,
                    },
                    'geometry': {
                        'type': 'Point',
                        'coordinates': coords
                    },
                }
                global_collectables.append(obj)

            elif obj_type == 'CPOI':
                rotpos_trans = ch.prop_map.get(PropName.ROTPOS_TRANSFORM, RtpcProperty()).data
                cpoi_name = ch.prop_map.get(PropName.CPOI_NAME, RtpcProperty()).data.decode('utf-8')
                cpoi_desc = ch.prop_map.get(PropName.CPOI_DESC, RtpcProperty()).data.decode('utf-8')
                cpoi_name_tr = tr.get(cpoi_name, cpoi_name)
                cpoi_desc_tr = tr.get(cpoi_desc, cpoi_desc)

                if rotpos_trans is not None:
                    src_x0 = rotpos_trans[12]
                    src_y0 = rotpos_trans[14]
                else:
                    print('USING DEFAULT OFFSETS')
                    src_x0 = 0
                    src_y0 = 0

                x = (0 + src_x0) * src_to_dst_x_scale + dst_x0
                y = (0 + src_y0) * src_to_dst_y_scale + dst_y0
                coords = [x, y]

                obj = {
                    'type': 'Feature',
                    'properties': {
                        'type': obj_type,
                        'uid': obj_id,
                        'uid_str': '0x{:012X}'.format(obj_id),
                        'comment': comment,
                        'poi_name': cpoi_name,
                        'poi_desc': cpoi_desc,
                        'poi_name_tr': cpoi_name_tr,
                        'poi_desc_tr': cpoi_desc_tr,
                    },
                    'geometry': {
                        'type': 'Point',
                        'coordinates': coords
                    },
                }
                pois.append(obj)

    # LOAD from 'global/bookmarks_gen.blo
    bookmarks = []
    vnode = vfs.map_vpath_to_vfsnodes[b'global/bookmarks_gen.blo'][0]
    with vfs.file_obj_from(vnode, 'rb') as f:
        rtpc = Rtpc()
        rtpc.deserialize(f)
    chs = [rtpc.root_node]
    while len(chs) > 0:
        ch: RtpcNode = chs.pop(0)

        for c in ch.child_table:
            chs.append(c)

        # if k_class_name in ch.prop_map and ch.prop_map[k_class_name].data == b'CRegion':
        if PropName.CLASS_NAME in ch.prop_map:
            obj_type = ch.prop_map[PropName.CLASS_NAME].data.decode('utf-8')
            obj_id = ch.prop_map.get(PropName.INSTANCE_UID, RtpcProperty()).data
            comment = ch.prop_map.get(PropName.CLASS_COMMENT, RtpcProperty()).data.decode('utf-8')
            bookmark_name = ch.prop_map.get(PropName.BOOKMARK_NAME, RtpcProperty()).data.decode('utf-8')
            if obj_type == 'CBookMark':
                rotpos_trans = ch.prop_map.get(PropName.ROTPOS_TRANSFORM, RtpcProperty()).data

                if rotpos_trans is not None:
                    src_x0 = rotpos_trans[12]
                    src_y0 = rotpos_trans[14]
                else:
                    print('USING DEFAULT OFFSETS')
                    src_x0 = 0
                    src_y0 = 0

                x = (0 + src_x0) * src_to_dst_x_scale + dst_x0
                y = (0 + src_y0) * src_to_dst_y_scale + dst_y0
                coords = [x, y]

                obj = {
                    'type': 'Feature',
                    'properties': {
                        'type': obj_type,
                        'uid': obj_id,
                        'uid_str': '0x{:012X}'.format(obj_id),
                        'comment': comment,
                        'bookmark_name': bookmark_name,
                    },
                    'geometry': {
                        'type': 'Point',
                        'coordinates': coords
                    },
                }
                bookmarks.append(obj)

    # LOAD from global/collection.collectionc
    vnodes = vfs.map_vpath_to_vfsnodes[b'global/collection.collectionc']
    for i in range(len(vnodes)):
        vnode = vnodes[i]
        with vfs.file_obj_from(vnode, 'rb') as f:
            buffer = f.read(vnode.size_u)
            with open('d{}.dat'.format(i), 'wb') as fo:
                fo.write(buffer)
    vnode = vnodes[1]
    with vfs.file_obj_from(vnode, 'rb') as f:
        buffer = f.read(vnode.size_u)
        adf = load_adf(buffer)

    collectables = []
    for v in adf.table_instance_values[0]['Collectibles']:
        obj_id = v['ID']
        cid = v['Name'].decode('utf-8')
        name = cid + '_name'
        name = tr.get(name, name)
        desc = cid + '_desc'
        desc = tr.get(desc, desc)
        position = v['Position']
        x = (position[0]) * src_to_dst_x_scale + dst_x0
        y = (position[2]) * src_to_dst_y_scale + dst_y0
        coords = [x, y]

        obj = {
            'type': 'Feature',
            'properties': {
                'type': 'collection.collectionc',
                'uid': obj_id,
                'uid_str': '0x{:012X}'.format(obj_id),
                'collectable_id': cid,
                'collectable_name': name,
                'collectable_desc': desc,
            },
            'geometry': {
                'type': 'Point',
                'coordinates': coords
            },
        }
        collectables.append(obj)

    dpath = wdir + 'map/z0'
    os.makedirs(dpath, exist_ok=True)
    fpath = dpath + '/data.js'

    with open(fpath, 'w') as f:
        f.write('var region_data = {};\n'.format(json.dumps(regions, indent=4)))
        f.write('var global_collectable_data = {};\n'.format(json.dumps(global_collectables, indent=4)))
        f.write('var poi_data = {};\n'.format(json.dumps(pois, indent=4)))
        f.write('var bookmark_data = {};\n'.format(json.dumps(bookmarks, indent=4)))
        f.write('var collectable_data = {};\n'.format(json.dumps(collectables, indent=4)))


def main():
    game_dir = '/home/krys/prj/as_games/GenerationZero_BETA/'
    game_id = 'gzb'
    working_dir = './work/gzb/'
    archive_paths = []
    for cat in ['initial', 'supplemental', 'optional']:
        archive_paths.append(os.path.join(game_dir, 'archives_win64', cat))

    vfs = vfs_structure_prep(game_dir, game_id, archive_paths, working_dir)

    plugin_make_web_map(vfs, working_dir)


if __name__ == "__main__":
    main()


# def export_map():
#     ai = []
#     for i in range(16):
#         ai.append([None] * 16)
#     for i in range(256):
#         x = i % 16
#         y = i // 16
#         fn = 'textures/ui/map_reserve_0/zoom3/{}.ddsc'.format(i)
#         fn = fn.encode('ascii')
#         vnode = vfs_global.map_vpath_to_vfsnodes[fn][0]
#         img = Ddsc()
#         with vfs_global.file_obj_from(vnode) as f:
#             img.load_ddsc(f)
#         ai[y][x] = img.mips[0].data
#
#     import numpy as np
#     from PIL import Image
#     for i in range(16):
#         ai[i] = np.hstack(ai[i])
#     ai = np.vstack(ai)
#     img = Image.fromarray(ai)
#     img.save(working_dir + '/z0.png')
#
#     return img
