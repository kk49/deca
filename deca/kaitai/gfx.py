# This is a generated file! Please edit source .ksy file and use kaitai-struct-compiler to rebuild

from pkg_resources import parse_version
from kaitaistruct import __version__ as ks_version, KaitaiStruct, KaitaiStream, BytesIO
from enum import Enum
import zlib


if parse_version(ks_version) < parse_version('0.7'):
    raise Exception("Incompatible Kaitai Struct Python API: 0.7 or later is required, but you have %s" % (ks_version))

class Gfx(KaitaiStruct):
    """First pass at a parser for ScaleForm GFX files.
    https://help.autodesk.com/view/SCLFRM/ENU/?guid=__scaleform_help_flash_support_controltags_html
    
    .. seealso::
       Source - https://www.adobe.com/content/dam/acom/en/devnet/pdf/swf-file-format-spec.pdf
    """

    class Compressions(Enum):
        zlib = 67
        none = 70
        lzma = 90

    class TagType(Enum):
        end_of_file = 0
        show_frame = 1
        define_shape = 2
        free_character = 3
        place_object = 4
        remove_object = 5
        set_background_color = 9
        define_sound = 14
        define_shape2 = 22
        place_object2 = 26
        remove_object2 = 28
        define_shape3 = 32
        define_edit_text = 37
        define_sprite = 39
        frame_label = 43
        define_morph_shape = 46
        export_assets = 56
        script_limits = 65
        file_attributes = 69
        place_object3 = 70
        import_assets2 = 71
        define_font_info3 = 73
        define_text_info = 74
        define_font3 = 75
        symbol_class = 76
        metadata = 77
        define_scaling_grid = 78
        do_abc = 82
        define_shape5 = 83
        define_scene_and_frame_label_data = 86
        gfx_exporter_info = 1000
        gfx_define_external_image = 1001
        gfx_font_texture_info = 1002
        gfx_define_external_gradient_image = 1003
        gfx_define_gradient_map = 1004
        gfx_define_compacted_font = 1005
        gfx_define_external_sound = 1006
        gfx_define_external_stream_sound = 1007
        gfx_define_sub_image = 1008
        gfx_define_external_image2 = 1009
    def __init__(self, _io, _parent=None, _root=None):
        self._io = _io
        self._parent = _parent
        self._root = _root if _root else self
        self._read()

    def _read(self):
        self.compression = self._root.Compressions(self._io.read_u1())
        self.signature = self._io.ensure_fixed_contents(b"\x46\x58")
        self.version = self._io.read_u1()
        self.len_file = self._io.read_u4le()
        if self.compression == self._root.Compressions.none:
            self._raw_plain_body = self._io.read_bytes_full()
            io = KaitaiStream(BytesIO(self._raw_plain_body))
            self.plain_body = self._root.SwfBody(io, self, self._root)

        if self.compression == self._root.Compressions.zlib:
            self._raw__raw_zlib_body = self._io.read_bytes_full()
            self._raw_zlib_body = zlib.decompress(self._raw__raw_zlib_body)
            io = KaitaiStream(BytesIO(self._raw_zlib_body))
            self.zlib_body = self._root.SwfBody(io, self, self._root)


    class Rgb(KaitaiStruct):
        def __init__(self, _io, _parent=None, _root=None):
            self._io = _io
            self._parent = _parent
            self._root = _root if _root else self
            self._read()

        def _read(self):
            self.r = self._io.read_u1()
            self.g = self._io.read_u1()
            self.b = self._io.read_u1()


    class DoAbcBody(KaitaiStruct):
        def __init__(self, _io, _parent=None, _root=None):
            self._io = _io
            self._parent = _parent
            self._root = _root if _root else self
            self._read()

        def _read(self):
            self.flags = self._io.read_u4le()
            self.name = (self._io.read_bytes_term(0, False, True, True)).decode(u"ASCII")
            self.abcdata = self._io.read_bytes_full()


    class SwfBody(KaitaiStruct):
        def __init__(self, _io, _parent=None, _root=None):
            self._io = _io
            self._parent = _parent
            self._root = _root if _root else self
            self._read()

        def _read(self):
            self.rect = self._root.Rect(self._io, self, self._root)
            self.frame_rate = self._io.read_u2le()
            self.frame_count = self._io.read_u2le()
            self.tags = []
            i = 0
            while True:
                _ = self._root.Tag(self._io, self, self._root)
                self.tags.append(_)
                if _.record_header.tag_type == self._root.TagType.end_of_file:
                    break
                i += 1


    class Rect(KaitaiStruct):
        def __init__(self, _io, _parent=None, _root=None):
            self._io = _io
            self._parent = _parent
            self._root = _root if _root else self
            self._read()

        def _read(self):
            self.b1 = self._io.read_u1()
            self.skip = self._io.read_bytes(self.num_bytes)

        @property
        def num_bits(self):
            if hasattr(self, '_m_num_bits'):
                return self._m_num_bits if hasattr(self, '_m_num_bits') else None

            self._m_num_bits = (self.b1 >> 3)
            return self._m_num_bits if hasattr(self, '_m_num_bits') else None

        @property
        def num_bytes(self):
            if hasattr(self, '_m_num_bytes'):
                return self._m_num_bytes if hasattr(self, '_m_num_bytes') else None

            self._m_num_bytes = (((self.num_bits * 4) - 3) + 7) // 8
            return self._m_num_bytes if hasattr(self, '_m_num_bytes') else None


    class Tag(KaitaiStruct):
        def __init__(self, _io, _parent=None, _root=None):
            self._io = _io
            self._parent = _parent
            self._root = _root if _root else self
            self._read()

        def _read(self):
            self.record_header = self._root.RecordHeader(self._io, self, self._root)
            _on = self.record_header.tag_type
            if _on == self._root.TagType.set_background_color:
                self._raw_tag_body = self._io.read_bytes(self.record_header.len)
                io = KaitaiStream(BytesIO(self._raw_tag_body))
                self.tag_body = self._root.Rgb(io, self, self._root)
            elif _on == self._root.TagType.script_limits:
                self._raw_tag_body = self._io.read_bytes(self.record_header.len)
                io = KaitaiStream(BytesIO(self._raw_tag_body))
                self.tag_body = self._root.ScriptLimitsBody(io, self, self._root)
            elif _on == self._root.TagType.define_sound:
                self._raw_tag_body = self._io.read_bytes(self.record_header.len)
                io = KaitaiStream(BytesIO(self._raw_tag_body))
                self.tag_body = self._root.DefineSoundBody(io, self, self._root)
            elif _on == self._root.TagType.export_assets:
                self._raw_tag_body = self._io.read_bytes(self.record_header.len)
                io = KaitaiStream(BytesIO(self._raw_tag_body))
                self.tag_body = self._root.SymbolClassBody(io, self, self._root)
            elif _on == self._root.TagType.symbol_class:
                self._raw_tag_body = self._io.read_bytes(self.record_header.len)
                io = KaitaiStream(BytesIO(self._raw_tag_body))
                self.tag_body = self._root.SymbolClassBody(io, self, self._root)
            elif _on == self._root.TagType.gfx_exporter_info:
                self._raw_tag_body = self._io.read_bytes(self.record_header.len)
                io = KaitaiStream(BytesIO(self._raw_tag_body))
                self.tag_body = self._root.GfxExporterInfoBody(io, self, self._root)
            elif _on == self._root.TagType.import_assets2:
                self._raw_tag_body = self._io.read_bytes(self.record_header.len)
                io = KaitaiStream(BytesIO(self._raw_tag_body))
                self.tag_body = self._root.ImportAssets2Body(io, self, self._root)
            elif _on == self._root.TagType.do_abc:
                self._raw_tag_body = self._io.read_bytes(self.record_header.len)
                io = KaitaiStream(BytesIO(self._raw_tag_body))
                self.tag_body = self._root.DoAbcBody(io, self, self._root)
            elif _on == self._root.TagType.gfx_define_external_image:
                self._raw_tag_body = self._io.read_bytes(self.record_header.len)
                io = KaitaiStream(BytesIO(self._raw_tag_body))
                self.tag_body = self._root.GfxDefineExternalImageBody(io, self, self._root)
            elif _on == self._root.TagType.gfx_define_external_image2:
                self._raw_tag_body = self._io.read_bytes(self.record_header.len)
                io = KaitaiStream(BytesIO(self._raw_tag_body))
                self.tag_body = self._root.GfxDefineExternalImage2Body(io, self, self._root)
            else:
                self.tag_body = self._io.read_bytes(self.record_header.len)


    class SymbolClassBody(KaitaiStruct):
        def __init__(self, _io, _parent=None, _root=None):
            self._io = _io
            self._parent = _parent
            self._root = _root if _root else self
            self._read()

        def _read(self):
            self.num_symbols = self._io.read_u2le()
            self.symbols = [None] * (self.num_symbols)
            for i in range(self.num_symbols):
                self.symbols[i] = self._root.SymbolClassBody.Symbol(self._io, self, self._root)


        class Symbol(KaitaiStruct):
            def __init__(self, _io, _parent=None, _root=None):
                self._io = _io
                self._parent = _parent
                self._root = _root if _root else self
                self._read()

            def _read(self):
                self.tag = self._io.read_u2le()
                self.name = (self._io.read_bytes_term(0, False, True, True)).decode(u"ASCII")



    class DefineSoundBody(KaitaiStruct):

        class SamplingRates(Enum):
            rate_5_5_khz = 0
            rate_11_khz = 1
            rate_22_khz = 2
            rate_44_khz = 3

        class Bps(Enum):
            sound_8_bit = 0
            sound_16_bit = 1

        class Channels(Enum):
            mono = 0
            stereo = 1
        def __init__(self, _io, _parent=None, _root=None):
            self._io = _io
            self._parent = _parent
            self._root = _root if _root else self
            self._read()

        def _read(self):
            self.id = self._io.read_u2le()
            self.format = self._io.read_bits_int(4)
            self.sampling_rate = self._root.DefineSoundBody.SamplingRates(self._io.read_bits_int(2))
            self.bits_per_sample = self._root.DefineSoundBody.Bps(self._io.read_bits_int(1))
            self.num_channels = self._root.DefineSoundBody.Channels(self._io.read_bits_int(1))
            self._io.align_to_byte()
            self.num_samples = self._io.read_u4le()


    class GfxExporterInfoBody(KaitaiStruct):
        def __init__(self, _io, _parent=None, _root=None):
            self._io = _io
            self._parent = _parent
            self._root = _root if _root else self
            self._read()

        def _read(self):
            self.version = self._io.read_u2le()
            if self.version >= 266:
                self.flags = self._io.read_u4le()

            self.bitmap_format = self._io.read_u2le()
            self.prefix_len = self._io.read_u1()
            self.prefix = (self._io.read_bytes(self.prefix_len)).decode(u"ASCII")
            self.name_len = self._io.read_u1()
            self.name = (self._io.read_bytes(self.name_len)).decode(u"ASCII")
            self.extra = self._io.read_bytes_full()


    class GfxDefineExternalImageBody(KaitaiStruct):
        def __init__(self, _io, _parent=None, _root=None):
            self._io = _io
            self._parent = _parent
            self._root = _root if _root else self
            self._read()

        def _read(self):
            self.character_id = self._io.read_u2le()
            self.bitmap_format = self._io.read_u2le()
            self.target_width = self._io.read_u2le()
            self.target_height = self._io.read_u2le()
            self.file_name_len = self._io.read_u1()
            self.file_name = (self._io.read_bytes(self.file_name_len)).decode(u"ASCII")
            self.extra = self._io.read_bytes_full()


    class GfxDefineExternalImage2Body(KaitaiStruct):
        def __init__(self, _io, _parent=None, _root=None):
            self._io = _io
            self._parent = _parent
            self._root = _root if _root else self
            self._read()

        def _read(self):
            self.character_id = self._io.read_u4le()
            self.bitmap_format = self._io.read_u2le()
            self.target_width = self._io.read_u2le()
            self.target_height = self._io.read_u2le()
            self.export_name_len = self._io.read_u1()
            self.export_name = (self._io.read_bytes(self.export_name_len)).decode(u"ASCII")
            self.file_name_len = self._io.read_u1()
            self.file_name = (self._io.read_bytes(self.file_name_len)).decode(u"ASCII")
            self.extra = self._io.read_bytes_full()


    class ImportAssets2Body(KaitaiStruct):
        def __init__(self, _io, _parent=None, _root=None):
            self._io = _io
            self._parent = _parent
            self._root = _root if _root else self
            self._read()

        def _read(self):
            self.url = (self._io.read_bytes_term(0, False, True, True)).decode(u"ASCII")
            self.download_now = self._io.read_u1()
            self.has_digest = self._io.read_u1()
            if self.has_digest == 1:
                self.sha1 = self._io.read_bytes(20)

            self.num_symbols = self._io.read_u2le()
            self.symbols = [None] * (self.num_symbols)
            for i in range(self.num_symbols):
                self.symbols[i] = self._root.ImportAssets2Body.Symbol(self._io, self, self._root)


        class Symbol(KaitaiStruct):
            def __init__(self, _io, _parent=None, _root=None):
                self._io = _io
                self._parent = _parent
                self._root = _root if _root else self
                self._read()

            def _read(self):
                self.tag = self._io.read_u2le()
                self.name = (self._io.read_bytes_term(0, False, True, True)).decode(u"ASCII")



    class RecordHeader(KaitaiStruct):
        def __init__(self, _io, _parent=None, _root=None):
            self._io = _io
            self._parent = _parent
            self._root = _root if _root else self
            self._read()

        def _read(self):
            self.tag_code_and_length = self._io.read_u2le()
            if self.small_len == 63:
                self.big_len = self._io.read_s4le()


        @property
        def tag_type(self):
            if hasattr(self, '_m_tag_type'):
                return self._m_tag_type if hasattr(self, '_m_tag_type') else None

            self._m_tag_type = self._root.TagType((self.tag_code_and_length >> 6))
            return self._m_tag_type if hasattr(self, '_m_tag_type') else None

        @property
        def small_len(self):
            if hasattr(self, '_m_small_len'):
                return self._m_small_len if hasattr(self, '_m_small_len') else None

            self._m_small_len = (self.tag_code_and_length & 63)
            return self._m_small_len if hasattr(self, '_m_small_len') else None

        @property
        def len(self):
            if hasattr(self, '_m_len'):
                return self._m_len if hasattr(self, '_m_len') else None

            self._m_len = (self.big_len if self.small_len == 63 else self.small_len)
            return self._m_len if hasattr(self, '_m_len') else None


    class ScriptLimitsBody(KaitaiStruct):
        def __init__(self, _io, _parent=None, _root=None):
            self._io = _io
            self._parent = _parent
            self._root = _root if _root else self
            self._read()

        def _read(self):
            self.max_recursion_depth = self._io.read_u2le()
            self.script_timeout_seconds = self._io.read_u2le()



