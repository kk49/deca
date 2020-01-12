meta:
  id: var_int
  title: Variable length integer helper
  license: CC0-1.0
  ks-version: 0.8
doc: |
  LIMITATIONS:
    Max number of bits is 32
  SWF has can have integers of variable bit lengths determined at runtime. This provides support for that
params:
  - id: raw
  - id: num_bits
    type: u1
    doc: Number of bits per digit. Only values of 4 and 8 are supported.
  - id: is_signed
    type: bool
    doc: Endianness of bit array. True means signed integer, false means unsigned integer
  - id: is_le
    type: bool
    doc: Endianness of bit array. True means little-endian, false is for big-endian.
seq:
  - id: raw
    type: b1
    repeat: expr
    repeat-expr: num_bits

instances:
  value:
    value: >
        is_le ? (
          (((num_bits >  0) and raw[ 0]) ? 1 : 0) <<  0 |
          (((num_bits >  1) and raw[ 1]) ? 1 : 0) <<  1 |
          (((num_bits >  2) and raw[ 2]) ? 1 : 0) <<  2 |
          (((num_bits >  3) and raw[ 3]) ? 1 : 0) <<  3 |
          (((num_bits >  4) and raw[ 4]) ? 1 : 0) <<  4 |
          (((num_bits >  5) and raw[ 5]) ? 1 : 0) <<  5 |
          (((num_bits >  6) and raw[ 6]) ? 1 : 0) <<  6 |
          (((num_bits >  7) and raw[ 7]) ? 1 : 0) <<  7 |
          (((num_bits >  8) and raw[ 8]) ? 1 : 0) <<  8 |
          (((num_bits >  9) and raw[ 9]) ? 1 : 0) <<  9 |
          (((num_bits > 10) and raw[10]) ? 1 : 0) << 10 |
          (((num_bits > 11) and raw[11]) ? 1 : 0) << 11 |
          (((num_bits > 12) and raw[12]) ? 1 : 0) << 12 |
          (((num_bits > 13) and raw[13]) ? 1 : 0) << 13 |
          (((num_bits > 14) and raw[14]) ? 1 : 0) << 14 |
          (((num_bits > 15) and raw[15]) ? 1 : 0) << 15 |
          (((num_bits > 16) and raw[16]) ? 1 : 0) << 16 |
          (((num_bits > 17) and raw[17]) ? 1 : 0) << 17 |
          (((num_bits > 18) and raw[18]) ? 1 : 0) << 18 |
          (((num_bits > 19) and raw[19]) ? 1 : 0) << 19 |
          (((num_bits > 20) and raw[20]) ? 1 : 0) << 20 |
          (((num_bits > 21) and raw[21]) ? 1 : 0) << 21 |
          (((num_bits > 22) and raw[22]) ? 1 : 0) << 22 |
          (((num_bits > 23) and raw[23]) ? 1 : 0) << 23 |
          (((num_bits > 24) and raw[24]) ? 1 : 0) << 24 |
          (((num_bits > 25) and raw[25]) ? 1 : 0) << 25 |
          (((num_bits > 26) and raw[26]) ? 1 : 0) << 26 |
          (((num_bits > 27) and raw[27]) ? 1 : 0) << 27 |
          (((num_bits > 28) and raw[28]) ? 1 : 0) << 28 |
          (((num_bits > 29) and raw[29]) ? 1 : 0) << 29 |
          (((num_bits > 30) and raw[30]) ? 1 : 0) << 30 |
          (((num_bits > 31) and raw[31]) ? 1 : 0) << 31 |
          ((is_signed and raw[is_le ? (num_bits - 1) : 0]) ? (-1 << num_bits): 0)
        ) : (
          (((num_bits >  0) and raw[ 0]) ? 1 : 0) << ((num_bits - 1) -  0) |
          (((num_bits >  1) and raw[ 1]) ? 1 : 0) << ((num_bits - 1) -  1) |
          (((num_bits >  2) and raw[ 2]) ? 1 : 0) << ((num_bits - 1) -  2) |
          (((num_bits >  3) and raw[ 3]) ? 1 : 0) << ((num_bits - 1) -  3) |
          (((num_bits >  4) and raw[ 4]) ? 1 : 0) << ((num_bits - 1) -  4) |
          (((num_bits >  5) and raw[ 5]) ? 1 : 0) << ((num_bits - 1) -  5) |
          (((num_bits >  6) and raw[ 6]) ? 1 : 0) << ((num_bits - 1) -  6) |
          (((num_bits >  7) and raw[ 7]) ? 1 : 0) << ((num_bits - 1) -  7) |
          (((num_bits >  8) and raw[ 8]) ? 1 : 0) << ((num_bits - 1) -  8) |
          (((num_bits >  9) and raw[ 9]) ? 1 : 0) << ((num_bits - 1) -  9) |
          (((num_bits > 10) and raw[10]) ? 1 : 0) << ((num_bits - 1) - 10) |
          (((num_bits > 11) and raw[11]) ? 1 : 0) << ((num_bits - 1) - 11) |
          (((num_bits > 12) and raw[12]) ? 1 : 0) << ((num_bits - 1) - 12) |
          (((num_bits > 13) and raw[13]) ? 1 : 0) << ((num_bits - 1) - 13) |
          (((num_bits > 14) and raw[14]) ? 1 : 0) << ((num_bits - 1) - 14) |
          (((num_bits > 15) and raw[15]) ? 1 : 0) << ((num_bits - 1) - 15) |
          (((num_bits > 16) and raw[16]) ? 1 : 0) << ((num_bits - 1) - 16) |
          (((num_bits > 17) and raw[17]) ? 1 : 0) << ((num_bits - 1) - 17) |
          (((num_bits > 18) and raw[18]) ? 1 : 0) << ((num_bits - 1) - 18) |
          (((num_bits > 19) and raw[19]) ? 1 : 0) << ((num_bits - 1) - 19) |
          (((num_bits > 20) and raw[20]) ? 1 : 0) << ((num_bits - 1) - 20) |
          (((num_bits > 21) and raw[21]) ? 1 : 0) << ((num_bits - 1) - 21) |
          (((num_bits > 22) and raw[22]) ? 1 : 0) << ((num_bits - 1) - 22) |
          (((num_bits > 23) and raw[23]) ? 1 : 0) << ((num_bits - 1) - 23) |
          (((num_bits > 24) and raw[24]) ? 1 : 0) << ((num_bits - 1) - 24) |
          (((num_bits > 25) and raw[25]) ? 1 : 0) << ((num_bits - 1) - 25) |
          (((num_bits > 26) and raw[26]) ? 1 : 0) << ((num_bits - 1) - 26) |
          (((num_bits > 27) and raw[27]) ? 1 : 0) << ((num_bits - 1) - 27) |
          (((num_bits > 28) and raw[28]) ? 1 : 0) << ((num_bits - 1) - 28) |
          (((num_bits > 29) and raw[29]) ? 1 : 0) << ((num_bits - 1) - 29) |
          (((num_bits > 30) and raw[30]) ? 1 : 0) << ((num_bits - 1) - 30) |
          (((num_bits > 31) and raw[31]) ? 1 : 0) << ((num_bits - 1) - 31) |
          ((is_signed and raw[is_le ? (num_bits - 1) : 0]) ? (-1 << num_bits): 0)
        )
