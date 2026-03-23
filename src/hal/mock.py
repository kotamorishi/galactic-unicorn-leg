"""Mock hardware implementation for PC-based testing.

Provides fake implementations of all HAL interfaces that work
without any MicroPython or Galactic Unicorn hardware.
"""

import time
from hal.interfaces import (
    DisplayInterface, AudioInterface, NetworkInterface,
    ButtonInterface, SystemInterface,
)


class MockDisplay(DisplayInterface):

    def __init__(self):
        self.initialized = False
        self.font = "bitmap8"
        self.pen_color = (0, 0, 0)
        self.brightness = 50
        self.framebuffer = []
        self.update_count = 0

    def init(self):
        self.initialized = True

    def set_font(self, font_name):
        # font_name can be a string ("bitmap8") or bytearray (custom font)
        if isinstance(font_name, (bytes, bytearray)):
            self.font = "custom_{}px".format(font_name[0])  # height is byte 0
        else:
            self.font = font_name

    def set_pen(self, r, g, b):
        self.pen_color = (r, g, b)

    def clear(self):
        self.framebuffer.clear()

    def draw_text(self, text, x, y, wrap=-1, scale=1):
        self.framebuffer.append({
            "type": "text", "text": text,
            "x": x, "y": y, "wrap": wrap, "scale": scale,
            "color": self.pen_color, "font": self.font,
        })

    def measure_text(self, text, scale=1):
        if self.font == "bitmap6":
            char_width = 6
        elif self.font.startswith("custom_"):
            char_width = 6  # GohuFont 11px is 6px wide
        else:
            char_width = 8
        return len(text) * char_width * scale

    def draw_pixel(self, x, y):
        self.framebuffer.append({
            "type": "pixel", "x": x, "y": y,
            "color": self.pen_color,
        })

    def pixel_span(self, x, y, length):
        self.framebuffer.append({
            "type": "pixel_span", "x": x, "y": y, "length": length,
            "color": self.pen_color,
        })

    def draw_line(self, x1, y1, x2, y2):
        self.framebuffer.append({
            "type": "line", "x1": x1, "y1": y1, "x2": x2, "y2": y2,
            "color": self.pen_color,
        })

    def draw_rectangle(self, x, y, w, h):
        self.framebuffer.append({
            "type": "rectangle", "x": x, "y": y, "w": w, "h": h,
            "color": self.pen_color,
        })

    def update(self):
        self.update_count += 1

    def set_brightness(self, level):
        self.brightness = max(0, min(100, level))

    def get_brightness(self):
        return self.brightness

    def get_light_level(self):
        return 2000


class MockAudio(AudioInterface):

    def __init__(self):
        self.initialized = False
        self.volume = 0.5
        self.playing = False
        self.play_log = []

    def init(self):
        self.initialized = True

    def play_tone(self, channel, waveform, frequency, volume,
                  attack, decay, sustain, release, duration_ms):
        self.playing = True
        self.play_log.append({
            "type": "tone", "channel": channel, "waveform": waveform,
            "frequency": frequency, "volume": volume,
            "attack": attack, "decay": decay,
            "sustain": sustain, "release": release,
            "duration_ms": duration_ms,
        })

    async def play_sequence(self, notes):
        for note in notes:
            self.play_tone(
                channel=note.get("channel", 0),
                waveform=note.get("waveform", "square"),
                frequency=note["frequency"],
                volume=note.get("volume", 0.5),
                attack=note.get("attack", 0.01),
                decay=note.get("decay", 0.1),
                sustain=note.get("sustain", 0.5),
                release=note.get("release", 0.2),
                duration_ms=note.get("duration_ms", 200),
            )
        self.playing = False

    def stop(self):
        self.playing = False

    def set_volume(self, volume):
        self.volume = max(0.0, min(1.0, volume))

    def get_volume(self):
        return self.volume


class MockNetwork(NetworkInterface):

    def __init__(self):
        self.connected = False
        self.ip = None
        self.ssid = None
        self.ap_active = False
        self.ap_ssid = None
        self.ntp_synced = False
        self._scan_results = []
        self._connect_should_fail = False

    def connect_sta(self, ssid, password, timeout_s=30):
        if self._connect_should_fail:
            return False
        self.connected = True
        self.ssid = ssid
        self.ip = "192.168.1.100"
        return True

    def disconnect_sta(self):
        self.connected = False
        self.ip = None
        self.ssid = None

    def start_ap(self, ssid, password=None):
        self.ap_active = True
        self.ap_ssid = ssid

    def stop_ap(self):
        self.ap_active = False
        self.ap_ssid = None

    def is_connected(self):
        return self.connected

    def get_ip(self):
        return self.ip if self.connected else None

    def get_ap_ip(self):
        return "192.168.4.1"

    def get_rssi(self):
        return -45 if self.connected else None

    def get_ssid(self):
        return self.ssid if self.connected else None

    def scan_networks(self):
        return self._scan_results

    def sync_ntp(self):
        self.ntp_synced = True
        return True


class MockButtons(ButtonInterface):

    def __init__(self):
        self._pressed = set()

    def press(self, button_name):
        """Test helper: simulate button press."""
        self._pressed.add(button_name)

    def release(self, button_name):
        """Test helper: simulate button release."""
        self._pressed.discard(button_name)

    def is_pressed(self, button_name):
        return button_name in self._pressed


class MockSystem(SystemInterface):

    def __init__(self):
        self.reset_count = 0
        self.free_memory = 150000
        self._rtc_time = (2026, 3, 21, 5, 12, 0, 0, 0)

    def reset(self):
        self.reset_count += 1

    def get_free_memory(self):
        return self.free_memory

    def collect_garbage(self):
        return self.free_memory

    def get_rtc_time(self):
        return self._rtc_time

    def set_rtc_time(self, time_tuple):
        """Test helper: set fake RTC time."""
        self._rtc_time = time_tuple
