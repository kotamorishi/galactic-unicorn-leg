"""Configuration manager with safe file operations.

All config files are JSON stored on the Pico W flash filesystem.
Writes use tmp+rename for atomicity to prevent corruption on power loss.
"""

import os

try:
    import ujson as json
except ImportError:
    import json


WIFI_CONFIG_FILE = "wifi_config.json"
APP_CONFIG_FILE = "app_config.json"
OTA_CONFIG_FILE = "ota_config.json"
VERSION_FILE = "version.json"

DEFAULT_APP_CONFIG = {
    "message": {
        "text": "Hello!",
        "display_mode": "scroll",
        "scroll_speed": "medium",
        "color": {"r": 255, "g": 255, "b": 255},
        "bg_color": {"r": 0, "g": 0, "b": 0},
        "font": "bitmap8",
    },
    "schedules": [],
    "system": {
        "brightness": 50,
        "timezone_offset": 9,
    },
}

DEFAULT_OTA_CONFIG = {
    "repo": "",
    "branch": "main",
    "app_path": "src/",
    "check_hour": 3,
}

DEFAULT_VERSION = {
    "version": "unknown",
}

SCROLL_SPEEDS = ("slow", "medium", "fast")
DISPLAY_MODES = ("fixed", "scroll")
FONTS = ("bitmap6", "bitmap8")
DAYS = ("mon", "tue", "wed", "thu", "fri", "sat", "sun")


def _file_exists(path):
    try:
        os.stat(path)
        return True
    except OSError:
        return False


def _safe_write(path, data):
    """Write JSON data atomically via tmp file + rename."""
    tmp_path = path + ".tmp"
    raw = json.dumps(data)
    with open(tmp_path, "w") as f:
        f.write(raw)
    try:
        os.rename(tmp_path, path)
    except OSError:
        # Some MicroPython builds require remove before rename
        if _file_exists(path):
            os.remove(path)
        os.rename(tmp_path, path)


def _safe_read(path, default=None):
    """Read JSON file. Returns default if missing or corrupted."""
    if not _file_exists(path):
        return default
    try:
        with open(path, "r") as f:
            return json.load(f)
    except (ValueError, OSError):
        return default


def _deep_merge(base, override):
    """Merge override into base recursively. Returns new dict."""
    result = {}
    for k in base:
        if k in override:
            if isinstance(base[k], dict) and isinstance(override[k], dict):
                result[k] = _deep_merge(base[k], override[k])
            else:
                result[k] = override[k]
        else:
            result[k] = base[k]
    for k in override:
        if k not in base:
            result[k] = override[k]
    return result


def _clamp(value, min_val, max_val):
    if value < min_val:
        return min_val
    if value > max_val:
        return max_val
    return value


def _validate_color(color):
    """Validate and sanitize an RGB color dict."""
    if not isinstance(color, dict):
        return {"r": 255, "g": 255, "b": 255}
    return {
        "r": _clamp(int(color.get("r", 255)), 0, 255),
        "g": _clamp(int(color.get("g", 255)), 0, 255),
        "b": _clamp(int(color.get("b", 255)), 0, 255),
    }


def _validate_schedule(sched):
    """Validate and sanitize a single schedule entry."""
    text = str(sched.get("message", ""))
    if len(text) > 128:
        text = text[:128]
    validated = {
        "id": int(sched.get("id", 0)),
        "enabled": bool(sched.get("enabled", True)),
        "start_time": _validate_time_str(sched.get("start_time", "00:00")),
        "end_time": _validate_time_str(sched.get("end_time", "23:59")),
        "days": _validate_days(sched.get("days", list(DAYS))),
        "message": text,
        "sound": _validate_sound(sched.get("sound", {})),
    }
    return validated


def _validate_time_str(time_str):
    """Validate HH:MM format. Returns valid time string."""
    if not isinstance(time_str, str) or len(time_str) != 5:
        return "00:00"
    parts = time_str.split(":")
    if len(parts) != 2:
        return "00:00"
    try:
        h = _clamp(int(parts[0]), 0, 23)
        m = _clamp(int(parts[1]), 0, 59)
        return "{:02d}:{:02d}".format(h, m)
    except (ValueError, TypeError):
        return "00:00"


