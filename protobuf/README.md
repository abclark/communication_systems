# Protocol Buffers: Building from Scratch

This project implements Google's Protocol Buffers wire format from the ground up, following the historical development and design decisions that shaped the format.

---

## What is Protocol Buffers?

A **serialization format** — a way to turn structured data into bytes (and back).

```
Python dict  ──serialize──►  bytes  ──deserialize──►  Python dict
```

Google created it to replace ad-hoc text formats with something:
- **Compact** (binary, not text)
- **Fast** (no string parsing)
- **Cross-language** (one schema, many languages)
- **Evolvable** (add fields without breaking old code)

---

## Concepts

This section explains everything you need to understand the protobuf wire format.

### The Big Picture: Why Binary?

**JSON** (text-based):
```json
{"age": 150, "name": "Alice"}
```
- 30 bytes
- Human readable
- Requires parsing quotes, colons, braces
- Numbers stored as ASCII digits ("150" = 3 bytes)

**Protobuf** (binary):
```
08 96 01 12 05 41 6c 69 63 65
```
- 10 bytes (3x smaller!)
- Not human readable
- No parsing — just read bytes
- Numbers stored efficiently (150 = 2 bytes)

**Trade-off:** Protobuf sacrifices readability for speed and size. You need a schema to interpret the bytes.

---

### Varints: The Foundation

Everything in protobuf is built on **varints** — variable-length integers that use fewer bytes for smaller numbers.

#### The Problem

Fixed-size integers waste space:
```
Value 1 as int32:   00 00 00 01  (4 bytes, 3 wasted)
Value 1 as int64:   00 00 00 00 00 00 00 01  (8 bytes, 7 wasted)
```

Most real-world numbers are small (field numbers, lengths, enum values), so this waste adds up.

#### The Solution

Use 7 bits per byte for data, 1 bit as a "continuation flag":

```
Byte:    [C][D D D D D D D]
          │  └─────────────── 7 bits of data
          └────────────────── 1 bit: Continue? (1=yes, 0=no)
```

- If the high bit is 1: more bytes follow
- If the high bit is 0: this is the last byte

#### Example: Encoding 150

```
150 in binary: 10010110 (needs more than 7 bits!)

Step 1: Take lowest 7 bits
  150 & 0x7F = 150 & 01111111 = 0010110 = 22

Step 2: More bits remaining?
  150 >> 7 = 1 (yes!)
  So set continuation bit: 22 | 0x80 = 10010110 = 0x96

Step 3: Take next 7 bits
  1 & 0x7F = 1

Step 4: More bits remaining?
  1 >> 7 = 0 (no!)
  So don't set continuation bit: 0x01

Result: [0x96, 0x01] = 2 bytes
```

#### Why Least Significant Bits First?

Varints are **little-endian within the varint** — lowest bits come first. This allows:
1. Easy streaming (process bytes as they arrive)
2. Simple decoding (shift and OR as you go)

#### Varint Size Chart

| Value | Bytes Needed |
|-------|--------------|
| 0-127 | 1 byte |
| 128-16,383 | 2 bytes |
| 16,384-2,097,151 | 3 bytes |
| Up to 2^28-1 | 4 bytes |
| Up to 2^35-1 | 5 bytes |

---

### Wire Types: How to Read the Right Amount

When decoding, you need to know: **how many bytes does this value occupy?**

Wire types solve this. There are only **4 used wire types**:

| Wire Type | Name | Size | Used For |
|-----------|------|------|----------|
| 0 | VARINT | Variable | int32, int64, uint32, uint64, bool, enum |
| 1 | I64 | Fixed 8 bytes | fixed64, sfixed64, double |
| 2 | LEN | Length-prefixed | string, bytes, nested messages, repeated fields |
| 5 | I32 | Fixed 4 bytes | fixed32, sfixed32, float |

*(Wire types 3 and 4 existed in early protobuf for "groups" but are deprecated.)*

#### Why Only 4 Types?

