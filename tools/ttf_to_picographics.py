"""Convert a TTF/OTF font to PicoGraphics font_t bytearray format.

Rasterizes the font at the target pixel height using Pillow,
then encodes as column-major bitmap data for PicoGraphics.

Usage:
  python3 ttf_to_picographics.py <font.ttf> [height] [--upper] > ../src/display/font11.bin

--upper sizes the font so CAPITALS fill the full height and maps a-z to the
uppercase glyphs. For a 53x11 LED sign this buys ~3px of glyph height over
mixed-case fitting. Glyphs that overflow that box (Q, parens, @, /) are
re-rendered one size down so they stay legible instead of being cropped.
"""

import sys
from PIL import Image, ImageDraw, ImageFont


EXTENDED_CODEPOINTS = [
    0x00C6, 0x00D8, 0x00C5, 0x00E6, 0x00F8,
    0x00E5, 0x00DE, 0x00FE, 0x00A9, 0x00B0,
]
NUM_CHARS = 95 + len(EXTENDED_CODEPOINTS)

# Reference glyphs for --upper sizing: no descenders, no Q tail
CAPS_REF = "HEXOB05"
LOWER_TO_UPPER = {0x00E6: 0x00C6, 0x00F8: 0x00D8, 0x00E5: 0x00C5, 0x00FE: 0x00DE}


def find_font_size(ttf_path, target_height, test_chars):
    """Find the largest font point size whose tallest test glyph fits in target_height."""
    for sz in range(target_height * 3, 0, -1):
        font = ImageFont.truetype(ttf_path, sz)
        img = Image.new("L", (len(test_chars) * sz, sz * 3), 0)
        draw = ImageDraw.Draw(img)
        draw.text((0, 0), test_chars, fill=255, font=font)
        bbox = img.getbbox()
        if bbox:
            h = bbox[3] - bbox[1]
            if h <= target_height:
                return sz, font
    return 1, ImageFont.truetype(ttf_path, 1)


def measure_global_metrics(font, target_height, test_chars):
    """Measure the global top and bottom of the reference glyphs for a consistent baseline."""
    canvas_h = target_height * 3
    img = Image.new("L", (len(test_chars) * canvas_h, canvas_h), 0)
    draw = ImageDraw.Draw(img)
    draw.text((0, 0), test_chars, fill=255, font=font)
    bbox = img.getbbox()
    if bbox is None:
        return 0, target_height
    return bbox[1], bbox[3]  # global_top, global_bottom in canvas coords


