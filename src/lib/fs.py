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
    """Write JSON data atomically via tmp file + rename."""
    tmp_path = path + ".tmp"
    raw = json.dumps(data)
    with open(tmp_path, "w") as f:
        f.write(raw)
    try:
        os.rename(tmp_path, path)
    except OSError:
        if file_exists(path):
            os.remove(path)
        os.rename(tmp_path, path)


def safe_read_json(path, default=None):
    """Read JSON file. Returns default if missing or corrupted."""
    if not file_exists(path):
        return default
    try:
        with open(path, "r") as f:
            return json.load(f)
    except (ValueError, OSError):
        return default
