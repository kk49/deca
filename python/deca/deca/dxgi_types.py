import struct


'''
https://docs.microsoft.com/en-us/windows/win32/direct3ddds/dds-header
https://docs.microsoft.com/en-us/windows/win32/direct3ddds/dds-pixelformat
https://docs.microsoft.com/en-us/windows/win32/direct3ddds/dds-header-dxt10
https://docs.microsoft.com/en-us/windows/win32/direct3ddds/dx-graphics-dds-pguide
https://docs.microsoft.com/en-us/windows/win32/api/dxgiformat/ne-dxgiformat-dxgi_format
https://docs.microsoft.com/en-us/windows/win32/direct3d10/d3d10-graphics-programming-guide-resources-data-conversion
https://docs.microsoft.com/en-us/windows/win32/direct3d11/texture-block-compression-in-direct3d-11
https://docs.microsoft.com/en-us/windows/win32/direct3d11/bc6h-format
https://docs.microsoft.com/en-us/windows/win32/direct3d11/bc7-format
https://docs.microsoft.com/en-us/windows/win32/direct3d11/bc7-format-mode-reference
https://docs.microsoft.com/en-us/windows/win32/direct3ddxgi/format-support-for-direct3d-11-1-feature-level-hardware
'''


DXGI_FORMAT_UNKNOWN	                    = 0
DXGI_FORMAT_R32G32B32A32_TYPELESS       = 1
DXGI_FORMAT_R32G32B32A32_FLOAT          = 2
DXGI_FORMAT_R32G32B32A32_UINT           = 3
DXGI_FORMAT_R32G32B32A32_SINT           = 4
DXGI_FORMAT_R32G32B32_TYPELESS          = 5
DXGI_FORMAT_R32G32B32_FLOAT             = 6
DXGI_FORMAT_R32G32B32_UINT              = 7
DXGI_FORMAT_R32G32B32_SINT              = 8
DXGI_FORMAT_R16G16B16A16_TYPELESS       = 9
DXGI_FORMAT_R16G16B16A16_FLOAT          = 10
DXGI_FORMAT_R16G16B16A16_UNORM          = 11
DXGI_FORMAT_R16G16B16A16_UINT           = 12
DXGI_FORMAT_R16G16B16A16_SNORM          = 13
DXGI_FORMAT_R16G16B16A16_SINT           = 14
DXGI_FORMAT_R32G32_TYPELESS             = 15
DXGI_FORMAT_R32G32_FLOAT                = 16
DXGI_FORMAT_R32G32_UINT                 = 17
DXGI_FORMAT_R32G32_SINT                 = 18
DXGI_FORMAT_R32G8X24_TYPELESS           = 19
DXGI_FORMAT_D32_FLOAT_S8X24_UINT        = 20
DXGI_FORMAT_R32_FLOAT_X8X24_TYPELESS    = 21
DXGI_FORMAT_X32_TYPELESS_G8X24_UINT     = 22
DXGI_FORMAT_R10G10B10A2_TYPELESS        = 23
DXGI_FORMAT_R10G10B10A2_UNORM           = 24
DXGI_FORMAT_R10G10B10A2_UINT            = 25
DXGI_FORMAT_R11G11B10_FLOAT             = 26
DXGI_FORMAT_R8G8B8A8_TYPELESS           = 27
DXGI_FORMAT_R8G8B8A8_UNORM              = 28
DXGI_FORMAT_R8G8B8A8_UNORM_SRGB         = 29
DXGI_FORMAT_R8G8B8A8_UINT               = 30
DXGI_FORMAT_R8G8B8A8_SNORM              = 31
DXGI_FORMAT_R8G8B8A8_SINT               = 32
DXGI_FORMAT_R16G16_TYPELESS             = 33
DXGI_FORMAT_R16G16_FLOAT                = 34
DXGI_FORMAT_R16G16_UNORM                = 35
DXGI_FORMAT_R16G16_UINT                 = 36
DXGI_FORMAT_R16G16_SNORM                = 37
DXGI_FORMAT_R16G16_SINT                 = 38
DXGI_FORMAT_R32_TYPELESS                = 39
DXGI_FORMAT_D32_FLOAT                   = 40
DXGI_FORMAT_R32_FLOAT                   = 41
DXGI_FORMAT_R32_UINT                    = 42
DXGI_FORMAT_R32_SINT                    = 43
DXGI_FORMAT_R24G8_TYPELESS              = 44
DXGI_FORMAT_D24_UNORM_S8_UINT           = 45
DXGI_FORMAT_R24_UNORM_X8_TYPELESS       = 46
DXGI_FORMAT_X24_TYPELESS_G8_UINT        = 47
DXGI_FORMAT_R8G8_TYPELESS               = 48
DXGI_FORMAT_R8G8_UNORM                  = 49
DXGI_FORMAT_R8G8_UINT                   = 50
DXGI_FORMAT_R8G8_SNORM                  = 51
DXGI_FORMAT_R8G8_SINT                   = 52
DXGI_FORMAT_R16_TYPELESS                = 53
DXGI_FORMAT_R16_FLOAT                   = 54
DXGI_FORMAT_D16_UNORM                   = 55
DXGI_FORMAT_R16_UNORM                   = 56
DXGI_FORMAT_R16_UINT                    = 57
DXGI_FORMAT_R16_SNORM                   = 58
DXGI_FORMAT_R16_SINT                    = 59
DXGI_FORMAT_R8_TYPELESS                 = 60
DXGI_FORMAT_R8_UNORM                    = 61
DXGI_FORMAT_R8_UINT                     = 62
DXGI_FORMAT_R8_SNORM                    = 63
DXGI_FORMAT_R8_SINT                     = 64
DXGI_FORMAT_A8_UNORM                    = 65
DXGI_FORMAT_R1_UNORM                    = 66
DXGI_FORMAT_R9G9B9E5_SHAREDEXP          = 67
DXGI_FORMAT_R8G8_B8G8_UNORM             = 68
DXGI_FORMAT_G8R8_G8B8_UNORM             = 69
DXGI_FORMAT_BC1_TYPELESS                = 70
DXGI_FORMAT_BC1_UNORM                   = 71
DXGI_FORMAT_BC1_UNORM_SRGB              = 72
DXGI_FORMAT_BC2_TYPELESS                = 73
DXGI_FORMAT_BC2_UNORM                   = 74
DXGI_FORMAT_BC2_UNORM_SRGB              = 75
DXGI_FORMAT_BC3_TYPELESS                = 76
DXGI_FORMAT_BC3_UNORM                   = 77
DXGI_FORMAT_BC3_UNORM_SRGB              = 78
DXGI_FORMAT_BC4_TYPELESS                = 79
DXGI_FORMAT_BC4_UNORM                   = 80
DXGI_FORMAT_BC4_SNORM                   = 81
DXGI_FORMAT_BC5_TYPELESS                = 82
DXGI_FORMAT_BC5_UNORM                   = 83
DXGI_FORMAT_BC5_SNORM                   = 84
DXGI_FORMAT_B5G6R5_UNORM                = 85
DXGI_FORMAT_B5G5R5A1_UNORM              = 86
DXGI_FORMAT_B8G8R8A8_UNORM              = 87
DXGI_FORMAT_B8G8R8X8_UNORM              = 88
DXGI_FORMAT_R10G10B10_XR_BIAS_A2_UNORM  = 89
DXGI_FORMAT_B8G8R8A8_TYPELESS           = 90
DXGI_FORMAT_B8G8R8A8_UNORM_SRGB         = 91
DXGI_FORMAT_B8G8R8X8_TYPELESS           = 92
DXGI_FORMAT_B8G8R8X8_UNORM_SRGB         = 93
DXGI_FORMAT_BC6H_TYPELESS               = 94
DXGI_FORMAT_BC6H_UF16                   = 95
DXGI_FORMAT_BC6H_SF16                   = 96
DXGI_FORMAT_BC7_TYPELESS                = 97
DXGI_FORMAT_BC7_UNORM                   = 98
DXGI_FORMAT_BC7_UNORM_SRGB              = 99
DXGI_FORMAT_AYUV                        = 100
DXGI_FORMAT_Y410                        = 101
DXGI_FORMAT_Y416                        = 102
DXGI_FORMAT_NV12                        = 103
DXGI_FORMAT_P010                        = 104
DXGI_FORMAT_P016                        = 105
DXGI_FORMAT_420_OPAQUE                  = 106
DXGI_FORMAT_YUY2                        = 107
DXGI_FORMAT_Y210                        = 108
DXGI_FORMAT_Y216                        = 109
DXGI_FORMAT_NV11                        = 110
DXGI_FORMAT_AI44                        = 111
DXGI_FORMAT_IA44                        = 112
DXGI_FORMAT_P8                          = 113
DXGI_FORMAT_A8P8                        = 114
DXGI_FORMAT_B4G4R4A4_UNORM              = 115

