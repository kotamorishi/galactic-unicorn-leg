"""Hardware Abstraction Layer interfaces.

All hardware-dependent operations go through these interfaces.
Use hal.real for the actual Galactic Unicorn hardware.
Use hal.mock for PC-based testing.
"""


class DisplayInterface:
    """Abstract interface for LED matrix display."""

    WIDTH = 53
    HEIGHT = 11

    def init(self):
        """Initialize the display hardware."""
        raise NotImplementedError

    def set_font(self, font_name):
        """Set the current font. Valid: 'bitmap6', 'bitmap8'."""
        raise NotImplementedError

    def set_pen(self, r, g, b):
        """Set the current drawing color."""
        raise NotImplementedError

    def clear(self):
        """Clear the framebuffer."""
        raise NotImplementedError

    def draw_text(self, text, x, y, wrap=-1, scale=1):
        """Draw text at position (x, y)."""
        raise NotImplementedError

    def measure_text(self, text, scale=1):
        """Return pixel width of text string."""
        raise NotImplementedError

    def draw_pixel(self, x, y):
        """Draw a single pixel at (x, y)."""
        raise NotImplementedError

    def draw_line(self, x1, y1, x2, y2):
        """Draw a line from (x1,y1) to (x2,y2)."""
        raise NotImplementedError

    def draw_rectangle(self, x, y, w, h):
        """Draw a filled rectangle."""
        raise NotImplementedError

    def update(self):
        """Push framebuffer to the LED matrix."""
        raise NotImplementedError

    def set_brightness(self, level):
        """Set display brightness (0-100)."""
        raise NotImplementedError

    def get_brightness(self):
        """Get current brightness (0-100)."""
        raise NotImplementedError

    def get_light_level(self):
        """Get ambient light sensor reading (0-4095, higher = brighter)."""
        raise NotImplementedError


class AudioInterface:
    """Abstract interface for audio playback."""

    def init(self):
        """Initialize the audio hardware."""
        raise NotImplementedError

    def play_tone(self, channel, waveform, frequency, volume,
                  attack, decay, sustain, release, duration_ms):
        """Play a single tone with ADSR envelope on a channel."""
        raise NotImplementedError

    def play_sequence(self, notes):
        """Play a sequence of notes.

        notes: list of dicts, each with keys:
            channel, waveform, frequency, volume,
            attack, decay, sustain, release, duration_ms, pause_ms
        """
        raise NotImplementedError

    def stop(self):
        """Stop all audio playback."""
        raise NotImplementedError

    def set_volume(self, volume):
        """Set master volume (0.0 - 1.0)."""
        raise NotImplementedError

    def get_volume(self):
        """Get current master volume (0.0 - 1.0)."""
        raise NotImplementedError


class NetworkInterface:
    """Abstract interface for WiFi networking."""

    def connect_sta(self, ssid, password, timeout_s=30):
        """Connect to a WiFi network. Returns True on success."""
        raise NotImplementedError

    def disconnect_sta(self):
        """Disconnect from WiFi."""
        raise NotImplementedError

    def start_ap(self, ssid, password=None):
        """Start an access point."""
        raise NotImplementedError

    def stop_ap(self):
        """Stop the access point."""
        raise NotImplementedError

    def is_connected(self):
        """Return True if connected to WiFi (STA mode)."""
        raise NotImplementedError

    def get_ip(self):
        """Return current IP address as string, or None."""
        raise NotImplementedError

    def get_ap_ip(self):
        """Return AP mode IP address as string."""
        raise NotImplementedError

    def get_rssi(self):
        """Return WiFi signal strength (RSSI) or None."""
        raise NotImplementedError

    def get_ssid(self):
        """Return currently connected SSID or None."""
        raise NotImplementedError

    def scan_networks(self):
        """Scan and return list of available networks.

        Returns list of dicts: [{"ssid": str, "rssi": int}, ...]
        """
        raise NotImplementedError

    def sync_ntp(self):
        """Synchronize RTC via NTP. Returns True on success."""
        raise NotImplementedError


class ButtonInterface:
    """Abstract interface for physical buttons."""

    def is_pressed(self, button_name):
        """Check if a button is currently pressed.

        Valid names: 'a', 'b', 'c', 'd', 'sleep',
                     'volume_up', 'volume_down',
                     'brightness_up', 'brightness_down'
        """
        raise NotImplementedError


class SystemInterface:
    """Abstract interface for system operations."""

    def reset(self):
        """Perform a software reset / reboot."""
        raise NotImplementedError

    def get_free_memory(self):
        """Return free RAM in bytes."""
        raise NotImplementedError

    def collect_garbage(self):
        """Run garbage collection and return free memory after."""
        raise NotImplementedError

    def get_rtc_time(self):
        """Return current RTC time as (year, month, day, weekday, hour, minute, second, subsecond)."""
        raise NotImplementedError
