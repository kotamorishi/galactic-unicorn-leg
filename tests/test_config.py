"""Tests for config/config_manager.py"""

import json
import os
import pytest


class TestWifiConfig:

    def test_no_config_returns_none(self, config_in_temp):
        assert config_in_temp.load_wifi_config() is None

    def test_wifi_config_exists_false(self, config_in_temp):
        assert config_in_temp.wifi_config_exists() is False

    def test_save_and_load(self, config_in_temp):
        config_in_temp.save_wifi_config("MySSID", "MyPassword")
        result = config_in_temp.load_wifi_config()
        assert result == {"ssid": "MySSID", "password": "MyPassword"}

    def test_wifi_config_exists_true(self, config_in_temp):
        config_in_temp.save_wifi_config("test", "pass")
        assert config_in_temp.wifi_config_exists() is True

    def test_empty_ssid_returns_none(self, config_in_temp, temp_dir):
        with open(str(temp_dir / "wifi_config.json"), "w") as f:
            json.dump({"ssid": "", "password": "pass"}, f)
        assert config_in_temp.load_wifi_config() is None

    def test_corrupt_file_returns_none(self, config_in_temp, temp_dir):
        with open(str(temp_dir / "wifi_config.json"), "w") as f:
            f.write("not json{{{")
        assert config_in_temp.load_wifi_config() is None

    def test_delete_wifi_config(self, config_in_temp):
        config_in_temp.save_wifi_config("test", "pass")
        assert config_in_temp.wifi_config_exists() is True
        config_in_temp.delete_wifi_config()
        assert config_in_temp.wifi_config_exists() is False


class TestAppConfig:

    def test_default_config_when_missing(self, config_in_temp):
        config = config_in_temp.load_app_config()
        assert config["message"]["text"] == "Hello!"
        assert config["message"]["display_mode"] == "scroll"
        assert config["schedules"] == []
        assert config["system"]["brightness"] == 50

    def test_save_and_load(self, config_in_temp):
        config = config_in_temp.load_app_config()
        config["message"]["text"] = "Test Message"
        saved = config_in_temp.save_app_config(config)
        loaded = config_in_temp.load_app_config()
        assert loaded["message"]["text"] == "Test Message"

    def test_validation_clamps_color(self, config_in_temp):
        config = config_in_temp.load_app_config()
        config["message"]["color"] = {"r": 300, "g": -10, "b": 128}
        saved = config_in_temp.save_app_config(config)
        assert saved["message"]["color"]["r"] == 255
        assert saved["message"]["color"]["g"] == 0
        assert saved["message"]["color"]["b"] == 128

    def test_validation_clamps_brightness(self, config_in_temp):
        config = config_in_temp.load_app_config()
        config["system"]["brightness"] = 150
        saved = config_in_temp.save_app_config(config)
        assert saved["system"]["brightness"] == 100

    def test_validation_limits_text_length(self, config_in_temp):
        config = config_in_temp.load_app_config()
        config["message"]["text"] = "A" * 200
        saved = config_in_temp.save_app_config(config)
        assert len(saved["message"]["text"]) == 128

    def test_validation_rejects_invalid_mode(self, config_in_temp):
        config = config_in_temp.load_app_config()
        config["message"]["display_mode"] = "invalid"
        saved = config_in_temp.save_app_config(config)
        assert saved["message"]["display_mode"] == "scroll"

    def test_validation_rejects_invalid_font(self, config_in_temp):
        config = config_in_temp.load_app_config()
        config["message"]["font"] = "comic_sans"
        saved = config_in_temp.save_app_config(config)
        assert saved["message"]["font"] == "bitmap8"

    def test_validation_rejects_invalid_speed(self, config_in_temp):
        config = config_in_temp.load_app_config()
        config["message"]["scroll_speed"] = "ludicrous"
        saved = config_in_temp.save_app_config(config)
        assert saved["message"]["scroll_speed"] == "medium"

    def test_corrupt_config_returns_defaults(self, config_in_temp, temp_dir):
        with open(str(temp_dir / "app_config.json"), "w") as f:
            f.write("broken{{{")
        config = config_in_temp.load_app_config()
        assert config["message"]["text"] == "Hello!"

    def test_partial_config_merged_with_defaults(self, config_in_temp, temp_dir):
        with open(str(temp_dir / "app_config.json"), "w") as f:
            json.dump({"message": {"text": "Custom"}}, f)
        config = config_in_temp.load_app_config()
        assert config["message"]["text"] == "Custom"
        assert config["message"]["font"] == "bitmap8"  # default
        assert config["system"]["brightness"] == 50  # default


class TestScheduleValidation:

    def test_valid_schedule(self, config_in_temp):
        config = config_in_temp.load_app_config()
        config["schedules"] = [{
            "id": 1, "enabled": True,
            "start_time": "08:00", "end_time": "09:00",
            "days": ["mon", "tue"], "sound": {"enabled": True, "preset_id": 4, "volume": 70},
        }]
        saved = config_in_temp.save_app_config(config)
        s = saved["schedules"][0]
        assert s["id"] == 1
        assert s["start_time"] == "08:00"
        assert s["days"] == ["mon", "tue"]
        assert s["sound"]["preset_id"] == 4

    def test_invalid_time_format(self, config_in_temp):
        config = config_in_temp.load_app_config()
        config["schedules"] = [{"id": 1, "start_time": "bad", "end_time": "25:99"}]
        saved = config_in_temp.save_app_config(config)
        assert saved["schedules"][0]["start_time"] == "00:00"
        assert saved["schedules"][0]["end_time"] == "23:59"  # clamped to valid range

    def test_invalid_days_filtered(self, config_in_temp):
        config = config_in_temp.load_app_config()
        config["schedules"] = [{"id": 1, "days": ["mon", "invalid", "fri"]}]
        saved = config_in_temp.save_app_config(config)
        assert saved["schedules"][0]["days"] == ["mon", "fri"]

    def test_preset_id_clamped(self, config_in_temp):
        config = config_in_temp.load_app_config()
        config["schedules"] = [{"id": 1, "sound": {"preset_id": 99, "volume": -10}}]
        saved = config_in_temp.save_app_config(config)
        assert saved["schedules"][0]["sound"]["preset_id"] == 20
        assert saved["schedules"][0]["sound"]["volume"] == 0


class TestVersionConfig:

    def test_default_version(self, config_in_temp):
        v = config_in_temp.load_version()
        assert v["version"] == "unknown"

    def test_save_and_load_version(self, config_in_temp):
        config_in_temp.save_version("abc1234")
        v = config_in_temp.load_version()
        assert v["version"] == "abc1234"


class TestOtaConfig:

    def test_default_ota_config(self, config_in_temp):
        ota = config_in_temp.load_ota_config()
        assert ota["repo"] == ""
        assert ota["branch"] == "main"
        assert ota["check_hour"] == 3


class TestSafeWrite:

    def test_atomic_write_no_leftover_tmp(self, config_in_temp):
        config_in_temp.save_wifi_config("test", "pass")
        # No .tmp file should remain
        import glob
        tmp_files = glob.glob(str(config_in_temp.WIFI_CONFIG_FILE) + ".tmp")
        assert len(tmp_files) == 0