DXGI_FORMAT_P208                        = 130
DXGI_FORMAT_V208                        = 131
DXGI_FORMAT_V408                        = 132

DXGI_FORMAT_FORCE_UINT                  = 0xffffffff


'''
Reference:
https://docs.microsoft.com/en-us/windows/win32/direct3ddds/dds-header
'''


'''
DDSD_CAPS;          Required in every .dds file.	0x1
DDSD_HEIGHT;        Required in every .dds file.	0x2
DDSD_WIDTH;         Required in every .dds file.	0x4
DDSD_PITCH;         Required when pitch is provided for an uncompressed texture.	0x8
DDSD_PIXELFORMAT;   Required in every .dds file.	0x1000
DDSD_MIPMAPCOUNT;   Required in a mipmapped texture.	0x20000
DDSD_LINEARSIZE;    Required when pitch is provided for a compressed texture.	0x80000
DDSD_DEPTH;         Required in a depth texture.	0x800000
'''
dwFlagsTest = [
    [0x1, 'DDSD_CAPS'],
    [0x2, 'DDSD_HEIGHT'],
    [0x4, 'DDSD_WIDTH'],
    [0x8, 'DDSD_PITCH'],
    [0x1000, 'DDSD_PIXELFORMAT'],
    [0x20000, 'DDSD_MIPMAPCOUNT'],
    [0x80000, 'DDSD_LINEARSIZE'],
    [0x800000, 'DDSD_DEPTH'],
]
DDSD_CAPS = 0x1
DDSD_HEIGHT = 0x2
DDSD_WIDTH = 0x4
DDSD_PITCH = 0x8
DDSD_PIXELFORMAT = 0x1000
DDSD_MIPMAPCOUNT = 0x20000
DDSD_LINEARSIZE = 0x80000
DDSD_DEPTH = 0x800000


