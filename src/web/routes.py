"""HTTP route definitions for the web UI and API."""

import gc
from config import config_manager
from audio.presets import get_preset_list
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
        # Include brightness offset for Web UI sync
        if "get_brightness_offset" in app.ctx:
            status["brightness_offset"] = app.ctx["get_brightness_offset"]()
        return _json_response(status)

    @app.route("/api/message", methods=["GET"])
    async def api_get_message(req):
        config = config_manager.load_app_config()
        return _json_response(config["message"])

    @app.route("/api/message", methods=["POST"])
    async def api_set_message(req):
        try:
            data = req.json
            if data is None:
                return _json_response({"error": "Invalid JSON"}, 400)
            config = config_manager.load_app_config()
            # Merge only valid message fields to preserve bg_color/border
            # and reject unexpected fields from other endpoints
            valid_keys = {"text", "display_mode", "scroll_speed", "color", "bg_color",
                          "border", "border_color", "font"}
            for k, v in data.items():
                if k in valid_keys:
                    config["message"][k] = v
            saved = config_manager.save_app_config(config)
            app.ctx["display_renderer"].clear_bitmap()
            app.ctx["display_renderer"].configure(saved["message"])
            app.ctx["display_renderer"].set_active(True, manual=True)
            # Invalidate cached message config so scheduler picks up changes
            if "invalidate_msg_cache" in app.ctx:
                app.ctx["invalidate_msg_cache"]()
            return _json_response(saved["message"])
        except Exception as e:
            print("api_set_message error:", e)
            return _json_response({"error": str(e)}, 500)

    @app.route("/api/schedules", methods=["GET"])
    async def api_get_schedules(req):
        config = config_manager.load_app_config()
        return _json_response(config["schedules"])

    @app.route("/api/schedules", methods=["POST"])
    async def api_set_schedules(req):
        try:
            data = req.json
            if not isinstance(data, list):
                return _json_response({"error": "Expected array"}, 400)
            config = config_manager.load_app_config()
            config["schedules"] = data
            saved = config_manager.save_app_config(config)
            app.ctx["scheduler"].set_schedules(saved["schedules"])
            return _json_response(saved["schedules"])
        except Exception as e:
            print("api_set_schedules error:", e)
            return _json_response({"error": str(e)}, 500)

    @app.route("/api/sound/preview", methods=["POST"])
    async def api_preview_sound(req):
        try:
            data = req.json
            if data is None:
                return _json_response({"error": "Invalid JSON"}, 400)
            preset_id = data.get("preset_id", 1)
            volume = data.get("volume", 50)
            await app.ctx["audio_player"].play_preset(preset_id, volume)
            return _json_response({"status": "ok"})
        except Exception as e:
            print("api_preview_sound error:", e)
            return _json_response({"error": str(e)}, 500)

    @app.route("/api/sound/presets", methods=["GET"])
    async def api_get_presets(req):
        return _json_response(get_preset_list())

    @app.route("/api/system/brightness", methods=["POST"])
    async def api_set_brightness(req):
        try:
            data = req.json
            if data is None:
                return _json_response({"error": "Invalid JSON"}, 400)
            offset = data.get("brightness_offset", 0)
            config = config_manager.load_app_config()
            config["system"]["brightness_offset"] = offset
            config_manager.save_app_config(config)
            app.ctx["set_brightness_offset"](offset)
            app.ctx["update_auto_brightness"]()
            return _json_response({"brightness_offset": offset})
        except Exception as e:
            print("api_set_brightness error:", e)
            return _json_response({"error": str(e)}, 500)

    @app.route("/api/system/timezone", methods=["POST"])
    async def api_set_timezone(req):
        try:
            data = req.json
            if data is None:
                return _json_response({"error": "Invalid JSON"}, 400)
            tz = data.get("timezone_offset", 9)
            config = config_manager.load_app_config()
            config["system"]["timezone_offset"] = tz
            saved = config_manager.save_app_config(config)
            app.ctx["scheduler"].set_timezone_offset(tz)
            return _json_response({"timezone_offset": saved["system"]["timezone_offset"]})
        except Exception as e:
            print("api_set_timezone error:", e)
            return _json_response({"error": str(e)}, 500)

    @app.route("/api/system/volume", methods=["POST"])
    async def api_set_volume(req):
        try:
            data = req.json
            if data is None:
                return _json_response({"error": "Invalid JSON"}, 400)
            volume = data.get("volume", 50)
            app.ctx["audio_player"]._audio.set_volume(volume / 100.0)
            return _json_response({"volume": volume})
        except Exception as e:
            print("api_set_volume error:", e)
            return _json_response({"error": str(e)}, 500)

    @app.route("/api/wifi/scan", methods=["GET"])
    async def api_wifi_scan(req):
        networks = app.ctx["wifi_manager"].scan_networks()
        return _json_response(networks)

    @app.route("/api/wifi/connect", methods=["POST"])
    async def api_wifi_connect(req):
        try:
            data = req.json
            if data is None:
                return _json_response({"error": "Invalid JSON"}, 400)
            ssid = data.get("ssid", "")
            password = data.get("password", "")
            if not ssid:
                return _json_response({"error": "SSID required"}, 400)

            config_manager.save_wifi_config(ssid, password)

            try:
                import uasyncio as _asyncio
            except ImportError:
                import asyncio as _asyncio

            async def _deferred_reboot():
                await _asyncio.sleep(2)
                app.ctx["system_hal"].reset()

            _asyncio.create_task(_deferred_reboot())
            return _json_response({"status": "saved", "message": "WiFi saved. Rebooting..."})
        except Exception as e:
            print("api_wifi_connect error:", e)
            return _json_response({"error": str(e)}, 500)

    @app.route("/api/bitmap", methods=["POST"])
    async def api_set_bitmap(req):
        try:
            gc.collect()
            data = req.json
            if data is None:
                return _json_response({"error": "Invalid JSON"}, 400)

            width = data.get("width", 0)
            height = data.get("height", 0)
            fmt = data.get("format", "mono")
            mode = data.get("display_mode", "scroll")
            speed = data.get("scroll_speed", "medium")

            if height != 11:
                return _json_response({"error": "height must be 11"}, 400)
            max_w = 5000 if fmt == "mono" else 360
            if width < 1 or width > max_w:
                return _json_response({"error": "width 1-{}".format(max_w)}, 400)
            if fmt not in ("mono", "rgb"):
                return _json_response({"error": "format must be mono or rgb"}, 400)

            try:
                import ubinascii
                raw = ubinascii.a2b_base64(data["data"])
            except ImportError:
                import binascii
                raw = binascii.a2b_base64(data["data"])

            if fmt == "mono":
                expected = ((width + 7) // 8) * height
            else:
                expected = width * height * 3
            if len(raw) != expected:
                return _json_response({"error": "data size mismatch: got {} expected {}".format(len(raw), expected)}, 400)

            color = data.get("color", {"r": 255, "g": 255, "b": 255})
            bg = data.get("bg_color", {"r": 0, "g": 0, "b": 0})

            renderer = app.ctx["display_renderer"]
            renderer.set_bitmap(
                width, height, fmt, bytearray(raw),
                (color.get("r", 255), color.get("g", 255), color.get("b", 255)),
                (bg.get("r", 0), bg.get("g", 0), bg.get("b", 0)),
                mode, speed,
            )
            return _json_response({"status": "ok", "width": width, "format": fmt, "mode": mode})
        except Exception as e:
            print("api_set_bitmap error:", e)
            return _json_response({"error": str(e)}, 500)

    @app.route("/api/bitmap", methods=["DELETE"])
    async def api_clear_bitmap(req):
        renderer = app.ctx["display_renderer"]
        renderer.clear_bitmap()
        config = config_manager.load_app_config()
        renderer.configure(config["message"])
        renderer.set_active(True, manual=True)
        return _json_response({"status": "ok", "mode": "text"})

    @app.route("/api/ota/check", methods=["POST"])
    async def api_ota_check(req):
        try:
            if "ota_updater" not in app.ctx or app.ctx["ota_updater"] is None:
                return _json_response({"error": "OTA not configured"}, 400)
            result = await app.ctx["ota_updater"].check_and_update()
            return _json_response(result)
        except Exception as e:
            print("api_ota_check error:", e)
            return _json_response({"error": str(e)}, 500)

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

    active_message = config["message"]["text"]

    for s in config.get("schedules", []):
        if not s.get("enabled"):
            continue
        if is_day_match(weekday, s.get("days", [])):
            if is_time_in_range(hour, minute, s["start_time"], s["end_time"]):
                active = True
                active_end = s["end_time"]
                if s.get("message"):
                    active_message = s["message"]
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
        "message": active_message if active else config["message"]["text"],
        "active_end": active_end,
        "next_start": next_start,
        "next_day": next_day,
    }
