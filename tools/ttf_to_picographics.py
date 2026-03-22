"""Convert a TTF/OTF font to PicoGraphics font_t bytearray format.

Rasterizes the font at the target pixel height using Pillow,
then encodes as column-major bitmap data for PicoGraphics.

Usage:
  python3 ttf_to_picographics.py <font.ttf> [height] > ../src/display/font11_data.py

Default height is 11.
"""

import sys
from PIL import Image, ImageDraw, ImageFont


# PicoGraphics font_t character set (105 chars)
EXTENDED_CODEPOINTS = [
    0x00C6, 0x00D8, 0x00C5, 0x00E6, 0x00F8,
    0x00E5, 0x00DE, 0x00FE, 0x00A9, 0x00B0,
]
NUM_CHARS = 95 + len(EXTENDED_CODEPOINTS)


def rasterize_glyph(font, char, target_height):
    """Render a single character and return (width, grid) where grid[y][x] = 0 or 1."""
    # Render character on a large canvas to measure
    img = Image.new("L", (target_height * 3, target_height * 3), 0)
    draw = ImageDraw.Draw(img)
    draw.text((0, 0), char, fill=255, font=font)

    # Find bounding box
    bbox = img.getbbox()
    if bbox is None:
        # Space or blank character
        space_w = max(target_height // 3, 2)
        return space_w, [[0] * space_w for _ in range(target_height)]

    left, top, right, bottom = bbox
    glyph_w = right - left
    glyph_h = bottom - top

    # Re-render centered vertically in target_height
    img2 = Image.new("L", (glyph_w + 2, target_height), 0)
    draw2 = ImageDraw.Draw(img2)
    y_off = (target_height - glyph_h) // 2
    draw2.text((-left, y_off - top), char, fill=255, font=font)

    # Convert to binary grid
    width = img2.width
    grid = []
    for y in range(target_height):
        row = []
        for x in range(width):
            row.append(1 if img2.getpixel((x, y)) > 127 else 0)
        grid.append(row)

    return width, grid


def grid_to_columns(grid, width, height):
    """Convert grid to column-major bytes for font_t.

    For height > 8: B0 = rows 8+, B1 = rows 0-7 (PicoGraphics byte order).
    """
    columns = []
    for x in range(width):
        col_val = 0
        for y in range(height):
            if y < len(grid) and x < len(grid[y]) and grid[y][x]:
                col_val |= (1 << y)
        if height > 8:
            columns.append((col_val >> 8) & 0xFF)  # B0: rows 8+
            columns.append(col_val & 0xFF)          # B1: rows 0-7
        else:
            columns.append(col_val & 0xFF)
    return columns


def main():
    if len(sys.argv) < 2:
        print("Usage: python3 ttf_to_picographics.py <font.ttf> [height]", file=sys.stderr)
        sys.exit(1)

    ttf_path = sys.argv[1]
    target_height = int(sys.argv[2]) if len(sys.argv) > 2 else 11

    # Find the right font size that fits in target_height
    # Try sizes from target_height down until it fits
    best_size = target_height
    for sz in range(target_height * 2, 0, -1):
        font = ImageFont.truetype(ttf_path, sz)
        # Test with a tall character
        img = Image.new("L", (sz * 3, sz * 3), 0)
        draw = ImageDraw.Draw(img)
        draw.text((0, 0), "Hg|", fill=255, font=font)
        bbox = img.getbbox()
        if bbox:
            h = bbox[3] - bbox[1]
            if h <= target_height:
                best_size = sz
                break

    font = ImageFont.truetype(ttf_path, best_size)
    print("# Using font size {} for target height {}px".format(best_size, target_height), file=sys.stderr)

    # Build character set
    codepoints = list(range(0x20, 0x7F)) + EXTENDED_CODEPOINTS

    # Rasterize all glyphs
    glyphs = {}
    max_width = 0
    for cp in codepoints:
        ch = chr(cp)
        w, grid = rasterize_glyph(font, ch, target_height)
        glyphs[cp] = (w, grid)
        max_width = max(max_width, w)

    print("# Max glyph width: {}px, {} characters".format(max_width, len(codepoints)), file=sys.stderr)

    # Build font_t
    bytes_per_col = 2 if target_height > 8 else 1
    widths = []
    glyph_data = []

    for cp in codepoints:
        w, grid = glyphs[cp]
        widths.append(w)
        cols = grid_to_columns(grid, w, target_height)
        # Pad to max_width
        while len(cols) < max_width * bytes_per_col:
            cols.append(0)
        glyph_data.extend(cols[:max_width * bytes_per_col])

    data = bytes([target_height, max_width] + widths + glyph_data)
    print("# font_t: {} bytes".format(len(data)), file=sys.stderr)

    # Preview some glyphs
    for ch in "AHe!":
        cp = ord(ch)
        w, grid = glyphs[cp]
        print("# Glyph '{}' ({}px wide):".format(ch, w), file=sys.stderr)
        for row in grid:
            print("#   " + "".join("#" if p else "." for p in row), file=sys.stderr)

    # Output Python module
    print('"""Custom font {}px - auto-generated from TTF. Do not edit."""'.format(target_height))
    print("")
    print("FONT_11 = bytearray([")
    for i in range(0, len(data), 16):
        chunk = data[i:i + 16]
        hex_str = ", ".join("0x{:02X}".format(b) for b in chunk)
        if i + 16 >= len(data):
            print("    {}".format(hex_str))
        else:
            print("    {},".format(hex_str))
    print("])")


if __name__ == "__main__":
    main()
