"""HTTP route definitions for the web UI and API."""

import gc
from config import config_manager
from audio.presets import get_preset, get_preset_list
from lib.microdot import Response
from web.templates import render_main_page, render_settings_page, render_setup_page
from web.templates import STATIC_DIR, STATIC_FILES

# Static assets are requested with a ?v=<tag> cache-buster (see
# templates.asset_tag), so browsers may keep them for a long time.
STATIC_MAX_AGE = 30 * 24 * 3600


def _json_response(data, status=200):
    """Helper to return a JSON response."""
    return data, status, {"Content-Type": "application/json"}


async def _guard(generator, page):
    """Stream a page, turning a mid-render failure into something visible.

    Headers are already sent by the time microdot iterates the generator, so a
    route-level try/except cannot help: the browser just gets a truncated body.
    """
    try:
        async for chunk in generator:
            yield chunk
    except Exception as e:
        print("render error ({}):".format(page), e)
        yield "<pre>render error: {}</pre>".format(e)


def _html(generator, page="page"):
    return _guard(generator, page), 200, {"Content-Type": "text/html"}


def _sound_args(data):
    """Validate a sound request. Returns (preset_id, volume, count, error).

    get_preset() is keyed by int, so an unvalidated "3" from JSON used to look
    up nothing, play nothing, and still answer 200 ok.
    """
    preset_id = config_manager.clamp_int(data.get("preset_id", 1), 1, 20, None)
    if preset_id is None or get_preset(preset_id) is None:
        return None, None, None, "Unknown preset_id"
    volume = config_manager.clamp_volume(data.get("volume", 50))
    count = config_manager.clamp_int(data.get("count", 1), 1, 10, 1)
    return preset_id, volume, count, None


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
            _add_time(scheduler, status)
            return _html(render_main_page(config, presets, status), "main")

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
        return _html(
            render_settings_page(wifi_status, version, free_mem, config["system"]),
            "settings")

    @app.route("/setup")
    async def setup_page(req):
        try:
            networks = app.ctx["wifi_manager"].scan_networks()
        except Exception:
            networks = []
        return _html(render_setup_page(networks), "setup")

    # --- Static assets (whitelisted; never build paths from user input) ---

    @app.route("/static/<name>")
    async def static_file(req, name):
        ctype = STATIC_FILES.get(name)
        if ctype is None:
            return "Not found", 404, {"Content-Type": "text/plain"}
        try:
            return Response.send_file(STATIC_DIR + "/" + name, content_type=ctype,
                                      max_age=STATIC_MAX_AGE)
        except OSError:
            return "Not found", 404, {"Content-Type": "text/plain"}

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
        _add_time(scheduler, status)
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
            preset_id, volume, count, err = _sound_args(data)
            if err:
                return _json_response({"error": err}, 400)
            await app.ctx["audio_player"].play_preset(preset_id, volume, count=count)
            return _json_response({"status": "ok"})
        except Exception as e:
            print("api_preview_sound error:", e)
            return _json_response({"error": str(e)}, 500)

    @app.route("/api/call", methods=["POST"])
    async def api_call(req):
        """Ring the sound AND flash a temporary alert message on the LED.

        Used by the ESP32 tap button. Kept separate from /api/sound/preview so
        the web UI's "Test Sound" button doesn't light up the display.
        """
        try:
            data = req.json or {}
            preset_id, volume, count, err = _sound_args(data)
            if err:
                return _json_response({"error": err}, 400)
            show_alert = app.ctx.get("show_alert")
            if show_alert:
                show_alert()  # non-blocking: sets up the display, auto-restores later
            await app.ctx["audio_player"].play_preset(preset_id, volume, count=count)
            return _json_response({"status": "ok"})
        except Exception as e:
            print("api_call error:", e)
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
            config = config_manager.load_app_config()
            config["system"]["brightness_offset"] = data.get("brightness_offset", 0)
            saved = config_manager.save_app_config(config)
            # The clamped value, not the raw one: runtime and flash must not
            # disagree, and a bad type here used to reach the hardware.
            offset = saved["system"]["brightness_offset"]
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
            config = config_manager.load_app_config()
            config["system"]["timezone_offset"] = data.get("timezone_offset", 9)
            saved = config_manager.save_app_config(config)
            # An unvalidated offset here broke the scheduler until reboot
            tz = saved["system"]["timezone_offset"]
            app.ctx["scheduler"].set_timezone_offset(tz)
            return _json_response({"timezone_offset": tz})
        except Exception as e:
            print("api_set_timezone error:", e)
            return _json_response({"error": str(e)}, 500)

    @app.route("/api/system/volume", methods=["POST"])
    async def api_set_volume(req):
        try:
            data = req.json
            if data is None:
                return _json_response({"error": "Invalid JSON"}, 400)
            volume = config_manager.clamp_volume(data.get("volume", 50))
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

            # Reject before rebooting into credentials that cannot be used:
            # wlan.connect() would raise before the web server exists.
            if not config_manager.save_wifi_config(ssid, password):
                return _json_response({"error": "Invalid SSID or password"}, 400)

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
            bar = data.get("bar_color", None)

            renderer = app.ctx["display_renderer"]
            renderer.set_bitmap(
                width, height, fmt, raw,
                (color.get("r", 255), color.get("g", 255), color.get("b", 255)),
                (bg.get("r", 0), bg.get("g", 0), bg.get("b", 0)),
                mode, speed,
                bar_color=(bar.get("r", 0), bar.get("g", 0), bar.get("b", 0)) if bar else None,
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


def _add_time(scheduler, status):
    """Add the device's local time ("HH:MM:SS") and weekday to a status dict."""
    try:
        _, _, _, weekday, hour, minute, second = scheduler.get_current_time()
        day_names = ["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"]
        status["time"] = "{:02d}:{:02d}:{:02d}".format(hour, minute, second)
        status["day"] = day_names[weekday]
    except Exception:
        status["time"] = "--:--:--"
        status["day"] = ""
    return status


def _get_display_status(scheduler, config):
    """Build current display status for the UI."""
    try:
        _, _, _, weekday, hour, minute, _ = scheduler.get_current_time()
    except Exception:
        return {"active": False, "message": config["message"]["text"],
                "color": config["message"].get("color") or {}}

    from scheduler.scheduler import is_time_in_range, is_day_match

    active = False
    active_end = None
    next_start = None
    next_day = None

    active_message = config["message"]["text"]
    active_color = config["message"].get("color") or {}

    for s in config.get("schedules", []):
        if not s.get("enabled"):
            continue
        if is_day_match(weekday, s.get("days", [])):
            if is_time_in_range(hour, minute, s["start_time"], s["end_time"]):
                active = True
                active_end = s["end_time"]
                if s.get("message"):
                    active_message = s["message"]
                if s.get("color"):
                    active_color = s["color"]
                break

    if not active:
        # Find next upcoming schedule
        day_names = ["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"]
        _best = 1441
        for s in config.get("schedules", []):
            if not s.get("enabled"):
                continue
            if is_day_match(weekday, s.get("days", [])):
                sh, sm = [int(x) for x in s["start_time"].split(":")]
                start = sh * 60 + sm
                # Soonest, not first in list order
                if start > hour * 60 + minute and (
                    next_start is None or start < _best
                ):
                    _best = start
                    next_start = s["start_time"]
                    next_day = day_names[weekday]
        if next_start is None:
            for offset in range(1, 8):
                check_day = (weekday + offset) % 7
                best = None
                for s in config.get("schedules", []):
                    if not s.get("enabled"):
                        continue
                    if is_day_match(check_day, s.get("days", [])):
                        # Earliest on that day, not first in list order
                        if best is None or s["start_time"] < best:
                            best = s["start_time"]
                if best:
                    next_start = best
                    next_day = day_names[check_day]
                    break

    return {
        "active": active,
        "message": active_message if active else config["message"]["text"],
        "color": active_color if active else (config["message"].get("color") or {}),
        "active_end": active_end,
        "next_start": next_start,
        "next_day": next_day,
    }
