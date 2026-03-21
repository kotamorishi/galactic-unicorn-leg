"""WiFi connection manager with auto-reconnection.

Handles STA mode connection, AP mode for initial setup,
NTP sync, and exponential backoff reconnection.
"""

from config import config_manager

AP_SSID = "GalacticUnicorn-Setup"
RECONNECT_DELAYS = [5, 10, 20, 40, 60]  # seconds, exponential backoff
RECONNECT_PAUSE = 300  # 5 min pause after all retries exhausted
CHECK_INTERVAL_S = 30
NTP_SYNC_INTERVAL_S = 3600  # 1 hour


class WiFiManager:

    def __init__(self, network_hal, system_hal):
        self._net = network_hal
        self._system = system_hal
        self._mode = None  # "sta", "ap", or None
        self._reconnect_attempt = 0
        self._last_check_ms = 0
        self._last_ntp_sync_ms = 0
        self._ntp_synced = False

    def start_sta(self):
        """Try to connect using saved WiFi config.

        Returns True if connected, False if config missing or connection failed.
        """
        wifi_cfg = config_manager.load_wifi_config()
        if wifi_cfg is None:
            return False

        connected = self._net.connect_sta(
            wifi_cfg["ssid"],
            wifi_cfg["password"],
            timeout_s=30,
        )
        if connected:
            self._mode = "sta"
            self._reconnect_attempt = 0
            return True
        return False

    def start_ap(self):
        """Start access point for WiFi setup."""
        self._net.stop_ap()
        self._net.start_ap(AP_SSID)
        self._mode = "ap"

    def stop_ap(self):
        """Stop access point."""
        self._net.stop_ap()
        if self._mode == "ap":
            self._mode = None

    def sync_ntp(self):
        """Perform NTP time sync. Returns True on success."""
        result = self._net.sync_ntp()
        if result:
            self._ntp_synced = True
        return result

    def is_connected(self):
        return self._net.is_connected()

    def get_ip(self):
        return self._net.get_ip()

    def get_ap_ip(self):
        return self._net.get_ap_ip()

    def get_status(self):
        """Return current WiFi status dict for Web UI."""
        return {
            "mode": self._mode,
            "connected": self._net.is_connected(),
            "ip": self._net.get_ip(),
            "ssid": self._net.get_ssid(),
            "rssi": self._net.get_rssi(),
            "ntp_synced": self._ntp_synced,
        }

    def scan_networks(self):
        """Scan for available WiFi networks."""
        return self._net.scan_networks()

    def try_connect_and_save(self, ssid, password):
        """Test connection and save if successful.

        Returns True on success. Used by captive portal setup.
        """
        self._net.disconnect_sta()
        connected = self._net.connect_sta(ssid, password, timeout_s=15)
        if connected:
            config_manager.save_wifi_config(ssid, password)
            self._mode = "sta"
            self._reconnect_attempt = 0
            return True
        return False

    def check_connection(self, current_ms):
        """Periodic connection check. Call from main loop.

        Handles auto-reconnection with exponential backoff.
        Also handles periodic NTP re-sync.

        Args:
            current_ms: Current time in milliseconds (from time.ticks_ms or similar)
        """
        if self._mode != "sta":
            return

        # Periodic NTP re-sync
        if self._ntp_synced and self._net.is_connected():
            if current_ms - self._last_ntp_sync_ms >= NTP_SYNC_INTERVAL_S * 1000:
                self.sync_ntp()
                self._last_ntp_sync_ms = current_ms

        # Connection check
        if current_ms - self._last_check_ms < CHECK_INTERVAL_S * 1000:
            return
        self._last_check_ms = current_ms

        if self._net.is_connected():
            self._reconnect_attempt = 0
            return

        # Connection lost — attempt reconnect
        self._attempt_reconnect()

    def _attempt_reconnect(self):
        """Try to reconnect with exponential backoff."""
        if self._reconnect_attempt >= len(RECONNECT_DELAYS):
            # All retries exhausted, will try again after RECONNECT_PAUSE
            # (handled by check_connection interval)
            self._reconnect_attempt = 0
            return

        wifi_cfg = config_manager.load_wifi_config()
        if wifi_cfg is None:
            return

        connected = self._net.connect_sta(
            wifi_cfg["ssid"],
            wifi_cfg["password"],
            timeout_s=10,
        )

        if connected:
            self._reconnect_attempt = 0
            self.sync_ntp()
        else:
            self._reconnect_attempt += 1

    def get_reconnect_delay(self):
        """Return current reconnect delay in seconds (for logging/debug)."""
        if self._reconnect_attempt < len(RECONNECT_DELAYS):
            return RECONNECT_DELAYS[self._reconnect_attempt]
        return RECONNECT_PAUSE