The wire format doesn't need to know if a value is a `bool` vs `int32` — both are just varints. The schema tells the application how to interpret the decoded value.

This separation is key to **forward compatibility**: old code can skip unknown fields by reading the wire type and consuming the right number of bytes.

---

### Tags: Identifying Fields

Every field on the wire starts with a **tag** that encodes:
1. **Field number** — which field is this? (from the schema)
2. **Wire type** — how to read the value

#### Tag Encoding

```
tag = (field_number << 3) | wire_type
```

The tag itself is encoded as a varint.

#### Why 3 Bits for Wire Type?

3 bits = 8 possible values. Only 4 are used (0, 1, 2, 5), leaving room for future expansion.

#### Example: Field 1, Wire Type 0

```
tag = (1 << 3) | 0
    = 8 | 0
    = 8
    = 0x08 (as varint)
```

#### Example: Field 2, Wire Type 2

```
tag = (2 << 3) | 2
    = 16 | 2
    = 18
    = 0x12 (as varint)
```

#### Decoding a Tag

```
Given tag byte 0x08:
  wire_type = 0x08 & 0x07 = 0  (lowest 3 bits)
  field_num = 0x08 >> 3 = 1    (remaining bits)
```

#### Multi-byte Tags

Field numbers > 15 require multi-byte tags:

```
Field 16, wire type 0:
  tag = (16 << 3) | 0 = 128 = 0x80 0x01 (varint)
```

This is why protobuf best practices suggest using field numbers 1-15 for frequently-used fields.

---

### Field Encoding: Complete Examples

#### Wire Type 0: VARINT (Integers, Bools, Enums)

**Encoding `age = 150` as field 1:**

```
Step 1: Tag
  (1 << 3) | 0 = 8 → 0x08

Step 2: Value
  150 → 0x96 0x01 (varint)

Result: 08 96 01 (3 bytes)
```

**Encoding `active = true` as field 3:**

```
Step 1: Tag
  (3 << 3) | 0 = 24 → 0x18

Step 2: Value
  true = 1 → 0x01 (varint)

Result: 18 01 (2 bytes)
```

**Encoding `status = ACTIVE` (enum value 1) as field 4:**

```
Same as bool — enums are just integers!
Result: 20 01 (2 bytes)
```

#### Wire Type 2: LEN (Strings, Bytes, Nested Messages)

**Encoding `name = "Hi"` as field 2:**

```
Step 1: Tag
  (2 << 3) | 2 = 18 → 0x12

Step 2: Length
  len("Hi") = 2 → 0x02 (varint)

Step 3: Data
  "Hi" in UTF-8 → 0x48 0x69

Result: 12 02 48 69 (4 bytes)
         │  │  └──┴── "Hi"
         │  └──────── length = 2
         └─────────── tag (field 2, wire type 2)
```

**Nested messages use the same encoding** — the inner message is just bytes:

```
Inner message: {age: 5}  →  08 05
Outer field 3, wire type 2:

Result: 1a 02 08 05
         │  │  └──┴── inner message bytes
         │  └──────── length = 2
         └─────────── tag (field 3, wire type 2)
```

#### Wire Type 5: I32 (Fixed 32-bit)

**Encoding `count = 1000` as field 3 (fixed32):**

```
Step 1: Tag
  (3 << 3) | 5 = 29 → 0x1D

Step 2: Value (4 bytes, little-endian)
  1000 = 0x000003E8
  Little-endian: E8 03 00 00

Result: 1D E8 03 00 00 (5 bytes)
```

**Little-endian** means least significant byte first:
```
1000 = 0x000003E8

Big-endian:    00 00 03 E8  (most significant first)
Little-endian: E8 03 00 00  (least significant first) ← protobuf uses this
```

#### Wire Type 1: I64 (Fixed 64-bit)

**Encoding `big_count = 1000` as field 4 (fixed64):**

```
Step 1: Tag
  (4 << 3) | 1 = 33 → 0x21

Step 2: Value (8 bytes, little-endian)
  1000 = 0x00000000000003E8
  Little-endian: E8 03 00 00 00 00 00 00

Result: 21 E8 03 00 00 00 00 00 00 (9 bytes)
```