'''
DDSCAPS_COMPLEX	Optional; 0x8
    must be used on any file that contains more than one surface (a mipmap, a cubic environment map, or 
    mipmapped volume texture).
DDSCAPS_MIPMAP	Optional; 0x400000
    should be used for a mipmap.	
DDSCAPS_TEXTURE	Required; 0x1000
'''
dwCapsTest = [
    [0x8, 'DDSCAPS_COMPLEX'],
    [0x400000, 'DDSCAPS_MIPMAP'],
    [0x1000, 'DDSCAPS_TEXTURE'],
]
DDSCAPS_COMPLEX = 0x8
DDSCAPS_MIPMAP = 0x400000
DDSCAPS_TEXTURE = 0x1000


'''
DDSCAPS2_CUBEMAP	Required for a cube map.	0x200
DDSCAPS2_CUBEMAP_POSITIVEX	Required when these surfaces are stored in a cube map.	0x400
DDSCAPS2_CUBEMAP_NEGATIVEX	Required when these surfaces are stored in a cube map.	0x800
DDSCAPS2_CUBEMAP_POSITIVEY	Required when these surfaces are stored in a cube map.	0x1000
DDSCAPS2_CUBEMAP_NEGATIVEY	Required when these surfaces are stored in a cube map.	0x2000
DDSCAPS2_CUBEMAP_POSITIVEZ	Required when these surfaces are stored in a cube map.	0x4000
DDSCAPS2_CUBEMAP_NEGATIVEZ	Required when these surfaces are stored in a cube map.	0x8000
DDSCAPS2_VOLUME	Required for a volume texture.	0x200000
'''
dwCaps2Test = [
    [0x200, 'DDSCAPS2_CUBEMAP'],
    [0x400, 'DDSCAPS2_CUBEMAP_POSITIVEX'],
    [0x800, 'DDSCAPS2_CUBEMAP_NEGATIVEX'],
    [0x1000, 'DDSCAPS2_CUBEMAP_POSITIVEY'],
    [0x2000, 'DDSCAPS2_CUBEMAP_NEGATIVEY'],
    [0x4000, 'DDSCAPS2_CUBEMAP_POSITIVEZ'],
    [0x8000, 'DDSCAPS2_CUBEMAP_NEGATIVEZ'],
    [0x200000, 'DDSCAPS2_VOLUME'],
]
DDSCAPS2_CUBEMAP = 0x200
DDSCAPS2_CUBEMAP_POSITIVEX = 0x400
DDSCAPS2_CUBEMAP_NEGATIVEX = 0x800
DDSCAPS2_CUBEMAP_POSITIVEY = 0x1000
DDSCAPS2_CUBEMAP_NEGATIVEY = 0x2000
DDSCAPS2_CUBEMAP_POSITIVEZ = 0x4000
DDSCAPS2_CUBEMAP_NEGATIVEZ = 0x8000
DDSCAPS2_VOLUME = 0x200000

DDS_CUBEMAP_POSITIVEX = DDSCAPS2_CUBEMAP | DDSCAPS2_CUBEMAP_POSITIVEX
DDS_CUBEMAP_NEGATIVEX = DDSCAPS2_CUBEMAP | DDSCAPS2_CUBEMAP_NEGATIVEX
DDS_CUBEMAP_POSITIVEY = DDSCAPS2_CUBEMAP | DDSCAPS2_CUBEMAP_POSITIVEY
DDS_CUBEMAP_NEGATIVEY = DDSCAPS2_CUBEMAP | DDSCAPS2_CUBEMAP_NEGATIVEY
DDS_CUBEMAP_POSITIVEZ = DDSCAPS2_CUBEMAP | DDSCAPS2_CUBEMAP_POSITIVEZ
DDS_CUBEMAP_NEGATIVEZ = DDSCAPS2_CUBEMAP | DDSCAPS2_CUBEMAP_NEGATIVEZ

DDS_CUBEMAP_ALLFACES = \
    DDS_CUBEMAP_POSITIVEX | DDS_CUBEMAP_NEGATIVEX | \
    DDS_CUBEMAP_POSITIVEY | DDS_CUBEMAP_NEGATIVEY | \
    DDS_CUBEMAP_POSITIVEZ | DDS_CUBEMAP_NEGATIVEZ


