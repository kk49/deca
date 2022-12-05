from deca.db_processor import vfs_structure_open
from deca.db_core import VfsDatabase
from deca.ff_adf import AdfDatabase
from deca.ff_adf_amf import AABB
from deca.ff_adf_amf_gltf import Deca3dMatrix
from deca.digest import process_translation_adf, process_codex_adf
from deca.util import make_dir_for_file, deca_root
from deca.export_map import export_map, tileset_make
import deca.ff_rtpc as rtpc
from deca.ff_rtpc import parse_prop_data
from PIL import Image
import numpy as np
import os
import json
import matplotlib.pyplot as plt
import shutil
import re


dst_x0 = 128
dst_y0 = -128
src_to_dst_x_scale = 128 / (16 * 1024)  # 180.0/(16*1024)
src_to_dst_y_scale = -128 / (16 * 1024)  # -90.0/(16*1024)


#         @0x000001a4(     420) 0xa949bc65 0x00000f5f 0x03 str    = @0x00000f5f(    3935) b'craftingmagazinenoiseshoes'
class RtpcVisitorMap(rtpc.RtpcVisitor):
    def __init__(self, tr):
        super(RtpcVisitorMap, self).__init__()
        self.node_stack = []
        self.node_stack_index = -1

        self.tr = tr

        self.regions = []
        self.apex_social_control = {}
        self.points = {
            'CLootCrateSpawnPoint': [],
            'CLootCrateSpawnPointGroup': [],
            'CPlayerSpawnPoint': [],
            'CCollectable': [],
            'CBookMark': [],
            'CPOI': [],
            'CPOI.nest_marker_poi': [],
            'CraftingSchematic': [],
            'LootItem': [],
        }
        self.rtpc_class_name = None  # PropName.CLASS_NAME
        self.rtpc_class_comment = None  # PropName.CLASS_COMMENT
        self.rtpc_world = None  # rtpc_prop_world
        self.rtpc_script = None  # rtpc_prop_name_script
        self.rtpc_ref_apex_identifier = None  # rtpc_prop_ref_apex_identifier
        self.rtpc_cregion_border = None  # PropName.CREGION_BORDER
        self.rtpc_instance_uid = None  # PropName.INSTANCE_UID
        self.rtpc_cpoi_name = None  # PropName.CPOI_NAME
        self.rtpc_cpoi_desc = None  # PropName.CPOI_DESC
        self.rtpc_bookmark_name = None  # PropName.BOOKMARK_NAME
        self.rtpc_item_item_id = None
        self.rtpc_deca_loot_class = None  # 0x34beec18
        self.rtpc_deca_crafting_type = None  # 0xa949bc65

    def process_point(self):
        self.rtpc_world = Deca3dMatrix(col_major=self.rtpc_world)
        x = self.rtpc_world.data[0, 3]
        z = self.rtpc_world.data[1, 3]
        y = self.rtpc_world.data[2, 3]
        position = [x, z, y]
        coords = [
            x * src_to_dst_x_scale + dst_x0,
            y * src_to_dst_y_scale + dst_y0,
        ]

        obj = {
            'type': 'Feature',
            'properties': {
                'type': self.rtpc_class_name,
                'position': position,
            },
            'geometry': {
                'type': 'Point',
                'coordinates': coords,
            },
        }

        comment = ''
        if self.rtpc_class_comment is not None:
            comment = self.rtpc_class_comment
            obj['properties']['comment'] = comment

        if self.rtpc_instance_uid is not None:
            obj_id = self.rtpc_instance_uid
            obj['properties']['uid'] = obj_id
            obj['properties']['uid_str'] = '0x{:012X}'.format(obj_id)

        if self.rtpc_cpoi_name is not None:
            cpoi_name = self.rtpc_cpoi_name
            cpoi_name_tr = self.tr.get(cpoi_name, cpoi_name)
            obj['properties']['poi_name'] = cpoi_name
            obj['properties']['poi_name_tr'] = cpoi_name_tr

        if self.rtpc_cpoi_desc is not None:
            cpoi_desc = self.rtpc_cpoi_desc
            cpoi_desc_tr = self.tr.get(cpoi_desc, cpoi_desc)
            obj['properties']['poi_desc'] = cpoi_desc
            obj['properties']['poi_desc_tr'] = cpoi_desc_tr

        if self.rtpc_bookmark_name is not None:
            bookmark_name = self.rtpc_bookmark_name
            obj['properties']['bookmark_name'] = bookmark_name

        if self.rtpc_deca_loot_class is not None:
            loot_class = self.rtpc_deca_loot_class
            obj['properties']['loot_class'] = loot_class

        name = 'CPOI.{}'.format(comment)
        if name in self.points:
            self.points[name].append(obj)
        else:
            self.points[self.rtpc_class_name].append(obj)

    def process_loot_item(self, loot_item_type):
        world = None

        for ii in range(self.node_stack_index-1, -1, -1):
            if self.node_stack[ii][1] == 'CRigidObject':
                world = self.node_stack[ii][2]

        if world is not None:
            self.rtpc_world = Deca3dMatrix(col_major=world)  # get position from CRigidObject ancestor
            x = self.rtpc_world.data[0, 3]
            z = self.rtpc_world.data[1, 3]
            y = self.rtpc_world.data[2, 3]
            position = [x, z, y]
            coords = [
                x * src_to_dst_x_scale + dst_x0,
                y * src_to_dst_y_scale + dst_y0,
            ]

            obj = {
                'type': 'Feature',
                'properties': {
                    'type': loot_item_type,
                    'position': position,
                },
                'geometry': {
                    'type': 'Point',
                    'coordinates': coords,
                },
            }

            if self.rtpc_item_item_id is not None:
                comment = self.rtpc_item_item_id
                obj['properties']['comment'] = comment

            if self.rtpc_instance_uid is not None:
                obj_id = self.rtpc_instance_uid
                obj['properties']['uid'] = obj_id
                obj['properties']['uid_str'] = '0x{:012X}'.format(obj_id)

            if self.rtpc_cpoi_name is not None:
                cpoi_name = self.rtpc_cpoi_name
                cpoi_name_tr = self.tr.get(cpoi_name, cpoi_name)
                obj['properties']['poi_name'] = cpoi_name
                obj['properties']['poi_name_tr'] = cpoi_name_tr

            if self.rtpc_cpoi_desc is not None:
                cpoi_desc = self.rtpc_cpoi_desc
                cpoi_desc_tr = self.tr.get(cpoi_desc, cpoi_desc)
                obj['properties']['poi_desc'] = cpoi_desc
                obj['properties']['poi_desc_tr'] = cpoi_desc_tr

            if self.rtpc_bookmark_name is not None:
                bookmark_name = self.rtpc_bookmark_name
                obj['properties']['bookmark_name'] = bookmark_name

            if self.rtpc_deca_loot_class is not None:
                loot_class = self.rtpc_deca_loot_class
                obj['properties']['loot_class'] = loot_class

            self.points[loot_item_type].append(obj)

    def process_CRegion(self):
        self.rtpc_world = Deca3dMatrix(col_major=self.rtpc_world)
        obj_type = self.rtpc_class_name
        obj_id = self.rtpc_instance_uid
        comment = self.rtpc_class_comment
        ref_matrix = self.rtpc_world.data
        border = np.array(self.rtpc_cregion_border).reshape((-1, 4)).transpose()
        border[3, :] = 1.0
        border = np.matmul(ref_matrix, border)
        border = border.transpose()

        if len(border) == 0:
            x = self.rtpc_world.data[0, 3]
            z = self.rtpc_world.data[1, 3]
            y = self.rtpc_world.data[2, 3]
            position = [x, z, y]
            position = [position, position]
        else:
            position = [
                np.min(border, axis=1)[0:3].tolist(),
                np.max(border, axis=1)[0:3].tolist(),
            ]

        coords = border * np.array([src_to_dst_x_scale, 0, src_to_dst_y_scale, 0]) + np.array([dst_x0, 0, dst_y0, 0])
        coords = [list(v) for v in coords[:, [0, 2]]]

        obj = {
            'type': 'Feature',
            'properties': {
                'type': obj_type,
                'position': position,
                'uid': obj_id,
                'uid_str': '0x{:012X}'.format(obj_id),
                'comment': comment,
            },
            'geometry': {
                'type': 'Polygon',
                'coordinates': [coords]
            },
        }
        self.regions.append(obj)

    def process_CGraphObject(self):
        self.rtpc_world = Deca3dMatrix(col_major=self.rtpc_world)
        script = self.rtpc_script

        if script == 'graphs/check_apex_social_event.graph':
            apex_id = self.rtpc_ref_apex_identifier

            ref_matrix = self.rtpc_world.data
            x = ref_matrix[0, 3]
            z = ref_matrix[1, 3]
            y = ref_matrix[2, 3]
            position = [x, z, y]
            coords = [
                x * src_to_dst_x_scale + dst_x0,
                y * src_to_dst_y_scale + dst_y0,
            ]

            obj = {
                'type': 'Feature',
                'properties': {
                    'type': 'apex_social',
                    'apex_id': apex_id,
                    'position': position,
                },
                'geometry': {
                    'type': 'Point',
                    'coordinates': coords,
                },
            }

            lst = self.apex_social_control.get(apex_id, [])
            lst.append(obj)
            self.apex_social_control[apex_id] = lst

    def node_start(self, bufn, pos, index, node_info):
        self.node_stack_index += 1
        if len(self.node_stack) <= self.node_stack_index:
            self.node_stack.append([None, None, None])
        self.node_stack[self.node_stack_index][0] = index
        self.node_stack[self.node_stack_index][1] = None
        self.node_stack[self.node_stack_index][2] = None

    def node_end(self, bufn, pos, index, node_info):
        self.node_stack_index -= 1

    def props_start(self, bufn, pos, count):
        self.rtpc_class_name = None  # PropName.CLASS_NAME
        self.rtpc_class_comment = None  # PropName.CLASS_COMMENT
        self.rtpc_world = None  # rtpc_prop_world
        self.rtpc_script = None  # rtpc_prop_name_script
        self.rtpc_ref_apex_identifier = None  # rtpc_prop_ref_apex_identifier
        self.rtpc_cregion_border = None  # PropName.CREGION_BORDER
        self.rtpc_instance_uid = None  # PropName.INSTANCE_UID
        self.rtpc_cpoi_name = None  # PropName.CPOI_NAME
        self.rtpc_cpoi_desc = None  # PropName.CPOI_DESC
        self.rtpc_bookmark_name = None  # PropName.BOOKMARK_NAME
        self.rtpc_item_item_id = None
        self.rtpc_deca_loot_class = None  # 0x34beec18
        self.rtpc_deca_crafting_type = None  # 0xa949bc65

    def props_end(self, bufn, pos, count):
        point_types = {
            'CLootCrateSpawnPoint', 'CLootCrateSpawnPointGroup', 'CBookMark', 'CPOI', 'CCollectable',
            'CPlayerSpawnPoint'
        }

        if self.rtpc_class_name in point_types:
            self.process_point(),
        elif self.rtpc_class_name == 'CGraphObject':
            if self.rtpc_script == 'graphs/check_apex_social_event.graph':
                self.process_CGraphObject()
            elif self.rtpc_script == 'graphs/interact_lootitem.graph' and isinstance(self.rtpc_item_item_id, str):
                if self.rtpc_item_item_id.startswith('schematic_'):
                    self.process_loot_item('CraftingSchematic')
                else:
                    self.process_loot_item('LootItem')

        elif self.rtpc_class_name == 'CRegion':
            self.process_CRegion()

    def prop_start(self, bufn, pos, index, prop_info):
        prop_pos, prop_name_hash, prop_data_pos, prop_data_raw, prop_type = prop_info
        if rtpc.h_prop_class == prop_name_hash:
            self.rtpc_class_name = parse_prop_data(bufn, prop_info)[0].decode('utf-8')
            self.node_stack[self.node_stack_index][1] = self.rtpc_class_name
        elif rtpc.h_prop_name == prop_name_hash:
            self.rtpc_class_comment = parse_prop_data(bufn, prop_info)[0].decode('utf-8')
        elif rtpc.h_prop_world == prop_name_hash:
            self.rtpc_world = parse_prop_data(bufn, prop_info)[0]
            self.node_stack[self.node_stack_index][2] = self.rtpc_world
        elif rtpc.h_prop_script == prop_name_hash:
            self.rtpc_script = parse_prop_data(bufn, prop_info)[0].decode('utf-8')
        elif rtpc.h_prop_ref_apex_identifier == prop_name_hash:
            self.rtpc_ref_apex_identifier = parse_prop_data(bufn, prop_info)[0].decode('utf-8')
        elif rtpc.h_prop_border == prop_name_hash:
            self.rtpc_cregion_border = parse_prop_data(bufn, prop_info)[0]
        elif rtpc.h_prop_object_id == prop_name_hash:
            self.rtpc_instance_uid = parse_prop_data(bufn, prop_info)[0]
        elif rtpc.h_prop_label_key == prop_name_hash:
            self.rtpc_cpoi_name = parse_prop_data(bufn, prop_info)[0].decode('utf-8')
        elif rtpc.h_prop_deca_cpoi_desc == prop_name_hash:
            self.rtpc_cpoi_desc = parse_prop_data(bufn, prop_info)[0].decode('utf-8')
        elif rtpc.h_prop_note == prop_name_hash:
            self.rtpc_bookmark_name = parse_prop_data(bufn, prop_info)[0].decode('utf-8')
        elif rtpc.h_prop_item_item_id == prop_name_hash:
            self.rtpc_item_item_id = parse_prop_data(bufn, prop_info)[0].decode('utf-8')
        elif rtpc.h_prop_spawn_tags == prop_name_hash:
            self.rtpc_deca_loot_class = parse_prop_data(bufn, prop_info)[0].decode('utf-8')
        elif rtpc.h_prop_deca_crafting_type == prop_name_hash:
            self.rtpc_deca_crafting_type = parse_prop_data(bufn, prop_info)[0].decode('utf-8')


