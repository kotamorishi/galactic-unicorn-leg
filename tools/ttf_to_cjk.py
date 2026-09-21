"""Convert a CJK pixel font (TTF) to a flat glyph file the device can seek into.

PicoGraphics font_t holds 105 glyphs, which is nowhere near enough for Japanese,
so CJK text is composed into a 1-bit bitmap instead and handed to the renderer's
existing mono bitmap path. This builds the glyph store that composition reads.

Records are fixed size and sorted by codepoint, so the device binary-searches the
file with seek() and never holds an index in RAM:

  u16 BE codepoint | u8 advance width | MAX_WIDTH * 2 column bytes

Each column is a little-endian u16 bitmask, bit N = row N from the top — the same
bit order src/display/cjk_font.py reads back.

Usage:
  python3 ttf_to_cjk.py <font.ttf> <pt_size> [panel_height] > ../src/display/cjk11.bin

k8x12 (https://littlelimit.net/k8x12.htm) at 12pt gives 11px-tall glyphs with an
8px advance for kanji/kana and 4px for halfwidth, which is the tallest full-JIS
coverage that fits an 11-row panel:

  python3 ttf_to_cjk.py ../k8x12.ttf 12 11 > ../src/display/cjk11.bin
"""

import sys
import struct
from PIL import Image, ImageDraw, ImageFont
from fontTools.ttLib import TTFont

MAX_WIDTH = 8
# Glyphs whose ink spans the full height, used to find the shared baseline
BASELINE_PROBE = "本日国晴天亜"


def measure_baseline(font, px):
    """Return the canvas row the tallest glyphs start on."""
    img = Image.new("L", (px * 12, px * 4), 0)
    ImageDraw.Draw(img).text((0, px), BASELINE_PROBE, fill=255, font=font)
    bbox = img.getbbox()
    if bbox is None:
        raise ValueError("baseline probe rendered blank")
    return bbox[1]


def build(ttf_path, px, height):
    font = ImageFont.truetype(ttf_path, px)
    measure = ImageDraw.Draw(Image.new("L", (1, 1)))
    top = measure_baseline(font, px)
    canvas = px * 3

    codepoints = sorted(
        cp for cp in TTFont(ttf_path).getBestCmap() if 0x20 <= cp <= 0xFFFF
    )

    out = bytearray()
    clipped = []
    for cp in codepoints:
        char = chr(cp)
        advance = min(int(measure.textlength(char, font=font)), MAX_WIDTH)
        img = Image.new("L", (canvas, canvas), 0)
        ImageDraw.Draw(img).text((0, px), char, fill=255, font=font)

        columns = []
        for x in range(advance):
            value = 0
            for y in range(height):
                if img.getpixel((x, top + y)) > 127:
                    value |= 1 << y
            columns.append(value)

        # Ink below the panel is dropped; report it rather than silently crop
        for y in range(height, canvas - top):
            if any(img.getpixel((x, top + y)) > 127 for x in range(advance)):
                clipped.append(char)
                break

        record = struct.pack(">HB", cp, advance)
        record += b"".join(struct.pack("<H", c) for c in columns)
        out += record.ljust(3 + MAX_WIDTH * 2, b"\0")

    return out, codepoints, clipped


def main():
    if len(sys.argv) < 3:
        print(__doc__, file=sys.stderr)
        sys.exit(1)

    ttf_path = sys.argv[1]
    px = int(sys.argv[2])
    height = int(sys.argv[3]) if len(sys.argv) > 3 else 11

    data, codepoints, clipped = build(ttf_path, px, height)
    record = 3 + MAX_WIDTH * 2
    print("# {} glyphs, record={}B, total={}KB".format(
        len(codepoints), record, len(data) // 1024), file=sys.stderr)
    if clipped:
        print("# WARNING {} glyphs have ink below row {}: {}".format(
            len(clipped), height - 1, "".join(clipped[:40])), file=sys.stderr)

    sys.stdout.buffer.write(data)


if __name__ == "__main__":
    main()
