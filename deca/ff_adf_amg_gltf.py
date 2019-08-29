import os
import copy
from deca.util import remove_prefix_if_present
from deca.ff_avtx import image_load
from deca.ff_adf import *
from deca.ff_adf_amf import *
import pygltflib as pyg


def _get_or_none(index, list_data):
    if index < len(list_data):
        return list_data[index]
    else:
        return None


class Deca3dDatabase:
    def __init__(self, vfs, export_dir):
        self.vfs = vfs
        self.export_dir = export_dir
        self.map_vpath_to_texture = {}
        self.map_vpath_to_meshc = {}
        self.map_vpath_to_modelc = {}

    def gltf_add_texture(self, gltf, vpath):
        item = self.map_vpath_to_texture.get(vpath, Deca3dTexture(vpath))
        self.map_vpath_to_texture[vpath] = item
        return item.add_to_gltf(self.vfs, self, gltf)

    def gltf_add_meshc(self, gltf, vpath):
        item = self.map_vpath_to_meshc.get(vpath, Deca3dMeshc(vpath))
        self.map_vpath_to_meshc[vpath] = item
        return item.add_to_gltf(self.vfs, self, gltf)

    def gltf_add_modelc(self, gltf, vpath):
        item = self.map_vpath_to_modelc.get(vpath, Deca3dModelc(vpath))
        self.map_vpath_to_modelc[vpath] = item
        return item.add_to_gltf(self.vfs, self, gltf)

    def gltf_finalize_mesh(self, mmap, mesh_org: pyg.Mesh):
        mesh = copy.deepcopy(mesh_org)
        p: pyg.Primitive
        for p in mesh.primitives:
            p.material = mmap.get(p.material, None)

        return mesh


class Deca3dTexture:
    def __init__(self, vpath):
        self.vpath = vpath
        self.gltf_id = None
        self.texture_saved = False

    def add_to_gltf(self, vfs, db: Deca3dDatabase, gltf: pyg.GLTF2):
        if not self.texture_saved:
            vfs.logger.log('Setup Texture: {}'.format(self.vpath))
            # dump textures
            texture_fn = None
            if len(self.vpath) > 0:
                texture_node = vfs.map_vpath_to_vfsnodes.get(self.vpath, [])
                if len(texture_node) > 0:
                    texture_node = texture_node[0]
                    ddsc = image_load(vfs, texture_node, save_raw_data=True)
                    npimp = ddsc.mips[0].pil_image()
                    texture_fn = self.vpath.decode('utf-8')
                    texture_fn = texture_fn.replace('/', '_') + '.png'
                    texture_fn_full = os.path.join(db.export_dir, texture_fn)
                    npimp.save(texture_fn_full)
                else:
                    vfs.logger.log('WARNING: Missing Texture file: {}'.format(self.vpath))

            if texture_fn is not None:
                gltf_image = pyg.Image()
                gltf_image.uri = texture_fn
                image_idx = len(gltf.images)
                gltf.images.append(gltf_image)

                gltf_texture = pyg.Texture()
                gltf_texture.source = image_idx
                # gltf_texture.sampler
                # gltf_texture.extras

                self.gltf_id = len(gltf.textures)
                gltf.textures.append(gltf_texture)

            self.texture_saved = True

        return self.gltf_id


