"""Font loader — reads font11.bin binary file to save RAM."""



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


FONT_PATH = _data_dir() + "/font11.bin"
FONT_11 = None


def get_font():
    """Lazy-load font_t bytearray from binary file on first use."""
    global FONT_11
    if FONT_11 is None:
        with open(FONT_PATH, "rb") as f:
            FONT_11 = bytearray(f.read())
    return FONT_11
