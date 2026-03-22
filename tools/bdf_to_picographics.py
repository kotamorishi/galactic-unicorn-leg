"""Convert a BDF bitmap font to PicoGraphics font_t bytearray format.

PicoGraphics font_t format:
  byte 0:      height (uint8)
  byte 1:      max_width (uint8)
  bytes 2-106: widths[105] - width of each of 105 characters
               (96 ASCII 0x20-0x7F + 9 extended: ae, thorn, etc.)
  bytes 107+:  glyph data, column-major
               For height <= 8: 1 byte per column
               For height 9-16: 2 bytes per column (low byte = upper rows)
               Each glyph occupies max_width columns (padded with 0)
               Bit 0 = top pixel, bit N = Nth row from top

Character mapping (105 chars):
  Index 0-94:  ASCII 0x20 (' ') through 0x7E ('~')  = 95 chars
  Index 95:    0x00C6 (AE ligature)
  Index 96:    0x00D8 (O with stroke)
  Index 97:    0x00C5 (A with ring)
  Index 98:    0x00E6 (ae ligature)
  Index 99:    0x00F8 (o with stroke)
  Index 100:   0x00E5 (a with ring)
  Index 101:   0x00DE (Thorn)
  Index 102:   0x00FE (thorn)
  Index 103:   0x00A9 (copyright)
  Index 104:   0x00B0 (degree)
  Total: 105

Usage:
  python3 bdf_to_picographics.py source_font.bdf > ../src/display/font11_data.py
"""

import sys
import re


# Extended characters after ASCII 0x20-0x7E
EXTENDED_CODEPOINTS = [
    0x00C6,  # Æ
    0x00D8,  # Ø
    0x00C5,  # Å
    0x00E6,  # æ
    0x00F8,  # ø
    0x00E5,  # å
    0x00DE,  # Þ
    0x00FE,  # þ
    0x00A9,  # ©
    0x00B0,  # °
]

NUM_CHARS = 95 + len(EXTENDED_CODEPOINTS)  # 105


def parse_bdf(path):
    """Parse a BDF font file and return glyph data.

    Returns dict: codepoint -> {width, height, bbox, bitmap_rows}
    """
    glyphs = {}
    font_height = 0
    font_ascent = 0

    with open(path, "r") as f:
        lines = f.readlines()

    i = 0
    while i < len(lines):
        line = lines[i].strip()

        if line.startswith("FONTBOUNDINGBOX"):
            parts = line.split()
            font_height = int(parts[2])

        if line.startswith("FONT_ASCENT"):
            font_ascent = int(line.split()[1])

        if line.startswith("STARTCHAR"):
            # Parse one glyph
            codepoint = None
            bbx_w = 0
            bbx_h = 0
            bbx_xoff = 0
            bbx_yoff = 0
            dwidth = 0
            bitmap = []

            i += 1
            while i < len(lines):
                gl = lines[i].strip()
                if gl.startswith("ENCODING"):
                    codepoint = int(gl.split()[1])
                elif gl.startswith("DWIDTH"):
                    dwidth = int(gl.split()[1])
                elif gl.startswith("BBX"):
                    parts = gl.split()
                    bbx_w = int(parts[1])
                    bbx_h = int(parts[2])
                    bbx_xoff = int(parts[3])
                    bbx_yoff = int(parts[4])
                elif gl == "BITMAP":
                    i += 1
                    while i < len(lines) and lines[i].strip() != "ENDCHAR":
                        bitmap.append(int(lines[i].strip(), 16))
                        i += 1
                    break
                i += 1

            if codepoint is not None:
                glyphs[codepoint] = {
                    "width": dwidth,
                    "bbx_w": bbx_w,
                    "bbx_h": bbx_h,
                    "bbx_xoff": bbx_xoff,
                    "bbx_yoff": bbx_yoff,
                    "bitmap": bitmap,
                }
        i += 1

    return glyphs, font_height, font_ascent