---

### Signed Integers: A Subtle Trap

Standard varints don't handle negative numbers well:

```
-1 as int32 = 0xFFFFFFFF (two's complement)
As varint: FF FF FF FF FF FF FF FF FF 01 (10 bytes!)
```

**Solution: ZigZag encoding** (used by `sint32`, `sint64`):

```
Encode: (n << 1) ^ (n >> 31)  // for 32-bit

 0 →  0
-1 →  1
 1 →  2
-2 →  3
 2 →  4
```

This maps small negative numbers to small positive numbers, keeping varints short.

*Our implementation doesn't include ZigZag, but it's easy to add if needed.*

---

### Message Structure

A protobuf message is simply **concatenated fields**:

```
Message:
  age = 150 (field 1)
  name = "Hi" (field 2)

Encoded:
  [field 1 encoding][field 2 encoding]
  [08 96 01       ][12 02 48 69     ]

Final bytes: 08 96 01 12 02 48 69
```

#### Field Order Doesn't Matter

These encode the same logical message:
```
08 96 01 12 02 48 69  (field 1, then field 2)
12 02 48 69 08 96 01  (field 2, then field 1)
```

The decoder processes fields in whatever order they appear.

#### Repeated Fields

Same field number can appear multiple times:

```
tags = [1, 2, 3] (field 5, repeated int32)

Encoded as three separate fields:
  28 01  (field 5 = 1)
  28 02  (field 5 = 2)
  28 03  (field 5 = 3)
```

Or with "packed" encoding (more efficient):

```
2A 03 01 02 03  (field 5, wire type 2, length 3, values 1,2,3)
```

---

### Decoding: Reading Unknown Bytes

The decoder doesn't need a schema to **parse** bytes — only to **interpret** them.

#### Decoding Algorithm

```
offset = 0
while offset < len(data):
    1. Read tag (varint) → get field_number and wire_type
    2. Based on wire_type:
       - 0: read varint
       - 1: read 8 bytes
       - 2: read length (varint), then read that many bytes
       - 5: read 4 bytes
    3. Store result[field_number] = value
    4. Advance offset
```

#### Example: Decoding `08 96 01 12 02 48 69`

| Offset | Bytes | Action | Result |
|--------|-------|--------|--------|
| 0 | `08` | Tag: field=1, wire=0 | |
| 1 | `96 01` | Varint: 150 | field 1 = 150 |
| 3 | `12` | Tag: field=2, wire=2 | |
| 4 | `02` | Length: 2 | |
| 5 | `48 69` | Bytes: "Hi" | field 2 = "Hi" |
| 7 | (end) | Done | `{1: 150, 2: "Hi"}` |

---

### Design Principles

#### Forward Compatibility

Old code can read new messages:
- Unknown fields are skipped (wire type tells you how many bytes)
- Missing fields get default values

#### Backward Compatibility

New code can read old messages:
- Missing fields get default values
- New optional fields won't break old producers

#### Field Numbers Are Forever

Once assigned, a field number should never be reused for a different purpose. If you remove a field, mark it as `reserved` in the schema.

#### Default Values

In proto3, default values aren't transmitted:
- Integer: 0
- Bool: false
- String: ""
- Enum: first value (usually 0)

This saves bytes but means you can't distinguish "explicitly set to 0" from "not set."

---

### Comparison With Other Formats

| Format | Type | Human Readable | Size | Speed | Schema |
|--------|------|----------------|------|-------|--------|
| JSON | Text | Yes | Large | Slow | Optional |
| XML | Text | Yes | Very Large | Very Slow | Optional |
| Protobuf | Binary | No | Small | Fast | Required |
| MessagePack | Binary | No | Small | Fast | No |

**When to use protobuf:**
- High-volume services (RPC, streaming)
- Size/speed matter more than debuggability
- You control both producer and consumer

