meta:
  id: rtpc
  file-extension: rtpc
  endian: le
seq:
- id: header
  type: rtpc_header
- id: container
  type: container
  doc: JC4 containers are flattened, with order preserved by 3 properties in the root container
types:
  rtpc_header:
    seq:
      - id: magic
        contents: RTPC
      - id: version
        type: u4
  container:
    seq:
      - id: name_hash
        type: u4
      - id: offset
        type: u4
      - id: property_count
        type: u2
      - id: container_count
        type: u2
    instances:
      body:
        pos: offset
        type: container_body(property_count, container_count)
  container_body:
    params:
      - id: property_count
        type: u2
      - id: container_count
        type: u2
    seq:
      - id: properties
        type: property_header
        repeat: expr
        repeat-expr: property_count
      - id: containers
        type: container
        repeat: expr
        repeat-expr: container_count
      - id: valid_properties
        type: u4
  property_header:
    seq:
      - id: name_hash
        type: u4
      - id: raw_data
        type: u4
      - id: variant_type
        type: u1
        enum: variant
    instances:
      simple_f4:
        value: raw_data.as<f4>
      offset_value:
        pos: raw_data
        type:
          switch-on: variant_type
          cases:
            variant::unassigned: unassigned
            variant::uint32: m_u4
            variant::float: m_f4
            variant::string: string
            variant::vec2: f4_array_param(2)
            variant::vec3: f4_array_param(3)
            variant::vec4: f4_array_param(4)
            variant::matrix_3x3: f4_array_param(9)
            variant::matrix_4x4: f4_array_param(16)
            variant::uint32_array: u4_array
            variant::float_array: f4_array
            variant::byte_array: byte_array
            variant::deprecated: unassigned
            variant::object_id: object_id
            variant::event: event
            variant::total: unassigned
            _: unassigned
  m_u4: {}
  m_f4: {}
  string:
    seq:
      - id: value
        terminator: 0
        type: str
        encoding: UTF-8
  f4_array_param:
    params:
      - id: count
        type: u4
    seq:
      - id: values
        type: f4
        repeat: expr
        repeat-expr: count
  u32_array_param:
    params:
      - id: count
        type: u4
    seq:
      - id: values
        type: u4
        repeat: expr
        repeat-expr: count
  f4_array:
    seq:
      - id: count
        type: u4
      - id: values
        type: f4
        repeat: expr
        repeat-expr: count
  u4_array:
    seq:
      - id: count
        type: u4
      - id: values
        type: u4
        repeat: expr
        repeat-expr: count
  unassigned:
    {}
  byte_array:
    seq:
      - id: count
        type: u4
      - id: values
        size: count
  object_id:
    seq:
      - id: oid
        type: u8
    instances:
      user_data:
        doc: May need to reverse oid before & 255
        value: oid & 255
  event:
    seq:
      - id: count
        type: u4
      - id: pair
        type: u32_array_param(2)
        repeat: expr
        repeat-expr: count
enums:
  variant:
    0: unassigned
    1: uint32
    2: float
    3: string
    4: vec2
    5: vec3
    6: vec4
    7: matrix_3x3
    8: matrix_4x4
    9: uint32_array
    10: float_array
    11: byte_array
    12: deprecated
    13: object_id
    14: event
    15: total