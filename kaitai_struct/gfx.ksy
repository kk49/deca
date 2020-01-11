meta:
  id: gfx
  title: Autodesk ScaleForm (an extension to Shockwave Flash, Macromedia Flash)
  file-extension: gfx
  xref:
    justsolve: GFX
    loc: fmt/507
    # mime: application/x-shockwave-flash
    wikidata: Q594447
  license: CC0-1.0
  endian: le
#  imports:
#    - abc_bytecode
doc: |
  First pass at a parser for ScaleForm GFX files.
  https://help.autodesk.com/view/SCLFRM/ENU/?guid=__scaleform_help_flash_support_controltags_html
doc-ref: https://www.adobe.com/content/dam/acom/en/devnet/pdf/swf-file-format-spec.pdf
seq:
  - id: compression
    -orig-id: Signature
    type: u1
    enum: compressions
  - id: signature
    -orig-id: Signature
    contents: "FX"
  - id: version
    -orig-id: Version
    type: u1
  - id: len_file
    -orig-id: FileLength
    type: u4
  - id: plain_body
    size-eos: true
    type: swf_body
    if: compression == compressions::none
  - id: zlib_body
    size-eos: true
    process: zlib
    type: swf_body
    if: compression == compressions::zlib
types:
  swf_body:
    seq:
      - id: rect
        type: rect
      - id: frame_rate
        type: u2
      - id: frame_count
        type: u2
      - id: tags
        type: tag
        repeat: until
        repeat-until: _.record_header.tag_type == tag_type::end_of_file
  rect:
    seq:
      - id: b1
        type: u1
      - id: skip
        size: num_bytes
    instances:
      num_bits:
        value: b1 >> 3
      num_bytes:
        value: ((num_bits * 4 - 3) + 7) / 8
  rgb:
    seq:
      - id: r
        type: u1
      - id: g
        type: u1
      - id: b
        type: u1
  record_header:
    seq:
      - id: tag_code_and_length
        type: u2
      - id: big_len
        type: s4
        if: small_len == 0x3f
    instances:
      tag_type:
        value: 'tag_code_and_length >> 6'
        enum: tag_type
      small_len:
        value: 'tag_code_and_length & 0b111111'
      len:
        value: 'small_len == 0x3f ? big_len : small_len'
  tag:
    seq:
      - id: record_header
        type: record_header
      - id: tag_body
        size: record_header.len
        type:
          switch-on: record_header.tag_type
          cases:
            'tag_type::define_sound': define_sound_body
            'tag_type::do_abc': do_abc_body
            'tag_type::script_limits': script_limits_body
            'tag_type::symbol_class': symbol_class_body
            'tag_type::set_background_color': rgb
            'tag_type::export_assets': symbol_class_body
            'tag_type::import_assets2': import_assets2_body
            'tag_type::gfx_exporter_info': gfx_exporter_info_body
            'tag_type::gfx_define_external_image': gfx_define_external_image_body
            'tag_type::gfx_define_external_image2': gfx_define_external_image2_body
  define_sound_body:
    seq:
      - id: id
        -orig-id: SoundId
        type: u2
      - id: format
        -orig-id: SoundFormat
        type: b4
      - id: sampling_rate
        -orig-id: SoundRate
        type: b2
        enum: sampling_rates
        doc: Sound sampling rate, as per enum. Ignored for Nellymoser and Speex codecs.
      - id: bits_per_sample
        -orig-id: SoundSize
        type: b1
        enum: bps
      - id: num_channels
        -orig-id: SoundType
        type: b1
        enum: channels
      - id: num_samples
        type: u4
    enums:
      sampling_rates:
        0: rate_5_5_khz
        1: rate_11_khz
        2: rate_22_khz
        3: rate_44_khz
      bps:
        0: sound_8_bit
        1: sound_16_bit
      channels:
        0: mono
        1: stereo
  do_abc_body:
    seq:
      - id: flags
        type: u4
      - id: name
        type: strz
        encoding: ASCII
      - id: abcdata
        size-eos: true
        #type: abc_bytecode
  script_limits_body:
    seq:
      - id: max_recursion_depth
        type: u2
      - id: script_timeout_seconds
        type: u2
  symbol_class_body:
    seq:
      - id: num_symbols
        type: u2
      - id: symbols
        type: symbol
        repeat: expr
        repeat-expr: num_symbols
    types:
      symbol:
        seq:
          - id: tag
            type: u2
          - id: name
            type: strz
            encoding: ASCII
  import_assets2_body:
    seq:
      - id: url
        type: strz
        encoding: ASCII
      - id: download_now
        type: u1
      - id: has_digest
        type: u1
      - id: sha1
        size: 20
        if: has_digest == 1
      - id: num_symbols
        type: u2
      - id: symbols
        type: symbol
        repeat: expr
        repeat-expr: num_symbols
    types:
      symbol:
        seq:
          - id: tag
            type: u2
          - id: name
            type: strz
            encoding: ASCII

  gfx_exporter_info_body:
    seq:
      - id: version
        type: u2
      - id: flags
        type: u4
        if: version >= 0x10a
      - id: bitmap_format
        type: u2
      - id: prefix_len
        type: u1
      - id: prefix
        type: str
        encoding: ASCII
        size: prefix_len
      - id: name_len
        type: u1
      - id: name
        type: str
        encoding: ASCII
        size: name_len
      - id: extra
        size-eos: true
  gfx_define_external_image_body:
    seq:
      - id: character_id
        -orig-id: characterId
        type: u2
      - id: bitmap_format
        type: u2
      - id: target_width
        type: u2
      - id: target_height
        type: u2
      - id: file_name_len
        type: u1
      - id: file_name
        type: str
        encoding: ASCII
        size: file_name_len
      - id: extra
        size-eos: true
  gfx_define_external_image2_body:
    seq:
      - id: character_id
        -orig-id: characterId
        type: u4
      - id: bitmap_format
        type: u2
      - id: target_width
        type: u2
      - id: target_height
        type: u2
      - id: export_name_len
        type: u1
      - id: export_name
        type: str
        encoding: ASCII
        size: export_name_len
      - id: file_name_len
        type: u1
      - id: file_name
        type: str
        encoding: ASCII
        size: file_name_len
      - id: extra
        size-eos: true

enums:
  compressions:
    0x46: none # G
    0x43: zlib # C
    0x5a: lzma # Z
  tag_type:
    0: end_of_file
    1: show_frame
    2: define_shape
    3: free_character
    4: place_object
    5: remove_object
    9: set_background_color
    14: define_sound
    22: define_shape2
    26: place_object2
    28: remove_object2
    32: define_shape3
    37: define_edit_text
    39: define_sprite
    43: frame_label
    46: define_morph_shape
    56: export_assets
    65: script_limits
    69: file_attributes
    70: place_object3
    71: import_assets2
    73: define_font_info3
    74: define_text_info
    75: define_font3
    76: symbol_class
    77: metadata
    78: define_scaling_grid
    82: do_abc
    83: define_shape5
    86: define_scene_and_frame_label_data
    1000: gfx_exporter_info  # ExporterInfo
    1001: gfx_define_external_image  # DefineExternalImage
    1002: gfx_font_texture_info  # FontTextureInfo
    1003: gfx_define_external_gradient_image  # DefineExternalGradientImage
    1004: gfx_define_gradient_map  # DefineGradientMap
    1005: gfx_define_compacted_font  # DefineCompactedFont
    1006: gfx_define_external_sound  # DefineExternalSound
    1007: gfx_define_external_stream_sound  # DefineExternalStreamSound
    1008: gfx_define_sub_image
    1009: gfx_define_external_image2
