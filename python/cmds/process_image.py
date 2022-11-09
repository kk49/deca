import sys
from deca.file import ArchiveFile
import deca.ff_avtx


def main():
    if len(sys.argv) > 1:
        filename = sys.argv[1]
    else:
        filename = '/home/krys/prj/work/gz/mod/textures/decals/commecrial_decal_01_bepp_alpha_dif.dds'
        # filename = '/home/krys/prj/work/gz/mod/models/characters/machines/dreadnought/textures/dreadnought_body_01_ai_dif.ddsc.dds'

    ddsc = deca.ff_avtx.Ddsc()
    with ArchiveFile(open(filename, 'rb')) as f:
        ddsc.load_dds(f)


if __name__ == "__main__":
    main()
