from deca.ff_adf import extract_adftypes_from_exe


def main():
    map_type, map_type_filename = extract_adftypes_from_exe('/home/krys/.steam/steam/steamapps/common/GenerationZero/GenerationZero_F.exe', '/home/krys/prj/deca/resources/adf/')

    print(len(map_type))

    print(map_type[3371486195])


if __name__ == "__main__":
    main()