'''
DDPF_ALPHAPIXELS	Texture contains alpha data; dwRGBAlphaBitMask contains valid data.	0x1
DDPF_ALPHA	Used in some older DDS files for alpha channel only uncompressed data (dwRGBBitCount contains 
    the alpha channel bitcount; dwABitMask contains valid data)	0x2
DDPF_FOURCC	Texture contains compressed RGB data; dwFourCC contains valid data.	0x4
DDPF_RGB	Texture contains uncompressed RGB data; dwRGBBitCount and the RGB masks 
    (dwRBitMask, dwGBitMask, dwBBitMask) contain valid data.	0x40
DDPF_YUV	Used in some older DDS files for YUV uncompressed data (dwRGBBitCount contains the YUV bit count; 
    dwRBitMask contains the Y mask, dwGBitMask contains the U mask, dwBBitMask contains the V mask)	0x200
DDPF_LUMINANCE	Used in some older DDS files for single channel color uncompressed data (dwRGBBitCount 
    contains the luminance channel bit count; dwRBitMask contains the channel mask). Can be combined with 
    DDPF_ALPHAPIXELS for a two channel DDS file.	0x20000
'''
dwPFFlagsTest = [
    [0x1, 'DDPF_ALPHAPIXELS'],
    [0x2, 'DDPF_ALPHA'],
    [0x4, 'DDPF_FOURCC'],
    [0x40, 'DDPF_RGB'],
    [0x200, 'DDPF_YUV'],
    [0x20000, 'DDPF_LUMINANCE'],
]
DDPF_ALPHAPIXELS = 0x1
DDPF_ALPHA = 0x2
DDPF_FOURCC = 0x4
DDPF_RGB = 0x40
DDPF_YUV = 0x200
DDPF_LUMINANCE = 0x20000


# todo add d3d format support eventually?
dw_four_cc_convert = {
    b'DXT1': DXGI_FORMAT_BC1_UNORM,
    b'DXT2': DXGI_FORMAT_BC2_UNORM,
    b'DXT3': DXGI_FORMAT_BC2_UNORM,
    b'DXT4': DXGI_FORMAT_BC3_UNORM,
    b'DXT5': DXGI_FORMAT_BC3_UNORM,
    b'BC4U': DXGI_FORMAT_BC4_UNORM,
    b'BC4S': DXGI_FORMAT_BC4_SNORM,
    b'ATI1': DXGI_FORMAT_BC4_UNORM,
    b'ATI2': DXGI_FORMAT_BC5_UNORM,
    b'BC5U': DXGI_FORMAT_BC5_UNORM,
    b'BC5S': DXGI_FORMAT_BC5_SNORM,
    b'RGBG': DXGI_FORMAT_R8G8_B8G8_UNORM,
    b'GRGB': DXGI_FORMAT_G8R8_G8B8_UNORM,
    36: DXGI_FORMAT_R16G16B16A16_UNORM,
    110: DXGI_FORMAT_R16G16B16A16_SNORM,
    111: DXGI_FORMAT_R16_FLOAT,
    112: DXGI_FORMAT_R16G16_FLOAT,
    113: DXGI_FORMAT_R16G16B16A16_FLOAT,
    114: DXGI_FORMAT_R32_FLOAT,
    115: DXGI_FORMAT_R32G32_FLOAT,
    116: DXGI_FORMAT_R32G32B32A32_FLOAT,

    # b'DXT2': D3DFMT_DXT2,
    # b'DXT4': D3DFMT_DXT4,
    # b'UYVY': D3DFMT_UYVY,
    # b'YUY2': D3DFMT_YUY2,
    # 117: D3DFMT_CxV8U8,

    b'DX10': None
}

dw_four_cc_downgrade = {
    DXGI_FORMAT_BC1_UNORM: b'DXT1',
    DXGI_FORMAT_BC2_UNORM: b'DXT3',
    DXGI_FORMAT_BC3_UNORM: b'DXT5',
}

'''
DXGI_FORMAT_BC1_UNORM D3DFMT_DXT1 DDS_FOURCC	"DXT1"
DXGI_FORMAT_BC2_UNORM D3DFMT_DXT3 DDS_FOURCC	"DXT3"
DXGI_FORMAT_BC3_UNORM D3DFMT_DXT5 DDS_FOURCC	"DXT5"
* DXGI_FORMAT_BC4_UNORM DDS_FOURCC	"BC4U"
* DXGI_FORMAT_BC4_SNORM DDS_FOURCC	"BC4S" 
* DXGI_FORMAT_BC5_UNORM DDS_FOURCC	"ATI2"
* DXGI_FORMAT_BC5_SNORM DDS_FOURCC	"BC5S"
DXGI_FORMAT_R8G8_B8G8_UNORM D3DFMT_R8G8_B8G8 DDS_FOURCC	"RGBG"
DXGI_FORMAT_G8R8_G8B8_UNORM D3DFMT_G8R8_G8B8 DDS_FOURCC	"GRGB"
* DXGI_FORMAT_R16G16B16A16_UNORM D3DFMT_A16B16G16R16 DDS_FOURCC	36
* DXGI_FORMAT_R16G16B16A16_SNORM D3DFMT_Q16W16V16U16 DDS_FOURCC	110
* DXGI_FORMAT_R16_FLOAT D3DFMT_R16F DDS_FOURCC	111
* DXGI_FORMAT_R16G16_FLOAT D3DFMT_G16R16F DDS_FOURCC	112
* DXGI_FORMAT_R16G16B16A16_FLOAT D3DFMT_A16B16G16R16F DDS_FOURCC	113
* DXGI_FORMAT_R32_FLOAT D3DFMT_R32F DDS_FOURCC	114
* DXGI_FORMAT_R32G32_FLOAT D3DFMT_G32R32F DDS_FOURCC	115
* DXGI_FORMAT_R32G32B32A32_FLOAT D3DFMT_A32B32G32R32F DDS_FOURCC	116

D3DFMT_DXT2 DDS_FOURCC	"DXT2" 
D3DFMT_DXT4 DDS_FOURCC	"DXT4"
D3DFMT_UYVY DDS_FOURCC	"UYVY"
D3DFMT_YUY2 DDS_FOURCC	"YUY2"
D3DFMT_CxV8U8 DDS_FOURCC	117
Any DXGI format	DDS_FOURCC	"DX10"
'''

