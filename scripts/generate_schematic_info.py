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

        self.node_stack = []
        self.node_stack_index = -1

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

    def process_crafting_schematic(self):
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

            obj = [position, self.rtpc_item_item_id]

            self.schematics.append(obj)

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
        if \
                isinstance(self.rtpc_script, str) and \
                self.rtpc_script == 'graphs/interact_lootitem.graph' and \
                self.rtpc_class_name == 'CGraphObject':
            if isinstance(self.rtpc_item_item_id, str):
                self.process_crafting_schematic()
            else:
                print('Missing item ID')

    def prop_start(self, bufn, pos, index, prop_info):
        prop_pos, prop_name_hash, prop_data_pos, prop_data_raw, prop_type = prop_info
        if rtpc.prop_class_name == prop_name_hash:
            self.rtpc_class_name = parse_prop_data(bufn, prop_info)[0].decode('utf-8')
            self.node_stack[self.node_stack_index][1] = self.rtpc_class_name
        elif rtpc.prop_class_comment == prop_name_hash:
            self.rtpc_class_comment = parse_prop_data(bufn, prop_info)[0].decode('utf-8')
        elif rtpc.prop_world == prop_name_hash:
            self.rtpc_world = parse_prop_data(bufn, prop_info)[0]
            self.node_stack[self.node_stack_index][2] = self.rtpc_world
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
        elif rtpc.prop_item_item_id == prop_name_hash:
            self.rtpc_item_item_id = parse_prop_data(bufn, prop_info)[0].decode('utf-8')
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


schematics = []
resources = set()
benefits = set()
for i, schematic in enumerate(visitor.schematics):
    name: str
    position, name = schematic
    if name.startswith('schematic_'):
        equip = vfs.lookup_equipment_from_name(name)
        crafting = equip['Crafting']

        stats_file = crafting['StatsFile']
        stats_vnode = vfs.nodes_where_match(v_hash=stats_file)
        stats = adf_db.read_node(vfs, stats_vnode[0])
        stats = stats.table_instance_values[0]

        stat_bonuses = {}

        if stats['HealthBonus']['UIValue'] != 0.0:
            stat_bonuses['Health Bonus'] = stats['HealthBonus']['UIValue']

        if stats['DamageResistance']['OverallUIValue'] != 0.0:
            stat_bonuses['Overall Resistance'] = stats['DamageResistance']['OverallUIValue']
        if stats['DamageResistance']['BulletUIValue'] != 0.0:
            stat_bonuses['Bullet Resistance'] = stats['DamageResistance']['BulletUIValue']
        if stats['DamageResistance']['ExplosionUIValue'] != 0.0:
            stat_bonuses['Explosion Resistance'] = stats['DamageResistance']['ExplosionUIValue']
        if stats['DamageResistance']['FireUIValue'] != 0.0:
            stat_bonuses['Fire Resistance'] = stats['DamageResistance']['FireUIValue']
        if stats['DamageResistance']['FallUIValue'] != 0.0:
            stat_bonuses['Fall Resistance'] = stats['DamageResistance']['FallUIValue']
        if stats['DamageResistance']['ImpactUIValue'] != 0.0:
            stat_bonuses['Impact Resistance'] = stats['DamageResistance']['ImpactUIValue']
        if stats['DamageResistance']['GasUIValue'] != 0.0:
            stat_bonuses['Gas Resistance'] = stats['DamageResistance']['GasUIValue']

        if stats['MovementSpeed']['UIValue'] != 0.0:
            stat_bonuses['Movement Speed'] = stats['MovementSpeed']['UIValue']
        if stats['JumpBoost']['UIValue'] != 0.0:
            stat_bonuses['Jump Boost'] = stats['JumpBoost']['UIValue']
        if stats['Visiblity']['UIValue'] != 0.0:
            stat_bonuses['Visibility Reduction'] = stats['Visiblity']['UIValue']
        if stats['NoiseReduction']['UIValue'] != 0.0:
            stat_bonuses['Noise Reduction'] = stats['NoiseReduction']['UIValue']

        for k in stat_bonuses.keys():
            benefits.add(k)

        required_resource = crafting['RequiredResources']
        required_resources = {}
        for rr in required_resource:
            resource_hash = rr['EquipmentHash']
            resource_str = vfs.hash_string_match(hash32=resource_hash)[0][1].decode('utf-8')
            amount = rr['Amount']
            resources.add(resource_str)
            required_resources[resource_str] = amount

        schematics.append([position, name, required_resources, stat_bonuses])

item_type = {
    'jacket': 'Jacket',
    'pants': 'Pants',
    'shirt': 'Shirt',
    'shoes': 'Shoes',
}

quality_factor = {
    'q1': 'q1',
    'q2': 'q2',
    'q3': 'q3',
    'q4': 'q4',
    'q5': 'q5',
}

benefits = sorted(benefits)
resources = sorted(resources)

print('{| class = "article-table"')
print('!Item Type')
print('!Quality')
print('!Benefits')
print('!Resources')
# for benefit in benefits:
#     print(f'!{benefit}')
print('!Location')

ss = sorted(schematics)


for ele in ss:
    position, name, required_resources, stat_bonuses = ele
    it = ''
    bt = ''
    qt = ''
    for k, v in item_type.items():
        if name.find(k) >= 0:
            it = v
            break

    for k, v in quality_factor.items():
        if name.find(k) >= 0:
            qt = v
            break

    print('|-')
    print('|{}'.format(it))
    print('|{}'.format(qt))

    bs = [f'{b} ({stat_bonuses[b]*100:.0f}%)' for b in benefits if b in stat_bonuses]
    bs = ', '.join(bs)
    print(f'|{bs}')

    rs = [f'{required_resources[r]} {r}' for r in resources if r in required_resources]
    rs = ', '.join(rs)
    print(f'|{rs}')

    print('| {:.1f}, {:.1f}'.format(ele[0][0], ele[0][2]))
print('|}')

# generate list of all placed objects
with open('placed_equipment.tsv', 'w') as f:
    f.write(f'ID\tItem Name\tItem Desc\tX\tY\n')

    for i, schematic in enumerate(visitor.schematics):
        name: str
        position, name = schematic
        if name is not None:
            equip = vfs.lookup_equipment_from_name(name)
            if equip is not None:
                equip_name = equip['DisplayNameHash']
                equip_name_list = vfs.hash_string_match(hash32=equip_name)
                if equip_name_list:
                    equip_name = equip_name_list[0][1].decode('utf-8')
                    equip_name = tr.get(equip_name, equip_name)
                equip_desc = equip['DisplayDescriptionHash']
                equip_desc_list = vfs.hash_string_match(hash32=equip_desc)
                if equip_desc_list:
                    equip_desc = equip_desc_list[0][1].decode('utf-8')
                    equip_desc = tr.get(equip_desc, equip_desc)
            else:
                equip_name = 'UNKNOWN'
                equip_desc = 'UNKNOWN'
            f.write(f'{name}\t{equip_name}\t{equip_desc}\t{position[0]}\t{position[2]}\n')

