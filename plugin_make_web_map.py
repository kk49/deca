from deca.ff_vfs import VfsStructure
from deca.ff_avtx import Ddsc
from deca.ff_rtpc import Rtpc, PropName, RtpcProperty, RtpcNode
from deca.hash_jenkins import hash_little
from PIL import Image
import numpy as np
import pickle
import os


def plugin_make_web_map(vfs, wdir):
    build_image_tiles = False
    build_regions = True

    # build images
    if build_image_tiles:
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
        zone_dir = wdir + 'map/z0'
        os.makedirs(zone_dir, exist_ok=True)
        img.save(zone_dir + '/full.png')

        # determine zoom levels
        tile_size = 256
        shp = ai.shape
        max_width = max(*shp)
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
            width = max_width >> z
            zpath = zone_dir + '/itile/{}'.format(zlevel)
            print('Generate Zoom: {}'.format(zpath))

            # shrink image
            if zimgs[zlevel] is None:
                zimgs[zlevel] = zimgs[zlevel + 1].resize((shp[0] >> z, shp[1] >> z), Image.LANCZOS)

            if not os.path.isdir(zpath):
                for x in range(0, 2 ** zlevel):
                    dpath = zpath + '/{}'.format(x)
                    os.makedirs(dpath, exist_ok=True)
                    for y in range(0, 2 ** zlevel):
                        fpath = dpath + '/{}.png'.format(y)
                        zimgs[zlevel].crop((x*tile_size, y*tile_size, (x+1) * tile_size, (y+1) * tile_size)).save(fpath)

    # extract regions
    if build_regions:
        vnode = vfs.map_vpath_to_vfsnodes[b'global/global.blo'][0]
        with vfs.file_obj_from(vnode, 'rb') as f:
            rtpc = Rtpc()
            rtpc.deserialize(f)

        h_class_region = hash_little(b'CRegion')

        dst_x0 = 128
        dst_y0 = -128

        src_to_dst_x_scale = 128 / (16*1024)  # 180.0/(16*1024)
        src_to_dst_y_scale = -128 / (16*1024)  # -90.0/(16*1024)

        dpath = wdir + 'map/z0'
        os.makedirs(dpath, exist_ok=True)
        fpath = dpath + '/regions.js'
        with open(fpath, 'w') as f:
            f.write('var regions_json = [')
            chs = [rtpc.root_node]
            while len(chs) > 0:
                ch: RtpcNode = chs.pop(0)

                for c in ch.child_table:
                    chs.append(c)

                # if k_class_name in ch.prop_map and ch.prop_map[k_class_name].data == b'CRegion':
                if PropName.CLASS_NAME_HASH in ch.prop_map and ch.prop_map[PropName.CLASS_NAME_HASH].data == h_class_region:
                    border = ch.prop_map[PropName.CREGION_BORDER].data
                    objid = ch.prop_map[PropName.INSTANCE_UID].data
                    comment = ch.prop_map.get(PropName.CLASS_COMMENT, RtpcProperty()).data
                    rotpos_trans = ch.prop_map.get(PropName.ROTPOS_TRANSFORM, RtpcProperty()).data

                    if rotpos_trans is not None:
                        src_x0 = rotpos_trans[12]
                        src_y0 = rotpos_trans[14]
                    else:
                        print('USING DEFAULT OFFSETS')
                        src_x0 = -7016.08642578125
                        src_y0 = -1591.216064453125

                    if len(border) % 4 != 0:
                        raise Exception('Unexpected')
                    f.write('{\n')
                    f.write('"type": "Feature",\n')
                    f.write('"properties": {{"uid": "0x{:016X}"}},\n'.format(objid))
                    f.write('"geometry": { "type": "Polygon",\n')
                    f.write('"coordinates": [[\n')

                    for i in range(len(border) // 4):
                        x = (border[4*i + 0] + src_x0) * src_to_dst_x_scale + dst_x0
                        y = (border[4*i + 2] + src_y0) * src_to_dst_y_scale + dst_y0
                        f.write('[{}, {}],\n'.format(x, y))
                    f.write(']]\n')
                    f.write('}},\n')
            f.write('];\n')


def main():
    prefix_in = '/home/krys/prj/gz/archives_win64/'
    working_dir = './work/gz/'
    ver = 3
    debug = False

    cache_file = working_dir + 'vfs_cache.pickle'
    if os.path.isfile(cache_file):
        with open(cache_file, 'rb') as f:
            vfs = pickle.load(f)
    else:
        vfs = VfsStructure(working_dir)
        vfs.load_from_archives(prefix_in, debug=debug)
        with open(cache_file, 'wb') as f:
            pickle.dump(vfs, f, protocol=pickle.HIGHEST_PROTOCOL)

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
