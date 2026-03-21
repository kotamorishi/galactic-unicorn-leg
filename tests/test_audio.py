"""Tests for audio/presets.py — validate preset data structure."""

import pytest
from audio.presets import PRESETS, VALID_WAVEFORMS, get_preset, get_preset_list


class TestPresetData:

    def test_all_20_presets_exist(self):
        assert len(PRESETS) == 20
        for i in range(1, 21):
            assert i in PRESETS, f"Preset {i} missing"

    def test_all_presets_have_required_keys(self):
        for pid, preset in PRESETS.items():
            assert "name" in preset, f"Preset {pid} missing 'name'"
            assert "category" in preset, f"Preset {pid} missing 'category'"
            assert "notes" in preset, f"Preset {pid} missing 'notes'"
            assert isinstance(preset["notes"], list), f"Preset {pid} 'notes' not a list"
            assert len(preset["notes"]) > 0, f"Preset {pid} has no notes"

    def test_all_notes_have_required_keys(self):
        required = {"frequency", "waveform", "volume", "attack", "decay",
                     "sustain", "release", "duration_ms", "pause_ms"}
        for pid, preset in PRESETS.items():
            for i, note in enumerate(preset["notes"]):
                for key in required:
                    assert key in note, f"Preset {pid} note {i} missing '{key}'"

    def test_all_waveforms_valid(self):
        for pid, preset in PRESETS.items():
            for note in preset["notes"]:
                assert note["waveform"] in VALID_WAVEFORMS, \
                    f"Preset {pid}: invalid waveform '{note['waveform']}'"

    def test_frequency_range(self):
        for pid, preset in PRESETS.items():
            for note in preset["notes"]:
                assert 20 <= note["frequency"] <= 20000, \
                    f"Preset {pid}: frequency {note['frequency']} out of audible range"

    def test_volume_range(self):
        for pid, preset in PRESETS.items():
            for note in preset["notes"]:
                assert 0.0 <= note["volume"] <= 1.0, \
                    f"Preset {pid}: volume {note['volume']} out of range"

    def test_adsr_non_negative(self):
        for pid, preset in PRESETS.items():
            for note in preset["notes"]:
                assert note["attack"] >= 0, f"Preset {pid}: negative attack"
                assert note["decay"] >= 0, f"Preset {pid}: negative decay"
                assert note["sustain"] >= 0, f"Preset {pid}: negative sustain"
                assert note["release"] >= 0, f"Preset {pid}: negative release"

    def test_duration_positive(self):
        for pid, preset in PRESETS.items():
            for note in preset["notes"]:
                assert note["duration_ms"] > 0, \
                    f"Preset {pid}: duration must be positive"

    def test_pause_non_negative(self):
        for pid, preset in PRESETS.items():
            for note in preset["notes"]:
                assert note["pause_ms"] >= 0, \
                    f"Preset {pid}: negative pause"

    def test_categories_valid(self):
        valid_cats = {"notification", "alarm", "melody", "sfx"}
        for pid, preset in PRESETS.items():
            assert preset["category"] in valid_cats, \
                f"Preset {pid}: invalid category '{preset['category']}'"


class TestPresetAPI:

    def test_get_preset_valid(self):
        p = get_preset(1)
        assert p is not None
        assert p["name"] == "Simple Beep"

    def test_get_preset_invalid(self):
        assert get_preset(999) is None

    def test_get_preset_list(self):
        lst = get_preset_list()
        assert len(lst) == 20
        assert lst[0]["id"] == 1
        assert "name" in lst[0]
        assert "category" in lst[0]

    def test_preset_list_sorted(self):
        lst = get_preset_list()
        ids = [p["id"] for p in lst]
        assert ids == sorted(ids)
