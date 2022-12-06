from typing import Optional
import xml.etree.ElementTree as ElementTree
from .util import remove_prefix_if_present
from .ff_avtx import image_load, ddsc_write_to_dds, ddsc_write_to_png, ddsc_clean
from .ff_adf import *
from .ff_adf_amf import *
import pygltflib as pyg
import scipy.spatial.transform as sst
import copy
import subprocess
import sys

def _get_or_none(index, list_data):
    if index < len(list_data):
        return list_data[index]
    else:
        return None


class Deca3dMatrix:
    def __init__(self, col_major=None, row_major=None):
        assert not ((col_major is not None) and (row_major is not None))

        self.data = None

        if col_major is not None:
            self.data = np.array(col_major).reshape(4, 4).transpose()

        if row_major is not None:
            self.data = np.array(col_major).reshape(4, 4)

    def prep(self):
        if self.data is None:
            self.data = np.identity(4)

    def translate(self, vec3):
        self.prep()
        self.data[0:3, 3] += vec3

    def col_major_list(self):
        if self.data is None:
            return None
        else:
            return list(self.data.transpose().reshape((-1,)))

    def row_major_list(self):
        if self.data is None:
            return None
        else:
            return list(self.data.reshape((-1,)))

    @staticmethod
    def matmul(a, b):
        if a is None or a.data is None:
            return b
        if b is None or b.data is None:
            return a

        mat = Deca3dMatrix()
        mat.data = np.matmul(a.data, b.data)
        return mat


class Deca3dDatabase:
    def __init__(self, vfs: VfsDatabase, resource_prefix_abs, resource_prefix_uri, flat_file_layout, texture_format):
        self.vfs = vfs
        self.adf_db = AdfDatabase(vfs)
        self.resource_prefix_abs = resource_prefix_abs
        self.resource_prefix_uri = resource_prefix_uri
        self.map_vpath_to_texture = {}
        self.map_vpath_to_meshc = {}
        self.map_vpath_to_modelc = {}
        self.map_vpath_to_hk_skeleton = {}
        self.flat_file_layout = flat_file_layout
        self.texture_format = texture_format

    def gltf_add_texture(self, gltf, v_path):
        item = self.map_vpath_to_texture.get(v_path, Deca3dTexture(v_path))
        self.map_vpath_to_texture[v_path] = item
        return item.add_to_gltf(self.vfs, self.adf_db, self, gltf, self.texture_format)

    def gltf_add_meshc(self, gltf, v_path):
        item = self.map_vpath_to_meshc.get(v_path, Deca3dMeshc(v_path))
        self.map_vpath_to_meshc[v_path] = item
        return item.add_to_gltf(self.vfs, self.adf_db, self, gltf)

    def gltf_add_modelc(self, gltf, v_path, material_properties=None):
        item = self.map_vpath_to_modelc.get(v_path, Deca3dModelc(v_path, material_properties))
        self.map_vpath_to_modelc[v_path] = item
        return item.add_to_gltf(self.vfs, self.adf_db, self, gltf)

    def gltf_add_hk_skeleton(self, gltf, v_path, scene):
        item = self.map_vpath_to_hk_skeleton.get(v_path, Deca3dHkSkeleton(v_path, scene))
        self.map_vpath_to_hk_skeleton[v_path] = item
        return item.add_to_gltf(self.vfs, self.adf_db, self, gltf)

    def gltf_finalize_mesh(self, mesh_org: pyg.Mesh, material_map=None):
        mesh = copy.deepcopy(mesh_org)
        p: pyg.Primitive
        for p in mesh.primitives:
            p.material = material_map.get(p.material, None)

        return mesh


class Deca3dTexture:
    def __init__(self, v_path):
        self.v_path = v_path
        self.gltf_id = None
        self.texture_saved = False

    def add_to_gltf(self, vfs: VfsDatabase, adf_db, db: Deca3dDatabase, gltf: pyg.GLTF2, texture_format):
        if not self.texture_saved:
            vfs.logger.log('Texture:Setup: {}'.format(self.v_path))
            # dump textures
            texture_fn_uri = None
            if len(self.v_path) > 0:
                texture_nodes = vfs.nodes_where_match(v_path=self.v_path)
                if len(texture_nodes) > 0:
                    texture_fn = self.v_path.decode('utf-8')
                    if not texture_fn.endswith(texture_format):
                        texture_fn += '.' + texture_format

                    if db.flat_file_layout:
                        texture_fn = texture_fn.replace('/', '_')
                    texture_fn_uri = os.path.join(db.resource_prefix_uri, texture_fn)
                    texture_fn_absolute = os.path.join(db.resource_prefix_abs, texture_fn)

                    if not os.path.isfile(texture_fn_absolute):
                        texture_node = texture_nodes[0]
                        ddsc = image_load(vfs, texture_node, save_raw_data=True)

                        if ddsc_clean(ddsc):
                            vfs.logger.warning('WARNING: {}: missing high resolution data'.format(self.v_path))

                        os.makedirs(os.path.dirname(texture_fn_absolute), exist_ok=True)

                        if texture_fn_absolute.endswith('png'):
                            ddsc_write_to_png(ddsc, texture_fn_absolute)
                        elif texture_fn_absolute.endswith('ddsc') or texture_fn_absolute.endswith('dds'):
                            ddsc_write_to_dds(ddsc, texture_fn_absolute)
                        else:
                            vfs.logger.log('ERROR: {}: Unhandled Texture format: {}'.format(self.v_path, texture_format))

                else:
                    vfs.logger.log('WARNING: Missing Texture file: {}'.format(self.v_path))

            # Setup GLTF.Image
            if texture_fn_uri is not None:
                gltf_image = pyg.Image()
                gltf_image.uri = texture_fn_uri
                image_idx = len(gltf.images)
                gltf.images.append(gltf_image)

                gltf_texture = pyg.Texture()
                gltf_texture.source = image_idx
                # gltf_texture.sampler
                # gltf_texture.extras

                texture_index = len(gltf.textures)
                gltf.textures.append(gltf_texture)

                self.gltf_id = texture_index

            self.texture_saved = True

        return self.gltf_id


