import re
from deca.db_core import VfsDatabase
from deca.db_processor import vfs_structure_open
from deca.ff_adf import AdfDatabase
from deca.digest import process_translation_adf, process_codex_adf
from deca.ff_adf_amf_gltf import Deca3dMatrix
import deca.ff_rtpc as rtpc
from deca.ff_rtpc import parse_prop_data

vfs: VfsDatabase = vfs_structure_open('/home/krys/prj/work/gz/project.json')
adf_db = AdfDatabase(vfs)

# load translation
vnode = vfs.nodes_where_match(v_path=b'text/master_eng.stringlookup')[0]
tr = process_translation_adf(vfs, adf_db, vnode)


#         @0x000001a4(     420) 0xa949bc65 0x00000f5f 0x03 str    = @0x00000f5f(    3935) b'craftingmagazinenoiseshoes'
class RtpcVisitorSchematic(rtpc.RtpcVisitor):
    def __init__(self, tr):
        super(RtpcVisitorSchematic, self).__init__()
        self.tr = tr
        self.schematics = []

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
        self.rtpc_deca_loot_class = None  # 0x34beec18
        self.rtpc_deca_crafting_type = None  # 0xa949bc65

    def process_crafting_schematic(self):
        self.rtpc_world = Deca3dMatrix(col_major=self.rtpc_world)
        x = self.rtpc_world.data[0, 3]
        z = self.rtpc_world.data[1, 3]
        y = self.rtpc_world.data[2, 3]
        position = [x, z, y]

        obj = [position, self.rtpc_deca_crafting_type]

        self.schematics.append(obj)

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
        self.rtpc_deca_loot_class = None  # 0x34beec18
        self.rtpc_deca_crafting_type = None  # 0xa949bc65

    def props_end(self, bufn, pos, count):
        if isinstance(self.rtpc_deca_crafting_type, str) and self.rtpc_deca_crafting_type.startswith('crafting') and self.rtpc_class_name == 'CRigidObject':
            self.process_crafting_schematic()

    def prop_start(self, bufn, pos, index, prop_info):
        prop_pos, prop_name_hash, prop_data_pos, prop_data_raw, prop_type = prop_info
        if rtpc.prop_class_name == prop_name_hash:
            self.rtpc_class_name = parse_prop_data(bufn, prop_info)[0].decode('utf-8')
        elif rtpc.prop_class_comment == prop_name_hash:
            self.rtpc_class_comment = parse_prop_data(bufn, prop_info)[0].decode('utf-8')
        elif rtpc.prop_world == prop_name_hash:
            self.rtpc_world = parse_prop_data(bufn, prop_info)[0]
        elif rtpc.prop_name_script == prop_name_hash:
            self.rtpc_script = parse_prop_data(bufn, prop_info)[0].decode('utf-8')
        elif rtpc.prop_ref_apex_identifier == prop_name_hash:
            self.rtpc_ref_apex_identifier = parse_prop_data(bufn, prop_info)[0].decode('utf-8')
        elif rtpc.prop_cregion_border == prop_name_hash:
            self.rtpc_cregion_border = parse_prop_data(bufn, prop_info)[0]
        elif rtpc.prop_instance_uid == prop_name_hash:
            self.rtpc_instance_uid = parse_prop_data(bufn, prop_info)[0]
        elif rtpc.prop_cpoi_name == prop_name_hash:
            self.rtpc_cpoi_name = parse_prop_data(bufn, prop_info)[0].decode('utf-8')
        elif rtpc.prop_cpoi_desc == prop_name_hash:
            self.rtpc_cpoi_desc = parse_prop_data(bufn, prop_info)[0].decode('utf-8')
        elif rtpc.prop_bookmark_name == prop_name_hash:
            self.rtpc_bookmark_name = parse_prop_data(bufn, prop_info)[0].decode('utf-8')
        elif rtpc.prop_deca_loot_class == prop_name_hash:
            self.rtpc_deca_loot_class = parse_prop_data(bufn, prop_info)[0].decode('utf-8')
        elif rtpc.prop_deca_crafting_type == prop_name_hash:
            self.rtpc_deca_crafting_type = parse_prop_data(bufn, prop_info)[0].decode('utf-8')


print('PROCESSING: blo(s)')
visitor = RtpcVisitorSchematic(tr)
# blo_expr = re.compile(rb'^.*schematic.blo$')
blo_expr = re.compile(rb'^.*blo$')

vpaths = vfs.nodes_select_distinct_vpath()
vpaths = [v for v in vpaths if blo_expr.match(v)]

for fn in vpaths:
    print('PROCESSING: {}'.format(fn))
    vnodes = vfs.nodes_where_match(v_path=fn)
    vnode = vnodes[0]
    with vfs.file_obj_from(vnode) as f:
        buffer = f.read()

    visitor.visit(buffer)

benefits = {
    'bullet': 'Bullet Damage Reduction',
    'explosive': 'Explosive Damage Reduction',
    'fire': 'Fire Damage Reduction',
    'fall': 'Fall Damage Reduction',
    'noise': 'Noise Reduction',
    'visibility': 'Visibility Reduction',
    'jump': 'Jump Bonus',
}

item_type = {
    'jacket': 'Jacket',
    'pants': 'Pants',
    'shirt': 'Shirt',
    'shoes': 'Shoes',
}

print('{| class = "article-table"')
print('!Item Type')
print('!Benefit')
print('!Location')

ss = sorted(visitor.schematics)

for ele in ss:
    ele_type: str = ele[1]
    it = ''
    bt = ''
    for k, v in item_type.items():
        if ele_type.find(k) >= 0:
            it = v
            break

    for k, v in benefits.items():
        if ele_type.find(k) >= 0:
            bt = v
            break

    print('|-')
    print('|{}'.format(it))
    print('|{}'.format(bt))
    print('| {:.1f}, {:.1f}'.format(ele[0][0], ele[0][2]))
print('|}')
