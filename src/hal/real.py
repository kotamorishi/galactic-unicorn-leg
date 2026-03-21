"""Real hardware implementation for Galactic Unicorn.

Only import this module on the actual Pico W device.
"""

from galactic import GalacticUnicorn
from picographics import PicoGraphics, DISPLAY_GALACTIC_UNICORN
from hal.interfaces import (
    DisplayInterface, AudioInterface, NetworkInterface,
    ButtonInterface, SystemInterface,
)


class RealDisplay(DisplayInterface):

    def __init__(self):
        self._gu = None
        self._gfx = None
        self._current_pen = None

    def init(self):
        self._gu = GalacticUnicorn()
        self._gfx = PicoGraphics(display=DISPLAY_GALACTIC_UNICORN)
        return self._gu

    def set_font(self, font_name):
        self._gfx.set_font(font_name)

    def set_pen(self, r, g, b):
        self._current_pen = self._gfx.create_pen(r, g, b)
        self._gfx.set_pen(self._current_pen)

    def clear(self):
        black = self._gfx.create_pen(0, 0, 0)
        self._gfx.set_pen(black)
        self._gfx.clear()
        if self._current_pen is not None:
            self._gfx.set_pen(self._current_pen)

    def draw_text(self, text, x, y, wrap=-1, scale=1):
        self._gfx.text(text, x, y, wrap, scale)

    def measure_text(self, text, scale=1):
        return self._gfx.measure_text(text, scale)

    def draw_pixel(self, x, y):
        self._gfx.pixel(x, y)

    def draw_line(self, x1, y1, x2, y2):
        self._gfx.line(x1, y1, x2, y2)

    def draw_rectangle(self, x, y, w, h):
        self._gfx.rectangle(x, y, w, h)

    def update(self):
        self._gu.update(self._gfx)

    def set_brightness(self, level):
        # GalacticUnicorn brightness is 0-255, we accept 0-100
        raw = int(level * 2.55)
        self._gu.set_brightness(raw)

    def get_brightness(self):
        return int(self._gu.get_brightness() / 2.55)


class RealAudio(AudioInterface):

    def __init__(self, gu_instance):
        self._gu = gu_instance

    def init(self):
        pass

    def play_tone(self, channel, waveform, frequency, volume,
                  attack, decay, sustain, release, duration_ms):
        ch = self._gu.synth_channel(channel)
        waveform_map = {
            "square": GalacticUnicorn.WAVEFORM_SQUARE,
            "sine": GalacticUnicorn.WAVEFORM_SINE,
            "triangle": GalacticUnicorn.WAVEFORM_TRIANGLE,
            "sawtooth": GalacticUnicorn.WAVEFORM_SAW,
            "noise": GalacticUnicorn.WAVEFORM_NOISE,
        }
        wf = waveform_map.get(waveform, GalacticUnicorn.WAVEFORM_SQUARE)
        ch.configure(
            waveforms=wf,
            frequency=frequency,
            volume=volume,
            attack=attack,
            decay=decay,
            sustain=sustain,
            release=release,
        )
        ch.trigger_attack()
        self._gu.play_synth()

    async def play_sequence(self, notes):
        import uasyncio as asyncio
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
            await asyncio.sleep_ms(note.get("duration_ms", 200))
            ch = self._gu.synth_channel(note.get("channel", 0))
            ch.trigger_release()
            pause = note.get("pause_ms", 50)
            if pause > 0:
                await asyncio.sleep_ms(pause)

    def stop(self):
        self._gu.stop_playing()

    def set_volume(self, volume):
        self._gu.set_volume(volume)

    def get_volume(self):
        return self._gu.get_volume()


class RealNetwork(NetworkInterface):

    def __init__(self):
        self._wlan = None
        self._ap = None

    def connect_sta(self, ssid, password, timeout_s=30):
        import network
        import time
        self._wlan = network.WLAN(network.STA_IF)
        self._wlan.active(True)
        self._wlan.connect(ssid, password)
        deadline = time.time() + timeout_s
        while not self._wlan.isconnected():
            if time.time() > deadline:
                return False
            time.sleep(1)
        return True

    def disconnect_sta(self):
        if self._wlan:
            self._wlan.disconnect()
            self._wlan.active(False)

    def start_ap(self, ssid, password=None):
        import network
        self._ap = network.WLAN(network.AP_IF)
        self._ap.active(True)
        # Pico W requires password (min 8 chars) for stable AP
        ap_pass = password if password else "unicorn1"
        self._ap.config(essid=ssid, password=ap_pass)

    def stop_ap(self):
        if self._ap:
            self._ap.active(False)

    def is_connected(self):
        if self._wlan is None:
            return False
        return self._wlan.isconnected()

    def get_ip(self):
        if self._wlan and self._wlan.isconnected():
            return self._wlan.ifconfig()[0]
        return None

    def get_ap_ip(self):
        if self._ap:
            return self._ap.ifconfig()[0]
        return "192.168.4.1"

    def get_rssi(self):
        if self._wlan and self._wlan.isconnected():
            return self._wlan.status("rssi")
        return None

    def get_ssid(self):
        if self._wlan and self._wlan.isconnected():
            return self._wlan.config("essid")
        return None

    def scan_networks(self):
        import network
        try:
            wlan = network.WLAN(network.STA_IF)
            was_active = wlan.active()
            if not was_active:
                wlan.active(True)
            import time
            time.sleep(2)  # Allow time for scan after activation
            results = wlan.scan()
            if not was_active:
                wlan.active(False)
            networks = []
            seen = set()
            for r in results:
                ssid = r[0].decode("utf-8") if isinstance(r[0], bytes) else r[0]
                if ssid and ssid not in seen:
                    seen.add(ssid)
                    networks.append({"ssid": ssid, "rssi": r[3]})
            networks.sort(key=lambda x: x["rssi"], reverse=True)
            return networks
        except Exception as e:
            print("scan_networks error:", e)
            return []

    def sync_ntp(self):
        try:
            import ntptime
            ntptime.settime()
            return True
        except Exception:
            return False


class RealButtons(ButtonInterface):

    _BUTTON_MAP = {
        "a": GalacticUnicorn.SWITCH_A,
        "b": GalacticUnicorn.SWITCH_B,
        "c": GalacticUnicorn.SWITCH_C,
        "d": GalacticUnicorn.SWITCH_D,
        "sleep": GalacticUnicorn.SWITCH_SLEEP,
        "volume_up": GalacticUnicorn.SWITCH_VOLUME_UP,
        "volume_down": GalacticUnicorn.SWITCH_VOLUME_DOWN,
        "brightness_up": GalacticUnicorn.SWITCH_BRIGHTNESS_UP,
        "brightness_down": GalacticUnicorn.SWITCH_BRIGHTNESS_DOWN,
    }

    def __init__(self, gu_instance):
        self._gu = gu_instance

    def is_pressed(self, button_name):
        btn = self._BUTTON_MAP.get(button_name)
        if btn is None:
            return False
        return self._gu.is_pressed(btn)


class RealSystem(SystemInterface):

    def reset(self):
        import machine
        machine.reset()

    def get_free_memory(self):
        import gc
        return gc.mem_free()

    def collect_garbage(self):
        import gc
        gc.collect()
        return gc.mem_free()

    def get_rtc_time(self):
        from machine import RTC
        return RTC().datetime()