class Deca3dMeshc:
    # The mesh is never stored in the gltf directly
    # The mesh stores it's accessors, buffer views, and buffers in the gltf when used
    # The mesh writes out it's support files (buffers) when used
    def __init__(self, vpath):
        self.vpath = vpath
        self.meshes = None

    def add_to_gltf(self, vfs, db: Deca3dDatabase, gltf: pyg.GLTF2):
        if self.meshes is None:
            vfs.logger.log('Setup Meshc: {}'.format(self.vpath))
            mesh_adf = adf_node_read(vfs, vfs.map_vpath_to_vfsnodes[self.vpath][0])
            assert len(mesh_adf.table_instance) == 2
            assert mesh_adf.table_instance[0].type_hash == 0xea60065d
            assert mesh_adf.table_instance[1].type_hash == 0x67b3a453
            mesh_header = AmfMeshHeader(mesh_adf, mesh_adf.table_instance_full_values[0])
            mesh_buffers = AmfMeshBuffers(mesh_adf, mesh_adf.table_instance_full_values[1])

            hrmesh_vpath = mesh_header.highLodPath
            hrmesh_vpath2 = remove_prefix_if_present(b'intermediate/', hrmesh_vpath)
            hrmesh_node = None
            if hrmesh_vpath in vfs.map_vpath_to_vfsnodes:
                hrmesh_node = vfs.map_vpath_to_vfsnodes[hrmesh_vpath][0]
            elif hrmesh_vpath2 is not None and hrmesh_vpath2 in vfs.map_vpath_to_vfsnodes:
                hrmesh_node = vfs.map_vpath_to_vfsnodes[hrmesh_vpath2][0]
            if hrmesh_node is not None:
                hrmesh_adf = adf_node_read(vfs, hrmesh_node)
                assert len(hrmesh_adf.table_instance) == 1
                assert hrmesh_adf.table_instance[0].type_hash == 0x67b3a453
                hrmesh_buffers = AmfMeshBuffers(hrmesh_adf, hrmesh_adf.table_instance_full_values[0])
                mesh_buffers.indexBuffers = mesh_buffers.indexBuffers + hrmesh_buffers.indexBuffers
                mesh_buffers.vertexBuffers = mesh_buffers.vertexBuffers + hrmesh_buffers.vertexBuffers

            # reformat buffers for GLTF
            amf_meshc_reformat(mesh_header, mesh_buffers)

            # process buffers
            index_buffer_fns = []
            index_buffer_ids = []
            vertex_buffer_fns = []
            vertex_buffer_ids = []

            for buffer in mesh_buffers.indexBuffers:
                index = len(gltf.buffers)
                fn = os.path.join(db.export_dir, 'buffer_index_{:03}.bin'.format(index))
                with open(fn, 'wb') as f:
                    f.write(buffer.data)
                index_buffer_fns.append(fn)
                index_buffer_ids.append(len(gltf.buffers))
                gltf.buffers.append(pyg.Buffer(
                    uri=os.path.basename(fn),
                    byteLength=os.stat(fn).st_size))

            for buffer in mesh_buffers.vertexBuffers:
                index = len(gltf.buffers)
                fn = os.path.join(db.export_dir, 'buffer_vertex_{:03}.bin'.format(index))
                with open(fn, 'wb') as f:
                    f.write(buffer.data)
                vertex_buffer_fns.append(fn)
                vertex_buffer_ids.append(len(gltf.buffers))
                gltf.buffers.append(pyg.Buffer(
                    uri=os.path.basename(fn),
                    byteLength=os.stat(fn).st_size))

            self.meshes = {}
            lod_group: AmfLodGroup
            for lod_group in mesh_header.lodGroups:
                vfs.logger.log('Exporting {}: LOD {}: Started'.format(self.vpath, lod_group.lodIndex))

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
                        elif stream_attr.format[1] == b'AmfFormat_R32G32B32A32_FLOAT_P1':
                            accessor.type = "VEC4"
                            accessor.componentType = pyg.FLOAT
                        elif stream_attr.format[1] == b'AmfFormat_R32G32B32A32_FLOAT_N1':
                            accessor.type = "VEC4"
                            accessor.componentType = pyg.FLOAT
                        else:
                            raise NotImplementedError('Unknown Stream Format: {}'.format(stream_attr.format[1]))

                        if stream_attr.usage[1] == b'AmfUsage_Position':
                            accessor.min = mesh_header.boundingBox.min
                            accessor.max = mesh_header.boundingBox.max

                        # add accessor
                        accessors_stream_idx = len(gltf.accessors)
                        gltf.accessors.append(accessor)
                        accessors_streams.append(accessors_stream_idx)
                        asl = accessors_stream_map.get(stream_attr.usage[1], [])
                        asl.append(accessors_stream_idx)
                        accessors_stream_map[stream_attr.usage[1]] = asl

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
                        )

                        # !!!!!! TEMPORARILY SAVE STRING HERE TO BE REPLACE BY MATERIAL FROM MODEL
                        prim.material = submesh.subMeshId

                        gltf_mesh = pyg.Mesh()
                        gltf_mesh.name = submesh.subMeshId.decode('utf-8')
                        gltf_mesh.primitives.append(prim)
                        submeshes.append(gltf_mesh)
                    meshes.append(submeshes)
                self.meshes[lod_group.lodIndex] = meshes
                vfs.logger.log('Exporting {}: LOD {}: Complete'.format(self.vpath, lod_group.lodIndex))
        return self.meshes