'''
typedef struct {
  DWORD           dwSize;
  DWORD           dwFlags;
  DWORD           dwHeight;
  DWORD           dwWidth;
  DWORD           dwPitchOrLinearSize;
  DWORD           dwDepth;
  DWORD           dwMipMapCount;
  DWORD           dwReserved1[11];
  DDS_PIXELFORMAT ddspf;
  DWORD           dwCaps;
  DWORD           dwCaps2;
  DWORD           dwCaps3;
  DWORD           dwCaps4;
  DWORD           dwReserved2;
} DDS_HEADER;

struct DDS_PIXELFORMAT {
  DWORD dwSize;
  DWORD dwFlags;
  DWORD dwFourCC;
  DWORD dwRGBBitCount;
  DWORD dwRBitMask;
  DWORD dwGBitMask;
  DWORD dwBBitMask;
  DWORD dwABitMask;
};

typedef struct {
  DXGI_FORMAT              dxgiFormat;
  D3D10_RESOURCE_DIMENSION resourceDimension;
  UINT                     miscFlag;
  UINT                     arraySize;
  UINT                     miscFlags2;
} DDS_HEADER_DXT10;

'''


class DdsHeaderDxt10:
    __slots__ = [
        'dxgiFormat',  # DWORD / DXGI_FORMAT
        'resourceDimension',  # DWORD / D3D10_RESOURCE_DIMENSION
        'miscFlag',  # DWORD / UINT
        'arraySize',  # DWORD / UINT
        'miscFlags2',  # DWORD / UINT
    ]

    def __init__(self):
        self.dxgiFormat = None
        self.resourceDimension = 0
        self.miscFlag = 0
        self.arraySize = 1
        self.miscFlags2 = 0

    def __repr__(self):
        r = '\n'
        r += f'dxgiFormat: {self.dxgiFormat}\n'
        r += f'resourceDimension: {self.resourceDimension}\n'
        r += f'miscFlag: {self.miscFlag}\n'
        r += f'arraySize: {self.arraySize}\n'
        r += f'miscFlags2: {self.miscFlags2}\n'
        return r


class DdsPixelFormat:
    __slots__ = [
        'dwSize',  # DWORD
        'dwFlags',  # DWORD
        'dwFourCC',  # DWORD
        'dwRGBBitCount',  # DWORD
        'dwRBitMask',  # DWORD
        'dwGBitMask',  # DWORD
        'dwBBitMask',  # DWORD
        'dwABitMask',  # DWORD
    ]

    def __init__(self):
        self.dwSize = None
        self.dwFlags = 0
        self.dwFourCC = 0
        self.dwRGBBitCount = 0
        self.dwRBitMask = 0
        self.dwGBitMask = 0
        self.dwBBitMask = 0
        self.dwABitMask = 0

    def __repr__(self):
        if self.dwFourCC is None:
            four_cc = None
        else:
            four_cc = struct.unpack('I', self.dwFourCC)[0]
        dxgi_format = dw_four_cc_convert.get(self.dwFourCC, dw_four_cc_convert.get(four_cc, None))

        r = '\n'
        r += f'dwSize: {self.dwSize}\n'
        r += f'dwFlags: {self.dwFlags}\n'
        r += f'dwFourCC: {self.dwFourCC} ({four_cc}) dxgi:{dxgi_format}\n'
        r += f'dwRGBBitCount: {self.dwRGBBitCount}\n'
        r += f'dwRBitMask: {self.dwRBitMask}\n'
        r += f'dwGBitMask: {self.dwGBitMask}\n'
        r += f'dwBBitMask: {self.dwBBitMask}\n'
        r += f'dwABitMask: {self.dwABitMask}\n'
        return r