def rasterize_glyph(font, char, target_height, global_top, global_bottom):
    """Render a single character aligned to global baseline."""
    global_h = global_bottom - global_top
    y_shift = (target_height - global_h) // 2 - global_top  # shift to center in target

    # Render on large canvas
    canvas_sz = target_height * 3
    img = Image.new("L", (canvas_sz, canvas_sz), 0)
    draw = ImageDraw.Draw(img)
    draw.text((0, 0), char, fill=255, font=font)

    # Find horizontal bounds of this glyph
    bbox = img.getbbox()
    if bbox is None:
        space_w = max(target_height // 3, 2)
        return space_w, [[0] * space_w for _ in range(target_height)], False

    left, ink_top, right, ink_bottom = bbox
    glyph_w = right - left
    clipped = ink_top < global_top or ink_bottom > global_top + target_height

    # Extract glyph pixels with global vertical alignment
    width = glyph_w + 1  # +1 for spacing
    grid = []
    for y in range(target_height):
        row = []
        src_y = y - y_shift  # map target row to canvas row
        for x in range(width):
            src_x = left + x
            if 0 <= src_y < canvas_sz and 0 <= src_x < canvas_sz:
                row.append(1 if img.getpixel((src_x, src_y)) > 127 else 0)
            else:
                row.append(0)
        grid.append(row)

    return width, grid, clipped


def rasterize_fitted(ttf_path, char, target_height, max_size):
    """Render one glyph at the largest size that fits target_height, ink-centred.

    Used for glyphs the main size would crop (Q's tail, brackets, @, /).
    Never goes above max_size, or short glyphs like "_" would balloon in width.
    """
    canvas_sz = target_height * 4
    for sz in range(max_size, 0, -1):
        font = ImageFont.truetype(ttf_path, sz)
        img = Image.new("L", (canvas_sz, canvas_sz), 0)
        ImageDraw.Draw(img).text((0, 0), char, fill=255, font=font)
        bbox = img.getbbox()
        if bbox is None:
            continue
        left, top, right, bottom = bbox
        if bottom - top > target_height:
            continue
        width = right - left + 1
        pad = (target_height - (bottom - top)) // 2
        grid = []
        for y in range(target_height):
            src_y = top - pad + y
            grid.append([
                1 if 0 <= src_y < canvas_sz and img.getpixel((left + x, src_y)) > 127 else 0
                for x in range(width)
            ])
        return width, grid
    raise ValueError("no size fits {!r}".format(char))


def grid_to_columns(grid, width, height):
    """Convert grid to column-major bytes. B0=rows8+, B1=rows0-7."""
    columns = []
    for x in range(width):
        col_val = 0
        for y in range(height):
            if y < len(grid) and x < len(grid[y]) and grid[y][x]:
                col_val |= (1 << y)
        if height > 8:
            columns.append((col_val >> 8) & 0xFF)
            columns.append(col_val & 0xFF)
        else:
            columns.append(col_val & 0xFF)
    return columns


def main():
    if len(sys.argv) < 2:
        print("Usage: python3 ttf_to_picographics.py <font.ttf> [height]", file=sys.stderr)
        sys.exit(1)

    args = [a for a in sys.argv[1:] if not a.startswith("--")]
    upper_only = "--upper" in sys.argv

    ttf_path = args[0]
    target_height = int(args[1]) if len(args) > 1 else 11

    ref_chars = CAPS_REF if upper_only else "".join(chr(c) for c in range(0x21, 0x7F))
    sz, font = find_font_size(ttf_path, target_height, ref_chars)
    print("# Font size: {}pt for {}px target (upper_only={})".format(
        sz, target_height, upper_only), file=sys.stderr)

    global_top, global_bottom = measure_global_metrics(font, target_height, ref_chars)
    print("# Global metrics: top={}, bottom={}, height={}".format(
        global_top, global_bottom, global_bottom - global_top), file=sys.stderr)

    codepoints = list(range(0x20, 0x7F)) + EXTENDED_CODEPOINTS

    glyphs = {}
    max_width = 0
    refit = []
    for cp in codepoints:
        w, grid, clipped = rasterize_glyph(
            font, chr(cp), target_height, global_top, global_bottom)
        if clipped:
            w, grid = rasterize_fitted(ttf_path, chr(cp), target_height, sz)
            refit.append(chr(cp))
        glyphs[cp] = (w, grid)
        max_width = max(max_width, w)

    if refit:
        print("# Re-fitted (would have been cropped): {}".format("".join(refit)),
              file=sys.stderr)

    if upper_only:
        for cp in range(ord("a"), ord("z") + 1):
            glyphs[cp] = glyphs[cp - 32]
        for lo, up in LOWER_TO_UPPER.items():
            glyphs[lo] = glyphs[up]
        max_width = max(w for w, _ in glyphs.values())

    print("# Max width: {}px, {} chars".format(max_width, len(codepoints)), file=sys.stderr)

    bytes_per_col = 2 if target_height > 8 else 1
    widths = []
    glyph_data = []
    for cp in codepoints:
        w, grid = glyphs[cp]
        widths.append(w)
        cols = grid_to_columns(grid, w, target_height)
        while len(cols) < max_width * bytes_per_col:
            cols.append(0)
        glyph_data.extend(cols[:max_width * bytes_per_col])

    data = bytes([target_height, max_width] + widths + glyph_data)
    print("# font_t: {} bytes".format(len(data)), file=sys.stderr)

    # Preview
    for ch in "AHeg!":
        cp = ord(ch)
        w, grid = glyphs[cp]
        print("# '{}' ({}px):".format(ch, w), file=sys.stderr)
        for row in grid:
            print("#   " + "".join("#" if p else "." for p in row[:w]), file=sys.stderr)

    sys.stdout.buffer.write(data)


if __name__ == "__main__":
    main()
