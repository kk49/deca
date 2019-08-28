import struct
import pprint
import numpy as np
from deca.ff_adf import Adf, AdfValue, adf_value_extract


# TODO classes based on data in GenZero files, how dynamic do we have to be?


class AmfClass:
    def __init__(self):
        pass

    def parse(self, adf: Adf, value_raw: AdfValue):
        pass


'''
class AmfXXX(AmfClass):
    def __init__(self, adf: Adf = None, value_raw: AdfValue = None):
        AmfClass.__init__(self)

        if adf is not None and value_raw is not None:
            self.parse(adf, value_raw)

    def parse(self, adf: Adf, value_raw : AdfValue):
        pass
'''


class AmfBoundingBox(AmfClass):
    def __init__(self, adf: Adf = None, value_raw: AdfValue = None):
        AmfClass.__init__(self)
        self.min = None
        self.max = None

        if adf is not None and value_raw is not None:
            self.parse(adf, value_raw)

    def parse(self, adf: Adf, value_raw: AdfValue):
        value = value_raw.value
        self.min = value['Min'].value
        self.max = value['Max'].value


class AmfMaterial(AmfClass):
    def __init__(self, adf: Adf = None, value_raw: AdfValue = None):
        AmfClass.__init__(self)
        self.name = None
        self.renderBlockId = None
        self.attributes = None
        self.textures = None

        if adf is not None and value_raw is not None:
            self.parse(adf, value_raw)

    def parse(self, adf: Adf, value_raw: AdfValue):
        value = value_raw.value
        self.name = value['Name'].hash_string
        self.renderBlockId = value['RenderBlockId'].hash_string
        self.attributes = adf_value_extract(value['Attributes'])
        self.textures = [th.hash_string for th in value['Textures'].value]


class AmfModel(AmfClass):
    def __init__(self, adf: Adf = None, value_raw: AdfValue = None):
        AmfClass.__init__(self)
        self.mesh = None
        self.lodSlots = None
        self.memoryTag = None
        self.lodFactor = None
        self.materials = None

        if adf is not None and value_raw is not None:
            self.parse(adf, value_raw)

    def parse(self, adf: Adf, value_raw: AdfValue):
        value = value_raw.value
        self.mesh = value['Mesh'].hash_string
        self.lodSlots = list(value['LodSlots'].value)
        self.memoryTag = value['MemoryTag'].value
        self.lodFactor = value['LodFactor'].value
        self.materials = [AmfMaterial(adf, mv) for mv in value['Materials'].value]


class AmfSubMesh(AmfClass):
    def __init__(self, adf: Adf = None, value_raw: AdfValue = None):
        AmfClass.__init__(self)
        self.subMeshId = None
        self.indexCount = None
        self.indexStreamOffset = None
        self.boundingBox = None

        if adf is not None and value_raw is not None:
            self.parse(adf, value_raw)

    def parse(self, adf: Adf, value_raw: AdfValue):
        value = value_raw.value
        self.subMeshId = value['SubMeshId'].hash_string
        self.indexCount = value['IndexCount'].value
        self.indexStreamOffset = value['IndexStreamOffset'].value
        self.boundingBox = AmfBoundingBox(adf, value['BoundingBox'])


class AmfStreamAttribute(AmfClass):
    def __init__(self, adf: Adf = None, value_raw: AdfValue = None):
        AmfClass.__init__(self)
        self.usage = None
        self.format = None
        self.streamIndex = None
        self.streamOffset = None
        self.streamStride = None
        self.packingData = None

        if adf is not None and value_raw is not None:
            self.parse(adf, value_raw)

    def parse(self, adf: Adf, value_raw: AdfValue):
        value = value_raw.value
        self.usage: AdfValue = value['Usage']
        self.usage = (self.usage.value, self.usage.enum_string)
        self.format: AdfValue = value['Format']
        self.format = (self.format.value, self.format.enum_string)
        self.streamIndex = value['StreamIndex'].value
        self.streamOffset = value['StreamOffset'].value
        self.streamStride = value['StreamStride'].value
        self.packingData = struct.unpack('ff', value['PackingData'].value)


