import struct
import numpy as np
from deca.ff_adf import Adf, AdfValue, adf_value_extract


# TODO classes based on data in GenZero files, how dynamic do we have to be?


class AABB:
    def __init__(self, all6: [np.ndarray, list] = None, min3: [np.ndarray, list] = None, max3: [np.ndarray, list] = None):
        if all6 is not None and min3 is None and max3 is None:
            self.min = np.array(all6[0:3])
            self.max = np.array(all6[3:6])
        elif all6 is None and min3 is not None and max3 is not None:
            self.min = np.array(min3)
            self.max = np.array(max3)
        else:
            raise ValueError('AABB::__init__: incorrect parameters')

    def mid(self):
        return 0.5 * (self.min + self.max)

    def union(self, other):
        if other is None:
            return AABB(min3=self.min, max3=self.max)
        else:
            return AABB(
                min3=np.fmin(self.min, other.min),
                max3=np.fmax(self.max, other.max),
            )


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
    def __init__(self, adf: Adf = None, value_raw: AdfValue = None, merged_buffers=False):
        AmfClass.__init__(self)
        self.subMeshId = None
        self.indexCount = None
        self.indexStreamOffset = None
        self.boundingBox = None

        self._merged_buffers = merged_buffers

        if adf is not None and value_raw is not None:
            self.parse(adf, value_raw)

    def parse(self, adf: Adf, value_raw: AdfValue):
        value = value_raw.value
        self.subMeshId = value['SubMeshId'].hash_string
        self.indexCount = value['IndexCount'].value
        self.boundingBox = AmfBoundingBox(adf, value['BoundingBox'])

        if self._merged_buffers:
            self.indexStreamOffset = 0
        else:
            self.indexStreamOffset = value['IndexStreamOffset'].value


class AmfStreamAttribute(AmfClass):
    def __init__(self, adf: Adf = None, value_raw: AdfValue = None):
        AmfClass.__init__(self)
        self.usage = None
        self.format = None
        self.streamIndex = None
        self.streamOffset = None
        self.streamStride = None
        self.packingData = None
        self.min = None
        self.max = None

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
    def __init__(self, adf: Adf = None, value_raw: AdfValue = None, merged_buffers=False):
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

        self._merged_buffers = merged_buffers

        if adf is not None and value_raw is not None:
            self.parse(adf, value_raw)

    def parse(self, adf: Adf, value_raw: AdfValue):
        value = value_raw.value
        self.meshTypeId = value['MeshTypeId'].hash_string
        self.indexCount = value['IndexCount'].value
        self.vertexCount = value['VertexCount'].value

        self.indexBufferStride = value['IndexBufferStride'].value
        self.vertexStreamStrides = list(value['VertexStreamStrides'].value)
        self.vertexStreamOffsets = value['VertexStreamOffsets'].value

        if self._merged_buffers:
            merged_buffer_index = value['MergedBufferIndex'].value
            self.indexBufferIndex = merged_buffer_index
            self.indexBufferOffset = 0
            self.vertexBufferIndices = [merged_buffer_index] * len(self.vertexStreamOffsets)
        else:
            self.indexBufferIndex = value['IndexBufferIndex'].value
            self.indexBufferOffset = value['IndexBufferOffset'].value
            self.vertexBufferIndices = list(value['VertexBufferIndices'].value)

        self.textureDensities = value['TextureDensities'].value
        self.meshProperties = adf_value_extract(value['MeshProperties'])
        self.boneIndexLookup = value['BoneIndexLookup'].value
        self.subMeshes = [AmfSubMesh(adf, v, merged_buffers=self._merged_buffers) for v in value['SubMeshes'].value]
        self.streamAttributes = [AmfStreamAttribute(adf, v) for v in value['StreamAttributes'].value]


class AmfLodGroup(AmfClass):
    def __init__(self, adf: Adf = None, value_raw: AdfValue = None, merged_buffers=False):
        AmfClass.__init__(self)
        self.lodIndex = None
        self.meshes = None

        self._merged_buffers = merged_buffers

        if adf is not None and value_raw is not None:
            self.parse(adf, value_raw)

    def parse(self, adf: Adf, value_raw: AdfValue):
        value = value_raw.value
        self.lodIndex = value['LODIndex'].value
        self.meshes = [AmfMesh(adf, v, merged_buffers=self._merged_buffers) for v in value['Meshes'].value]