class Deca3dMeshc:
    # The mesh is never stored in the gltf directly
    # The mesh stores it's accessors, buffer views, and buffers in the gltf when used
    # The mesh writes out it's support files (buffers) when used
    def __init__(self, v_path):
        self.v_path = v_path
        self.meshes = None

    def add_to_gltf(self, vfs: VfsDatabase, adf_db: AdfDatabase, db: Deca3dDatabase, gltf: pyg.GLTF2):
        if self.meshes is None:
            vfs.logger.log('Setup Meshc: {}'.format(self.v_path))
            mesh_adf = adf_db.read_node(vfs, vfs.nodes_where_match(v_path=self.v_path)[0])
            assert len(mesh_adf.table_instance) == 2
            # 0xea60065d - gz/hp, 0x7A2C9B73 - rg2, 0x6f841426 - hp (also)
            assert mesh_adf.table_instance[0].type_hash in {0xea60065d, 0x7A2C9B73, 0x6f841426}
            # 0x67b3a453 - gz, 0xe6834477 - hp, 0x0E1C0800 - rg2
            assert mesh_adf.table_instance[1].type_hash in {0x67b3a453, 0xe6834477, 0x0E1C0800}
            mesh_header = AmfMeshHeader(
                mesh_adf,
                mesh_adf.table_instance_full_values[0],
                merged_buffers=mesh_adf.table_instance[0].type_hash in {0x7A2C9B73})
            mesh_buffers = AmfMeshBuffers(
                mesh_adf,
                mesh_adf.table_instance_full_values[1],
                merged_buffers=mesh_adf.table_instance[1].type_hash in {0x0E1C0800})

            hrmesh_vpath = mesh_header.highLodPath
            hrmesh_vpath2 = remove_prefix_if_present(b'intermediate/', hrmesh_vpath)
            hrmesh_node = None

            hrmesh_nodes = vfs.nodes_where_match(v_path=hrmesh_vpath)
            if hrmesh_nodes:
                hrmesh_node = hrmesh_nodes[0]
            elif hrmesh_vpath2 is not None:
                hrmesh_nodes = vfs.nodes_where_match(v_path=hrmesh_vpath2)
                if hrmesh_nodes:
                    hrmesh_node = hrmesh_nodes[0]

            if hrmesh_node is not None:
                hrmesh_adf = adf_db.read_node(vfs, hrmesh_node)
                assert len(hrmesh_adf.table_instance) == 1
                # assert hrmesh_adf.table_instance[0].type_hash == 0x67b3a453
                hrmesh_buffers = AmfMeshBuffers(
                    hrmesh_adf,
                    hrmesh_adf.table_instance_full_values[0],
                    merged_buffers=mesh_adf.table_instance[1].type_hash in {0x0E1C0800})
                mesh_buffers.indexBuffers = mesh_buffers.indexBuffers + hrmesh_buffers.indexBuffers
                mesh_buffers.vertexBuffers = mesh_buffers.vertexBuffers + hrmesh_buffers.vertexBuffers

            # reformat buffers for GLTF
            amf_meshc_reformat(mesh_header, mesh_buffers)

            # process buffers
            index_buffer_fns = []
            index_buffer_ids = []
            vertex_buffer_fns = []
            vertex_buffer_ids = []

            for index, buffer in enumerate(mesh_buffers.indexBuffers):
                fn = self.v_path.decode('utf-8') + '.buffer_index_{:03}.bin'.format(index)
                if db.flat_file_layout:
                    fn = fn.replace('/', '_')
                fn_uri = os.path.join(db.resource_prefix_uri, fn)
                fn_abs = os.path.join(db.resource_prefix_abs, fn)
                if not os.path.isfile(fn_abs):
                    os.makedirs(os.path.dirname(fn_abs), exist_ok=True)
                    with open(fn_abs, 'wb') as f:
                        f.write(buffer.data)
                index_buffer_fns.append(fn_abs)
                index_buffer_ids.append(len(gltf.buffers))
                gltf.buffers.append(pyg.Buffer(uri=fn_uri, byteLength=os.stat(fn_abs).st_size))

            for index, buffer in enumerate(mesh_buffers.vertexBuffers):
                fn = self.v_path.decode('utf-8') + '.buffer_vertex_{:03}.bin'.format(index)
                if db.flat_file_layout:
                    fn = fn.replace('/', '_')
                fn_uri = os.path.join(db.resource_prefix_uri, fn)
                fn_abs = os.path.join(db.resource_prefix_abs, fn)
                if not os.path.isfile(fn_abs):
                    os.makedirs(os.path.dirname(fn_abs), exist_ok=True)
                    with open(fn_abs, 'wb') as f:
                        f.write(buffer.data)
                vertex_buffer_fns.append(fn_abs)
                vertex_buffer_ids.append(len(gltf.buffers))
                gltf.buffers.append(pyg.Buffer(uri=fn_uri, byteLength=os.stat(fn_abs).st_size))

            self.meshes = {}
            lod_group: AmfLodGroup
            for lod_group in mesh_header.lodGroups:
                vfs.logger.log('Exporting {}: LOD {}: Started'.format(self.v_path, lod_group.lodIndex))

                meshes = []
                mesh: AmfMesh
                for mesh in lod_group.meshes:
                    # Setup bufferViews: APEX streams are GLTF2's buffer views
                    index_stream_ids = []
                    buffer_view = pyg.BufferView()
                    buffer_view.buffer = index_buffer_ids[mesh.indexBufferIndex]
                    buffer_view.byteLength = mesh.indexCount * mesh.indexBufferStride
                    buffer_view.byteOffset = mesh.indexBufferOffset
                    # buffer_view.byteStride = mesh.indexBufferStride  # commented out accessor handles size
                    buffer_view.target = 34963  # ELEMENT_ARRAY_BUFFER #TODO
                    index_stream_ids.append(len(gltf.bufferViews))
                    gltf.bufferViews.append(buffer_view)

                    vertex_stream_ids = []
                    for idx in range(len(mesh.vertexBufferIndices)):
                        buffer_view = pyg.BufferView()
                        buffer_view.buffer = vertex_buffer_ids[mesh.vertexBufferIndices[idx]]
                        buffer_view.byteLength = mesh.vertexCount * mesh.vertexStreamStrides[idx]
                        buffer_view.byteOffset = mesh.vertexStreamOffsets[idx]
                        buffer_view.byteStride = mesh.vertexStreamStrides[idx]
                        buffer_view.target = 34962  # ARRAY_BUFFER #TODO
                        vertex_stream_ids.append(len(gltf.bufferViews))
                        gltf.bufferViews.append(buffer_view)

                    # Setup GLTF accessors
                    possibly_skin = False
                    accessors_streams = []
                    accessors_stream_map = {}
                    stream_attr: AmfStreamAttribute
                    for stream_attr in mesh.streamAttributes:
                        accessor = pyg.Accessor()
                        accessor.bufferView = vertex_stream_ids[stream_attr.streamIndex]
                        accessor.byteOffset = stream_attr.streamOffset
                        accessor.count = mesh.vertexCount
                        if stream_attr.format[1] == b'AmfFormat_R16G16B16_SNORM':
                            accessor.type = "VEC3"
                            accessor.componentType = pyg.SHORT
                            accessor.normalized = True
                        elif stream_attr.format[1] == b'AmfFormat_R16G16_SNORM':
                            accessor.type = "VEC2"
                            accessor.componentType = pyg.SHORT
                            accessor.normalized = True
                        elif stream_attr.format[1] == b'AmfFormat_R16G16_UNORM':
                            accessor.type = "VEC2"
                            accessor.componentType = pyg.UNSIGNED_SHORT
                            accessor.normalized = True
                        elif stream_attr.format[1] == b'AmfFormat_R16_SNORM':
                            accessor.type = "SCALAR"
                            accessor.componentType = pyg.SHORT
                            accessor.normalized = True
                        elif stream_attr.format[1] == b'AmfFormat_R32_UINT':
                            accessor.type = "SCALAR"
                            accessor.componentType = pyg.UNSIGNED_INT
                        elif stream_attr.format[1] == b'AmfFormat_R8G8B8A8_UNORM':
                            accessor.type = "VEC4"
                            accessor.componentType = pyg.UNSIGNED_BYTE
                            accessor.normalized = True
                        elif stream_attr.format[1] == b'AmfFormat_R8G8B8A8_UINT':
                            accessor.type = "VEC4"
                            accessor.componentType = pyg.UNSIGNED_BYTE
                        elif stream_attr.format[1] == b'AmfFormat_R16G16B16A16_SINT':
                            accessor.type = "VEC4"
                            accessor.componentType = pyg.SHORT
                        elif stream_attr.format[1] == b'AmfFormat_R32_UNIT_VEC_AS_FLOAT':
                            accessor.type = "SCALAR"
                            accessor.componentType = pyg.FLOAT
                        elif stream_attr.format[1] == b'AmfFormat_R32_R8G8B8A8_UNORM_AS_FLOAT':
                            accessor.type = "SCALAR"
                            accessor.componentType = pyg.FLOAT
                        elif stream_attr.format[1] == b'AmfFormat_R32_FLOAT':
                            accessor.type = "SCALAR"
                            accessor.componentType = pyg.FLOAT
                        elif stream_attr.format[1] == b'AmfFormat_R32G32_FLOAT':
                            accessor.type = "VEC2"
                            accessor.componentType = pyg.FLOAT
                        elif stream_attr.format[1] == b'AmfFormat_R32G32B32_FLOAT':
                            accessor.type = "VEC3"
                            accessor.componentType = pyg.FLOAT
                        elif stream_attr.format[1] == b'AmfFormat_R32G32B32A32_FLOAT':
                            accessor.type = "VEC4"
                            accessor.componentType = pyg.FLOAT
                        elif stream_attr.format[1] == b'DecaFormat_R32G32B32A32_FLOAT_P1':
                            accessor.type = "VEC4"
                            accessor.componentType = pyg.FLOAT
                        elif stream_attr.format[1] == b'DecaFormat_R32G32B32A32_FLOAT_N1':
                            accessor.type = "VEC4"
                            accessor.componentType = pyg.FLOAT
                        else:
                            raise NotImplementedError('Unknown Stream Format: {}'.format(stream_attr.format[1]))

                        if stream_attr.usage[1] == b'AmfUsage_Position':
                            accessor.min = list(stream_attr.min.astype(dtype=np.double))
                            accessor.max = list(stream_attr.max.astype(dtype=np.double))

                        if stream_attr.usage[1] in {b'AmfUsage_BoneIndex', b'AmfUsage_BoneWeight'}:
                            possibly_skin = True

                        # add accessor
                        accessors_stream_idx = len(gltf.accessors)
                        gltf.accessors.append(accessor)
                        accessors_streams.append(accessors_stream_idx)
                        asl = accessors_stream_map.get(stream_attr.usage[1], [])
                        asl.append(accessors_stream_idx)
                        accessors_stream_map[stream_attr.usage[1]] = asl

                    do_skin = \
                        mesh.meshProperties is not None and \
                        mesh.meshProperties.get('IsSkinnedMesh', 0) == 1 and \
                        len(mesh.boneIndexLookup) > 0

                    do_skin = do_skin or possibly_skin

                    submeshes = []
                    submesh: AmfSubMesh
                    for submesh in mesh.subMeshes:
                        # submesh index accessor
                        accessor = pyg.Accessor()
                        accessor.bufferView = index_stream_ids[0]
                        accessor.byteOffset = submesh.indexStreamOffset
                        accessor.count = submesh.indexCount
                        accessor.type = "SCALAR"
                        accessor.componentType = 5123  # UNSIGNED_SHORT

                        # add accessor
                        accessor_idx = len(gltf.accessors)
                        gltf.accessors.append(accessor)

                        prim = pyg.Primitive()
                        prim.indices = accessor_idx

                        prim.attributes = pyg.Attributes(
                            POSITION=_get_or_none(0, accessors_stream_map.get(b'AmfUsage_Position', [])),
                            TEXCOORD_0=_get_or_none(0, accessors_stream_map.get(b'AmfUsage_TextureCoordinate', [])),
                            TEXCOORD_1=_get_or_none(1, accessors_stream_map.get(b'AmfUsage_TextureCoordinate', [])),
                            NORMAL=_get_or_none(0, accessors_stream_map.get(b'AmfUsage_Normal', [])),
                            TANGENT=_get_or_none(0, accessors_stream_map.get(b'AmfUsage_Tangent', [])),
                            COLOR_0=_get_or_none(0, accessors_stream_map.get(b'AmfUsage_Color', [])),
                            JOINTS_0=_get_or_none(0, accessors_stream_map.get(b'AmfUsage_BoneIndex', [])),
                            WEIGHTS_0=_get_or_none(0, accessors_stream_map.get(b'AmfUsage_BoneWeight', [])),
                        )

                        # !!!!!! TEMPORARILY SAVE STRING HERE TO BE REPLACE BY MATERIAL FROM MODEL
                        prim.material = submesh.subMeshId

                        gltf_mesh = pyg.Mesh()
                        gltf_mesh.name = submesh.subMeshId.decode('utf-8')
                        gltf_mesh.primitives.append(prim)
                        submeshes.append(gltf_mesh)

                    meshes.append((submeshes, do_skin))
                self.meshes[lod_group.lodIndex] = meshes
                vfs.logger.log('Exporting {}: LOD {}: Complete'.format(self.v_path, lod_group.lodIndex))
        return self.meshes


