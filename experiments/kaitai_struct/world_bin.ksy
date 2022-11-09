meta:
  id: world_bin
  file-extension: bin
  endian: le

doc: |
  File format for older world.bin in APEX engine games, at least Generation Zero
  and theHunter:COTW. It seems like it's a weird inline RTPC file
  
seq:
  - id: header_ver_0
    type: u1

  - id: header_ver_1
    type: u2

  - id: object_count
    type: u2

  - id: objects
    type: object
    repeat: expr
    repeat-expr: object_count

types:
  object:
    seq:
      - id: name
        type: u4
        
      - id: unk0
        type: u1
        
      - id: unk1
        type: u2
        
      - id: count
        type: u2
        
      - id: members
        type: element
        repeat: expr
        repeat-expr: count
        
  element:
    seq:
      - id: name
        type: u4

      - id: type_id
        type: u1

      - id: data_u4
        type: u4
        if: type_id == 1
      
      - id: data_f4
        type: f4
        if: type_id == 2

      - id: data_strn
        type: strn
        if: type_id == 3
        
      - id: data_vec3
        type: f4
        repeat: expr
        repeat-expr: 3
        if: type_id == 5

      - id: data_mat3x4
        type: mat3x4
        if: type_id == 8

      - id: data_events
        type: events
        if: type_id == 14

  strn:
    seq:
      - id: len
        type: u2
      - id: data
        size: len
        type: str
        encoding: ascii
        
  events:
    seq:
      - id: len
        type: u4
      - id: data
        type: u8
        repeat: expr
        repeat-expr: len
        
  vec3:
    seq:
      - id: x
        type: f4
      - id: y
        type: f4
      - id: z
        type: f4
        
  mat3x4:
    seq:
      - id: mat3x3
        type: f4
        repeat: expr
        repeat-expr: 9
      - id: vec3
        type: f4
        repeat: expr
        repeat-expr: 3