class AmfMesh(AmfClass):
    def __init__(self, adf: Adf = None, value_raw: AdfValue = None):
        AmfClass.__init__(self)
        self.meshTypeId = None
        self.indexCount = None
        self.vertexCount = None
        self.indexBufferIndex = None
        self.indexBufferStride = None
        self.indexBufferOffset = None
        self.vertexBufferIndices = None
        self.vertexStreamStrides = None
        self.vertexStreamOffsets = None
        self.textureDensities = None
        self.meshProperties = None
        self.boneIndexLookup = None
        self.subMeshes = None
        self.streamAttributes = None

        if adf is not None and value_raw is not None:
            self.parse(adf, value_raw)

    def parse(self, adf: Adf, value_raw: AdfValue):
        value = value_raw.value
        self.meshTypeId = value['MeshTypeId'].hash_string
        self.indexCount = value['IndexCount'].value
        self.vertexCount = value['VertexCount'].value
        self.indexBufferIndex = value['IndexBufferIndex'].value
        self.indexBufferStride = value['IndexBufferStride'].value
        self.indexBufferOffset = value['IndexBufferOffset'].value
        self.vertexBufferIndices = list(value['VertexBufferIndices'].value)
        self.vertexStreamStrides = list(value['VertexStreamStrides'].value)
        self.vertexStreamOffsets = value['VertexStreamOffsets'].value
        self.textureDensities = value['TextureDensities'].value
        self.meshProperties = adf_value_extract(value['MeshProperties'])
        self.boneIndexLookup = value['BoneIndexLookup'].value
        self.subMeshes = [AmfSubMesh(adf, v) for v in value['SubMeshes'].value]
        self.streamAttributes = [AmfStreamAttribute(adf, v) for v in value['StreamAttributes'].value]


class AmfLodGroup(AmfClass):
    def __init__(self, adf: Adf = None, value_raw: AdfValue = None):
        AmfClass.__init__(self)
        self.lodIndex = None
        self.meshes = None

        if adf is not None and value_raw is not None:
            self.parse(adf, value_raw)

    def parse(self, adf: Adf, value_raw: AdfValue):
        value = value_raw.value
        self.lodIndex = value['LODIndex'].value
        self.meshes = [AmfMesh(adf, v) for v in value['Meshes'].value]


class AmfMeshHeader(AmfClass):
    def __init__(self, adf: Adf = None, value_raw: AdfValue = None):
        AmfClass.__init__(self)
        self.boundingBox = None
        self.memoryTag = None
        self.lodGroups = None
        self.highLodPath = None

        if adf is not None and value_raw is not None:
            self.parse(adf, value_raw)

    def parse(self, adf: Adf, value_raw: AdfValue):
        value = value_raw.value
        self.boundingBox = AmfBoundingBox(adf, value['BoundingBox'])
        self.memoryTag = value['MemoryTag'].value
        self.highLodPath = value['HighLodPath'].hash_string
        self.lodGroups = [AmfLodGroup(adf, v) for v in value['LodGroups'].value]


class AmfBuffer(AmfClass):
    def __init__(self, adf: Adf = None, value_raw: AdfValue = None):
        AmfClass.__init__(self)
        self.data = None
        self.createSrv = None

        if adf is not None and value_raw is not None:
            self.parse(adf, value_raw)

    def parse(self, adf: Adf, value_raw: AdfValue):
        value = value_raw.value
        self.data = value['Data'].value
        self.createSrv = value['CreateSRV'].value


class AmfMeshBuffers(AmfClass):
    def __init__(self, adf: Adf = None, value_raw: AdfValue = None):
        AmfClass.__init__(self)
        self.memoryTag = None
        self.indexBuffers = None
        self.vertexBuffers = None
        if adf is not None and value_raw is not None:
            self.parse(adf, value_raw)

    def parse(self, adf: Adf, value_raw: AdfValue):
        value = value_raw.value
        self.memoryTag = value['MemoryTag']
        self.indexBuffers = [AmfBuffer(adf, v) for v in value['IndexBuffers'].value]
        self.vertexBuffers = [AmfBuffer(adf, v) for v in value['VertexBuffers'].value]


