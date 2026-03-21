"""Test that all source modules can be imported without SyntaxError.

Catches typos, unclosed strings, mismatched brackets, etc.
"""

import importlib
import pytest


MODULES = [
    "hal.interfaces",
    "hal.mock",
    "config.config_manager",
    "audio.presets",
    "audio.player",
    "display.renderer",
    "scheduler.scheduler",
    "wifi.manager",
    "wifi.captive_dns",
    "web.templates",
    "web.routes",
    "web.server",
    "ota.updater",
]


@pytest.mark.parametrize("module", MODULES)
def test_module_imports(module):
    """Every source module must import without error."""
    importlib.import_module(module)
