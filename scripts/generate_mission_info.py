import re
from deca.vfs_processor import vfs_structure_open
from deca.ff_adf import adf_read_node
from deca.digest import process_translation_adf

vfs = vfs_structure_open('/home/krys/prj/work/gz/project.json')

# load translation
vnode = vfs.map_vpath_to_vfsnodes[b'text/master_eng.stringlookup'][0]
with vfs.file_obj_from(vnode, 'rb') as f:
    tr = process_translation_adf(vfs, f, vnode.size_u)

vnode = vfs.map_vpath_to_vfsnodes[b'missions/missions.group.hpmissionsc'][0]
adf = adf_read_node(vfs, vnode)


class GZMission:
    def __init__(self, tr, v):
        self.id = v.value['Id'].value

        mission_name = v.value['Name'].hash_string.decode('utf-8')
        mission_name_short = v.value['NameShort'].hash_string.decode('utf-8')
        mission_summary = v.value['Summary'].hash_string.decode('utf-8')
        mission_description = v.value['Description'].hash_string.decode('utf-8')

        self.name = tr.get(mission_name, mission_name).replace('\n', '<br/>')
        self.name_short = tr.get(mission_name_short, mission_name_short).replace('\n', '<br/>')
        self.summary = tr.get(mission_summary, mission_summary).replace('\n', '<br/>')
        self.description = tr.get(mission_description, mission_description).replace('\n', '<br/>')

        self.dep_required = v.value['DependenciesRequired'].value
        self.dep_optional = v.value['DependenciesOptional'].value

    def __repr__(self):
        str = ''
        str += f'{self.id}\n'
        str += f'  {self.name}\n'
        str += f'  {self.name_short}\n'
        str += f'  {self.summary}\n'
        str += f'  {self.description}\n'
        str += f'  {self.dep_required}\n'
        str += f'  {self.dep_optional}\n'

        return str


missions = {}
for mraw in adf.table_instance_full_values[0].value['Missions'].value:
    mission = GZMission(tr, mraw)
    missions[mission.id] = mission

with open('missions.tsv', 'w') as f:
    f.write('id\tname\tname_short\tsummary\tdescription\tdep_required\tdep_optional\n')
    for k, v in missions.items():
        f.write(f'{v.id}\t{v.name}\t{v.name_short}\t{v.summary}\t{v.description}\t{v.dep_required}\t{v.dep_optional}\n')