class Deca3dModelc:
    # The model stores it's mesh with material info in the gltf when instantiated in node, only once.
    # The model stores it's material, texture info, ... in the gltf when used
    # The model writes out it's support files (textures) when used
    # The model creates a copy of the DecaMeshc mesh when it "loads" it meshc file
    def __init__(self, vpath):
        self.vpath = vpath
        self.models = None

    def add_to_gltf(self, vfs, db: Deca3dDatabase, gltf: pyg.GLTF2):
        if self.models is None:
            vfs.logger.log('Setup Modelc: {}'.format(self.vpath))

            if self.vpath not in vfs.map_vpath_to_vfsnodes:
                raise EDecaFileMissing('Not Mapped: {}'.format(self.vpath))

            node = list(vfs.map_vpath_to_vfsnodes[self.vpath])

            if len(node) == 0:
                raise EDecaFileMissing('No Nodes: {}'.format(self.vpath))

            node = node[0]
            model_adf = adf_node_read(vfs, node)
            model = AmfModel(model_adf, model_adf.table_instance_full_values[0])

            material_map = {}
            material: AmfMaterial
            for material in model.materials:
                if b'GeneralR2' == material.renderBlockId:
                    # add textures
                    textures = []
                    for texture_vpath in material.textures:
                        textures.append(db.gltf_add_texture(gltf, texture_vpath))

                    # add material
                    gltf_material = pyg.Material()
                    gltf_material.name = material.name.decode('utf-8')

                    mat_sg = {}
                    tid = textures[0]
                    if tid is not None:
                        mat_sg['diffuseTexture'] = pyg.MaterialTexture(index=tid)
                    tid = textures[2]
                    if tid is not None:
                        mat_sg['specularGlossinessTexture'] = pyg.MaterialTexture(index=tid)
                    gltf_material.extensions['KHR_materials_pbrSpecularGlossiness'] = mat_sg

                    tid = textures[1]
                    if tid is not None:
                        gltf_material.normalTexture = pyg.MaterialTexture(index=tid)

                    if material.attributes['UseEmissive']:
                        gltf_material.emissiveFactor = [1.0, 1.0, 1.0]
                        tid = textures[4]
                        if tid is not None:
                            gltf_material.emissiveTexture = pyg.MaterialTexture(index=tid)
                    else:
                        gltf_material.emissiveFactor = [0.0, 0.0, 0.0]

                    material_idx = len(gltf.materials)
                    gltf.materials.append(gltf_material)
                    material_map[material.name] = material_idx
                else:
                    vfs.logger.log('Unhandled RenderBlockId: {} Material Name: {}'.format(material.renderBlockId, material.name))

            meshes_all = db.gltf_add_meshc(gltf, model.mesh)
            meshes_new = {}
            for lod, meshes in meshes_all.items():
                ms = []
                for submeshes in meshes:
                    sms = []
                    for submesh in submeshes:
                        mesh_new = db.gltf_finalize_mesh(material_map, submesh)
                        mesh_new_idx = len(gltf.meshes)
                        gltf.meshes.append(mesh_new)
                        sms.append(mesh_new_idx)
                    ms.append(sms)
                meshes_new[lod] = ms

            self.models = meshes_new

        return self.models


class DecaGltf:
    def __init__(self, vfs, export_path):
        self.vfs = vfs
        self.export_dir = export_path + '.dir'
        os.makedirs(self.export_dir, exist_ok=True)

        self.db = Deca3dDatabase(self.vfs, self.export_dir)
        self.lod = None
        self.gltf = None
        self.g_scene = None

    def gltf_create(self, lod):
        assert self.gltf is None
        self.lod = lod
        self.gltf = pyg.GLTF2()
        self.gltf.asset.version = "2.0"
        self.gltf.asset.generator = "DECA extractor"
        self.g_scene = pyg.Scene()
        self.gltf.scene = len(self.gltf.scenes)
        self.gltf.scenes.append(self.g_scene)

    def gltf_save(self):
        assert self.gltf is not None
        fn = os.path.join(self.export_dir, 'model-lod_{}.gltf'.format(self.lod))
        self.gltf.save_json(fn)
        self.lod = None
        self.gltf = None
        self.g_scene = None

    def export_modelc(self, vpath, transform):
        self.vfs.logger.log('export_modelc: Started')
        # setup materials
        meshes_all = self.db.gltf_add_modelc(self.gltf, vpath)
        model_node = pyg.Node()
        model_node.matrix = transform
        for submeshes in meshes_all[self.lod]:
            for submesh in submeshes:
                mesh_node = pyg.Node()
                mesh_node.mesh = submesh
                mesh_node_idx = len(self.gltf.nodes)
                self.gltf.nodes.append(mesh_node)
                model_node.children.append(mesh_node_idx)

        model_node_idx = len(self.gltf.nodes)
        self.gltf.nodes.append(model_node)
        self.g_scene.nodes.append(model_node_idx)
        self.vfs.logger.log('export_modelc: Complete')
