import sys
from deca.ff_avtx import Ddsc, ddsc_write_to_png, ddsc_write_to_dds


def main():
    if len(sys.argv) > 1:
        filename = sys.argv[1]
    else:
        filename = '/home/krys/prj/test-deca/images/rg2/01f124a03533a3bb.dat'
        # filename = '/home/krys/prj/test-deca/images/rg2/269a7a27c601837e.ddsc'
        # filename = '/home/krys/prj/test-deca/images/rg2/26a057f5d16e88f0.ddsc'

    with open(filename, 'rb') as f:
        ddsc = Ddsc()
        ddsc.load_ddsc(f, save_raw_data=True)

    ddsc_write_to_png(ddsc, filename + '.png')
    ddsc_write_to_dds(ddsc, filename + '.dds')


if __name__ == "__main__":
    main()