def _validate_days(days):
    """Validate weekday list."""
    if not isinstance(days, list):
        return list(DAYS)
    return [d for d in days if d in DAYS]


def _validate_sound(sound):
    """Validate sound config within a schedule."""
    if not isinstance(sound, dict):
        return {"enabled": False, "preset_id": 1, "volume": 50}
    return {
        "enabled": bool(sound.get("enabled", False)),
        "preset_id": _clamp(int(sound.get("preset_id", 1)), 1, 20),
        "volume": _clamp(int(sound.get("volume", 50)), 0, 100),
    }


def _validate_message(msg):
    """Validate message config."""
    if not isinstance(msg, dict):
        msg = {}
    text = str(msg.get("text", "Hello!"))
    if len(text) > 128:
        text = text[:128]
    mode = msg.get("display_mode", "scroll")
    if mode not in DISPLAY_MODES:
        mode = "scroll"
    speed = msg.get("scroll_speed", "medium")
    if speed not in SCROLL_SPEEDS:
        speed = "medium"
    font = msg.get("font", "bitmap8")
    if font not in FONTS:
        font = "bitmap8"
    return {
        "text": text,
        "display_mode": mode,
        "scroll_speed": speed,
        "color": _validate_color(msg.get("color", {})),
        "bg_color": _validate_color(msg.get("bg_color", {"r": 0, "g": 0, "b": 0})),
        "font": font,
    }


def _validate_app_config(config):
    """Validate and sanitize full app config."""
    if not isinstance(config, dict):
        config = {}
    merged = _deep_merge(DEFAULT_APP_CONFIG, config)
    merged["message"] = _validate_message(merged.get("message", {}))
    schedules = merged.get("schedules", [])
    if not isinstance(schedules, list):
        schedules = []
    merged["schedules"] = [_validate_schedule(s) for s in schedules]
    system = merged.get("system", {})
    if not isinstance(system, dict):
        system = {}
    merged["system"] = {
        "brightness": _clamp(int(system.get("brightness", 50)), 0, 100),
        "timezone_offset": _clamp(int(system.get("timezone_offset", 9)), -12, 14),
    }
    return merged


# --- Public API ---

def load_wifi_config():
    """Load WiFi config. Returns None if not configured."""
    data = _safe_read(WIFI_CONFIG_FILE)
    if data is None:
        return None
    if not isinstance(data, dict):
        return None
    ssid = data.get("ssid", "")
    password = data.get("password", "")
    if not ssid:
        return None
    return {"ssid": ssid, "password": password}


def save_wifi_config(ssid, password):
    """Save WiFi credentials."""
    _safe_write(WIFI_CONFIG_FILE, {"ssid": ssid, "password": password})


def wifi_config_exists():
    """Check if WiFi config file exists."""
    return _file_exists(WIFI_CONFIG_FILE)


def load_app_config():
    """Load app config with validation. Returns defaults if missing/corrupt."""
    data = _safe_read(APP_CONFIG_FILE, DEFAULT_APP_CONFIG)
    return _validate_app_config(data)


def save_app_config(config):
    """Validate and save app config."""
    validated = _validate_app_config(config)
    _safe_write(APP_CONFIG_FILE, validated)
    return validated


def load_ota_config():
    """Load OTA config. Returns defaults if missing."""
    data = _safe_read(OTA_CONFIG_FILE, DEFAULT_OTA_CONFIG)
    if not isinstance(data, dict):
        return dict(DEFAULT_OTA_CONFIG)
    return _deep_merge(DEFAULT_OTA_CONFIG, data)


def save_ota_config(config):
    """Save OTA config."""
    _safe_write(OTA_CONFIG_FILE, config)


def load_version():
    """Load version info. Returns default if missing."""
    data = _safe_read(VERSION_FILE, DEFAULT_VERSION)
    if not isinstance(data, dict):
        return dict(DEFAULT_VERSION)
    return data


def save_version(version_str):
    """Save version string."""
    _safe_write(VERSION_FILE, {"version": version_str})


def delete_wifi_config():
    """Delete WiFi config (used for factory reset)."""
    if _file_exists(WIFI_CONFIG_FILE):
        os.remove(WIFI_CONFIG_FILE)
