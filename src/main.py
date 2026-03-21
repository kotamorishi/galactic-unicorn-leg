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

def on_schedule_active(schedule):
    """Called when a schedule is currently active."""
    renderer.set_active(True)


def on_schedule_start(schedule):
    """Called once when a schedule period begins."""
    sound = schedule.get("sound", {})
    if sound.get("enabled"):
        asyncio.create_task(
            player.play_preset(
                sound.get("preset_id", 1),
                sound.get("volume", 50),
            )
        )


def on_no_schedule():
    """Called when no schedule is active."""
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
    """Check schedules every minute."""
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
    ip_showing = False
    while True:
        try:
            a_pressed = buttons_hal.is_pressed("a")
            d_pressed = buttons_hal.is_pressed("d")

            # A+D long press → WiFi reset
            if a_pressed and d_pressed:
                if ad_press_start == 0:
                    ad_press_start = _ticks_ms()
                elif _ticks_diff(_ticks_ms(), ad_press_start) >= 5000:
                    config_manager.delete_wifi_config()
                    system_hal.reset()
            else:
                ad_press_start = 0

            # A only → show IP address
            if a_pressed and not d_pressed and not ip_showing:
                ip_showing = True
                ip = wifi_mgr.get_ip() or "No WiFi"
                renderer.show_status(ip)
                await asyncio.sleep(5)
                renderer.clear_status()
                ip_showing = False

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
