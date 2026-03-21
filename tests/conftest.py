"""Shared fixtures for all tests."""

import sys
import os
import json
import tempfile
import pytest

# Add src/ to path so imports work like they do on the device
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))

from hal.mock import MockDisplay, MockAudio, MockNetwork, MockButtons, MockSystem


@pytest.fixture
def mock_display():
    d = MockDisplay()
    d.init()
    return d


@pytest.fixture
def mock_audio():
    a = MockAudio()
    a.init()
    return a


@pytest.fixture
def mock_network():
    return MockNetwork()


@pytest.fixture
def mock_buttons():
    return MockButtons()


@pytest.fixture
def mock_system():
    return MockSystem()


@pytest.fixture
def temp_dir(tmp_path, monkeypatch):
    """Provide a temp directory and patch config_manager to use it."""
    monkeypatch.chdir(tmp_path)
    return tmp_path


@pytest.fixture
def config_in_temp(temp_dir, monkeypatch):
    """Patch config_manager file paths to use temp directory."""
    import config.config_manager as cm
    monkeypatch.setattr(cm, "WIFI_CONFIG_FILE", str(temp_dir / "wifi_config.json"))
    monkeypatch.setattr(cm, "APP_CONFIG_FILE", str(temp_dir / "app_config.json"))
    monkeypatch.setattr(cm, "OTA_CONFIG_FILE", str(temp_dir / "ota_config.json"))
    monkeypatch.setattr(cm, "VERSION_FILE", str(temp_dir / "version.json"))
    return cm
