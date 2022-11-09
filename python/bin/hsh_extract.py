import sys
import struct


def main():
    if len(sys.argv) != 3:
        print("USAGE: python hsh_extract.py <IN_FILE, hsh> <OUT_FILE, txt>", file=sys.stderr)
        exit(1)

    str_list = []
    s = b''
    with open(sys.argv[1], "rb") as f:
        while True:
            cs = f.read(1)

            if cs is None or len(cs) == 0:
                break

            c = cs[0]
            if c == 0:

                hsh = f.read(4)
                hsh = struct.unpack("<I", hsh)

                # print(f"{s.decode()}")

                str_list.append((s, hsh))
                s = b''
            else:
                s = s + cs

    with open(sys.argv[2], "wb") as f:
        for s, hsh in str_list:
            f.write(s)
            f.write(b"\n")

    print(f"Extracted {len(str_list)} strings", file=sys.stderr)


if __name__ == '__main__':
    main()
