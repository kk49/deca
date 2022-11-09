from .ff_avtx import Ddsc
from .db_core import VfsDatabase
import os
import numpy as np
from PIL import Image


def tileset_make(img, tile_path, export_full, export_tiles, tile_size=256, max_zoom=-1):
    # save full image, mainly for debugging
    os.makedirs(tile_path, exist_ok=True)

    if export_full:
        img.save(os.path.join(tile_path, 'full.png'))

    if export_tiles:
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
                    dpath = os.path.join(zpath, '{}'.format(x))
                    os.makedirs(dpath, exist_ok=True)
                    for y in range(0, 2 ** zlevel):
                        fpath = os.path.join(dpath, '{}.png'.format(y))
                        zimgs[zlevel].crop((x * tile_size, y * tile_size, (x + 1) * tile_size, (y + 1) * tile_size)).save(
                            fpath)

        for zlevel in range(zooms, max_zoom + 1):
            width = tile_size >> (zlevel - (zooms - 1))
            zpath = os.path.join(tile_path, '{}'.format(zlevel))
            print('Generate Zoom: {}'.format(zpath))
            if not os.path.isdir(zpath):
                for x in range(0, 2 ** zlevel):
                    dpath = os.path.join(zpath, '{}'.format(x))
                    os.makedirs(dpath, exist_ok=True)
                    for y in range(0, 2 ** zlevel):
                        fpath = os.path.join(dpath, '{}.png'.format(y))
                        img = zimgs[(zooms - 1)]
                        img = img.crop((x * width, y * width, (x + 1) * width, (y + 1) * width))
                        img = img.resize((tile_size, tile_size), Image.NEAREST)
                        img.save(fpath)


def export_map(vfs: VfsDatabase, map_vpath, export_path, export_full, export_tiles):
    # find highest resolution
    max_zoom = 0
    while True:
        fn = '{}{}/{}.ddsc'.format(map_vpath, max_zoom + 1, 0)
        fn = fn.encode('ascii')
        vnode = vfs.nodes_where_match(v_path=fn)
        if len(vnode) > 0:
            max_zoom = max_zoom + 1
        else:
            break

    radius = 1
    while True:
        next_radius = radius + 1
        fn = '{}{}/{}.ddsc'.format(map_vpath, max_zoom, next_radius * next_radius - 1)
        fn = fn.encode('ascii')
        vnode = vfs.nodes_where_match(v_path=fn)
        if len(vnode) > 0:
            radius = next_radius
        else:
            break

    tile_count = radius * radius
    tile_count_x = radius
    tile_count_y = radius

    if max_zoom > 0:
        # extract full res image
        ai = []
        for i in range(tile_count_y):
            ai.append([None] * tile_count_x)

        for i in range(tile_count):
            x = i % tile_count_x
            y = i // tile_count_x
            fn = '{}{}/{}.ddsc'.format(map_vpath, max_zoom, i)
            fn = fn.encode('ascii')

            vnode = vfs.nodes_where_match(v_path=fn)[0]
            img = Ddsc()
            with vfs.file_obj_from(vnode) as f:
                img.load_ddsc(f)
            ai[y][x] = img.mips[0].data

        for i in range(tile_count_x):
            ai[i] = np.hstack(ai[i])
        ai = np.vstack(ai)
        img = Image.fromarray(ai)

        tileset_make(img, export_path, export_full, export_tiles)