class Deca3dModelc:
    # The model stores it's mesh with material info in the gltf when instantiated in node, only once.
    # The model stores it's material, texture info, ... in the gltf when used
    # The model writes out it's support files (textures) when used
    # The model creates a copy of the DecaMeshc mesh when it "loads" it meshc file
    def __init__(self, v_path, material_properties=None):
        self.v_path = v_path
        self.models = None
        self.material_properties = material_properties

    def add_to_gltf(self, vfs: VfsDatabase, adf_db: AdfDatabase, db: Deca3dDatabase, gltf: pyg.GLTF2):
        if self.models is None:
            vfs.logger.log('Setup Modelc: {}'.format(self.v_path))

            nodes = vfs.nodes_where_match(v_path=self.v_path)
            if len(nodes) == 0:
                # raise EDecaFileMissing('Not Mapped: {}'.format(self.v_path))
                vfs.logger.warning(f"{EDecaFileMissing('Not Mapped: {}'.format(self.v_path))}")
                return None

            node = nodes[0]
            model_adf = adf_db.read_node(vfs, node)
            model = AmfModel(model_adf, model_adf.table_instance_full_values[0])

            material_map = {}
            material: AmfMaterial
            for material in model.materials:
                if material.renderBlockId in {b'GeneralR2', b'Character', b'CarPaint'}:
                    # add textures
                    textures = []
                    for texture_vpath in material.textures:
                        textures.append(db.gltf_add_texture(gltf, texture_vpath))

                    # [0] diffused color ,
                    # [1] normal bump map ,
                    # [2] MPM? ,
                    # [4] emissive , UseEmissive & EmissiveTextureHasColor
                    # [17] color_mask , UseColorMask

                    # add material
                    gltf_material = pyg.Material()
                    gltf_material.name = material.name.decode('utf-8')

                    # normal bump map
                    tid = textures[1]
                    if tid is not None:
                        gltf_material.normalTexture = pyg.NormalMaterialTexture(index=tid)

                    if material.attributes.get('UseEmissive', False):
                        gltf_material.emissiveFactor = [1.0, 1.0, 1.0]
                        tid = textures[4]
                        if tid is not None:
                            gltf_material.emissiveTexture = pyg.TextureInfo(index=tid)
                    else:
                        gltf_material.emissiveFactor = [0.0, 0.0, 0.0]

                    use_spec_gloss = False
                    if use_spec_gloss:
                        mat_sg = {}
                        tid = textures[0]
                        if tid is not None:
                            mat_sg['diffuseTexture'] = pyg.TextureInfo(index=tid)
                        tid = textures[2]
                        if tid is not None:
                            mat_sg['specularGlossinessTexture'] = pyg.TextureInfo(index=tid)

                        gltf_material.extensions['KHR_materials_pbrSpecularGlossiness'] = mat_sg
                    else:
                        mat_mr = pyg.PbrMetallicRoughness()

                        tid = textures[0]
                        if tid is not None:
                            mat_mr.baseColorTexture = pyg.TextureInfo(index=tid)

                        if len(textures) >= 3:
                            tid = textures[2]
                            if tid is not None:
                                mat_mr.metallicRoughnessTexture = pyg.TextureInfo(index=tid)

                        mat_mr.roughnessFactor = 1.0
                        mat_mr.metallicFactor = 1.0

                        gltf_material.pbrMetallicRoughness = mat_mr

                    # FOR TESTING, need to figure out how to use colormask with gltf
                    # if material.attributes['UseColorMask']:
                    #     tid = textures[17]
                    #     if tid is not None:
                    #         mat_sg['diffuseTexture'] = pyg.TextureInfo(index=tid)

                    material_idx = len(gltf.materials)
                    gltf.materials.append(gltf_material)
                    material_map[material.name] = material_idx
                elif b'VegetationFoliage' == material.renderBlockId:
                    vfs.logger.log('Hacky version of RenderBlockId: {} Material Name: {}'.format(material.renderBlockId, material.name))
                    # add textures
                    textures = []
                    for texture_vpath in material.textures:
                        textures.append(db.gltf_add_texture(gltf, texture_vpath))

                    # [0] diffused color ,
                    # [1] normal bump map ,
                    # [2] ?
                    # [3] MPM? ,

                    # add material
                    gltf_material = pyg.Material()
                    gltf_material.name = material.name.decode('utf-8')

                    # normal bump map
                    tid = textures[1]
                    if tid is not None:
                        gltf_material.normalTexture = pyg.NormalMaterialTexture(index=tid)

                    gltf_material.emissiveFactor = [0.0, 0.0, 0.0]

                    use_spec_gloss = False
                    if use_spec_gloss:
                        mat_sg = {}
                        tid = textures[0]
                        if tid is not None:
                            mat_sg['diffuseTexture'] = pyg.TextureInfo(index=tid)
                        tid = textures[3]
                        if tid is not None:
                            mat_sg['specularGlossinessTexture'] = pyg.TextureInfo(index=tid)

                        gltf_material.extensions['KHR_materials_pbrSpecularGlossiness'] = mat_sg
                    else:
                        mat_mr = pyg.PbrMetallicRoughness()

                        tid = textures[0]
                        if tid is not None:
                            mat_mr.baseColorTexture = pyg.TextureInfo(index=tid)

                        tid = textures[3]
                        if tid is not None:
                            mat_mr.metallicRoughnessTexture = pyg.TextureInfo(index=tid)

                        mat_mr.roughnessFactor = 1.0
                        mat_mr.metallicFactor = 1.0

                        gltf_material.pbrMetallicRoughness = mat_mr

                    material_idx = len(gltf.materials)
                    gltf.materials.append(gltf_material)
                    material_map[material.name] = material_idx
                elif b'VegetationBark' == material.renderBlockId:
                    vfs.logger.log('Hacky version of RenderBlockId: {} Material Name: {}'.format(material.renderBlockId,
                                                                                                 material.name))
                    # add textures
                    textures = []
                    for texture_vpath in material.textures:
                        textures.append(db.gltf_add_texture(gltf, texture_vpath))

                    # [0] diffused color ,
                    # [1] normal bump map ,
                    # [2] MPM? ,
                    # ?

                    # add material
                    gltf_material = pyg.Material()
                    gltf_material.name = material.name.decode('utf-8')

                    # normal bump map
                    tid = textures[1]
                    if tid is not None:
                        gltf_material.normalTexture = pyg.NormalMaterialTexture(index=tid)

                    gltf_material.emissiveFactor = [0.0, 0.0, 0.0]

                    use_spec_gloss = False
                    if use_spec_gloss:
                        mat_sg = {}
                        tid = textures[0]
                        if tid is not None:
                            mat_sg['diffuseTexture'] = pyg.TextureInfo(index=tid)
                        tid = textures[2]
                        if tid is not None:
                            mat_sg['specularGlossinessTexture'] = pyg.TextureInfo(index=tid)

                        gltf_material.extensions['KHR_materials_pbrSpecularGlossiness'] = mat_sg
                    else:
                        mat_mr = pyg.PbrMetallicRoughness()

                        tid = textures[0]
                        if tid is not None:
                            mat_mr.baseColorTexture = pyg.TextureInfo(index=tid)

                        tid = textures[2]
                        if tid is not None:
                            mat_mr.metallicRoughnessTexture = pyg.TextureInfo(index=tid)

                        mat_mr.roughnessFactor = 1.0
                        mat_mr.metallicFactor = 1.0

                        gltf_material.pbrMetallicRoughness = mat_mr

                    material_idx = len(gltf.materials)
                    gltf.materials.append(gltf_material)
                    material_map[material.name] = material_idx
                else:
                    vfs.logger.log(f'Unhandled RenderBlockId: {material.renderBlockId} Material Name: {material.name}')

            meshes_all = db.gltf_add_meshc(gltf, model.mesh)
            meshes_new = {}
            for lod, meshes in meshes_all.items():
                ms = []
                for submeshes in meshes:
                    sms = []
                    for submesh in submeshes[0]:
                        mesh_new = db.gltf_finalize_mesh(submesh, material_map=material_map)
                        mesh_new_idx = len(gltf.meshes)
                        gltf.meshes.append(mesh_new)
                        sms.append(mesh_new_idx)
                    ms.append((sms, submeshes[1]))
                meshes_new[lod] = ms

            self.models = meshes_new

        return self.models