# stream/buffer conversion routines
# details on float -> Vec3 / Vec4 / Color found here
# https://github.com/PredatorCZ/ApexLib/blob/master/src/AmfFormatEvaluators.h


def preconvert_scale(data_out, data_in, attrs: AmfStreamAttribute, pack, convert):
    if attrs.packingData[0] == 0.0:
        convert(data_out, data_in, attrs, pack)
    else:
        if pack:
            data_in_tmp = data_in.copy()
            if len(data_in_tmp.shape) == 2 and data_in_tmp.shape[1] == 2:
                data_in_tmp[:, 0] /= attrs.packingData[0]
                data_in_tmp[:, 1] /= attrs.packingData[1]
            else:
                data_in_tmp[:, :] /= attrs.packingData[0]
            convert(data_out, data_in_tmp, attrs, pack)
        else:
            convert(data_out, data_in, attrs, pack)
            if len(data_out.shape) == 2 and data_out.shape[1] == 2:
                data_out[:, 0] *= attrs.packingData[0]
                data_out[:, 1] *= attrs.packingData[1]
            else:
                data_out[:, :] *= attrs.packingData[0]


def convert_copy(data_out, data_in, attrs: AmfStreamAttribute, pack):
    if pack:
        data_out[:] = data_in[:]
    else:
        data_out[:] = data_in[:]


def convert_norm(data_out, data_in, attrs: AmfStreamAttribute, pack, scale):
    if pack:
        scale = scale
        data_out[:] = scale * data_in[:]
    else:
        scale = 1.0 / scale
        data_out[:] = scale * data_in[:]


def convert_norm_u16(data_out, data_in, attrs: AmfStreamAttribute, pack):
    convert_norm(data_out, data_in, attrs, pack, 0xffff)


def convert_norm_s16(data_out, data_in, attrs: AmfStreamAttribute, pack):
    convert_norm(data_out, data_in, attrs, pack, 0x7fff)


def convert_norm_u8(data_out, data_in, attrs: AmfStreamAttribute, pack):
    convert_norm(data_out, data_in, attrs, pack, 0xff)


def convert_norm_s8(data_out, data_in, attrs: AmfStreamAttribute, pack):
    convert_norm(data_out, data_in, attrs, pack, 0x7f)


def convert_R10G10B10A2_UNORM(data_out, data_in, attrs: AmfStreamAttribute, pack):
    raise NotImplementedError('convert_R10G10B10A2_UNORM')


def convert_R10G10B10A2_UINT(data_out, data_in, attrs: AmfStreamAttribute, pack):
    raise NotImplementedError('convert_R10G10B10A2_UINT')


def convert_R11G11B10_FLOAT(data_out, data_in, attrs: AmfStreamAttribute, pack):
    raise NotImplementedError('convert_R11G11B10_FLOAT')


def convert_R32_UNIT_VEC_AS_FLOAT(data_out, data_in, attrs: AmfStreamAttribute, pack):
    if pack:
        raise NotImplementedError('convert_R32_UNIT_VEC_AS_FLOAT: pack')
    else:
        data_out[:, 0] = data_in[:]
        data_out[:, 1] = data_in[:] * (1.0 / 256)
        data_out[:, 2] = data_in[:] * (1.0 / 256*256)
        data_out[:, :] = data_out - np.floor(data_out)


def convert_R32_R8G8B8A8_UNORM_AS_FLOAT(data_out, data_in, attrs: AmfStreamAttribute, pack):
    if pack:
        raise NotImplementedError('convert_R32_R8G8B8A8_UNORM_AS_FLOAT: pack')
    else:
        data_out[:, 0] = data_in[:]
        data_out[:, 1] = data_in[:] * (1.0 / 256)
        data_out[:, 2] = data_in[:] * (1.0 / (256*256))
        data_out[:, 3] = data_in[:] * (1.0 / (256*256*256))
        data_out[:, :] = data_out - np.floor(data_out)


def convert_R8G8B8A8_TANGENT_SPACE(data_out, data_in, attrs: AmfStreamAttribute, pack):
    raise NotImplementedError('convert_R8G8B8A8_TANGENT_SPACE')


