"""Shared filesystem utilities for safe file operations."""

import os

try:
    import ujson as json
except ImportError:
    import json


def file_exists(path):
    """Check if a file exists."""
    try:
        os.stat(path)
        return True
    except OSError:
        return False


def safe_write_json(path, data):
    """Write JSON data atomically via tmp file + rename.

    Skips the write when the file already holds exactly this content: flash is
    good for ~100K erase cycles, and holding a brightness button used to rewrite
    the whole config every 2 seconds whether or not anything changed.
    Returns True if it wrote.
    """
    raw = json.dumps(data)
    try:
        with open(path, "r") as f:
            if f.read() == raw:
                return False
    except OSError:
        pass
    tmp_path = path + ".tmp"
    with open(tmp_path, "w") as f:
        f.write(raw)
    try:
        os.rename(tmp_path, path)
    except OSError:
        if file_exists(path):
            os.remove(path)
        os.rename(tmp_path, path)
    return True


def safe_read_json(path, default=None):
    """Read JSON file. Returns default if missing or corrupted."""
    if not file_exists(path):
        return default
    try:
        with open(path, "r") as f:
            return json.load(f)
    except (ValueError, OSError):
        return default
