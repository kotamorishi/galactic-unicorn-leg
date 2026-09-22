"""Every src/ module must compile under MicroPython, not just CPython.

The test suite runs on CPython, so syntax MicroPython rejects ships green —
`yield from` inside an async generator did exactly that. mpy-cross is the only
cheap check that runs the real MicroPython parser.

Skipped if mpy-cross is not installed: `pip install mpy-cross`.
"""

import os
import subprocess

import pytest

mpy_cross = pytest.importorskip("mpy_cross")

SRC = os.path.join(os.path.dirname(__file__), "..", "src")

# Vendored third-party; not ours to fix
EXCLUDE = {"lib/microdot.py"}


def _sources():
    out = []
    for root, dirs, files in os.walk(SRC):
        dirs[:] = [d for d in dirs if d != "__pycache__"]
        for name in files:
            if not name.endswith(".py"):
                continue
            rel = os.path.relpath(os.path.join(root, name), SRC).replace("\\", "/")
            if rel not in EXCLUDE:
                out.append(rel)
    return sorted(out)


@pytest.mark.parametrize("rel", _sources())
def test_compiles_under_micropython(rel, tmp_path):
    result = subprocess.run(
        [mpy_cross.mpy_cross, "-o", str(tmp_path / "out.mpy"), os.path.join(SRC, rel)],
        capture_output=True,
        text=True,
    )
    assert result.returncode == 0, "{}\n{}".format(rel, result.stderr.strip())
