"""HTTP route definitions for the web UI and API."""

import gc
from config import config_manager
from audio.presets import get_preset_list, get_preset
from web.templates import render_main_page, render_settings_page, render_setup_page


def _json_response(data, status=200):
    """Helper to return a JSON response."""
    return data, status, {"Content-Type": "application/json"}


def _html(generator):
    return generator, 200, {"Content-Type": "text/html"}


def register(app):
    """Register all routes on the microdot app."""

    # --- Page routes ---

    @app.route("/")
    async def main_page(req):
        try:
            gc.collect()
            config = config_manager.load_app_config()
            presets = get_preset_list()
            scheduler = app.ctx["scheduler"]
            status = _get_display_status(scheduler, config)
            return _html(render_main_page(config, presets, status))

        except Exception as e:
            print("main_page error:", e)
            return str(e), 500, {"Content-Type": "text/plain"}

    @app.route("/settings")
    async def settings_page(req):
        gc.collect()
        wifi_status = app.ctx["wifi_manager"].get_status()
        config = config_manager.load_app_config()
        version = config_manager.load_version()
        free_mem = app.ctx["system_hal"].get_free_memory()
        return _html(render_settings_page(wifi_status, version, free_mem, config["system"]))

    @app.route("/setup")
    async def setup_page(req):
        try:
            networks = app.ctx["wifi_manager"].scan_networks()
        except Exception:
            networks = []
        return _html(render_setup_page(networks))

    # --- Captive portal detection ---
    # iOS/macOS
    @app.route("/hotspot-detect.html")
    async def captive_apple(req):
        return "", 302, {"Location": "http://192.168.4.1/setup"}

    # Android
    @app.route("/generate_204")
    async def captive_android(req):
        return "", 302, {"Location": "http://192.168.4.1/setup"}

    @app.route("/gen_204")
    async def captive_android2(req):
        return "", 302, {"Location": "http://192.168.4.1/setup"}

    # Windows
    @app.route("/connecttest.txt")
    async def captive_windows(req):
        return "", 302, {"Location": "http://192.168.4.1/setup"}

    @app.route("/redirect")
    async def captive_windows2(req):
        return "", 302, {"Location": "http://192.168.4.1/setup"}

    # --- API routes ---

    @app.route("/api/status", methods=["GET"])
    async def api_status(req):
        config = config_manager.load_app_config()
        scheduler = app.ctx["scheduler"]
        status = _get_display_status(scheduler, config)
        # Add server time
        try:
            _, _, _, weekday, hour, minute, second = scheduler.get_current_time()
            day_names = ["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"]
            status["time"] = "{:02d}:{:02d}:{:02d}".format(hour, minute, second)
            status["day"] = day_names[weekday]
        except Exception:
            status["time"] = "--:--:--"
            status["day"] = ""
        return _json_response(status)

    @app.route("/api/message", methods=["GET"])
    async def api_get_message(req):
        config = config_manager.load_app_config()
        return _json_response(config["message"])

    @app.route("/api/message", methods=["POST"])
    async def api_set_message(req):
        data = req.json
        if data is None:
            return _json_response({"error": "Invalid JSON"}, 400)
        config = config_manager.load_app_config()
        config["message"] = data
        saved = config_manager.save_app_config(config)
        app.ctx["display_renderer"].configure(saved["message"])
        app.ctx["display_renderer"].set_active(True)
        return _json_response(saved["message"])

    @app.route("/api/schedules", methods=["GET"])
    async def api_get_schedules(req):
        config = config_manager.load_app_config()
        return _json_response(config["schedules"])

    @app.route("/api/schedules", methods=["POST"])
    async def api_set_schedules(req):
        data = req.json
        if not isinstance(data, list):
            return _json_response({"error": "Expected array"}, 400)
        config = config_manager.load_app_config()
        config["schedules"] = data
        saved = config_manager.save_app_config(config)
        app.ctx["scheduler"].set_schedules(saved["schedules"])
        return _json_response(saved["schedules"])

    @app.route("/api/sound/preview", methods=["POST"])
    async def api_preview_sound(req):
        data = req.json
        if data is None:
            return _json_response({"error": "Invalid JSON"}, 400)
        preset_id = data.get("preset_id", 1)
        volume = data.get("volume", 50)
        await app.ctx["audio_player"].play_preset(preset_id, volume)
        return _json_response({"status": "ok"})

    @app.route("/api/sound/presets", methods=["GET"])
    async def api_get_presets(req):
        return _json_response(get_preset_list())

    @app.route("/api/system/brightness", methods=["POST"])
    async def api_set_brightness(req):
        data = req.json
        if data is None:
            return _json_response({"error": "Invalid JSON"}, 400)
        brightness = data.get("brightness", 50)
        config = config_manager.load_app_config()
        config["system"]["brightness"] = brightness
        saved = config_manager.save_app_config(config)
        app.ctx["display_renderer"]._display.set_brightness(brightness)
        return _json_response({"brightness": saved["system"]["brightness"]})

    @app.route("/api/system/timezone", methods=["POST"])
    async def api_set_timezone(req):
        data = req.json
        if data is None:
            return _json_response({"error": "Invalid JSON"}, 400)
        tz = data.get("timezone_offset", 9)
        config = config_manager.load_app_config()
        config["system"]["timezone_offset"] = tz
        saved = config_manager.save_app_config(config)
        app.ctx["scheduler"].set_timezone_offset(tz)
        return _json_response({"timezone_offset": saved["system"]["timezone_offset"]})

    @app.route("/api/system/volume", methods=["POST"])
    async def api_set_volume(req):
        data = req.json
        if data is None:
            return _json_response({"error": "Invalid JSON"}, 400)
        volume = data.get("volume", 50)
        app.ctx["audio_player"]._audio.set_volume(volume / 100.0)
        return _json_response({"volume": volume})

    @app.route("/api/wifi/scan", methods=["GET"])
    async def api_wifi_scan(req):
        networks = app.ctx["wifi_manager"].scan_networks()
        return _json_response(networks)

    @app.route("/api/wifi/connect", methods=["POST"])
    async def api_wifi_connect(req):
        data = req.json
        if data is None:
            return _json_response({"error": "Invalid JSON"}, 400)
        ssid = data.get("ssid", "")
        password = data.get("password", "")
        if not ssid:
            return _json_response({"error": "SSID required"}, 400)

        # Save credentials first, then reboot into STA mode
        # (Pico W can't reliably do AP→STA switch without reboot)
        from config import config_manager as cm
        cm.save_wifi_config(ssid, password)

        try:
            import uasyncio as _asyncio
        except ImportError:
            import asyncio as _asyncio

        async def _deferred_reboot():
            await _asyncio.sleep(2)
            app.ctx["system_hal"].reset()

        _asyncio.create_task(_deferred_reboot())
        return _json_response({"status": "saved", "message": "WiFi saved. Rebooting..."})

    @app.route("/api/ota/check", methods=["POST"])
    async def api_ota_check(req):
        if "ota_updater" not in app.ctx or app.ctx["ota_updater"] is None:
            return _json_response({"error": "OTA not configured"}, 400)
        result = await app.ctx["ota_updater"].check_and_update()
        return _json_response(result)

    @app.route("/api/system/reboot", methods=["POST"])
    async def api_reboot(req):
        try:
            import uasyncio as _asyncio
        except ImportError:
            import asyncio as _asyncio

        async def _deferred_reboot():
            await _asyncio.sleep(1)
            app.ctx["system_hal"].reset()

        _asyncio.create_task(_deferred_reboot())
        return _json_response({"status": "rebooting"})