def convert_R32G32B32A32_FLOAT_P1(data_out, data_in, attrs: AmfStreamAttribute, pack):
    if pack:
        data_out[:, 0] = data_in[:, 0]
        data_out[:, 1] = data_in[:, 1]
        data_out[:, 2] = data_in[:, 2]
        data_out[:, 3] = 1.0
    else:
        raise NotImplementedError('convert_R32G32B32A32_FLOAT_P1: unpack')


def convert_R32G32B32A32_FLOAT_N1(data_out, data_in, attrs: AmfStreamAttribute, pack):
    if pack:
        data_out[:, 0] = data_in[:, 0]
        data_out[:, 1] = data_in[:, 1]
        data_out[:, 2] = data_in[:, 2]
        data_out[:, 3] = -1.0
    else:
        raise NotImplementedError('convert_R32G32B32A32_FLOAT_P1: unpack')


class FormatInfo:
    def __init__(self, dtype_raw, dtype_mem, converter):
        self.dtype_raw = dtype_raw
        self.dtype_mem = dtype_mem
        self.converter = converter


# field_raw_size, field_comp_count, in_dtype, out_dtype, unpack, pack
field_format_info = {
    b'AmfFormat_R32G32B32A32_FLOAT': FormatInfo('4f4', '4f4', convert_copy),
    b'AmfFormat_R32G32B32A32_UINT': FormatInfo('4u4', '4u4', convert_copy),
    b'AmfFormat_R32G32B32A32_SINT': FormatInfo('4i4', '4i4', convert_copy),
    b'AmfFormat_R32G32B32_FLOAT': FormatInfo('3f4', '3f4', convert_copy),
    b'AmfFormat_R32G32B32_UINT': FormatInfo('3u4', '3u4', convert_copy),
    b'AmfFormat_R32G32B32_SINT': FormatInfo('3i4', '3i4', convert_copy),
    b'AmfFormat_R16G16B16A16_FLOAT': FormatInfo('4f2', '4f4', convert_copy),
    b'AmfFormat_R16G16B16A16_UNORM': FormatInfo('4u2', '4f4', convert_norm_u16),
    b'AmfFormat_R16G16B16A16_UINT': FormatInfo('4u2', '4u2', convert_copy),
    b'AmfFormat_R16G16B16A16_SNORM': FormatInfo('4i2', '4f4', convert_norm_s16),
    b'AmfFormat_R16G16B16A16_SINT': FormatInfo('4i2', '4i2', convert_copy),
    b'AmfFormat_R16G16B16_FLOAT': FormatInfo('3f2', '3f4', convert_copy),
    b'AmfFormat_R16G16B16_UNORM': FormatInfo('3u2', '3f4', convert_norm_u16),
    b'AmfFormat_R16G16B16_UINT': FormatInfo('3u2', '3u2', convert_copy),
    b'AmfFormat_R16G16B16_SNORM': FormatInfo('3i2', '3f4', convert_norm_s16),
    b'AmfFormat_R16G16B16_SINT': FormatInfo('3i2', '3i2', convert_copy),
    b'AmfFormat_R32G32_FLOAT': FormatInfo('2f4', '2f4', convert_copy),
    b'AmfFormat_R32G32_UINT': FormatInfo('2u4', '2u4', convert_copy),
    b'AmfFormat_R32G32_SINT': FormatInfo('2i4', '2i4', convert_copy),
    b'AmfFormat_R10G10B10A2_UNORM': FormatInfo('u4', '4f4', convert_R10G10B10A2_UNORM),
    b'AmfFormat_R10G10B10A2_UINT': FormatInfo('u4', '4u2', convert_R10G10B10A2_UINT),
    b'AmfFormat_R11G11B10_FLOAT': FormatInfo('u4', '3f4', convert_R11G11B10_FLOAT),
    b'AmfFormat_R8G8B8A8_UNORM': FormatInfo('4u1', '4f4', convert_norm_u8),
    b'AmfFormat_R8G8B8A8_UNORM_SRGB': FormatInfo('4u1', '4f4', convert_norm_u8),
    b'AmfFormat_R8G8B8A8_UINT': FormatInfo('4u1', '4u1', convert_copy),
    b'AmfFormat_R8G8B8A8_SNORM': FormatInfo('4i1', '4f4', convert_norm_s8),
    b'AmfFormat_R8G8B8A8_SINT': FormatInfo('4i1', '4i1', convert_copy),
    b'AmfFormat_R16G16_FLOAT': FormatInfo('2f2', '2f2', convert_copy),
    b'AmfFormat_R16G16_UNORM': FormatInfo('2u2', '2f2', convert_norm_u16),
    b'AmfFormat_R16G16_UINT': FormatInfo('2u2', '2u2', convert_copy),
    b'AmfFormat_R16G16_SNORM': FormatInfo('2i2', '2f2', convert_norm_s16),
    b'AmfFormat_R16G16_SINT': FormatInfo('2i2', '2i2', convert_copy),
    b'AmfFormat_R32_FLOAT': FormatInfo('f4', 'f4', convert_copy),
    b'AmfFormat_R32_UINT': FormatInfo('u4', 'u4', convert_copy),
    b'AmfFormat_R32_SINT': FormatInfo('i4', 'i4', convert_copy),
    b'AmfFormat_R8G8_UNORM': FormatInfo('2u1', '2f4', convert_norm_u8),
    b'AmfFormat_R8G8_UINT': FormatInfo('2u1', '2u1', convert_copy),
    b'AmfFormat_R8G8_SNORM': FormatInfo('2i1', '2f4', convert_norm_s8),
    b'AmfFormat_R8G8_SINT': FormatInfo('2i1', '2i1', convert_copy),
    b'AmfFormat_R16_FLOAT': FormatInfo('f2', 'f4', convert_copy),
    b'AmfFormat_R16_UNORM': FormatInfo('u2', 'f4', convert_norm_u16),
    b'AmfFormat_R16_UINT': FormatInfo('u2', 'u2', convert_copy),
    b'AmfFormat_R16_SNORM': FormatInfo('i2', 'f4', convert_norm_s16),
    b'AmfFormat_R16_SINT': FormatInfo('i2', 'i2', convert_copy),
    b'AmfFormat_R8_UNORM': FormatInfo('u1', 'f4', convert_norm_u8),
    b'AmfFormat_R8_UINT': FormatInfo('u1', 'u1', convert_copy),
    b'AmfFormat_R8_SNORM': FormatInfo('i1', 'f4', convert_norm_s8),
    b'AmfFormat_R8_SINT': FormatInfo('i1', 'i1', convert_copy),
    b'AmfFormat_R32_UNIT_VEC_AS_FLOAT': FormatInfo('f4', '3f4', convert_R32_UNIT_VEC_AS_FLOAT),
    b'AmfFormat_R32_R8G8B8A8_UNORM_AS_FLOAT': FormatInfo('f4', '4f4', convert_R32_R8G8B8A8_UNORM_AS_FLOAT),
    b'AmfFormat_R8G8B8A8_TANGENT_SPACE': FormatInfo('4i1', '4f4', convert_R8G8B8A8_TANGENT_SPACE),
    b'AmfFormat_R32G32B32A32_FLOAT_P1': FormatInfo('4f4', '3f4', convert_R32G32B32A32_FLOAT_P1),
    b'AmfFormat_R32G32B32A32_FLOAT_N1': FormatInfo('4f4', '3f4', convert_R32G32B32A32_FLOAT_N1),
}


