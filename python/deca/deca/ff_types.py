compression_00_none = 0
compression_v4_01_zlib = 0x01
compression_v4_02_unknown = 0x02
compression_v4_03_zstd = 0x03
compression_v4_04_oo = 0x04
compression_v3_zlib = 0xff

FTYPE_NOT_HANDLED = 'NOT'
FTYPE_ARC = 'arc'
FTYPE_TAB = 'tab'
FTYPE_AAF = 'aaf'
FTYPE_SARC = 'sarc'
FTYPE_BMP = 'bmp'
FTYPE_DDS = 'dds'
FTYPE_AVTX = 'avtx'
FTYPE_ATX = 'atx'
FTYPE_HMDDSC = 'hmddsc'
FTYPE_ADF = 'adf'
FTYPE_ADF_BARE = 'adfb'  # these are the adf files inside of the gdcc adf, type information is in the entry
FTYPE_TXT = 'txt'
FTYPE_OBC = 'obc'
FTYPE_RIFF = 'riff'
FTYPE_RTPC = 'rtpc'
FTYPE_TAG0 = 'tag0'
FTYPE_H2014 = 'h2014'
FTYPE_MDI = 'mdi'
FTYPE_PFX = 'pfx'
FTYPE_FSB5C = 'FSB5c'
FTYPE_RBMDL = 'rbmdl'
FTYPE_GDCBODY = 'gdc'
FTYPE_GFX = 'gfx'
FTYPE_OGG = 'ogg'
FTYPE_BINK_KB2 = 'kb2'
FTYPE_BINK_BIK = 'bik'
FTYPE_GT0C = 'gt0c'
FTYPE_GARC = 'garc'
FTYPE_ADF0 = 'adf0'
FTYPE_ADF5 = 'adf5'

FTYPE_SYMLINK = 'symlink'

FTYPE_EXE = 'exe'

FTYPE_NO_TYPE = 'META-NO-TYPE'  # used in file type matching to indicate that file should have no type
FTYPE_ANY_TYPE = 'META-ANY-TYPE'  # used in file type matching to indicate that file can have any type

ftype_list = {
    FTYPE_NO_TYPE: 1 << 0,
    FTYPE_SYMLINK: 1 << 1,
    FTYPE_ARC: 1 << 2,
    FTYPE_TAB: 1 << 3,
    FTYPE_AAF: 1 << 4,
    FTYPE_SARC: 1 << 5,
    FTYPE_BMP: 1 << 6,
    FTYPE_DDS: 1 << 7,
    FTYPE_AVTX: 1 << 8,
    FTYPE_ATX: 1 << 9,
    FTYPE_HMDDSC: 1 << 10,
    FTYPE_ADF: 1 << 11,
    FTYPE_ADF_BARE: 1 << 12,
    FTYPE_TXT: 1 << 13,
    FTYPE_OBC: 1 << 14,
    FTYPE_RIFF: 1 << 15,
    FTYPE_RTPC: 1 << 16,
    FTYPE_TAG0: 1 << 17,
    FTYPE_H2014: 1 << 18,
    FTYPE_MDI: 1 << 19,
    FTYPE_PFX: 1 << 20,
    FTYPE_FSB5C: 1 << 21,
    FTYPE_RBMDL: 1 << 22,
    FTYPE_GDCBODY: 1 << 23,
    FTYPE_GFX: 1 << 24,
    FTYPE_OGG: 1 << 25,
    FTYPE_BINK_KB2: 1 << 26,
    FTYPE_BINK_BIK: 1 << 27,
    FTYPE_GT0C: 1 << 28,
    FTYPE_GARC: 1 << 29,
    FTYPE_ADF0: 1 << 30,
    FTYPE_ADF5: 1 << 31,
    FTYPE_EXE: 1 << 63,
    FTYPE_ANY_TYPE: 0xFFffFFffFFffFFff,
}

ftype_adf_family = {FTYPE_ADF0, FTYPE_ADF, FTYPE_ADF_BARE, FTYPE_ADF5}
