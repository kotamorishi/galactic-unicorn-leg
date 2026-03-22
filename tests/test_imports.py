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


def test_main_module_level_execution():
    """Verify main.py module-level code runs without NameError.

    main.py uses mock HAL on PC. This catches definition order bugs
    like referencing a function before it's defined at module level.
    Sets sys._called_from_test to skip asyncio.run().
    """
    import sys
    sys._called_from_test = True
    try:
        import main  # noqa: F401 — triggers all module-level code
    finally:
        del sys._called_from_test
