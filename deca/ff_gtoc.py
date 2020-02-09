import io
from .file import ArchiveFile


class GtocArchiveEntry:
    src_uid = None
    path_hash32 = None
    archive_magic = None
    file_entries = []


class GtocFileEntry:
    offset_in_archive = None
    path_hash32 = None
    ext_hash32 = None
    file_size = None
    path = None


def process_buffer_gtoc(buffer, parent_uid):
    recs = []
    with ArchiveFile(io.BytesIO(buffer)) as f:
        magic = f.read_u32()
        file_count = f.read_u32()

        # process archive records
        archives = []
        for fi in range(file_count):
            path_hash32 = f.read_u32()

            archive_magic_number = f.read_u32()

            block_len = f.read_u32()

            blocks = []
            for i in range(block_len):
                block_pos = f.tell()
                record_id = block_pos + f.read_u32()
                offset_in_archive = f.read_u32()
                blocks.append([record_id, offset_in_archive])

            archives.append([path_hash32, archive_magic_number, blocks])

        # process file records
        toc = []
        while True:
            offset = f.tell()
            path_hash32 = f.read_u32()
            ext_hash32 = f.read_u32()
            file_size = f.read_u32()
            path = f.read_strz()

            if path_hash32 is None or ext_hash32 is None or file_size is None or path is None:
                break

            p = f.tell()
            p = (p + 3) // 4 * 4
            f.seek(p)

            toc.append([offset, path_hash32, ext_hash32, file_size, path])

            # print(files[fi])
            # print(vpath_hash32, ext_hash32, file_size, s)

    toc_map = dict([(fi[0], fi[1:]) for fi in toc])
    all_paths = [fi[4] for fi in toc]

    archive_entries = []
    for archive in archives:
        archive_entry = GtocArchiveEntry()
        archive_entry.src_uid = parent_uid
        archive_entry.path_hash32 = archive[0]
        archive_entry.archive_magic = archive[1]
        blocks = archive[2]

        file_entries = []
        for block in blocks:
            record_id = block[0]
            offset_in_archive = block[1]

            fe = toc_map[record_id]

            file_entry = GtocFileEntry()
            file_entry.offset_in_archive = offset_in_archive
            file_entry.path_hash32 = fe[0]
            file_entry.ext_hash32 = fe[1]
            file_entry.file_size = fe[2]
            file_entry.path = fe[3]

            file_entries.append(file_entry)

        archive_entry.file_entries = file_entries

        archive_entries.append(archive_entry)

    # record_ids = []
    # for archive in archives:
    #     record_ids += [block[0] for block in archive[2]]
    # record_ids_unique = set(record_ids)
    # record_ids_sorted = list(record_ids_unique)
    # record_ids_sorted.sort()
    #
    # magic_numbers = [archive[1] for archive in archives]
    # magic_numbers_unique = set(magic_numbers)
    # magic_numbers_sorted = list(magic_numbers_unique)
    # magic_numbers_sorted.sort()

    return archive_entries, all_paths