def glyph_to_columns(glyph, target_height, font_ascent):
    """Convert a BDF glyph bitmap to column-major format for font_t.

    BDF stores row-major (top to bottom), we need column-major.
    Each column is 2 bytes for height > 8.
    Bit 0 = top pixel.
    """
    width = glyph["width"]
    bbx_w = glyph["bbx_w"]
    bbx_h = glyph["bbx_h"]
    bbx_xoff = glyph["bbx_xoff"]
    bbx_yoff = glyph["bbx_yoff"]
    bitmap = glyph["bitmap"]

    # Build a full target_height x width pixel grid
    grid = [[0] * width for _ in range(target_height)]

    # Place the glyph bbox into the grid
    # BDF: y_offset from baseline. baseline = font_ascent from top.
    # Top of bbox = font_ascent - bbx_yoff - bbx_h
    top_y = font_ascent - bbx_yoff - bbx_h

    for row_idx, row_bits in enumerate(bitmap):
        y = top_y + row_idx
        if y < 0 or y >= target_height:
            continue
        for col_idx in range(bbx_w):
            # BDF bitmap: MSB is leftmost pixel
            # Each row is ceil(bbx_w / 8) bytes wide
            byte_width = (bbx_w + 7) // 8
            total_bits = byte_width * 8
            bit_pos = total_bits - 1 - col_idx
            if row_bits & (1 << bit_pos):
                x = bbx_xoff + col_idx
                if 0 <= x < width:
                    grid[y][x] = 1

    # Convert grid to column-major bytes
    columns = []
    for x in range(width):
        col_val = 0
        for y in range(target_height):
            if grid[y][x]:
                col_val |= (1 << y)
        # For height > 8: 2 bytes per column
        # PicoGraphics expects: B0 = rows 8-15 (bottom), B1 = rows 0-7 (top)
        if target_height > 8:
            columns.append((col_val >> 8) & 0xFF)  # B0: rows 8+
            columns.append(col_val & 0xFF)          # B1: rows 0-7
        else:
            columns.append(col_val & 0xFF)

    return columns


def build_font_t(glyphs, font_height, font_ascent):
    """Build the font_t bytearray."""
    # Determine character set
    codepoints = list(range(0x20, 0x7F)) + EXTENDED_CODEPOINTS
    assert len(codepoints) == NUM_CHARS

    # Find max width
    max_width = 0
    for cp in codepoints:
        if cp in glyphs:
            max_width = max(max_width, glyphs[cp]["width"])
    if max_width == 0:
        max_width = 6  # fallback

    # Build widths table and glyph data
    widths = []
    glyph_data = []
    bytes_per_col = 2 if font_height > 8 else 1

    for cp in codepoints:
        if cp in glyphs:
            g = glyphs[cp]
            w = g["width"]
            widths.append(w)
            cols = glyph_to_columns(g, font_height, font_ascent)
            # Pad to max_width columns
            while len(cols) < max_width * bytes_per_col:
                cols.append(0)
            glyph_data.extend(cols[:max_width * bytes_per_col])
        else:
            # Missing glyph: use space width, blank data
            widths.append(max_width // 2)
            glyph_data.extend([0] * (max_width * bytes_per_col))

    # Assemble font_t
    data = [font_height, max_width] + widths + glyph_data
    return bytes(data)


def main():
    if len(sys.argv) < 2:
        print("Usage: python3 bdf_to_picographics.py <font.bdf>", file=sys.stderr)
        sys.exit(1)

    bdf_path = sys.argv[1]
    glyphs, font_height, font_ascent = parse_bdf(bdf_path)

    print("# Parsed {} glyphs, height={}, ascent={}".format(
        len(glyphs), font_height, font_ascent), file=sys.stderr)

    font_data = build_font_t(glyphs, font_height, font_ascent)

    print("# font_t: {} bytes (height={}, max_width={}, {} chars)".format(
        len(font_data), font_data[0], font_data[1], NUM_CHARS), file=sys.stderr)

    # Output as Python module
    print('"""GohuFont 11px - auto-generated from BDF. Do not edit."""')
    print("")
    print("# PicoGraphics font_t format: height, max_width, widths[105], glyph_data")
    print("# Height: {}px, Max width: {}px, {} characters".format(
        font_data[0], font_data[1], NUM_CHARS))
    print("FONT_11 = bytearray([")

    # Print in rows of 16 bytes
    for i in range(0, len(font_data), 16):
        chunk = font_data[i:i+16]
        hex_str = ", ".join("0x{:02X}".format(b) for b in chunk)
        if i + 16 >= len(font_data):
            print("    {}".format(hex_str))
        else:
            print("    {},".format(hex_str))

    print("])")


if __name__ == "__main__":
    main()
