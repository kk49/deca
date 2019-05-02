import sys
import os
from deca.file import ArchiveFile
from deca.ff_adf import load_adf


if len(sys.argv) < 2:
    in_file = '/home/krys/prj/work/gzb/extracted/models/manmade/props/interior/civilian_01_answering_machine.hrmeshc'
    in_file = '/home/krys/prj/work/gzb/extracted/models/manmade/props/interior/civilian_01_answering_machine.modelc'
    in_file = '/home/krys/prj/work/gzb/extracted/graphs/check_region_difficulty.graphc'
    in_file = '/home/krys/prj/work/gzb/extracted/graphs/check_region_difficulty.graphc'
    in_file = '/home/krys/prj/work/gzb/extracted/gdc/global.gdcc'
    in_file = '/home/krys/prj/work/gz/extracted/environment/base.environc'
else:
    in_file = sys.argv[1]

file_sz = os.stat(in_file).st_size


with ArchiveFile(open(in_file, 'rb')) as f:
    buffer = f.read(file_sz)
    # dump_block(header, 0x10)

obj = load_adf(buffer)

print(obj.dump_to_string())
