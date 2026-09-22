"""Local preview server for the Web UI.

Runs the real microdot app and routes (src/web) on the PC, backed by the mock
HAL, so pages, static assets and API calls behave like on the device.

    python tools/preview_server.py            # http://localhost:8080
    python tools/preview_server.py --port 9000

Config files are written to a temp directory, never to src/.
"""

import argparse
import asyncio
import os
import sys
import tempfile

SRC = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "src")
sys.path.insert(0, SRC)

from hal.mock import MockDisplay, MockAudio, MockNetwork, MockSystem  # noqa: E402
from config import config_manager  # noqa: E402
from display.renderer import DisplayRenderer  # noqa: E402
from audio.player import AudioPlayer  # noqa: E402
from scheduler.scheduler import Scheduler  # noqa: E402
from wifi.manager import WiFiManager  # noqa: E402
from web.server import create_app  # noqa: E402


SAMPLE_CONFIG = {
    "message": {
        "text": "Hello from Galactic Unicorn",
        "display_mode": "scroll",
        "scroll_speed": "medium",
        "color": {"r": 255, "g": 178, "b": 36},
        "font": "bitmap8",
    },
    "schedules": [
        {"id": 1, "enabled": True, "start_time": "07:00", "end_time": "08:30",
         "days": ["mon", "tue", "wed", "thu", "fri"], "message": "GOOD MORNING",
         "color": {"r": 255, "g": 212, "b": 0},
         "sound": {"enabled": True, "preset_id": 4, "volume": 50}},
        {"id": 2, "enabled": True, "start_time": "07:30", "end_time": "08:00",
         "days": ["tue", "fri"], "message": "Trash day!",
         "color": {"r": 32, "g": 224, "b": 96},
         "sound": {"enabled": True, "preset_id": 15, "volume": 75}},
        {"id": 3, "enabled": True, "start_time": "18:00", "end_time": "19:00",
         "days": [], "message": "Dinner time",
         "color": {"r": 0, "g": 216, "b": 255},
         "sound": {"enabled": False, "preset_id": 1, "volume": 50}},
        {"id": 4, "enabled": False, "start_time": "22:00", "end_time": "06:00",
         "days": ["fri", "sat"], "message": "", "color": {},
         "sound": {"enabled": False, "preset_id": 1, "volume": 25}},
    ],
    "system": {"brightness": 50, "brightness_offset": 10, "timezone_offset": 0},
}


def build_app(workdir, sample=True):
    """Create the real web app with mock hardware. chdir()s into workdir."""
    os.chdir(workdir)
    if sample and not os.path.exists(config_manager.APP_CONFIG_FILE):
        config_manager.save_app_config(SAMPLE_CONFIG)

    system = MockSystem()
    display = MockDisplay()
    display.init()
    audio = MockAudio()
    audio.init()
    net = MockNetwork()
    net.connect_sta("MyHomeWiFi", "x")

    sched = Scheduler(system)
    cfg = config_manager.load_app_config()
    sched.set_timezone_offset(cfg["system"]["timezone_offset"])
    sched.set_schedules(cfg["schedules"])
    offset = {"v": cfg["system"]["brightness_offset"]}

    ctx = {
        "config_manager": config_manager,
        "wifi_manager": WiFiManager(net, system),
        "display_renderer": DisplayRenderer(display),
        "audio_player": AudioPlayer(audio),
        "scheduler": sched,
        "system_hal": system,
        "ota_updater": None,
        "invalidate_msg_cache": lambda: None,
        "set_brightness_offset": lambda v: offset.__setitem__("v", v),
        "get_brightness_offset": lambda: offset["v"],
        "update_auto_brightness": lambda: None,
    }
    return create_app(ctx)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--port", type=int, default=8080)
    ap.add_argument("--empty", action="store_true", help="start without sample schedules")
    args = ap.parse_args()
    workdir = tempfile.mkdtemp(prefix="gu-preview-")
    app = build_app(workdir, sample=not args.empty)
    print("Preview: http://localhost:{}/  (settings: /settings, wifi setup: /setup)".format(args.port))
    print("Config dir:", workdir)
    try:
        asyncio.run(app.start_server(host="0.0.0.0", port=args.port))
    except KeyboardInterrupt:
        print("\nStopped.")


if __name__ == "__main__":
    main()