**When NOT to use protobuf:**
- Public APIs where clients vary (JSON more accessible)
- Need to hand-edit data files
- Schema evolution is unpredictable

---

### Bitwise Operations Reference

These operations are used throughout protobuf encoding/decoding:

| Operation | Symbol | Example | Result | Purpose |
|-----------|--------|---------|--------|---------|
| AND | `&` | `150 & 0x7F` | 22 | Mask to keep lowest 7 bits |
| OR | `\|` | `22 \| 0x80` | 150 | Set the continuation bit |
| Left Shift | `<<` | `1 << 3` | 8 | Move field number into position |
| Right Shift | `>>` | `150 >> 7` | 1 | Remove lowest 7 bits |

#### Hexadecimal Quick Reference

```
0x7F = 0111 1111 = 127  (mask for 7 bits)
0x80 = 1000 0000 = 128  (continuation bit)
0x07 = 0000 0111 = 7    (mask for 3 bits / wire type)
0xFF = 1111 1111 = 255  (mask for 8 bits / one byte)
```

---

## Project Roadmap

### Phase 1: Varints ✅
The fundamental building block. Variable-length integers that use fewer bytes for small numbers.

- [x] Step 1: Encode varints
- [x] Step 2: Decode varints

### Phase 2: Tags ✅
How protobuf identifies fields on the wire.

- [x] Step 3: Understand wire types (0, 1, 2, 5)
- [x] Step 4: Encode tags (field_number + wire_type)
- [x] Step 5: Decode tags

### Phase 3: Scalar Fields ✅
Encoding simple values.

- [x] Step 6: Encode int32/int64 (wire type 0)
- [x] Step 7: Encode strings (wire type 2)
- [x] Step 8: Encode fixed32/fixed64 (wire types 5 and 1)

### Phase 4: Messages ✅
Putting fields together.

- [x] Step 9: Encode messages (concatenate fields)
- [x] Step 10: Decode messages (`decode_message`)

### Phase 5: Complex Types (Future)
Nested structures and arrays.

- [ ] Step 11: Nested messages
- [ ] Step 12: Repeated fields

### Phase 6: Schema (Optional)
Parsing .proto files.

- [ ] Step 13: Parse simple .proto syntax
- [ ] Step 14: Generate encoder/decoder from schema

---

## Historical Context

| Year | Event |
|------|-------|
| ~2001 | Google creates protobuf internally to replace ad-hoc formats |
| 2008 | Open-sourced as Protocol Buffers |
| 2015 | gRPC released (uses protobuf) |
| 2016 | Proto3 (simplified syntax) |

---

## Files

```
protobuf/
  README.md       — This file
  protobuf.py     — Implementation (built incrementally)
```

---

## Current Status

**Phases 1-4 Complete!**

We have a working protobuf encoder/decoder that supports:
- All four wire types (VARINT, I64, LEN, I32)
- Encoding: `encode_int_field`, `encode_string_field`, `encode_fixed32_field`, `encode_fixed64_field`
- Decoding: `decode_message` — decodes any message into `{field_number: value}`

### What We Built

| Function | Purpose |
|----------|---------|
| `encode_varint` / `decode_varint` | Variable-length integers |
| `encode_tag` / `decode_tag` | Field number + wire type |
| `encode_int_field` | Integer fields (wire type 0) |
| `encode_string_field` | String fields (wire type 2) |
| `encode_fixed32_field` / `decode_fixed32` | Fixed 32-bit (wire type 5) |
| `encode_fixed64_field` / `decode_fixed64` | Fixed 64-bit (wire type 1) |
| `decode_length_delimited` | Length-prefixed data (wire type 2) |
| `decode_message` | Full message decoder |

### Example Usage

```python
# Encode a message with two fields
message = encode_int_field(1, 150) + encode_string_field(2, "Hello")

# Decode it back
decoded = decode_message(message)
# {1: 150, 2: b'Hello'}
```

### Ready for gRPC

This implementation is sufficient for basic gRPC messages. Nested messages and repeated fields can be added as needed.