class AmfMeshHeader(AmfClass):
    def __init__(self, adf: Adf = None, value_raw: AdfValue = None, merged_buffers=False):
        AmfClass.__init__(self)
        self.boundingBox = None
        self.memoryTag = None
        self.lodGroups = None
        self.highLodPath = None

        self._merged_buffers = merged_buffers

        if adf is not None and value_raw is not None:
            self.parse(adf, value_raw)

    def parse(self, adf: Adf, value_raw: AdfValue):
        value = value_raw.value
        self.boundingBox = AmfBoundingBox(adf, value['BoundingBox'])
        self.memoryTag = value['MemoryTag'].value
        self.highLodPath = value['HighLodPath'].hash_string
        self.lodGroups = [AmfLodGroup(adf, v, merged_buffers=self._merged_buffers) for v in value['LodGroups'].value]


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
        self.createSrv = value.get('CreateSRV', AdfValue(None, None, None)).value


class AmfMeshBuffers(AmfClass):
    def __init__(self, adf: Adf = None, value_raw: AdfValue = None, merged_buffers=False):
        AmfClass.__init__(self)
        self.memoryTag = None
        self.indexBuffers = None
        self.vertexBuffers = None

        self._merged_buffers = merged_buffers

        if adf is not None and value_raw is not None:
            self.parse(adf, value_raw)

    def parse(self, adf: Adf, value_raw: AdfValue):
        value = value_raw.value
        self.memoryTag = value['MemoryTag']
        if self._merged_buffers:
            index_offsets = value['IndexOffsets'].value
            vertex_offsets = value['VertexOffsets'].value

            # TODO BUG IN APEX ENGINE, index offsets stored by index count :/
            index_offsets = [2 * i for i in index_offsets]

            buffer_data = value['MergedBuffer'].value['Data'].value
            buffer_create_srv = value['MergedBuffer'].value['CreateSRV'].value

            offsets = index_offsets + vertex_offsets + [len(buffer_data)]
            offsets.sort()
            ends = {}
            for i, offset in enumerate(offsets):
                if i+1 < len(offsets):
                    ends[offset] = offsets[i+1]

            self.indexBuffers = []
            for offset in index_offsets:
                new_buffer = AmfBuffer()
                new_buffer.data = buffer_data[offset:ends[offset]]
                new_buffer.createSrv = buffer_create_srv
                self.indexBuffers.append(new_buffer)

            self.vertexBuffers = []
            for offset in vertex_offsets:
                new_buffer = AmfBuffer()
                new_buffer.data = buffer_data[offset:ends[offset]]
                new_buffer.createSrv = buffer_create_srv
                self.vertexBuffers.append(new_buffer)

            # merged_buffer = [AmfBuffer(adf, v) for v in value['MergedBuffer'].value]
        else:
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
    if pack:
        raise NotImplementedError('convert_R8G8B8A8_TANGENT_SPACE: pack')
    else:
        # from http://www.humus.name/Articles/Persson_CreatingVastGameWorlds.pdf

        angles = np.pi * (data_in[:, :] * (1.0 / 0xff) * 2.0 - 1.0)

        sc0x = np.sin(angles[:, 0])
        sc0y = np.cos(angles[:, 0])
        sc0z = np.sin(angles[:, 1])
        sc0w = np.cos(angles[:, 1])
        sc1x = np.sin(angles[:, 2])
        sc1y = np.cos(angles[:, 2])
        sc1z = np.sin(angles[:, 3])
        sc1w = np.cos(angles[:, 3])

        t = np.array([sc0y * np.abs(sc0z), sc0x * np.abs(sc0z), sc0w]).transpose()
        b = np.array([sc1y * np.abs(sc1z), sc1x * np.abs(sc1z), sc1w]).transpose()
        n = np.cross(t, b)
        n[angles[:, 3] <= 0.0] = -n[angles[:, 3] <= 0.0]

        data_out[:, 0:3] = n
        data_out[:, 3:6] = t

        """incorrect version?
        q = data_in[:, :] * (1.0 / 0xff) * 2.0 - 1.0

        x = 0
        y = 1
        z = 2
        w = 3
        t = np.array([1.0, 0.0, 0.0]) + np.array([-2.0, 2.0, 2.0]) * q[:, [y]] * q[:, [y, x, w]] + np.array([-2.0, -2.0, 2.0]) * q[:, [z]] * q[:, [z, w, x]]
        # b = np.array([0.0, 1.0, 0.0]) + np.array([2.0, -2.0, 2.0]) * q[:, [z]] * q[:, [w, z, y]] + np.array([2.0, -2.0, -2.0]) * q[:, [x]] * q[:, [y, x, w]]
        n = np.array([0.0, 0.0, 1.0]) + np.array([2.0, 2.0, -2.0]) * q[:, [x]] * q[:, [z, w, x]] + np.array([-2.0, 2.0, -2.0]) * q[:, [y]] * q[:, [w, z, y]]

        data_out[:, 0:3] = n
        data_out[:, 3:6] = t
        """


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
    b'AmfFormat_R16G16_FLOAT': FormatInfo('2f2', '2f4', convert_copy),
    b'AmfFormat_R16G16_UNORM': FormatInfo('2u2', '2f4', convert_norm_u16),
    b'AmfFormat_R16G16_UINT': FormatInfo('2u2', '2u2', convert_copy),
    b'AmfFormat_R16G16_SNORM': FormatInfo('2i2', '2f4', convert_norm_s16),
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
    b'AmfFormat_R16_UINT': FormatInfo('u2', 'u4', convert_copy),
    b'AmfFormat_R16_SNORM': FormatInfo('i2', 'f4', convert_norm_s16),
    b'AmfFormat_R16_SINT': FormatInfo('i2', 'i4', convert_copy),
    b'AmfFormat_R8_UNORM': FormatInfo('u1', 'f4', convert_norm_u8),
    b'AmfFormat_R8_UINT': FormatInfo('u1', 'u4', convert_copy),
    b'AmfFormat_R8_SNORM': FormatInfo('i1', 'f4', convert_norm_s8),
    b'AmfFormat_R8_SINT': FormatInfo('i1', 'i4', convert_copy),
    b'AmfFormat_R32_UNIT_VEC_AS_FLOAT': FormatInfo('f4', '3f4', convert_R32_UNIT_VEC_AS_FLOAT),
    b'AmfFormat_R32_R8G8B8A8_UNORM_AS_FLOAT': FormatInfo('f4', '4f4', convert_R32_R8G8B8A8_UNORM_AS_FLOAT),
    b'AmfFormat_R8G8B8A8_TANGENT_SPACE': FormatInfo('4u1', '6f4', convert_R8G8B8A8_TANGENT_SPACE),  # normal, tangent
    b'DecaFormat_R32G32B32A32_FLOAT_P1': FormatInfo('4f4', '3f4', convert_R32G32B32A32_FLOAT_P1),
    b'DecaFormat_R32G32B32A32_FLOAT_N1': FormatInfo('4f4', '3f4', convert_R32G32B32A32_FLOAT_N1),
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

            sa_attr_org = mesh.streamAttributes
            sa_attr = np.array(mesh.streamAttributes)
            sa_aidx = np.array(list(range(len(sa_attr))))
            sa_usage = np.array([sa.usage[1] for sa in mesh.streamAttributes])
            sa_format = np.array([sa.format[1] for sa in mesh.streamAttributes])
            sa_stream_index = np.array([sa.streamIndex for sa in mesh.streamAttributes])
            sa_stream_offset = np.array([sa.streamOffset for sa in mesh.streamAttributes])
            sa_stream_stride = np.array([sa.streamStride for sa in mesh.streamAttributes])
            sa_stream_packing_data = np.array([sa.packingData for sa in mesh.streamAttributes])

            mesh.streamAttributes = []

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
                dtype_in_mem = []
                dtype_out_mem = []
                dtype_out = []

                offset = 0
                for ridx in reorder:
                    sattr_in: AmfStreamAttribute = sab_attr[ridx]

                    format_in = sattr_in.format[1]
                    usage_in = sattr_in.usage[1]
                    formats_out = [vertex_format_translate.get(format_in, format_in)]
                    usages_out = [usage_in]

                    if usage_in == b'AmfUsage_Tangent':
                        formats_out = [b'DecaFormat_R32G32B32A32_FLOAT_P1']
                        # formats_out = [b'DecaFormat_R32G32B32A32_FLOAT_N1']
                    elif usage_in == b'AmfUsage_TangentSpace':
                        usages_out = [b'AmfUsage_Normal', b'AmfUsage_Tangent']
                        formats_out = [b'AmfFormat_R32G32B32_FLOAT', b'DecaFormat_R32G32B32A32_FLOAT_P1']
                    elif usage_in == b'AmfUsage_BoneWeight':
                        formats_out = [b'AmfFormat_R32G32B32A32_FLOAT']

                    fi_in = field_format_info[format_in]
                    attributes_in.append(sattr_in)
                    dtype_in.append(fi_in.dtype_raw)
                    dtype_in_mem.append(fi_in.dtype_mem)

                    for format_out, usage_out in zip(formats_out, usages_out):
                        fi_out = field_format_info[format_out]
                        sattr_out = AmfStreamAttribute()
                        sattr_out.format = (None, format_out)
                        sattr_out.streamStride = None
                        sattr_out.streamOffset = offset
                        sattr_out.streamIndex = sattr_in.streamIndex
                        sattr_out.packingData = (0., 0.)
                        sattr_out.usage = (None, usage_out)

                        offset = offset + np.dtype(fi_out.dtype_raw).itemsize

                        attributes_out.append(sattr_out)
                        attributes_index.append(sab_aidx[ridx])

                        dtype_out.append(fi_out.dtype_raw)
                        dtype_out_mem.append(fi_out.dtype_mem)

                # update the record stride once we have calculated it
                vs_info[3] = offset
                for sattr in attributes_out:
                    sattr.streamStride = offset

                # setup conversion types
                dtype_in = str.join(', ', dtype_in)
                dtype_in_mem = str.join(', ', dtype_in_mem)
                dtype_out_mem = str.join(', ', dtype_out_mem)
                dtype_out = str.join(', ', dtype_out)
                dtype_in = np.dtype(dtype_in)
                dtype_in_mem = np.dtype(dtype_in_mem)
                dtype_out_mem = np.dtype(dtype_out_mem)
                dtype_out = np.dtype(dtype_out)

                # get original stream
                buf_in = vs_info[2]

                # translate original stream
                data_in = np.frombuffer(buf_in, dtype=dtype_in)
                data_in_mem = np.zeros((data_in.shape[0],), dtype=dtype_in_mem)

                for idx, sattr_in in enumerate(attributes_in):
                    finfo_in = field_format_info[sattr_in.format[1]]
                    if data_in.dtype.fields is None:
                        assert len(attributes_in) == 1
                        data_in_mem_field = data_in_mem
                        data_in_field = data_in
                    else:
                        fidx = 'f{}'.format(idx)
                        data_in_mem_field = data_in_mem[fidx]
                        data_in_field = data_in[fidx]

                    preconvert_scale(data_in_mem_field, data_in_field, sattr_in, False, finfo_in.converter)

                data_out_mem = np.frombuffer(data_in_mem.tobytes(), dtype=dtype_out_mem).copy()
                data_out = np.zeros((data_in.shape[0],), dtype=dtype_out)
                for idx, sattr_out in enumerate(attributes_out):
                    finfo_out = field_format_info[sattr_out.format[1]]
                    if data_out.dtype.fields is None:
                        assert len(attributes_out) == 1
                        data_out_mem_field = data_out_mem
                        data_out_field = data_out
                    else:
                        fidx = 'f{}'.format(idx)
                        data_out_mem_field = data_out_mem[fidx]
                        data_out_field = data_out[fidx]

                    # update bone indexs
                    if mesh.boneIndexLookup and sattr_out.usage[1] == b'AmfUsage_BoneIndex':
                        arr_map = np.array(mesh.boneIndexLookup)
                        data_out_mem_field[:, :] = arr_map[data_out_mem_field]

                    # TODO APEX Engine can handle bone weights that are all zero because no bones are attached,
                    #  GLTF2 cannot
                    if sattr_out.usage[1] == b'AmfUsage_BoneWeight':
                        msk = np.all(data_out_mem_field == 0.0, 1)
                        data_out_mem_field[msk] = np.asarray([1.0, 0.0, 0.0, 0.0])
                        s = np.sum(data_out_mem_field, 1)
                        data_out_mem_field = (data_out_mem_field.T / s).T

                    preconvert_scale(data_out_field, data_out_mem_field, sattr_out, True, finfo_out.converter)

                    # Normals should be unit length
                    if sattr_out.usage[1] == b'AmfUsage_Normal' or sattr_out.usage[1] == b'AmfUsage_Tangent':
                        norm = np.linalg.norm(data_out_field[:, 0:3], axis=1)
                        data_out_field[norm == 0, 0:3] = 1.0
                        norm = np.linalg.norm(data_out_field[:, 0:3], axis=1)
                        # norm[norm == 0] = 1.0
                        data_out_field[:, 0:3] = data_out_field[:, 0:3] / norm[:, np.newaxis]
                        data_out_field[np.isnan(norm), 0:3] = 0
                        data_out_field[np.isnan(norm), 0] = 1
                        if np.any(np.isnan(norm)):
                            print('WARNING: Found nan in data: {}'.format(sattr_out.usage[1]))

                    sattr_out.min = np.min(data_out_field, axis=0)
                    sattr_out.max = np.max(data_out_field, axis=0)

                # store updated stream
                vs_info[4] = bytes(data_out.data)

                # update attributes that use the current stream
                mesh.streamAttributes = mesh.streamAttributes + attributes_out

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
