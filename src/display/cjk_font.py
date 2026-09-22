"""Compose Japanese text into a 1-bit bitmap for the renderer's mono path.

PicoGraphics font_t has 105 glyph slots, so `font11` cannot carry kanji. Instead
this reads glyphs from display/cjk11.bin (built by tools/ttf_to_cjk.py) and packs
them into the same mono bitmap layout the /api/bitmap endpoint already uses, so
scrolling, colours and the indicator bar all come for free.

The file is fixed-size records sorted by codepoint, so lookup is a binary search
with seek() and needs no RAM index. That costs ~log2(7170) = 13 reads per
character, but it runs once when the message changes, never inside the frame loop.
"""


def _data_dir():
    """Directory holding the font binaries, independent of cwd.

    MicroPython sets __file__ for filesystem modules; tools/preview_server.py
    and the tests chdir() into a temp dir, which used to make these paths miss.
    """
    try:
        f = __file__.replace("\\", "/")
        return f.rsplit("/", 1)[0] if "/" in f else "display"
    except (NameError, AttributeError):  # pragma: no cover
        return "display"


FONT_PATH = _data_dir() + "/cjk11.bin"
HEIGHT = 11
MAX_WIDTH = 8
RECORD = 3 + MAX_WIDTH * 2

# Width used for a codepoint the font does not carry (drawn as blank)
MISSING_WIDTH = 4


def needs_bitmap(text):
    """True if text contains anything the 105-slot ASCII fonts cannot draw."""
    for ch in text:
        if ord(ch) > 0x7E:
            return True
    return False


def _find(f, count, cp, buf):
    """Binary-search the record whose codepoint is cp. Returns True if found."""
    lo = 0
    hi = count - 1
    while lo <= hi:
        mid = (lo + hi) >> 1
        f.seek(mid * RECORD)
        f.readinto(buf)
        key = (buf[0] << 8) | buf[1]
        if key < cp:
            lo = mid + 1
        elif key > cp:
            hi = mid - 1
        else:
            return True
    return False


def render(text):
    """Return (width, bitmap) for text, or None if the glyph file is missing.

    bitmap is row-major, 1 bit per pixel, MSB first — the layout
    DisplayRenderer._bitmap_get_pixel expects.
    """
    columns = []
    buf = bytearray(RECORD)
    try:
        f = open(FONT_PATH, "rb")
    except OSError:
        return None
    try:
        f.seek(0, 2)
        count = f.tell() // RECORD
        for ch in text:
            if _find(f, count, ord(ch), buf):
                advance = buf[2]
                for i in range(advance):
                    columns.append(buf[3 + i * 2] | (buf[4 + i * 2] << 8))
            else:
                for _ in range(MISSING_WIDTH):
                    columns.append(0)
    finally:
        f.close()

    width = len(columns)
    if width == 0:
        return 0, bytearray(0)

    row_bytes = (width + 7) // 8
    bitmap = bytearray(row_bytes * HEIGHT)
    for x in range(width):
        column = columns[x]
        if not column:
            continue
        byte_x = x >> 3
        mask = 0x80 >> (x & 7)
        for y in range(HEIGHT):
            if column >> y & 1:
                bitmap[y * row_bytes + byte_x] |= mask

    return width, bitmap
