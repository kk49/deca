import sys
import time
from deca.ff_avtx import Ddsc, ddsc_write_to_png, ddsc_write_to_dds


def main():
    if len(sys.argv) > 1:
        filename = sys.argv[1]
    else:
        # filename = '/home/krys/prj/test-deca/images/rg2/avtx_98/0099d5d87e9ee615.dat'
        # filename = '/home/krys/prj/test-deca/images/rg2/avtx_98/01f124a03533a3bb.dat'
        # filename = '/home/krys/prj/test-deca/images/rg2/avtx_98/269a7a27c601837e.dat'
        # filename = '/home/krys/prj/test-deca/images/rg2/avtx_98/26a057f5d16e88f0.dat'
        filename = '/home/krys/prj/test-deca/images/rg2/avtx_77/tree_diffuse_atlas.ddsc'

    for i in range(8):
        t0 = time.time()
        with open(filename, 'rb') as f:
            ddsc = Ddsc()
            ddsc.load_ddsc(f, save_raw_data=True)
        t1 = time.time()

        print(f'Time = {t1-t0}')

    ddsc_write_to_png(ddsc, filename + '.png')
    ddsc_write_to_dds(ddsc, filename + '.dds')


if __name__ == "__main__":
    main()
