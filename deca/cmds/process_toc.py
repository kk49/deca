from deca.ff_gtoc import process_buffer_gtoc

file = '/home/krys/prj/work/rg2/extracted/sarc.0.gtoc'
# file = '/home/krys/prj/work/rg2/extracted/resourcesets/expentities.gtoc'


with open(file, 'rb') as f:
    buffer = f.read()

process_buffer_gtoc(buffer, None)
