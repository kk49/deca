import pprint
from deca.ff_adf import *
from deca.ff_types import FTYPE_ADF_BARE
from deca.ff_avtx import image_load
from deca.xlsxwriter_hack import DecaWorkBook
from deca.util import remove_prefix_if_present
from deca.ff_adf_amf import *
import pygltflib as pyg


def buffer_read(f):
    buffer = b''
    while True:
        v = f.read(16 * 1024 * 1024)
        if len(v) == 0:
            break
        buffer = buffer + v

    return buffer


def adf_node_read(vfs, node):
    with ArchiveFile(vfs.file_obj_from(node)) as f:
        buffer = buffer_read(f)
    if node.ftype == FTYPE_ADF_BARE:
        adf = vfs.adf_db.load_adf_bare(buffer, node.adf_type, node.offset, node.size_u)
    else:
        adf = vfs.adf_db.load_adf(buffer)

    return adf


def adf_export(vfs, node, export_path, allow_overwrite=False):
    adf = adf_node_read(vfs, node)

    if adf is not None:
        if len(adf.table_instance) == 1:
            if adf.table_instance[0].type_hash == 0x0B73315D:
                fn = export_path + '.xlsx'

                if not allow_overwrite and os.path.exists(fn):
                    raise EDecaFileExists(fn)

                src = adf.table_instance_values[0]
                book = DecaWorkBook(fn)

                cell_formats = []
                for att in src['Attribute']:
                    fg_color = src['ColorData'][att['FGColorIndex'] - 1]
                    bg_color = src['ColorData'][att['BGColorIndex'] - 1]
                    fmt = book.add_format()
                    # fmt.set_bg_color('#{:06X}'.format(bg_color))
                    # fmt.set_font_color('#{:06X}'.format(fg_color))
                    cell_formats.append(fmt)

                for srcw in src['Sheet']:
                    cols = srcw['Cols']
                    rows = srcw['Rows']
                    name = srcw['Name']
                    cellindex = srcw['CellIndex']
                    worksheet = book.add_worksheet(name.decode('utf-8'))
                    for i in range(rows):
                        for j in range(cols):
                            r = i
                            c = j

                            cidx = cellindex[j + cols * i]
                            cdata = src['Cell'][cidx]

                            ctype = cdata['Type']
                            didx = cdata['DataIndex']
                            aidx = cdata['AttributeIndex']
                            cell_format = cell_formats[aidx]
                            if ctype == 0:
                                if didx < len(src['BoolData']):
                                    worksheet.write_boolean(r, c, src['BoolData'][didx], cell_format=cell_format)
                                else:
                                    # worksheet.write_string(r, c, 'Missing BoolData {}'.format(didx), cell_format=cell_format)
                                    pass
                            elif ctype == 1:
                                if didx < len(src['StringData']):
                                    worksheet.write_string(r, c, src['StringData'][didx].decode('utf-8'), cell_format=cell_format)
                                else:
                                    # worksheet.write_string(r, c, 'Missing StringData {}'.format(didx), cell_format=cell_format)
                                    pass
                            elif ctype == 2:
                                if didx < len(src['ValueData']):
                                    worksheet.write_number(r, c, src['ValueData'][didx], cell_format=cell_format)
                                else:
                                    # worksheet.write_string(r, c, 'Missing ValueData {}'.format(didx), cell_format=cell_format)
                                    pass
                            else:
                                raise NotImplemented('Unhandled Cell Type {}'.format(ctype))

                book.close()
            elif adf.table_instance[0].type_hash == 0xf7c20a69:  # AmfModel
                model_dir = fn = export_path + '.dir'
                os.makedirs(model_dir, exist_ok=True)
                model_adf = adf
                model = AmfModel(model_adf, model_adf.table_instance_full_values[0])

                # process .meshc and .hrmeshc file
                mesh_adf = adf_node_read(vfs, vfs.map_vpath_to_vfsnodes[model.mesh][0])
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
                gltf_amf_reformat_buffers(model, mesh_header, mesh_buffers)

                # process buffers and textures
                index_buffer_fns = []
                vertex_buffer_fns = []

                for buffer in mesh_buffers.indexBuffers:
                    fn = os.path.join(model_dir, 'buffer_index_{:03}.bin'.format(len(index_buffer_fns)))
                    index_buffer_fns.append(fn)
                    with open(fn, 'wb') as f:
                        f.write(buffer.data)
                for buffer in mesh_buffers.vertexBuffers:
                    fn = os.path.join(model_dir, 'buffer_vertex_{:03}.bin'.format(len(vertex_buffer_fns)))
                    vertex_buffer_fns.append(fn)
                    with open(fn, 'wb') as f:
                        f.write(buffer.data)

                # dump textures
                text_vpath_map = {}
                material_texture_fns = []
                for material in model.materials:
                    texture_fns = []
                    for texture_vpath in material.textures:
                        texture_fn = None
                        if len(texture_vpath) > 0:
                            texture_node = vfs.map_vpath_to_vfsnodes.get(texture_vpath, [])
                            if len(texture_node) > 0:
                                texture_node = texture_node[0]
                                ddsc = image_load(vfs, texture_node, save_raw_data=True)
                                npimp = ddsc.mips[0].pil_image()
                                texture_fn = texture_vpath.decode('utf-8')
                                texture_fn = texture_fn.replace('/', '_') + '.png'
                                text_vpath_map[texture_vpath] = texture_fn
                                texture_fn = os.path.join(model_dir, texture_fn)
                                npimp.save(texture_fn)
                            else:
                                print('WARNING: Missing Texture file: {}'.format(texture_vpath))
                        texture_fns.append(texture_fn)
                    material_texture_fns.append(texture_fns)

                # process model/mesh

                # add buffers
                buffer_list = []
                index_buffer_ids = []
                for buffer_fn in index_buffer_fns:
                    index_buffer_ids.append(len(buffer_list))
                    buffer_list.append(buffer_fn)

                vertex_buffer_ids = []
                for buffer_fn in vertex_buffer_fns:
                    vertex_buffer_ids.append(len(buffer_list))
                    buffer_list.append(buffer_fn)

                print('Exporting: Started')
                lod_group: AmfLodGroup
                for lod_group in mesh_header.lodGroups:
                    print('Exporting: LOD {}: Started'.format(model.lodSlots[lod_group.lodIndex]))
                    gltf = pyg.GLTF2()
                    gltf.asset.version = "2.0"
                    gltf.asset.generator = "DECA extractor"

                    for buffer in buffer_list:
                        gltf.buffers.append(pyg.Buffer(
                            uri=os.path.basename(buffer),
                            byteLength=os.stat(buffer).st_size))

                    # setup materials
                    tex_map = {}
                    material_map = {}
                    material: AmfMaterial
                    for material in model.materials:
                        if b'GeneralR2' == material.renderBlockId:
                            # add textures
                            for texture_vpath in material.textures:
                                if len(texture_vpath) > 0 and texture_vpath not in tex_map:
                                    texture_fn = text_vpath_map[texture_vpath]
                                    gltf_image = pyg.Image()
                                    gltf_image.uri = texture_fn
                                    image_idx = len(gltf.images)
                                    gltf.images.append(gltf_image)

                                    gltf_texture = pyg.Texture()
                                    gltf_texture.source = image_idx
                                    # gltf_texture.sampler
                                    # gltf_texture.extras

                                    texture_idx = len(gltf.textures)
                                    gltf.textures.append(gltf_texture)
                                    tex_map[texture_vpath] = texture_idx

                            # add material
                            gltf_material = pyg.Material()
                            gltf_material.name = material.name.decode('utf-8')
                            gltf_material.pbrMetallicRoughness = pyg.PbrMetallicRoughness()

                            gltf_material.pbrMetallicRoughness.baseColorTexture = pyg.MaterialTexture(index=tex_map[material.textures[0]])
                            gltf_material.normalTexture = pyg.MaterialTexture(index=tex_map[material.textures[1]])
                            gltf_material.occlusionTexture = pyg.MaterialTexture(index=tex_map[material.textures[2]])
                            if material.attributes['UseEmissive']:
                                gltf_material.emissiveTexture = pyg.MaterialTexture(index=tex_map[material.textures[4]])

                            material_idx = len(gltf.materials)
                            gltf.materials.append(gltf_material)
                            material_map[material.name] = material_idx
                        else:
                            print('Unhandled RenderBlockId: {} Material Name: {}'.format(material.renderBlockId, material.name))

                    # setup scene
                    lod_scene = pyg.Scene()

                    mesh_node = pyg.Node()
                    mesh_node.name = 'root-node-lodIndex-{:02}'.format(model.lodSlots[lod_group.lodIndex])

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
                                accessor.componentType = 5122  # (SHORT)
                                accessor.normalized = True
                            elif stream_attr.format[1] == b'AmfFormat_R16G16_SNORM':
                                accessor.type = "VEC2"
                                accessor.componentType = 5122  # (SHORT)
                                accessor.normalized = True
                            elif stream_attr.format[1] == b'AmfFormat_R16G16_UNORM':
                                accessor.type = "VEC2"
                                accessor.componentType = 5123  # (UNSIGNED_SHORT)
                                accessor.normalized = True
                            elif stream_attr.format[1] == b'AmfFormat_R16_SNORM':
                                accessor.type = "SCALAR"
                                accessor.componentType = 5122  # (SHORT)
                                accessor.normalized = True
                            elif stream_attr.format[1] == b'AmfFormat_R8G8B8A8_UNORM':
                                accessor.type = "VEC4"
                                accessor.componentType = 5121  # (UNSIGNED_BYTE)
                                accessor.normalized = True
                            elif stream_attr.format[1] == b'AmfFormat_R8G8B8A8_UINT':
                                accessor.type = "VEC4"
                                accessor.componentType = 5121  # (UNSIGNED_BYTE)
                            elif stream_attr.format[1] == b'AmfFormat_R32_UNIT_VEC_AS_FLOAT':
                                accessor.type = "SCALAR"
                                accessor.componentType = 5126  # (FLOAT)
                            elif stream_attr.format[1] == b'AmfFormat_R32_R8G8B8A8_UNORM_AS_FLOAT':
                                accessor.type = "SCALAR"
                                accessor.componentType = 5126  # (FLOAT)
                            elif stream_attr.format[1] == b'AmfFormat_R32_FLOAT':
                                accessor.type = "SCALAR"
                                accessor.componentType = 5126  # (FLOAT)
                            elif stream_attr.format[1] == b'AmfFormat_R32G32_FLOAT':
                                accessor.type = "VEC2"
                                accessor.componentType = 5126  # (FLOAT)
                            elif stream_attr.format[1] == b'AmfFormat_R32G32B32_FLOAT':
                                accessor.type = "VEC3"
                                accessor.componentType = 5126  # (FLOAT)
                            elif stream_attr.format[1] == b'AmfFormat_R32G32B32A32_FLOAT_P1':
                                accessor.type = "VEC4"
                                accessor.componentType = 5126  # (FLOAT)
                            elif stream_attr.format[1] == b'AmfFormat_R32G32B32A32_FLOAT_N1':
                                accessor.type = "VEC4"
                                accessor.componentType = 5126  # (FLOAT)
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

                        submesh: AmfSubMesh
                        for submesh in mesh.subMeshes:
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
                            prim.material = material_map.get(submesh.subMeshId, None)

                            def get_or_none(idx, ldata):
                                if idx < len(ldata):
                                    return ldata[idx]
                                else:
                                    return None

                            prim.attributes = pyg.Attributes(
                                POSITION=get_or_none(0, accessors_stream_map.get(b'AmfUsage_Position', [])),
                                TEXCOORD_0=get_or_none(0, accessors_stream_map.get(b'AmfUsage_TextureCoordinate', [])),
                                TEXCOORD_1=get_or_none(1, accessors_stream_map.get(b'AmfUsage_TextureCoordinate', [])),
                                NORMAL=get_or_none(0, accessors_stream_map.get(b'AmfUsage_Normal', [])),
                                TANGENT=get_or_none(0, accessors_stream_map.get(b'AmfUsage_Tangent', [])),
                                COLOR_0=get_or_none(0, accessors_stream_map.get(b'AmfUsage_Color', [])),
                            )

                            gltf_mesh = pyg.Mesh()
                            gltf_mesh.name = submesh.subMeshId.decode('utf-8')
                            gltf_mesh.primitives.append(prim)
                            mesh_idx = len(gltf.meshes)
                            gltf.meshes.append(gltf_mesh)

                            submesh_node = pyg.Node()
                            submesh_node.name = 'node-{}'.format(gltf_mesh.name)
                            submesh_node.mesh = mesh_idx
                            submesh_node_idx = len(gltf.nodes)
                            gltf.nodes.append(submesh_node)

                            mesh_node.children.append(submesh_node_idx)

                    # add node
                    mesh_node_idx = len(gltf.nodes)
                    gltf.nodes.append(mesh_node)

                    lod_scene.nodes.append(mesh_node_idx)

                    # add scene
                    gltf.scenes.append(lod_scene)
                    gltf.scene = 0
                    fn = os.path.join(model_dir, 'model-lod_{}.gltf'.format(model.lodSlots[lod_group.lodIndex]))
                    gltf.save_json(fn)
                    print('Exporting: LOD {}: Complete'.format(model.lodSlots[lod_group.lodIndex]))
                print('Exporting: Complete')

            else:
                fn = export_path + '.txt'

                if not allow_overwrite and os.path.exists(fn):
                    raise EDecaFileExists(fn)

                s = adf.dump_to_string()

                with open(fn, 'wt') as f:
                    f.write(s)
