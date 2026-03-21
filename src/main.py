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
from ota.updater import OTAUpdater
from web.server import create_app

# --- Component setup ---

renderer = DisplayRenderer(display_hal)
renderer.init()

player = AudioPlayer(audio_hal)
player.init()

sched = Scheduler(system_hal)
wifi_mgr = WiFiManager(network_hal, system_hal)
ota = OTAUpdater(system_hal, renderer)

# --- WiFi boot sequence ---

def boot_wifi():
    """Handle WiFi connection or AP mode setup.

    Returns True if STA connected, False if AP mode started.
    """
    renderer.show_status("Connecting...")
    renderer.render_frame()

    if not config_manager.wifi_config_exists():
        renderer.show_status("WiFi Setup")
        renderer.render_frame()
        wifi_mgr.start_ap()
        return False

    connected = wifi_mgr.start_sta()
    if not connected:
        renderer.show_status("WiFi Setup")
        renderer.render_frame()
        wifi_mgr.start_ap()
        return False

    # NTP sync
    renderer.show_status("NTP Sync...")
    renderer.render_frame()
    wifi_mgr.sync_ntp()

    renderer.clear_status()
    return True


def load_config():
    """Load app config and configure components."""
    config = config_manager.load_app_config()

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
        renderer.render_frame()
        interval = renderer.get_scroll_interval_ms()
        await asyncio.sleep_ms(interval)


async def scheduler_loop():
    """Check schedules every minute."""
    while True:
        try:
            sched.check()
        except Exception:
            pass
        await asyncio.sleep(60)


async def wifi_monitor_loop():
    """Monitor WiFi connection and handle reconnection."""
    while True:
        try:
            current_ms = time.ticks_ms() if hasattr(time, "ticks_ms") else int(time.time() * 1000)
            wifi_mgr.check_connection(current_ms)
        except Exception:
            pass
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
        except Exception:
            pass
        # Check every 30 minutes (will only trigger at check_hour)
        await asyncio.sleep(1800)


async def button_check_loop():
    """Monitor physical buttons for AP mode reset.

    Long press A+D together for 5 seconds → restart in AP mode.
    """
    press_start = 0
    while True:
        if buttons_hal.is_pressed("a") and buttons_hal.is_pressed("d"):
            if press_start == 0:
                press_start = time.ticks_ms() if hasattr(time, "ticks_ms") else int(time.time() * 1000)
            else:
                current = time.ticks_ms() if hasattr(time, "ticks_ms") else int(time.time() * 1000)
                elapsed = current - press_start
                if elapsed >= 5000:
                    # Reset WiFi config and reboot into AP mode
                    config_manager.delete_wifi_config()
                    system_hal.reset()
        else:
            press_start = 0
        await asyncio.sleep_ms(200)


# --- Main ---

async def main():
    """Main async entry point."""
    sta_connected = boot_wifi()

    config = load_config()

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

    # Start web server (this blocks the event loop — it must be last)
    await app.start_server(host="0.0.0.0", port=80)


# Run
try:
    asyncio.run(main())
except KeyboardInterrupt:
    pass
