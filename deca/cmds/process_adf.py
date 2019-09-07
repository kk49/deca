import sys
import os
from deca.file import ArchiveFile
from deca.ff_adf import Adf


if len(sys.argv) < 2:
    in_file = '/home/krys/prj/work/gzb/extracted/models/manmade/props/interior/civilian_01_answering_machine.hrmeshc'
    in_file = '/home/krys/prj/work/gzb/extracted/models/manmade/props/interior/civilian_01_answering_machine.modelc'
    in_file = '/home/krys/prj/work/gzb/extracted/graphs/check_region_difficulty.graphc'
    in_file = '/home/krys/prj/work/gzb/extracted/graphs/check_region_difficulty.graphc'
    in_file = '/home/krys/prj/work/gzb/extracted/gdc/global.gdcc'
    in_file = '/home/krys/prj/work/gz/extracted/environment/base.environc'
    in_file = '/home/krys/prj/work/gz/extracted/graphs/car_cabinlight_logic.graphc'
    in_file = '/home/krys/prj/work/gz_saves/76561198106670711.015/savegame'
else:
    in_file = sys.argv[1]

file_sz = os.stat(in_file).st_size

obj = Adf()
with ArchiveFile(open(in_file, 'rb')) as f:
    obj.deserialize(f)

print(obj.dump_to_string())
