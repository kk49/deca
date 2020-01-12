from deca.kaitai.gfx import Gfx
import os


prefix = '/home/krys/prj/work/gz/extracted/'
for file in os.listdir(prefix):
    if file.endswith('.dat'):
        print(file)
        gfx = Gfx.from_file(os.path.join(prefix, file))

        for tag in gfx.zlib_body.tags:
            print(f'  {tag.record_header.tag_type}')
            if Gfx.TagType.gfx_exporter_info == tag.record_header.tag_type:
                print(f'    name = {tag.tag_body.name}')
            elif Gfx.TagType.gfx_define_external_image == tag.record_header.tag_type:
                print(f'    file_name = {tag.tag_body.file_name}')
            elif Gfx.TagType.gfx_define_external_image2 == tag.record_header.tag_type:
                print(f'    file_name = {tag.tag_body.file_name}')
            elif Gfx.TagType.import_assets2 == tag.record_header.tag_type:
                print(f'    url = {tag.tag_body.url}')
