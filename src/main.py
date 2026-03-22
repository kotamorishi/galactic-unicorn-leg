"""Main entry point for Galactic Unicorn LED Display.

Boot sequence:
1. Initialize display hardware (must be before WiFi)
2. Check for WiFi config → connect STA or start AP mode
3. Sync NTP → set RTC
4. Load app config
5. Start async event loop with all tasks
"""

try:
    import uasyncio as asyncio
except ImportError:
    import asyncio

try:
    import utime as time
except ImportError:
    import time

import gc


def _ticks_ms():
    """Get current ticks in ms, compatible with CPython and MicroPython."""
    if hasattr(time, "ticks_ms"):
        return time.ticks_ms()
    return int(time.time() * 1000)


def _ticks_diff(end, start):
    """Overflow-safe tick difference."""
    if hasattr(time, "ticks_diff"):
        return time.ticks_diff(end, start)
    return end - start


# --- Hardware initialization ---
# GalacticUnicorn must be initialized before WiFi (known constraint)

try:
    from hal.real import RealDisplay, RealAudio, RealNetwork, RealButtons, RealSystem
    display_hal = RealDisplay()
    gu_instance = display_hal.init()
    audio_hal = RealAudio(gu_instance)
    network_hal = RealNetwork()
    buttons_hal = RealButtons(gu_instance)
    system_hal = RealSystem()
except ImportError:
    # Running on PC (testing) — use mocks
    from hal.mock import MockDisplay, MockAudio, MockNetwork, MockButtons, MockSystem
    display_hal = MockDisplay()
    display_hal.init()
    audio_hal = MockAudio()
    network_hal = MockNetwork()
    buttons_hal = MockButtons()
    system_hal = MockSystem()

from config import config_manager
from display.renderer import DisplayRenderer
from audio.player import AudioPlayer
from scheduler.scheduler import Scheduler
from wifi.manager import WiFiManager
from wifi.captive_dns import CaptiveDNS
from ota.updater import OTAUpdater
from web.server import create_app

# --- Component setup ---

renderer = DisplayRenderer(display_hal)
renderer.init(skip_hw_init=True)  # display_hal.init() already called above

player = AudioPlayer(audio_hal)
player.init()

sched = Scheduler(system_hal)
wifi_mgr = WiFiManager(network_hal, system_hal)
captive_dns = CaptiveDNS()
ota = OTAUpdater(system_hal, renderer)

# --- WiFi boot sequence ---

def _show_boot_msg(text, color=(255, 255, 255)):
    """Show a boot message on the LED and pause briefly for visibility."""
    display_hal.clear()
    display_hal.set_font("bitmap6")
    display_hal.set_pen(*color)
    display_hal.draw_text(text, 0, 3)
    display_hal.update()


def boot_wifi():
    """Handle WiFi connection or AP mode setup.

    Returns True if STA connected, False if AP mode started.
    """
    _show_boot_msg("Starting...")

    if not config_manager.wifi_config_exists():
        _start_ap_with_display()
        return False

    _show_boot_msg("WiFi...")
    connected = wifi_mgr.start_sta()
    if not connected:
        _start_ap_with_display()
        return False

    # NTP sync
    _show_boot_msg("NTP Sync...")
    wifi_mgr.sync_ntp()

    ip = wifi_mgr.get_ip() or ""
    _show_boot_msg(ip, color=(0, 255, 100))
    time.sleep(2)

    renderer.clear_status()
    return True


def _start_ap_with_display():
    """Start AP mode and show setup instructions on LED."""
    wifi_mgr.start_ap()
    ap_ip = wifi_mgr.get_ap_ip() or "192.168.4.1"
    # Configure renderer to scroll AP setup instructions
    renderer.configure({
        "text": "WiFi: GalacticUnicorn-Setup  Pass: unicorn1  Open: http://{ip}".format(ip=ap_ip),
        "display_mode": "scroll",
        "scroll_speed": "slow",
        "color": {"r": 0, "g": 200, "b": 255},
        "font": "bitmap6",
    })
    renderer.set_active(True)


def load_config(skip_display=False):
    """Load app config and configure components."""
    config = config_manager.load_app_config()

    if not skip_display:
        renderer.configure(config["message"])
    display_hal.set_brightness(config["system"].get("brightness", 50))

    sched.set_schedules(config["schedules"])
    sched.set_timezone_offset(config["system"].get("timezone_offset", 9))

    return config


# --- Scheduler callbacks ---

# Cached message config to avoid reading flash every minute
_cached_msg_config = None


def _get_msg_config():
    """Get message config, cached to avoid flash reads every scheduler tick."""
    global _cached_msg_config
    if _cached_msg_config is None:
        _cached_msg_config = config_manager.load_app_config()["message"]
    return _cached_msg_config


def invalidate_msg_cache():
    """Call when message config changes (from web API)."""
    global _cached_msg_config
    _cached_msg_config = None


def on_schedule_active(schedule):
    """Called when a schedule is currently active."""
    # Schedule takes over — clear manual mode
    renderer._manual_active = False
    # Update message text and color from schedule if set
    msg_text = schedule.get("message", "")
    sched_color = schedule.get("color", {})
    needs_update = (msg_text and msg_text != renderer._text) or \
                   (sched_color and sched_color != dict(zip(("r", "g", "b"), renderer._color)))
    if needs_update:
        msg_cfg = dict(_get_msg_config())
        if msg_text:
            msg_cfg["text"] = msg_text
        if sched_color:
            msg_cfg["color"] = sched_color
        renderer.configure(msg_cfg)
    renderer.set_active(True)


