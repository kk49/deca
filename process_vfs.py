from deca.ff_vfs import VfsStructure

prefix_in = '/home/krys/prj/gz/archives_win64/'
prefix_out = './test/gz/'
ver = 3
debug = False

vfs = VfsStructure(prefix_out)

vfs.load_from_archives(prefix_in, debug=debug)