def amf_meshc_reformat(mesh_header, mesh_buffers):
    # TODO this should be a parameter, remove model parameter
    vertex_format_translate = {
        b'AmfFormat_R16G16B16_SNORM': b'AmfFormat_R32G32B32_FLOAT',
        b'AmfFormat_R16G16_SNORM': b'AmfFormat_R32G32_FLOAT',
        b'AmfFormat_R16_SNORM': b'AmfFormat_R32_FLOAT',
        b'AmfFormat_R16_UNORM': b'AmfFormat_R32_FLOAT',
        b'AmfFormat_R16_UINT': b'AmfFormat_R32_UINT',
        b'AmfFormat_R32_UNIT_VEC_AS_FLOAT': b'AmfFormat_R32G32B32_FLOAT',
        b'AmfFormat_R32_R8G8B8A8_UNORM_AS_FLOAT': b'AmfFormat_R8G8B8A8_UNORM',
    }

    # get references to raw_buffers
    raw_buffers_index = [buffer.data for buffer in mesh_buffers.indexBuffers]
    raw_buffers_vertex = [buffer.data for buffer in mesh_buffers.vertexBuffers]

    # get info about vertex streams
    vertex_streams_all = {}
    lod_group: AmfLodGroup
    vinfo_dict = {}
    vinfo_all = []
    for lg_idx, lod_group in enumerate(mesh_header.lodGroups):
        mesh: AmfMesh
        m_dict = {}
        for m_idx, mesh in enumerate(lod_group.meshes):
            vs_dict = {}
            for vs_idx in range(len(mesh.vertexBufferIndices)):
                vinfo = [
                    (lg_idx, m_idx, vs_idx),
                    [
                        mesh.vertexBufferIndices[vs_idx],
                        mesh.vertexStreamOffsets[vs_idx],
                        mesh.vertexCount,
                        mesh.vertexStreamStrides[vs_idx],
                    ],
                    None,  # future stream_in data location
                    None,  # future stream_out stride location
                    None,  # future stream_out data location
                ]
                vs_dict[vs_idx] = vinfo
                vinfo_all.append(vinfo)
            m_dict[m_idx] = vs_dict
        vinfo_dict[lg_idx] = m_dict

    buffer_stream_info = {}
    buffer_stream_vsinfo = {}
    for vinfo in vinfo_all:
        # group streams by buffer
        buffer_index = vinfo[1][0]
        stream_begin = vinfo[1][1]
        stream_end = stream_begin + vinfo[1][2] * vinfo[1][3]

        # break up buffer into streams
        vinfo[2] = raw_buffers_vertex[buffer_index][stream_begin:stream_end]

        # update stream extents
        bi = buffer_stream_info.get(buffer_index, [])
        buffer_stream_info[buffer_index] = bi
        bi.append([stream_begin, stream_end])

        # update stream info, sortable by buffer and initial offset
        bi = buffer_stream_vsinfo.get(buffer_index, {})
        buffer_stream_vsinfo[buffer_index] = bi
        bi[stream_begin] = vinfo

    # process each buffer
    for bidx, bi in buffer_stream_info.items():
        # check for no overlaps in buffer streams #Paranoid
        buffer_length = len(raw_buffers_vertex[bidx])
        for i0 in range(len(bi)):
            e0 = bi[i0]

            if e0[0] >= buffer_length or e0[1] > buffer_length:
                raise Exception('Stream references outside of buffer {}: {}'.format(bidx, e0))

            for i1 in range(i0+1, len(bi)):
                e1 = bi[i1]
                if e0[0] < e1[0] and e0[1] <= e1[0]:
                    pass  # e0 before e1
                elif e0[0] >= e1[1] and e0[1] > e1[1]:
                    pass  # e0 after e1
                else:
                    raise Exception('Overlapping stream detected in buffer {}: {} {}'.format(bidx, e0, e1))

    lod_group: AmfLodGroup
    for lg_idx, lod_group in enumerate(mesh_header.lodGroups):
        mesh: AmfMesh
        for m_idx, mesh in enumerate(lod_group.meshes):
            vs_dict = vinfo_dict[lg_idx][m_idx]

            sa_attr = np.array(mesh.streamAttributes)
            sa_aidx = np.array(list(range(len(sa_attr))))
            sa_usage = np.array([sa.usage[1] for sa in mesh.streamAttributes])
            sa_format = np.array([sa.format[1] for sa in mesh.streamAttributes])
            sa_stream_index = np.array([sa.streamIndex for sa in mesh.streamAttributes])
            sa_stream_offset = np.array([sa.streamOffset for sa in mesh.streamAttributes])
            sa_stream_stride = np.array([sa.streamStride for sa in mesh.streamAttributes])
            sa_stream_packing_data = np.array([sa.packingData for sa in mesh.streamAttributes])

            for bidx, vs_info in vs_dict.items():
                sab_aidx = sa_aidx[sa_stream_index == bidx]
                sab_attr = sa_attr[sa_stream_index == bidx]
                sab_stream_offset = sa_stream_offset[sa_stream_index == bidx]
                sab_stream_stride = sa_stream_stride[sa_stream_index == bidx]
                assert np.all(sab_stream_stride[0] == sab_stream_stride)  # confirm all strides are the same
                reorder = np.argsort(sab_stream_offset)

                attributes_in = []
                attributes_out = []
                attributes_index = []
                dtype_in = []
                dtype_mem = []
                dtype_out = []

                offset = 0
                for ridx in reorder:
                    sattr_in: AmfStreamAttribute = sab_attr[ridx]

                    format_in = sattr_in.format[1]
                    format_out = vertex_format_translate.get(format_in, format_in)

                    if sattr_in.usage[1] == b'AmfUsage_Tangent':
                        format_out = b'AmfFormat_R32G32B32A32_FLOAT_P1'
                        # format_out = b'AmfFormat_R32G32B32A32_FLOAT_N1'

                    fi_in = field_format_info[format_in]
                    fi_out = field_format_info[format_out]

                    sattr_out = AmfStreamAttribute()
                    sattr_out.format = (None, format_out)
                    sattr_out.streamStride = None
                    sattr_out.streamOffset = offset
                    sattr_out.streamIndex = sattr_in.streamIndex
                    sattr_out.packingData = (0., 0.)
                    sattr_out.usage = sattr_in.usage

                    offset = offset + np.dtype(fi_out.dtype_raw).itemsize

                    attributes_in.append(sattr_in)
                    attributes_out.append(sattr_out)
                    attributes_index.append(sab_aidx[ridx])

                    dtype_in.append(fi_in.dtype_raw)
                    dtype_mem.append(fi_in.dtype_mem)
                    dtype_out.append(fi_out.dtype_raw)

                # update the record stride once we have calculated it
                vs_info[3] = offset
                for sattr in attributes_out:
                    sattr.streamStride = offset

                # setup conversion types
                dtype_in = str.join(', ', dtype_in)
                dtype_mem = str.join(', ', dtype_mem)
                dtype_out = str.join(', ', dtype_out)
                dtype_in = np.dtype(dtype_in)
                dtype_mem = np.dtype(dtype_mem)
                dtype_out = np.dtype(dtype_out)

                # get original stream
                buf_in = vs_info[2]

                # translate original stream
                data_in = np.frombuffer(buf_in, dtype=dtype_in)
                data_mem = np.zeros(data_in.shape, dtype=dtype_mem)
                data_out = np.zeros(data_in.shape, dtype=dtype_out)
                for idx, sattr_in in enumerate(attributes_in):
                    sattr_out = attributes_out[idx]
                    fidx = 'f{}'.format(idx)
                    finfo_in = field_format_info[sattr_in.format[1]]
                    finfo_out = field_format_info[sattr_out.format[1]]
                    preconvert_scale(data_mem[fidx], data_in[fidx], sattr_in, False, finfo_in.converter)
                    preconvert_scale(data_out[fidx], data_mem[fidx], sattr_out, True, finfo_out.converter)

                # store updated stream
                vs_info[4] = bytes(data_out.data)

                # update attributes that use the current stream
                for aidx, aout in zip(attributes_index, attributes_out):
                    mesh.streamAttributes[aidx] = aout

                pass  # bidx

            pass  # m_idx

        pass  # l_idx

    # rebuild buffers
    for bidx, bi in buffer_stream_vsinfo.items():
        offsets = list(bi.keys())
        offsets.sort()
        buffer_new = b''
        for offset_old in offsets:
            vs_info = bi[offset_old]
            lg_idx, m_idx, vs_idx = vs_info[0]
            mesh_header.lodGroups[lg_idx].meshes[m_idx].vertexStreamStrides[vs_idx] = vs_info[3]
            mesh_header.lodGroups[lg_idx].meshes[m_idx].vertexStreamOffsets[vs_idx] = len(buffer_new)
            buffer_new = buffer_new + vs_info[4]

        mesh_buffers.vertexBuffers[bidx].data = buffer_new

    pass  # function