class ToolMakeWebMap:
    def __init__(self, vfs_config):
        if isinstance(vfs_config, str):
            self.vfs: VfsDatabase = vfs_structure_open(vfs_config)
        else:
            self.vfs: VfsDatabase = vfs_config

        self.adf_db = AdfDatabase(self.vfs)

    def make_web_map(self, wdir, copy_support_files):
        force_topo_tiles = False

        # write results
        dpath = os.path.join(wdir, 'map', 'z0')
        os.makedirs(dpath, exist_ok=True)

        export_path = os.path.join(dpath, 'export')
        os.makedirs(export_path, exist_ok=True)

        # BUILD topo map
        topo_dst_path = wdir + 'map/z0/tile_t'
        if not os.path.isdir(topo_dst_path) or force_topo_tiles:  # this is slow so only do it once
            export_map(self.vfs, 'textures/ui/map_reserve_0/zoom', topo_dst_path, True, True)

        # BUILD warboard map
        topo_dst_path = wdir + 'map/z0/tile_wb'
        if not os.path.isdir(topo_dst_path) or force_topo_tiles:  # this is slow so only do it once
            export_map(self.vfs, 'textures/ui/warboard_map/zoom', topo_dst_path, True, True)

        # BUILD height map
        # extract full res image
        fn = b'terrain/global_heightfield.rawc'
        vnode = self.vfs.nodes_where_match(v_path=fn)[0]

        with self.vfs.file_obj_from(vnode) as f:
            buffer = f.read(1024 * 1024)

        aimg = np.frombuffer(buffer, count=512*512, dtype=np.float32)
        aimg = np.reshape(aimg, (512, 512))
        aimg = (aimg - aimg.min()) / (aimg.max() - aimg.min())

        # convert range of values to color map
        cm = plt.get_cmap('jet')
        cimg = cm(aimg)
        img = Image.fromarray((cimg[:, :, :3] * 255).astype(np.uint8))

        tileset_make(img, os.path.join(wdir, 'map', 'z0', 'tile_h'), True, True)

        # BUILD water nvwaveworks map
        # extract full res image
        fn = b'terrain/water_nvwaveworks_mod.rawc'
        vnode = self.vfs.nodes_where_match(v_path=fn)[0]

        with self.vfs.file_obj_from(vnode) as f:
            buffer = f.read(1024 * 1024)

        aimg = np.frombuffer(buffer, count=1024*1024, dtype=np.uint8)
        aimg = np.flipud(np.reshape(aimg, (1024, 1024)).astype(dtype=np.float32))
        aimg = (aimg - aimg.min()) / (aimg.max() - aimg.min())

        # convert range of values to color map
        cm = plt.get_cmap('jet')
        cimg = cm(aimg)
        img = Image.fromarray((cimg[:, :, :3] * 255).astype(np.uint8))

        tileset_make(img, os.path.join(wdir, 'map', 'z0', 'tile_wn'), True, True)

        # BUILD water gerstner map
        # extract full res image
        fn = b'terrain/water_gerstner_mod.rawc'
        vnode = self.vfs.nodes_where_match(v_path=fn)[0]

        with self.vfs.file_obj_from(vnode) as f:
            buffer = f.read(1024 * 1024)

        aimg = np.frombuffer(buffer, count=1024*1024, dtype=np.uint8)
        aimg = np.flipud(np.reshape(aimg, (1024, 1024)).astype(dtype=np.float32))
        aimg = (aimg - aimg.min()) / (aimg.max() - aimg.min())

        # convert range of values to color map
        cm = plt.get_cmap('jet')
        cimg = cm(aimg)
        img = Image.fromarray((cimg[:, :, :3] * 255).astype(np.uint8))

        tileset_make(img, os.path.join(wdir, 'map', 'z0', 'tile_wg'), True, True)

        # TODO parse terrain/nv_water_cull_mask.rawc ? 1 bit per pixel 512x512 pixels
        fn = b'terrain/nv_water_cull_mask.rawc'
        vnode = self.vfs.nodes_where_match(v_path=fn)[0]

        with self.vfs.file_obj_from(vnode) as f:
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

        tileset_make(img, os.path.join(wdir, 'map', 'z0', 'tile_wnm'), True, True)

        tile_overlays = []

        for crit in ['dreadnought', 'harvester', 'hunter', 'scout', 'skirmisher']:
            for ctype, color in zip(['a', 'b', 'c', 'd'], [[255, 0, 0, 255], [0, 255, 0, 255], [0, 0, 255, 255], [255, 0, 255, 255]]):
                tile_overlays.append([
                    'settings/hp_settings/hp_ai_textures/spawn_maps/spawn_{}_{}.bmp_datac'.format(crit, ctype).encode('ascii'),
                    'tile_spawn_{}_{}'.format(crit, ctype),
                    color
                ])

        tile_overlays.append([
            'settings/hp_settings/hp_ai_textures/bitmaps/dreadnought_forbidden_map.bmp_datac'.encode('ascii'),
            'tile_bitmap_dreadnought_forbidden_map',
            [255, 0, 0, 255]
        ])

        tile_overlays.append([
            'settings/hp_settings/hp_ai_textures/bitmaps/flee_reserve_0.bmp_datac'.encode('ascii'),
            'tile_bitmap_flee_reserve_0',
            [0, 255, 0, 255]
        ])

        tile_overlays.append([
            'settings/hp_settings/hp_ai_textures/bitmaps/animal_forbidden_map_0.bmp_datac'.encode('ascii'),
            'tile_bitmap_animal_forbidden_map_0',
            [0, 0, 255, 255]
        ])

        for tileo in tile_overlays:
            fn = tileo[0]
            vnode = self.vfs.nodes_where_match(v_path=fn)[0]

            bmp_adf = self.adf_db.read_node(self.vfs, vnode)

            bitfield = bmp_adf.table_instance_values[0]['Layers'][0]['Bitfield']
            bitfield = np.asarray(bitfield, dtype=np.uint32).data

            aimg = np.frombuffer(bitfield, count=8 * 1024, dtype=np.uint8)
            cimg = np.zeros((512, 512, 4), dtype=np.uint8)

            for r in range(256):
                rd = aimg[r * 32:(r + 1) * 32]
                # print(*['{:02X}'.format(v) for v in rd])
                for c in range(32):
                    for sc in range(8):
                        if rd[c] & (0x01 << sc) == 0:
                            cimg[128 + r, 128 + c * 8 + sc, :] = [0, 0, 0, 0]
                        else:
                            cimg[128 + r, 128 + c * 8 + sc, :] = tileo[2]
            # cimg = np.flip(cimg, 0)
            img = Image.fromarray(cimg)

            tileset_make(img, os.path.join(wdir, 'map', 'z0', '{}'.format(tileo[1])), True, True)

        # load translation
        vnode = self.vfs.nodes_where_match(v_path=b'text/master_eng.stringlookup')[0]
        tr = process_translation_adf(self.vfs, self.adf_db, vnode)

        # load collectable codex
        vnode = self.vfs.nodes_where_match(v_path=b'settings/hp_settings/codex_data.bin')[0]
        categories, codex = process_codex_adf(self.vfs, self.adf_db, vnode, export_path=export_path)

        print('PROCESSING: blo(s)')
        visitor = RtpcVisitorMap(tr)
        blo_expr = re.compile(rb'^.*blo$')

        vpaths = self.vfs.nodes_select_distinct_vpath()
        vpaths = [v for v in vpaths if blo_expr.match(v)]

        for fn in vpaths:
            print('PROCESSING: {}'.format(fn))
            vnodes = self.vfs.nodes_where_match(v_path=fn)
            vnode = vnodes[0]
            with self.vfs.file_obj_from(vnode) as f:
                buffer = f.read()

            visitor.visit(buffer)

        # for fn in vpaths:
        #     print('PROCESSING: {}'.format(fn))
        #     vnodes = self.vfs.nodes_where_match(v_path=fn)
        #     vnode = vnodes[0]
        #     with self.vfs.file_obj_from(vnode) as f:
        #         rtpc = Rtpc()
        #         rtpc.deserialize(f)
        #     rtpc.visit(visitor)

        # LOAD from global/collection.collectionc
        # todo dump of different vnodes, one in gdcc is stripped
        vnode = self.vfs.nodes_where_match(v_path=b'global/collection.collectionc')[0]
        adf = self.adf_db.read_node(self.vfs, vnode)
        collectables = []
        for v in adf.table_instance_values[0]['Collectibles']:
            obj_id = v['ID']
            cid = v['Name'].decode('utf-8')
            name, desc, icon, category = codex.get(cid, (cid, cid + '_desc', None, None))
            name = tr.get(name, name)
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
                    'collectable_name_tr': name,
                    'collectable_desc_tr': desc,
                    'position': position,
                },
                'geometry': {
                    'type': 'Point',
                    'coordinates': coords
                },
            }
            collectables.append(obj)

        # get all mdic AABBs
        print('PROCESSING: mdics')
        mdic_expr = re.compile(rb'^.*mdic$')
        mdics = []

        vpaths = self.vfs.nodes_select_distinct_vpath()
        vpaths = [v for v in vpaths if mdic_expr.match(v)]

        for fn in vpaths:
            print('PROCESSING: {}'.format(fn))
            vnodes = self.vfs.nodes_where_match(v_path=fn)
            vnode = vnodes[0]
            adf = self.adf_db.read_node(self.vfs, vnode)
            aabb = AABB(all6=adf.table_instance_values[0]['AABB'])
            border = [
                [aabb.min[0], aabb.min[2]],
                [aabb.max[0], aabb.min[2]],
                [aabb.max[0], aabb.max[2]],
                [aabb.min[0], aabb.max[2]],
            ]

            coords = []
            for pt in border:
                x = pt[0] * src_to_dst_x_scale + dst_x0
                y = pt[1] * src_to_dst_y_scale + dst_y0
                coords.append([x, y])

            obj = {
                'type': 'Feature',
                'properties': {
                    'type': 'mdic',
                    'uid': vnode.v_hash,
                    'uid_str': vnode.v_path.decode('utf-8'),
                    'comment': '',
                    'position': [aabb.min.tolist(), aabb.max.tolist()],
                },
                'geometry': {
                    'type': 'Polygon',
                    'coordinates': [coords]
                },
            }
            mdics.append(obj)


        # results from found rtpc records
        print('Region: count = {}'.format(len(visitor.regions)))
        print('Collectables: count = {}'.format(len(collectables)))
        print('MDICs: count = {}'.format(len(mdics)))
        for k, v in visitor.points.items():
            print('{}: count = {}'.format(k, len(v)))

        def point_sort(lst):
            return sorted(lst, key=lambda v: v['properties']['position'])

        def aabb_port(lst):
            return sorted(lst, key=lambda v: v['properties']['position'][0] + v['properties']['position'][1])

        apex_social_control = {}
        sorted_keys = sorted(visitor.apex_social_control.keys())
        for k in sorted_keys:
            v = visitor.apex_social_control[k]
            apex_social_control[k] = point_sort(v)

        data_list = [
            ['collectable_data', point_sort(collectables)],
            ['region_data', aabb_port(visitor.regions)],
            ['mdic_data', aabb_port(mdics)],
            ['c_collectable_data', point_sort(visitor.points['CCollectable'])],
            ['c_book_mark_data', point_sort(visitor.points['CBookMark'])],
            ['c_loot_crate_spawn_point_data', point_sort(visitor.points['CLootCrateSpawnPoint'])],
            ['c_loot_crate_spawn_point_group_data', point_sort(visitor.points['CLootCrateSpawnPointGroup'])],
            ['c_player_spawn_point_data', point_sort(visitor.points['CPlayerSpawnPoint'])],
            ['c_poi', point_sort(visitor.points['CPOI'])],
            ['c_poi_nest_marker_poi', point_sort(visitor.points['CPOI.nest_marker_poi'])],
            ['apex_social_control', apex_social_control],
            ['crafting_schematics', point_sort(visitor.points['CraftingSchematic'])],
            ['loot_items', point_sort(visitor.points['LootItem'])],
        ]
        for data_item in data_list:
            fp = f'data/{data_item[0]}.js'
            fp = os.path.join(dpath, fp)
            make_dir_for_file(fp)
            with open(fp, 'w') as f:
                f.write('var {} = {};\n'.format(data_item[0], json.dumps(data_item[1], indent=4)))

        if copy_support_files:
            dst = os.path.join(dpath, 'index.html')
            if os.path.exists(dst):
                print('WARNING: {} already exists will not over-write'.format(dst))
            else:
                shutil.copyfile(os.path.join('.', 'resources', 'make_web_map', 'index.html'), dst)

            dst = os.path.join(dpath, 'full.html')
            if os.path.exists(dst):
                print('WARNING: {} already exists will not over-write'.format(dst))
            else:
                shutil.copyfile(os.path.join('.', 'resources', 'make_web_map', 'full.html'), dst)

            dst = os.path.join(dpath, 'lib')
            if os.path.exists(dst):
                print('WARNING: {} already exists will not over-write'.format(dst))
            else:
                shutil.copytree(os.path.join('.', 'resources', 'make_web_map', 'lib'), dst)


def main():
    tool = ToolMakeWebMap(os.path.join(deca_root(), '..', 'work', 'gz', 'project.json'))
    tool.make_web_map(tool.vfs.working_dir, False)


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