def _get_display_status(scheduler, config):
    """Build current display status for the UI."""
    try:
        _, _, _, weekday, hour, minute, _ = scheduler.get_current_time()
    except Exception:
        return {"active": False, "message": config["message"]["text"]}

    from scheduler.scheduler import is_time_in_range, is_day_match

    active = False
    active_end = None
    next_start = None
    next_day = None

    for s in config.get("schedules", []):
        if not s.get("enabled"):
            continue
        if is_day_match(weekday, s.get("days", [])):
            if is_time_in_range(hour, minute, s["start_time"], s["end_time"]):
                active = True
                active_end = s["end_time"]
                break

    if not active:
        # Find next upcoming schedule
        day_names = ["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"]
        for s in config.get("schedules", []):
            if not s.get("enabled"):
                continue
            if is_day_match(weekday, s.get("days", [])):
                sh, sm = [int(x) for x in s["start_time"].split(":")]
                if sh * 60 + sm > hour * 60 + minute:
                    next_start = s["start_time"]
                    next_day = day_names[weekday]
                    break
        if next_start is None:
            for offset in range(1, 8):
                check_day = (weekday + offset) % 7
                for s in config.get("schedules", []):
                    if not s.get("enabled"):
                        continue
                    if is_day_match(check_day, s.get("days", [])):
                        next_start = s["start_time"]
                        next_day = day_names[check_day]
                        break
                if next_start:
                    break

    return {
        "active": active,
        "message": config["message"]["text"],
        "active_end": active_end,
        "next_start": next_start,
        "next_day": next_day,
    }
