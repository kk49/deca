import sys

from deca.ff_adf import AdfDatabase
import zstandard as zstd


def main():
    fn = sys.argv[1]

    adf_database = AdfDatabase()

    with open(fn, 'rb') as f:
        buf = f.read()

    adf = adf_database._load_adf(buf)

    if adf.instance_count == 1:
        adf_value = adf.table_instance_full_values[0].value
        if isinstance(adf_value, dict) and "SaveData" in adf_value:
            if adf_database.type_map_def[adf_value["SaveData"].value.type_id].name == b"SaveTrap":
                tmp_buf_c = buf[adf.max_file_position + 4:]
                dc = zstd.ZstdDecompressor()
                tmp_buf_u = dc.decompress(tmp_buf_c)

                with open(fn + ".extracted", "wb") as f:
                    f.write(tmp_buf_u)


if __name__ == "__main__":
    main()
