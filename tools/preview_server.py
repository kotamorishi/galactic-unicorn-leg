"""Local preview server for Web UI design review."""

import sys
import os
import json
import datetime
import asyncio
from http.server import HTTPServer, BaseHTTPRequestHandler

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))

from web.templates import render_main_page, render_settings_page, render_setup_page
from audio.presets import get_preset_list

FAKE_CONFIG = {
    "message": {
        "text": "Hello World! Welcome to Galactic Unicorn.",
        "display_mode": "scroll",
        "scroll_speed": "medium",
        "color": {"r": 255, "g": 200, "b": 0},
        "font": "bitmap8",
    },
    "schedules": [
        {
            "id": 1, "enabled": True,
            "start_time": "08:00", "end_time": "09:00",
            "days": ["mon", "tue", "wed", "thu", "fri"],
            "sound": {"enabled": True, "preset_id": 4, "volume": 50},
        },
        {
            "id": 2, "enabled": False,
            "start_time": "18:00", "end_time": "19:30",
            "days": ["sat", "sun"],
            "sound": {"enabled": False, "preset_id": 1, "volume": 50},
        },
    ],
    "system": {"brightness": 65, "timezone_offset": 9},
}

def _now_time():
    now = datetime.datetime.now()
    day_names = ["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"]
    return now.strftime("%H:%M:%S"), day_names[now.weekday()]

FAKE_STATUS = {
    "active": True,
    "message": "Hello World! Welcome to Galactic Unicorn.",
    "active_end": "09:00",
    "next_start": None,
    "next_day": None,
}

FAKE_STATUS_OFF = {
    "active": False,
    "message": "Hello World! Welcome to Galactic Unicorn.",
    "active_end": None,
    "next_start": "08:00",
    "next_day": "Mon",
}

FAKE_WIFI = {
    "mode": "sta", "connected": True, "ip": "192.168.1.42",
    "ssid": "MyHomeWiFi", "rssi": -45, "ntp_synced": True,
}

FAKE_VERSION = {"version": "abc1234"}

FAKE_NETWORKS = [
    {"ssid": "MyHomeWiFi", "rssi": -35},
    {"ssid": "Neighbor_5G", "rssi": -60},
    {"ssid": "CoffeeShop_Free", "rssi": -72},
]


class Handler(BaseHTTPRequestHandler):
    def do_GET(self):
        path = self.path.split("?")[0]
        presets = get_preset_list()

        def _status_with_time(base):
            s = dict(base)
            s["time"], s["day"] = _now_time()
            return s

        pages = {
            "/": lambda: render_main_page(FAKE_CONFIG, presets, _status_with_time(FAKE_STATUS)),
            "/off": lambda: render_main_page(FAKE_CONFIG, presets, _status_with_time(FAKE_STATUS_OFF)),
            "/settings": lambda: render_settings_page(FAKE_WIFI, FAKE_VERSION, 145000),
            "/setup": lambda: render_setup_page(FAKE_NETWORKS),
        }

        if self.do_GET_api(path):
            return

        if path in pages:
            self.send_response(200)
            self.send_header("Content-Type", "text/html; charset=utf-8")
            self.end_headers()
            gen = pages[path]()
            # Collect async generator chunks
            async def collect():
                parts = []
                async for chunk in gen:
                    parts.append(chunk)
                return "".join(parts)
            html = asyncio.run(collect())
            self.wfile.write(html.encode("utf-8"))
        else:
            self.send_response(404)
            self.end_headers()
            self.wfile.write(b"Not Found")

    def do_GET_api(self, path):
        if path == "/api/status":
            now = datetime.datetime.now()
            day_names = ["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"]
            data = dict(FAKE_STATUS)
            data["time"] = now.strftime("%H:%M:%S")
            data["day"] = day_names[now.weekday()]
            self.send_response(200)
            self.send_header("Content-Type", "application/json")
            self.end_headers()
            self.wfile.write(json.dumps(data).encode())
            return True
        return False

    def do_POST(self):
        self.send_response(200)
        self.send_header("Content-Type", "application/json")
        self.end_headers()
        self.wfile.write(json.dumps({"status": "ok (preview)"}).encode())

    def log_message(self, fmt, *args):
        print(f"  {args[0]}")


if __name__ == "__main__":
    port = 8080
    server = HTTPServer(("0.0.0.0", port), Handler)
    print(f"Preview: http://localhost:{port}")
    print(f"  /         Main (active)")
    print(f"  /off      Main (inactive)")
    print(f"  /settings Device settings")
    print(f"  /setup    WiFi setup")
    print("Ctrl+C to stop.")
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\nStopped.")