class DdsHeader:
    __slots__ = [
        'dwSize',  # DWORD
        'dwFlags',  # DWORD
        'dwHeight',  # DWORD
        'dwWidth',  # DWORD
        'dwPitchOrLinearSize',  # DWORD
        'dwDepth',  # DWORD
        'dwMipMapCount',  # DWORD
        'dwReserved1',  # DWORD * 11
        'ddspf',  # DDS_PIXELFORMAT
        'dwCaps',  # DWORD
        'dwCaps2',  # DWORD
        'dwCaps3',  # DWORD
        'dwCaps4',  # DWORD
        'dwReserved2',  # DWORD
    ]

    def __init__(self):
        self.dwSize = None
        self.dwFlags = 0
        self.dwHeight = 0
        self.dwWidth = 0
        self.dwPitchOrLinearSize = 0
        self.dwDepth = 0
        self.dwMipMapCount = 0
        self.dwReserved1 = None
        self.ddspf = DdsPixelFormat()
        self.dwCaps = 0
        self.dwCaps2 = 0
        self.dwCaps3 = 0
        self.dwCaps4 = 0
        self.dwReserved2 = None

    def __repr__(self):
        r = '\n'
        r += f'dwSize: {self.dwSize}\n'
        r += f'dwFlags: {self.dwFlags}\n'
        r += f'dwHeight: {self.dwHeight}\n'
        r += f'dwWidth: {self.dwWidth}\n'
        r += f'dwPitchOrLinearSize: {self.dwPitchOrLinearSize}\n'
        r += f'dwDepth: {self.dwDepth}\n'
        r += f'dwMipMapCount: {self.dwMipMapCount}\n'
        r += f'dwReserved1: {self.dwReserved1}\n'
        r += f'ddspf: {self.ddspf}\n'
        r += f'dwCaps: {self.dwCaps}\n'
        r += f'dwCaps2: {self.dwCaps2}\n'
        r += f'dwCaps3: {self.dwCaps3}\n'
        r += f'dwCaps4: {self.dwCaps4}\n'
        r += f'dwReserved2: {self.dwReserved2}\n'
        return r


dxgi_format_db = {
    2: [True, 16],      # DXGI_FORMAT_R32G32B32A32_FLOAT
    10: [True, 8],      # DXGI_FORMAT_R16G16B16A16_FLOAT
    26: [True, 4],      # DXGI_FORMAT_R11G11B10_FLOAT
    28: [True, 4],      # DXGI_FORMAT_R8G8B8A8_UNORM
    41: [True, 4],      # DXGI_FORMAT_R32_FLOAT
    53: [True, 2],      # DXGI_FORMAT_R16_TYPELESS u16
    54: [True, 2],      # DXGI_FORMAT_R16_TYPELESS f16
    58: [True, 2],      # DXGI_FORMAT_R16_SNORM s16
    60: [True, 1],      # DXGI_FORMAT_R8_TYPELESS u8
    63: [True, 1],      # DXGI_FORMAT_R8_TYPELESS s8
    87: [True, 4],      # DXGI_FORMAT_B8G8R8A8_UNORM
    70: [False, 8],     # DXGI_FORMAT_BC1_TYPELESS
    73: [False, 16],    # DXGI_FORMAT_BC2_TYPELESS
    76: [False, 16],    # DXGI_FORMAT_BC3_TYPELESS
    79: [False, 8],     # DXGI_FORMAT_BC4_TYPELESS
    82: [False, 16],    # DXGI_FORMAT_BC5_TYPELESS
    94: [False, 16],    # DXGI_FORMAT_BC6H_TYPELESS
    97: [False, 16],    # DXGI_FORMAT_BC7_TYPELESS
}

dxgi_base_format_db = {
    2: 2,       # DXGI_FORMAT_R32G32B32A32_FLOAT
    10: 10,     # DXGI_FORMAT_R16G16B16A16_FLOAT
    26: 26,     # DXGI_FORMAT_R11G11B10_FLOAT
    28: 28,     # DXGI_FORMAT_R8G8B8A8_UNORM
    41: 41,     # DXGI_FORMAT_R32_FLOAT

    # DXGI_FORMAT_R16_* u16
    53: 53, 55: 53, 56: 53, 57: 53,

    # DXGI_FORMAT_R16_* f16
    54: 54,

    # DXGI_FORMAT_R16_* s16
    58: 58, 59: 58,

    # DXGI_FORMAT_R8_* u8
    60: 60, 61: 60, 62: 60,

    # DXGI_FORMAT_R8_* s8
    63: 63, 64: 63,

    # DXGI_FORMAT_B8G8R8A8_UNORM
    87: 87,
    # DXGI_FORMAT_BC1_*
    70: 70, 71: 70, 72: 70,
    # DXGI_FORMAT_BC2_*
    73: 73, 74: 73, 75: 73,
    # DXGI_FORMAT_BC3_*
    76: 76, 77: 76, 78: 76,
    # DXGI_FORMAT_BC4_*
    79: 79, 80: 79, 81: 79,
    # DXGI_FORMAT_BC5_*
    82: 82, 83: 82, 84: 82,
    # DXGI_FORMAT_BC6H_
    94: 94, 95: 94, 96: 94,
    # DXGI_FORMAT_BC7_*
    97: 97, 98: 97, 99: 97,
}

