"""HTTP route definitions for the web UI and API."""

from config import config_manager
from audio.presets import get_preset_list
from web.templates import (
    render_index, render_message_page, render_schedule_page,
    render_sound_page, render_system_page, render_wifi_setup_page,
)


def _json_response(data, status=200):
    """Helper to return a JSON response."""
    return data, status, {"Content-Type": "application/json"}


def register(app):
    """Register all routes on the microdot app."""

    # --- Page routes ---

    @app.route("/")
    async def index(req):
        return render_index(), 200, {"Content-Type": "text/html"}

    @app.route("/message")
    async def message_page(req):
        config = config_manager.load_app_config()
        return render_message_page(config["message"]), 200, {"Content-Type": "text/html"}

    @app.route("/schedule")
    async def schedule_page(req):
        config = config_manager.load_app_config()
        return render_schedule_page(config["schedules"]), 200, {"Content-Type": "text/html"}

    @app.route("/sound")
    async def sound_page(req):
        presets = get_preset_list()
        return render_sound_page(presets), 200, {"Content-Type": "text/html"}

    @app.route("/system")
    async def system_page(req):
        wifi_status = app.ctx["wifi_manager"].get_status()
        config = config_manager.load_app_config()
        version = config_manager.load_version()
        return render_system_page(wifi_status, config["system"], version), 200, {"Content-Type": "text/html"}

    @app.route("/wifi-setup")
    async def wifi_setup_page(req):
        networks = app.ctx["wifi_manager"].scan_networks()
        return render_wifi_setup_page(networks), 200, {"Content-Type": "text/html"}

    # --- API routes ---

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
        # Update display renderer with new config
        app.ctx["display_renderer"].configure(saved["message"])
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
        # Update scheduler with new schedules
        app.ctx["scheduler"].set_schedules(saved["schedules"])
        return _json_response(saved["schedules"])

    @app.route("/api/schedules/<schedule_id>", methods=["DELETE"])
    async def api_delete_schedule(req, schedule_id):
        schedule_id = int(schedule_id)
        config = config_manager.load_app_config()
        config["schedules"] = [
            s for s in config["schedules"] if s.get("id") != schedule_id
        ]
        saved = config_manager.save_app_config(config)
        app.ctx["scheduler"].set_schedules(saved["schedules"])
        return _json_response(saved["schedules"])

    @app.route("/api/sound/presets", methods=["GET"])
    async def api_get_presets(req):
        return _json_response(get_preset_list())

    @app.route("/api/sound/preview", methods=["POST"])
    async def api_preview_sound(req):
        data = req.json
        if data is None:
            return _json_response({"error": "Invalid JSON"}, 400)
        preset_id = data.get("preset_id", 1)
        volume = data.get("volume", 50)
        await app.ctx["audio_player"].play_preset(preset_id, volume)
        return _json_response({"status": "ok"})

    @app.route("/api/system", methods=["GET"])
    async def api_get_system(req):
        wifi_status = app.ctx["wifi_manager"].get_status()
        config = config_manager.load_app_config()
        version = config_manager.load_version()
        free_mem = app.ctx["system_hal"].get_free_memory()
        return _json_response({
            "wifi": wifi_status,
            "system": config["system"],
            "version": version,
            "free_memory": free_mem,
        })

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
        success = app.ctx["wifi_manager"].try_connect_and_save(ssid, password)
        if success:
            return _json_response({"status": "connected", "ip": app.ctx["wifi_manager"].get_ip()})
        return _json_response({"error": "Connection failed"}, 400)

    @app.route("/api/wifi/status", methods=["GET"])
    async def api_wifi_status(req):
        return _json_response(app.ctx["wifi_manager"].get_status())

    @app.route("/api/ota/check", methods=["POST"])
    async def api_ota_check(req):
        if "ota_updater" not in app.ctx or app.ctx["ota_updater"] is None:
            return _json_response({"error": "OTA not configured"}, 400)
        result = await app.ctx["ota_updater"].check_and_update()
        return _json_response(result)

    @app.route("/api/system/reboot", methods=["POST"])
    async def api_reboot(req):
        app.ctx["system_hal"].reset()
        return _json_response({"status": "rebooting"})