class Deca3dHkSkeleton:
    def __init__(self, v_path, scene):
        self.v_path = v_path
        self.scene = scene
        self.skeleton = None

    def add_to_gltf(self, vfs: VfsDatabase, adf_db: AdfDatabase, db: Deca3dDatabase, gltf: pyg.GLTF2):
        if self.skeleton is None:
            vfs.logger.log('Setup Modelc: {}'.format(self.v_path))

            # get baked skeleton filename
            v_path = self.v_path
            v_path = os.path.splitext(v_path)
            v_path = v_path[0] + b'.bsk'
            fn = v_path.decode('utf-8')
            if db.flat_file_layout:
                fn = fn.replace('/', '_')
            ppath_skel_uri = os.path.join(db.resource_prefix_uri, fn)
            ppath_skel_raw = os.path.join(db.resource_prefix_abs, fn)
            ppath_skel_xml = ppath_skel_raw + '.xml'

            if not os.path.isfile(ppath_skel_raw):
                vnodes = vfs.nodes_where_match(v_path=v_path)

                if len(vnodes) == 0:
                    raise EDecaFileMissing('Not Mapped: {}'.format(v_path))

                vnode = vnodes[0]
                with vfs.file_obj_from(vnode) as f:
                    buffer = f.read()

                dir_path = os.path.dirname(ppath_skel_raw)
                os.makedirs(dir_path, exist_ok=True)
                with open(ppath_skel_raw, 'wb') as f:
                    f.write(buffer)

            exe_path, exe_name = os.path.split(sys.argv[0])
            bin_path = os.path.join("./", exe_path, "..", "..", "..", "root", "bin")

            cmd = '{} {} {}'.format(
                os.path.join(bin_path, 'bin2xml'),
                ppath_skel_raw,
                ppath_skel_xml,
            )

            run_out = None

            if not os.path.isfile(ppath_skel_xml):
                run_out = subprocess.run(cmd, shell=True, capture_output=True)

            if not os.path.isfile(ppath_skel_xml):
                if run_out is None:
                    stdout = 'stdout MISSING'
                    stderr = 'stderr MISSING'
                else:
                    stdout = run_out.stdout
                    stderr = run_out.stderr

                raise EDecaFileMissing('Not Mapped: {}, CMD: {}, SO: {}, SE: {}'.format(ppath_skel_xml, cmd, stdout, stderr))

            # TODO this is a hack
            tree = ElementTree.parse(ppath_skel_xml)
            root = tree.getroot()

            skel = None
            for child in root[0]:
                if child.tag == 'hkobject' and child.attrib.get('class', '') == 'hkaSkeleton':
                    skel = child
                    break

            if skel is None:
                raise EDecaErrorParse('Error parsing: {}'.format(ppath_skel_xml))

            parents = []
            bone_info = []
            poses = []
            num_bones = 0
            for child in skel:
                if child.attrib['name'] == 'parentIndices':
                    txt = child.text
                    txt = txt.replace('\t', ' ').replace('\n', ' ').split(' ')
                    parents = [int(v) for v in txt if len(v) > 0]
                if child.attrib['name'] == 'bones':
                    num_bones = int(child.attrib['numelements'])
                    for i in range(num_bones):
                        bone_info.append([child[i][0].text, child[i][1].text, ])
                if child.attrib['name'] == 'referencePose':
                    txt = child.text.replace('\t', ' ').replace('\n', ' ').replace('(', ' ').replace(')', ' ')
                    txt = txt.split(' ')
                    poses = [float(v) for v in txt if len(v) > 0]

            poses = np.array(poses).reshape((num_bones, 10))
            bones = [[v0[0], v0[1], v1, (v2[0:3], v2[3:7], v2[7:10])] for v0, v1, v2 in zip(bone_info, parents, poses)]

            bone_nodes = []
            bone_inv_matrix = []
            for bi, bone in enumerate(bones):
                name = bone[0]
                pidx = bone[2]
                translate = bone[3][0]
                rotate = bone[3][1]
                scale = bone[3][2]
                bnode = pyg.Node()
                bnode_idx = len(gltf.nodes)
                gltf.nodes.append(bnode)

                # nodes are not connect to other hierchy so must be added to scene
                #   manually, so root nodes must be added manually
                if pidx < 0:
                    self.scene.nodes.append(bnode_idx)
                bone_nodes.append([bnode_idx, bnode])
                bnode.name = name
                bnode.translation = list(translate)
                bnode.rotation = list(rotate)
                bnode.scale = list(scale)
                if 0 <= pidx < len(bone_nodes):
                    bone_nodes[pidx][1].children.append(bnode_idx)

                m_translate = np.eye(4)
                m_rotate = np.eye(4)
                m_scale = np.eye(4)

                m_translate[0:3, 3] = translate
                m_rotate[0:3, 0:3] = sst.Rotation(rotate).as_matrix()
                m_scale[0, 0] = scale[0]
                m_scale[1, 1] = scale[1]
                m_scale[2, 2] = scale[2]

                b_matrix = m_translate @ m_rotate @ m_scale
                if 0 <= pidx < len(bone_nodes):
                    imatrix_parent = bone_inv_matrix[pidx]
                else:
                    imatrix_parent = np.eye(4)
                imatrix = np.linalg.inv(b_matrix) @ imatrix_parent
                bone_inv_matrix.append(imatrix)

            # write ibm matricies
            fn = ppath_skel_raw + '.ibm.dat'
            with open(fn, 'wb') as f:
                for mat in bone_inv_matrix:
                    mat2 = mat.astype(dtype=np.float32)
                    mat2 = mat2.transpose()
                    mat2_bytes = mat2.tobytes()
                    f.write(mat2_bytes)
                    # print(mat2)

            # setup accessor
            buffer = pyg.Buffer()
            buffer.uri = ppath_skel_uri + '.ibm.dat'
            buffer.byteLength = 16 * 4 * len(bone_inv_matrix)
            buffer_idx = len(gltf.buffers)
            gltf.buffers.append(buffer)

            buffer_view = pyg.BufferView()
            buffer_view.buffer = buffer_idx
            buffer_view.byteOffset = 0
            # buffer_view.byteStride = 16 * 4
            buffer_view.byteLength = 16 * 4 * len(bone_inv_matrix)
            buffer_view_idx = len(gltf.bufferViews)
            gltf.bufferViews.append(buffer_view)

            accessor = pyg.Accessor()
            accessor.bufferView = buffer_view_idx
            accessor.byteOffset = 0
            accessor.count = len(bone_inv_matrix)
            accessor.type = "MAT4"
            accessor.componentType = pyg.FLOAT

            accessor_idx = len(gltf.accessors)
            gltf.accessors.append(accessor)

            # create skin
            skin = pyg.Skin()
            skin_joints = [bone_info[0] for bone_info in bone_nodes]
            skin.name = os.path.basename(self.v_path.decode('utf-8')) + ".armature"
            skin.skeleton = skin_joints[0]
            skin.joints = skin_joints
            skin.inverseBindMatrices = accessor_idx
            skin_idx = len(gltf.skins)
            gltf.skins.append(skin)

            self.skeleton = (skin_idx, skin, bone_nodes)

        return self.skeleton