dxgi_name_db = {
    DXGI_FORMAT_UNKNOWN: 'UNKNOWN',
    DXGI_FORMAT_R32G32B32A32_TYPELESS: 'R32G32B32A32_TYPELESS',
    DXGI_FORMAT_R32G32B32A32_FLOAT: 'R32G32B32A32_FLOAT',
    DXGI_FORMAT_R32G32B32A32_UINT: 'R32G32B32A32_UINT',
    DXGI_FORMAT_R32G32B32A32_SINT: 'R32G32B32A32_SINT',
    DXGI_FORMAT_R32G32B32_TYPELESS: 'R32G32B32_TYPELESS',
    DXGI_FORMAT_R32G32B32_FLOAT: 'R32G32B32_FLOAT',
    DXGI_FORMAT_R32G32B32_UINT: 'R32G32B32_UINT',
    DXGI_FORMAT_R32G32B32_SINT: 'R32G32B32_SINT',
    DXGI_FORMAT_R16G16B16A16_TYPELESS: 'R16G16B16A16_TYPELESS',
    DXGI_FORMAT_R16G16B16A16_FLOAT: 'R16G16B16A16_FLOAT',
    DXGI_FORMAT_R16G16B16A16_UNORM: 'R16G16B16A16_UNORM',
    DXGI_FORMAT_R16G16B16A16_UINT: 'R16G16B16A16_UINT',
    DXGI_FORMAT_R16G16B16A16_SNORM: 'R16G16B16A16_SNORM',
    DXGI_FORMAT_R16G16B16A16_SINT: 'R16G16B16A16_SINT',
    DXGI_FORMAT_R32G32_TYPELESS: 'R32G32_TYPELESS',
    DXGI_FORMAT_R32G32_FLOAT: 'R32G32_FLOAT',
    DXGI_FORMAT_R32G32_UINT: 'R32G32_UINT',
    DXGI_FORMAT_R32G32_SINT: 'R32G32_SINT',
    DXGI_FORMAT_R32G8X24_TYPELESS: 'R32G8X24_TYPELESS',
    DXGI_FORMAT_D32_FLOAT_S8X24_UINT: 'D32_FLOAT_S8X24_UINT',
    DXGI_FORMAT_R32_FLOAT_X8X24_TYPELESS: 'R32_FLOAT_X8X24_TYPELESS',
    DXGI_FORMAT_X32_TYPELESS_G8X24_UINT: 'X32_TYPELESS_G8X24_UINT',
    DXGI_FORMAT_R10G10B10A2_TYPELESS: 'R10G10B10A2_TYPELESS',
    DXGI_FORMAT_R10G10B10A2_UNORM: 'R10G10B10A2_UNORM',
    DXGI_FORMAT_R10G10B10A2_UINT: 'R10G10B10A2_UINT',
    DXGI_FORMAT_R11G11B10_FLOAT: 'R11G11B10_FLOAT',
    DXGI_FORMAT_R8G8B8A8_TYPELESS: 'R8G8B8A8_TYPELESS',
    DXGI_FORMAT_R8G8B8A8_UNORM: 'R8G8B8A8_UNORM',
    DXGI_FORMAT_R8G8B8A8_UNORM_SRGB: 'R8G8B8A8_UNORM_SRGB',
    DXGI_FORMAT_R8G8B8A8_UINT: 'R8G8B8A8_UINT',
    DXGI_FORMAT_R8G8B8A8_SNORM: 'R8G8B8A8_SNORM',
    DXGI_FORMAT_R8G8B8A8_SINT: 'R8G8B8A8_SINT',
    DXGI_FORMAT_R16G16_TYPELESS: 'R16G16_TYPELESS',
    DXGI_FORMAT_R16G16_FLOAT: 'R16G16_FLOAT',
    DXGI_FORMAT_R16G16_UNORM: 'R16G16_UNORM',
    DXGI_FORMAT_R16G16_UINT: 'R16G16_UINT',
    DXGI_FORMAT_R16G16_SNORM: 'R16G16_SNORM',
    DXGI_FORMAT_R16G16_SINT: 'R16G16_SINT',
    DXGI_FORMAT_R32_TYPELESS: 'R32_TYPELESS',
    DXGI_FORMAT_D32_FLOAT: 'D32_FLOAT',
    DXGI_FORMAT_R32_FLOAT: 'R32_FLOAT',
    DXGI_FORMAT_R32_UINT: 'R32_UINT',
    DXGI_FORMAT_R32_SINT: 'R32_SINT',
    DXGI_FORMAT_R24G8_TYPELESS: 'R24G8_TYPELESS',
    DXGI_FORMAT_D24_UNORM_S8_UINT: 'D24_UNORM_S8_UINT',
    DXGI_FORMAT_R24_UNORM_X8_TYPELESS: 'R24_UNORM_X8_TYPELESS',
    DXGI_FORMAT_X24_TYPELESS_G8_UINT: 'X24_TYPELESS_G8_UINT',
    DXGI_FORMAT_R8G8_TYPELESS: 'R8G8_TYPELESS',
    DXGI_FORMAT_R8G8_UNORM: 'R8G8_UNORM',
    DXGI_FORMAT_R8G8_UINT: 'R8G8_UINT',
    DXGI_FORMAT_R8G8_SNORM: 'R8G8_SNORM',
    DXGI_FORMAT_R8G8_SINT: 'R8G8_SINT',
    DXGI_FORMAT_R16_TYPELESS: 'R16_TYPELESS',
    DXGI_FORMAT_R16_FLOAT: 'R16_FLOAT',
    DXGI_FORMAT_D16_UNORM: 'D16_UNORM',
    DXGI_FORMAT_R16_UNORM: 'R16_UNORM',
    DXGI_FORMAT_R16_UINT: 'R16_UINT',
    DXGI_FORMAT_R16_SNORM: 'R16_SNORM',
    DXGI_FORMAT_R16_SINT: 'R16_SINT',
    DXGI_FORMAT_R8_TYPELESS: 'R8_TYPELESS',
    DXGI_FORMAT_R8_UNORM: 'R8_UNORM',
    DXGI_FORMAT_R8_UINT: 'R8_UINT',
    DXGI_FORMAT_R8_SNORM: 'R8_SNORM',
    DXGI_FORMAT_R8_SINT: 'R8_SINT',
    DXGI_FORMAT_A8_UNORM: 'A8_UNORM',
    DXGI_FORMAT_R1_UNORM: 'R1_UNORM',
    DXGI_FORMAT_R9G9B9E5_SHAREDEXP: 'R9G9B9E5_SHAREDEXP',
    DXGI_FORMAT_R8G8_B8G8_UNORM: 'R8G8_B8G8_UNORM',
    DXGI_FORMAT_G8R8_G8B8_UNORM: 'G8R8_G8B8_UNORM',
    DXGI_FORMAT_BC1_TYPELESS: 'BC1_TYPELESS',
    DXGI_FORMAT_BC1_UNORM: 'BC1_UNORM',
    DXGI_FORMAT_BC1_UNORM_SRGB: 'BC1_UNORM_SRGB',
    DXGI_FORMAT_BC2_TYPELESS: 'BC2_TYPELESS',
    DXGI_FORMAT_BC2_UNORM: 'BC2_UNORM',
    DXGI_FORMAT_BC2_UNORM_SRGB: 'BC2_UNORM_SRGB',
    DXGI_FORMAT_BC3_TYPELESS: 'BC3_TYPELESS',
    DXGI_FORMAT_BC3_UNORM: 'BC3_UNORM',
    DXGI_FORMAT_BC3_UNORM_SRGB: 'BC3_UNORM_SRGB',
    DXGI_FORMAT_BC4_TYPELESS: 'BC4_TYPELESS',
    DXGI_FORMAT_BC4_UNORM: 'BC4_UNORM',
    DXGI_FORMAT_BC4_SNORM: 'BC4_SNORM',
    DXGI_FORMAT_BC5_TYPELESS: 'BC5_TYPELESS',
    DXGI_FORMAT_BC5_UNORM: 'BC5_UNORM',
    DXGI_FORMAT_BC5_SNORM: 'BC5_SNORM',
    DXGI_FORMAT_B5G6R5_UNORM: 'B5G6R5_UNORM',
    DXGI_FORMAT_B5G5R5A1_UNORM: 'B5G5R5A1_UNORM',
    DXGI_FORMAT_B8G8R8A8_UNORM: 'B8G8R8A8_UNORM',
    DXGI_FORMAT_B8G8R8X8_UNORM: 'B8G8R8X8_UNORM',
    DXGI_FORMAT_R10G10B10_XR_BIAS_A2_UNORM: 'R10G10B10_XR_BIAS_A2_UNORM',
    DXGI_FORMAT_B8G8R8A8_TYPELESS: 'B8G8R8A8_TYPELESS',
    DXGI_FORMAT_B8G8R8A8_UNORM_SRGB: 'B8G8R8A8_UNORM_SRGB',
    DXGI_FORMAT_B8G8R8X8_TYPELESS: 'B8G8R8X8_TYPELESS',
    DXGI_FORMAT_B8G8R8X8_UNORM_SRGB: 'B8G8R8X8_UNORM_SRGB',
    DXGI_FORMAT_BC6H_TYPELESS: 'BC6H_TYPELESS',
    DXGI_FORMAT_BC6H_UF16: 'BC6H_UF16',
    DXGI_FORMAT_BC6H_SF16: 'BC6H_SF16',
    DXGI_FORMAT_BC7_TYPELESS: 'BC7_TYPELESS',
    DXGI_FORMAT_BC7_UNORM: 'BC7_UNORM',
    DXGI_FORMAT_BC7_UNORM_SRGB: 'BC7_UNORM_SRGB',
    DXGI_FORMAT_AYUV: 'AYUV',
    DXGI_FORMAT_Y410: 'Y410',
    DXGI_FORMAT_Y416: 'Y416',
    DXGI_FORMAT_NV12: 'NV12',
    DXGI_FORMAT_P010: 'P010',
    DXGI_FORMAT_P016: 'P016',
    DXGI_FORMAT_420_OPAQUE: '420_OPAQUE',
    DXGI_FORMAT_YUY2: 'YUY2',
    DXGI_FORMAT_Y210: 'Y210',
    DXGI_FORMAT_Y216: 'Y216',
    DXGI_FORMAT_NV11: 'NV11',
    DXGI_FORMAT_AI44: 'AI44',
    DXGI_FORMAT_IA44: 'IA44',
    DXGI_FORMAT_P8: 'P8',
    DXGI_FORMAT_A8P8: 'A8P8',
    DXGI_FORMAT_B4G4R4A4_UNORM: 'B4G4R4A4_UNORM',
    DXGI_FORMAT_P208: 'P208',
    DXGI_FORMAT_V208: 'V208',
    DXGI_FORMAT_V408: 'V408',
}


def raw_data_size(pixel_format, nx, ny):

    base_format = dxgi_base_format_db[pixel_format]
    is_uncompressed, ele_size = dxgi_format_db[base_format]

    if is_uncompressed:
        return ele_size * nx * ny
    else:
        return ele_size * ((nx + 3) // 4) * ((ny + 3) // 4)
