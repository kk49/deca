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
  - id: header_count
    type: u2

  - id: elements
    type: element
    repeat: eos

types:
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
        
  mat12:
    seq:
      - id: mat
        type: f4
        repeat: expr
        repeat-expr: 12
        
        
  element:
    seq:
      - id: name
        type: u4

      - id: type_id
        type: u1

      - id: data_01
        type: u4
        if: type_id == 1
      
      - id: data_02
        type: f4
        if: type_id == 2

      - id: data_03
        type: strn
        if: type_id == 3
        
      - id: data_05
        type: vec3
        if: type_id == 5

      - id: data_08
        type: mat12
        if: type_id == 8

      - id: data_0e
        type: events
        if: type_id == 14
      
      - id: data_f8
        type: vec3
        if: type_id == 248
        
      

      

  type3:
    seq:
      - id: type_id
        type: u1
      - id: len
        type: u2
      - id: val
        size: len
        type: str
        encoding: ascii