class DecaGltfScene:
    def __init__(self, deca_gltf, name=None):
        if isinstance(name, bytes):
            name = name.decode('utf-8')
        self.deca_gltf = deca_gltf
        self.index = None
        self.scene = pyg.Scene(name=name)

    def __enter__(self):
        self.deca_gltf.gltf_push(self)
        return self.scene

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.deca_gltf.gltf_pop(self)


class DecaGltfNode:
    def __init__(self, deca_gltf, name=None, matrix=None):
        if isinstance(name, bytes):
            name = name.decode('utf-8')
        self.deca_gltf = deca_gltf
        self.index = None
        self.node = pyg.Node(name=name, matrix=matrix)

    def __enter__(self):
        self.deca_gltf.gltf_push(self)
        return self.node

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.deca_gltf.gltf_pop(self)


class DecaGltf:
    def __init__(
            self, vfs: VfsDatabase, export_path, filename, lod=0,
            save_to_one_dir=False,
            flat_file_layout=False,
            include_skeleton=False,
            texture_format=None):
        self.vfs = vfs
        self.filename = filename
        self.lod = lod
        self.save_to_one_dir = save_to_one_dir
        self.flat_file_layout = flat_file_layout
        self.include_skeleton = include_skeleton
        if texture_format is None:
            self.texture_format = 'dds'
        else:
            self.texture_format = texture_format
        self.gltf = pyg.GLTF2()
        self.gltf.asset.version = "2.0"
        self.gltf.asset.generator = "DECA extractor"
        self.gltf.extensionsUsed.append('KHR_materials_pbrSpecularGlossiness')
        self.d_stack = []
        self.d_scene = DecaGltfScene(self, name='Scene0')

        if self.save_to_one_dir:
            self.export_path = os.path.join(export_path, filename + '.dir', 'model-lod_{}.gltf'.format(self.lod))
            self.resource_prefix_abs = os.path.join(export_path, filename + '.dir')
            self.resource_prefix_uri = ''
        else:
            self.export_path = os.path.join(export_path, filename + '-lod_{}.gltf'.format(self.lod))
            self.resource_prefix_abs = export_path
            self.resource_prefix_uri = ''
            dirs = os.path.dirname(filename)
            while len(dirs) > 0:
                self.resource_prefix_uri += '../'
                dirs = os.path.dirname(dirs)
        os.makedirs(os.path.dirname(self.export_path), exist_ok=True)

        self.db = Deca3dDatabase(
            self.vfs,
            self.resource_prefix_abs,
            self.resource_prefix_uri,
            self.flat_file_layout,
            self.texture_format)

    def gltf_save(self):
        assert self.gltf is not None
        assert len(self.d_stack) == 0
        self.gltf.save_json(self.export_path)

    def scene(self):
        return self.d_scene

    def gltf_push(self, item):
        if isinstance(item, DecaGltfScene):
            assert len(self.d_stack) == 0
            if item.index is None:
                item.index = len(self.gltf.scenes)
                self.gltf.scenes.append(item.scene)
                if item.index == 0:
                    self.gltf.scene = item.index

        elif isinstance(item, DecaGltfNode):
            assert len(self.d_stack) > 0  # at least scene has to be on stack
            assert item not in self.d_stack  # cannot already be on stack

            parent = self.d_stack[-1]
            assert isinstance(parent, DecaGltfNode) or isinstance(parent, DecaGltfScene)

            if item.index is None:
                item.index = len(self.gltf.nodes)
                self.gltf.nodes.append(item.node)

                if isinstance(parent, DecaGltfScene):
                    parent.scene.nodes.append(item.index)
                elif isinstance(parent, DecaGltfNode):
                    parent.node.children.append(item.index)

            if isinstance(parent, DecaGltfScene):
                assert item.index in parent.scene.nodes  # assert that is childen of parent
            elif isinstance(parent, DecaGltfNode):
                assert item.index in parent.node.children  # assert that is childen of parent

        self.d_stack.append(item)

    def gltf_pop(self, item):
        assert len(self.d_stack) > 0
        assert self.d_stack[-1] == item
        self.d_stack.pop(-1)

    def export_modelc(self, v_path, transform: Optional[Deca3dMatrix], material_properties=None, skeleton_raw_path=None):
        if transform is None:
            transform = Deca3dMatrix()

        self.vfs.logger.log('export_modelc: Started')
        # setup skeleton
        skeleton = None
        if self.include_skeleton and skeleton_raw_path is not None:
            skeleton = self.db.gltf_add_hk_skeleton(self.gltf, skeleton_raw_path, self.d_scene.scene)

        # setup materials
        meshes_all = self.db.gltf_add_modelc(
            self.gltf, v_path, material_properties=material_properties)

        if meshes_all is not None:
            with DecaGltfNode(self, name=os.path.basename(v_path), matrix=transform.col_major_list()):
                for mesh_info in meshes_all[self.lod]:
                    submeshes = mesh_info[0]

                    skin_idx = None
                    if mesh_info[1] and skeleton is not None:
                        skin_idx = skeleton[0]

                    for submesh in submeshes:
                        with DecaGltfNode(self) as mesh_node:
                            mesh_node.mesh = submesh
                            mesh_node.skin = skin_idx

        self.vfs.logger.log('export_modelc: Complete')
