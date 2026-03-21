"""Tests for display/renderer.py"""

import pytest
from display.renderer import DisplayRenderer, SCROLL_SPEED_MS


class TestDisplayRenderer:

    def test_configure_sets_properties(self, mock_display):
        r = DisplayRenderer(mock_display)
        r.init()
        r.configure({
            "text": "Hello",
            "display_mode": "scroll",
            "scroll_speed": "fast",
            "color": {"r": 255, "g": 0, "b": 0},
            "bg_color": {"r": 0, "g": 0, "b": 50},
            "font": "bitmap6",
        })
        assert r._text == "Hello"
        assert r._mode == "scroll"
        assert r._scroll_speed == "fast"
        assert r._color == (255, 0, 0)
        assert r._bg_color == (0, 0, 50)
        assert r._font == "bitmap6"

    def test_bg_color_default_black(self, mock_display):
        r = DisplayRenderer(mock_display)
        r.init()
        r.configure({
            "text": "Test",
            "display_mode": "fixed",
            "scroll_speed": "medium",
            "color": {"r": 255, "g": 255, "b": 255},
            "font": "bitmap8",
        })
        assert r._bg_color == (0, 0, 0)

    def test_bg_color_renders_as_rectangle(self, mock_display):
        r = DisplayRenderer(mock_display)
        r.init()
        r.configure({
            "text": "Hi",
            "display_mode": "fixed",
            "scroll_speed": "medium",
            "color": {"r": 255, "g": 255, "b": 255},
            "bg_color": {"r": 10, "g": 20, "b": 30},
            "font": "bitmap8",
        })
        r.set_active(True)
        r.render_frame()
        # Background should be drawn as a full-screen rectangle
        rects = [i for i in mock_display.framebuffer if i["type"] == "rectangle"]
        assert len(rects) >= 1
        bg = rects[0]
        assert bg["w"] == 53
        assert bg["h"] == 11
        assert bg["color"] == (10, 20, 30)

    def test_scroll_speed_mapping(self):
        assert SCROLL_SPEED_MS["slow"] == 80
        assert SCROLL_SPEED_MS["medium"] == 50
        assert SCROLL_SPEED_MS["fast"] == 25

    def test_render_frame_increments_update(self, mock_display):
        r = DisplayRenderer(mock_display)
        r.init()
        r.configure({"text": "Test", "display_mode": "fixed",
                     "color": {"r": 255, "g": 255, "b": 255}, "font": "bitmap8",
                     "scroll_speed": "medium"})
        r.set_active(True)
        r.render_frame()
        assert mock_display.update_count == 1

    def test_inactive_display_is_blank(self, mock_display):
        r = DisplayRenderer(mock_display)
        r.init()
        r.configure({"text": "Test", "display_mode": "fixed",
                     "color": {"r": 255, "g": 255, "b": 255}, "font": "bitmap8",
                     "scroll_speed": "medium"})
        r.set_active(False)
        r.render_frame()
        # Framebuffer should be empty (cleared, no text drawn)
        assert len(mock_display.framebuffer) == 0

    def test_scroll_position_decrements(self, mock_display):
        r = DisplayRenderer(mock_display)
        r.init()
        r.configure({"text": "Test", "display_mode": "scroll",
                     "color": {"r": 255, "g": 255, "b": 255}, "font": "bitmap8",
                     "scroll_speed": "medium"})
        r.set_active(True)

        initial_x = r._scroll_x
        r.render_frame()
        assert r._scroll_x == initial_x - 1

    def test_scroll_wraps_around(self, mock_display):
        r = DisplayRenderer(mock_display)
        r.init()
        r.configure({"text": "Hi", "display_mode": "scroll",
                     "color": {"r": 255, "g": 255, "b": 255}, "font": "bitmap8",
                     "scroll_speed": "medium"})
        r.set_active(True)

        text_width = mock_display.measure_text("Hi", 1)
        # Move scroll position past the wrap point
        r._scroll_x = -text_width - 1
        r.render_frame()
        assert r._scroll_x == mock_display.WIDTH

    def test_status_text_overrides_display(self, mock_display):
        r = DisplayRenderer(mock_display)
        r.init()
        r.configure({"text": "Normal", "display_mode": "fixed",
                     "color": {"r": 255, "g": 255, "b": 255}, "font": "bitmap8",
                     "scroll_speed": "medium"})
        r.set_active(True)
        r.show_status("Updating...")
        r.render_frame()

        # Status should be rendered, not normal text
        texts = [item["text"] for item in mock_display.framebuffer if item["type"] == "text"]
        assert "Updating..." in texts
        assert "Normal" not in texts

    def test_clear_status_returns_to_normal(self, mock_display):
        r = DisplayRenderer(mock_display)
        r.init()
        r.configure({"text": "Normal", "display_mode": "fixed",
                     "color": {"r": 255, "g": 255, "b": 255}, "font": "bitmap8",
                     "scroll_speed": "medium"})
        r.set_active(True)
        r.show_status("Updating...")
        r.clear_status()
        r.render_frame()

        texts = [item["text"] for item in mock_display.framebuffer if item["type"] == "text"]
        assert "Normal" in texts

    def test_fixed_mode_centers_text(self, mock_display):
        r = DisplayRenderer(mock_display)
        r.init()
        r.configure({"text": "Hi", "display_mode": "fixed",
                     "color": {"r": 255, "g": 255, "b": 255}, "font": "bitmap8",
                     "scroll_speed": "medium"})
        r.set_active(True)
        r.render_frame()

        text_items = [i for i in mock_display.framebuffer if i["type"] == "text"]
        assert len(text_items) == 1
        # Text should be centered
        text_width = mock_display.measure_text("Hi", 1)
        expected_x = (53 - text_width) // 2
        assert text_items[0]["x"] == expected_x