def on_schedule_start(schedule):
    """Called once when a schedule period begins."""
    sound = schedule.get("sound", {})
    if sound.get("enabled"):
        asyncio.create_task(
            _play_sound_3x(
                sound.get("preset_id", 1),
                sound.get("volume", 50),
            )
        )


async def _play_sound_3x(preset_id, volume):
    """Play a sound preset 3 times with 1-second pause between each."""
    for i in range(3):
        await player.play_preset(preset_id, volume)
        if i < 2:
            await asyncio.sleep(1)


def on_no_schedule():
    """Called when no schedule is active. Don't turn off if manually activated."""
    if not renderer._manual_active:
        renderer.set_active(False)


sched.on_schedule_active(on_schedule_active)
sched.on_schedule_start(on_schedule_start)
sched.on_no_schedule(on_no_schedule)


# --- Async tasks ---

async def display_loop():
    """Continuously render display frames."""
    while True:
        try:
            renderer.render_frame()
        except Exception as e:
            print("display_loop error:", e)
        interval = renderer.get_scroll_interval_ms()
        await asyncio.sleep_ms(interval)


async def scheduler_loop():
    """Check schedules every minute. First check is immediate."""
    while True:
        try:
            sched.check()
        except Exception as e:
            print("scheduler_loop error:", e)
        await asyncio.sleep(60)


async def wifi_monitor_loop():
    """Monitor WiFi connection and handle reconnection."""
    while True:
        try:
            wifi_mgr.check_connection(_ticks_ms(), _ticks_diff)
        except Exception as e:
            print("wifi_monitor error:", e)
        await asyncio.sleep(30)


async def ota_check_loop():
    """Daily OTA update check."""
    while True:
        try:
            _, _, _, _, hour, _, _ = sched.get_current_time()
            if ota.should_check_now(hour):
                renderer.set_active(False)
                result = await ota.check_and_update()
                if result.get("reboot_required"):
                    system_hal.reset()
        except Exception as e:
            print("ota_check error:", e)
        # Check every 30 minutes (will only trigger at check_hour)
        await asyncio.sleep(1800)


async def button_check_loop():
    """Monitor physical buttons.

    Button A: show IP address on LED for 5 seconds.
    Long press A+D together for 5 seconds: reset WiFi and reboot.
    """
    ad_press_start = 0
    info_expire = 0  # Non-blocking info display timeout
    while True:
        try:
            now = _ticks_ms()
            a_pressed = buttons_hal.is_pressed("a")
            b_pressed = buttons_hal.is_pressed("b")
            c_pressed = buttons_hal.is_pressed("c")
            d_pressed = buttons_hal.is_pressed("d")

            # Clear info display when expired
            if info_expire and _ticks_diff(now, info_expire) >= 0:
                renderer.clear_status()
                info_expire = 0

            # A+D long press → WiFi reset (always checked, even during info display)
            if a_pressed and d_pressed:
                if ad_press_start == 0:
                    ad_press_start = now
                elif _ticks_diff(now, ad_press_start) >= 5000:
                    config_manager.delete_wifi_config()
                    system_hal.reset()
            else:
                ad_press_start = 0

            # A only → show IP address (non-blocking)
            if a_pressed and not d_pressed and not b_pressed and not c_pressed and not info_expire:
                ip = wifi_mgr.get_ip() or "No WiFi"
                renderer.show_status(ip)
                info_expire = now + 5000

            # B only → show configured SSID (non-blocking)
            if b_pressed and not a_pressed and not d_pressed and not c_pressed and not info_expire:
                wifi_cfg = config_manager.load_wifi_config()
                ssid = wifi_cfg["ssid"] if wifi_cfg else "Not set"
                renderer.show_status(ssid)
                info_expire = now + 5000

            # C only → show ambient light level (non-blocking)
            if c_pressed and not a_pressed and not b_pressed and not d_pressed and not info_expire:
                light = display_hal.get_light_level()
                renderer.show_status("Light:{}".format(light))
                info_expire = now + 5000

        except Exception as e:
            print("button_check error:", e)
        await asyncio.sleep_ms(200)


# --- Main ---

async def main():
    """Main async entry point."""
    sta_connected = boot_wifi()

    config = load_config(skip_display=not sta_connected)

    # Create web app
    app_context = {
        "config_manager": config_manager,
        "wifi_manager": wifi_mgr,
        "display_renderer": renderer,
        "audio_player": player,
        "scheduler": sched,
        "system_hal": system_hal,
        "ota_updater": ota if sta_connected else None,
        "invalidate_msg_cache": invalidate_msg_cache,
    }
    app = create_app(app_context)

    # Determine server bind address
    if sta_connected:
        host = wifi_mgr.get_ip() or "0.0.0.0"
    else:
        host = wifi_mgr.get_ap_ip() or "192.168.4.1"

    # Start all async tasks
    asyncio.create_task(display_loop())
    asyncio.create_task(button_check_loop())

    if sta_connected:
        asyncio.create_task(scheduler_loop())
        asyncio.create_task(wifi_monitor_loop())
        asyncio.create_task(ota_check_loop())

        # If no schedules configured, keep display active by default
        if not config.get("schedules"):
            renderer.set_active(True)
    else:
        # AP mode: start captive DNS so phones auto-open the setup page
        asyncio.create_task(captive_dns.run())

    # Start web server (this blocks the event loop — it must be last)
    await app.start_server(host="0.0.0.0", port=80)


# Run
try:
    asyncio.run(main())
except KeyboardInterrupt:
    pass
