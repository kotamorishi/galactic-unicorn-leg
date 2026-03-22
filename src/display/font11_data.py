"""Font loader — reads font11.bin binary file to save RAM."""


FONT_11 = None


def get_font():
    """Lazy-load font_t bytearray from binary file on first use."""
    global FONT_11
    if FONT_11 is None:
        with open("display/font11.bin", "rb") as f:
            FONT_11 = bytearray(f.read())
    return FONT_11
