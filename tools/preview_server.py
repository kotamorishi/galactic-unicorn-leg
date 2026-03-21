"""Local preview server for Web UI design review.

Runs on PC using Python's built-in http.server.
Serves the same HTML templates that would run on the Pico W.
"""

import sys
import os
import json
from http.server import HTTPServer, BaseHTTPRequestHandler

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))

from web.templates import (
    render_index, render_message_page, render_schedule_page,
    render_sound_page, render_system_page, render_wifi_setup_page,
)
from audio.presets import get_preset_list

# Fake data for preview
FAKE_MESSAGE = {
    "text": "Hello World! This is a scrolling message on Galactic Unicorn.",
    "display_mode": "scroll",
    "scroll_speed": "medium",
    "color": {"r": 255, "g": 200, "b": 0},
    "font": "bitmap8",
}

FAKE_SCHEDULES = [
    {
        "id": 1, "enabled": True,
        "start_time": "08:00", "end_time": "09:00",
        "days": ["mon", "tue", "wed", "thu", "fri"],
        "sound": {"enabled": True, "preset_id": 4, "volume": 70},
    },
    {
        "id": 2, "enabled": False,
        "start_time": "18:00", "end_time": "19:30",
        "days": ["sat", "sun"],
        "sound": {"enabled": False, "preset_id": 1, "volume": 50},
    },
]

FAKE_WIFI_STATUS = {
    "mode": "sta",
    "connected": True,
    "ip": "192.168.1.42",
    "ssid": "MyHomeWiFi",
    "rssi": -45,
    "ntp_synced": True,
}

FAKE_SYSTEM = {"brightness": 65, "timezone_offset": 9}
FAKE_VERSION = {"version": "abc1234"}

FAKE_NETWORKS = [
    {"ssid": "MyHomeWiFi", "rssi": -35},
    {"ssid": "Neighbor_5G", "rssi": -60},
    {"ssid": "CoffeeShop_Free", "rssi": -72},
]


class PreviewHandler(BaseHTTPRequestHandler):

    def do_GET(self):
        path = self.path.split("?")[0]
        routes = {
            "/": lambda: render_index(),
            "/message": lambda: render_message_page(FAKE_MESSAGE),
            "/schedule": lambda: render_schedule_page(FAKE_SCHEDULES),
            "/sound": lambda: render_sound_page(get_preset_list()),
            "/system": lambda: render_system_page(FAKE_WIFI_STATUS, FAKE_SYSTEM, FAKE_VERSION),
            "/wifi-setup": lambda: render_wifi_setup_page(FAKE_NETWORKS),
        }

        if path in routes:
            html = routes[path]()
            self.send_response(200)
            self.send_header("Content-Type", "text/html; charset=utf-8")
            self.end_headers()
            self.wfile.write(html.encode("utf-8"))
        else:
            self.send_response(404)
            self.end_headers()
            self.wfile.write(b"Not Found")

    def do_POST(self):
        # Stub API responses for preview
        self.send_response(200)
        self.send_header("Content-Type", "application/json")
        self.end_headers()
        self.wfile.write(json.dumps({"status": "ok (preview mode)"}).encode())

    def log_message(self, format, *args):
        print(f"  {args[0]}")


if __name__ == "__main__":
    port = 8080
    server = HTTPServer(("0.0.0.0", port), PreviewHandler)
    print(f"Preview server running at http://localhost:{port}")
    print(f"Pages:")
    print(f"  http://localhost:{port}/          - Home")
    print(f"  http://localhost:{port}/message   - Message Settings")
    print(f"  http://localhost:{port}/schedule  - Schedule Settings")
    print(f"  http://localhost:{port}/sound     - Sound Settings")
    print(f"  http://localhost:{port}/system    - System Settings")
    print(f"  http://localhost:{port}/wifi-setup - WiFi Setup")
    print()
    print("Press Ctrl+C to stop.")
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\nStopped.")
