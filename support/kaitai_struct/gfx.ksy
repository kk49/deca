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
  imports:
    - var_int
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
      - id: num_bits
        type: b5
      - id: x_min_raw
        # type: var_int(num_bits, true, false)
        type: b1
        repeat: expr
        repeat-expr: num_bits
      - id: x_max_raw
        # type: var_int(num_bits, true, false)
        type: b1
        repeat: expr
        repeat-expr: num_bits
      - id: y_min_raw
        # type: var_int(num_bits, true, false)
        type: b1
        repeat: expr
        repeat-expr: num_bits
      - id: y_max_raw
        # type: var_int(num_bits, true, false)
        type: b1
        repeat: expr
        repeat-expr: num_bits
#    instances:
#      x_min:
#        value: 'x_min_raw.as<bin32>'
#        value: 'var_int(x_min_raw, num_bits, true, false)'

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
            'tag_type::define_shape3': define_shape3_body
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

  define_shape3_body:
    seq:
      - id: shape_id
        type: u2
      - id: bounds
        type: rect
      - id: shapes
        size-eos: true

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
    6: define_bits
    7: define_button
    8: jpeg_tables
    9: set_background_color
    10: define_font
    11: define_text
    12: do_action
    13: define_font_info
    14: define_sound
    15: start_sound
    16: no_operation_16
    17: define_button_sound
    18: sound_stream_head
    19: sound_stream_block
    20: define_bits_lossless
    21: define_bits_jpeg2
    22: define_shape2
    23: define_button_cxform
    24: protect
    25: no_operation_25
    26: place_object2
    27: no_operation_27
    28: remove_object2
    29: no_operation_29
    30: no_operation_30
    31: no_operation_31
    32: define_shape3
    33: define_text2
    34: define_button2
    35: define_bits_jpeg3
    36: define_bits_lossless2
    37: define_edit_text
    38: no_operation_38
    39: define_sprite
    40: name_character
    41: serial_number
    42: generator_text
    43: frame_label
    44: no_operation_44
    45: sound_stream_head2
    46: define_morph_shape
    47: no_operation_47
    48: define_font2
    49: define_info
    50: no_operation_50
    51: generator3
    52: external_font
    53: no_operation_53
    54: no_operation_54
    55: no_operation_55
    56: export_assets
    57: import_assets
    58: protect_debug
    59: do_init_action
    60: define_video_stream
    61: video_frame
    62: define_font_info2
    63: no_operation_63
    64: protect_debug2
    65: script_limits
    66: set_tab_limit
    67: define_shape_4
    68: no_operation_68
    69: file_attributes
    70: place_object3
    71: import_assets2
    72: no_operation_72
    73: define_font_info3
    74: define_text_info
    75: define_font3
    76: symbol_class  # this is not in the spec for scale forms
    77: metadata
    78: define_scaling_grid
    82: do_abc
    83: define_shape5
    84: define_morph_shape2
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
