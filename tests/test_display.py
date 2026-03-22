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
        r.configure({"text": "ABCDEFGHIJ", "display_mode": "scroll",
                     "color": {"r": 255, "g": 255, "b": 255}, "font": "bitmap8",
                     "scroll_speed": "medium"})
        r.set_active(True)

        initial_x = r._scroll_x
        r.render_frame()
        assert r._scroll_x == initial_x - 1

    def test_scroll_wraps_around(self, mock_display):
        from display.renderer import SCROLL_GAP
        r = DisplayRenderer(mock_display)
        r.init()
        # Use long text so it stays in scroll mode (not auto-downgraded)
        long_text = "ABCDEFGHIJ"  # 80px > 53px
        r.configure({"text": long_text, "display_mode": "scroll",
                     "color": {"r": 255, "g": 255, "b": 255}, "font": "bitmap8",
                     "scroll_speed": "medium"})
        r.set_active(True)

        text_width = mock_display.measure_text(long_text, 1)
        # Should NOT wrap yet — still within gap
        r._scroll_x = -text_width - 1
        r.render_frame()
        assert r._scroll_x != mock_display.WIDTH  # gap not exhausted yet

        # Should wrap after text_width + SCROLL_GAP
        r._scroll_x = -(text_width + SCROLL_GAP) - 1
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

    def test_fixed_x_cached_at_configure(self, mock_display):
        """Fixed mode X should be pre-calculated, not computed per frame."""
        r = DisplayRenderer(mock_display)
        r.init()
        r.configure({"text": "Hi", "display_mode": "fixed",
                     "color": {"r": 255, "g": 255, "b": 255}, "font": "bitmap8",
                     "scroll_speed": "medium"})
        text_width = mock_display.measure_text("Hi", 1)
        expected_x = (53 - text_width) // 2
        assert r._fixed_x == expected_x

    def test_y_offset_centered_bitmap8(self, mock_display):
        """bitmap8 (8px) on 11px display → Y = (11-8)//2 = 1"""
        r = DisplayRenderer(mock_display)
        r.init()
        r.configure({"text": "Hi", "display_mode": "fixed",
                     "color": {"r": 255, "g": 255, "b": 255}, "font": "bitmap8",
                     "scroll_speed": "medium"})
        r.set_active(True)
        r.render_frame()
        texts = [i for i in mock_display.framebuffer if i["type"] == "text"]
        assert texts[0]["y"] == 1  # (11 - 8) // 2

    def test_y_offset_centered_bitmap6(self, mock_display):
        """bitmap6 (6px) on 11px display → Y = (11-6)//2 = 2"""
        r = DisplayRenderer(mock_display)
        r.init()
        r.configure({"text": "Hi", "display_mode": "fixed",
                     "color": {"r": 255, "g": 255, "b": 255}, "font": "bitmap6",
                     "scroll_speed": "medium"})
        r.set_active(True)
        r.render_frame()
        texts = [i for i in mock_display.framebuffer if i["type"] == "text"]
        assert texts[0]["y"] == 2  # (11 - 6) // 2

    def test_font11_fills_full_height(self, mock_display):
        """font11 (11px) on 11px display → Y = 0 (no offset needed)"""
        r = DisplayRenderer(mock_display)
        r.init()
        r.configure({"text": "Hi", "display_mode": "fixed",
                     "color": {"r": 255, "g": 255, "b": 255}, "font": "font11",
                     "scroll_speed": "medium"})
        assert r._y_offset == 0  # (11 - 11) // 2 = 0
        r.set_active(True)
        r.render_frame()
        texts = [i for i in mock_display.framebuffer if i["type"] == "text"]
        assert texts[0]["y"] == 0
        assert mock_display.font == "custom_11px"

    def test_border_draws_top_and_bottom_lines(self, mock_display):
        r = DisplayRenderer(mock_display)
        r.init()
        r.configure({"text": "Hi", "display_mode": "fixed",
                     "color": {"r": 255, "g": 255, "b": 255}, "font": "bitmap8",
                     "scroll_speed": "medium", "border": True})
        r.set_active(True)
        r.render_frame()
        lines = [i for i in mock_display.framebuffer if i["type"] == "line"]
        assert len(lines) == 2
        # Top line at y=0, bottom line at y=10
        ys = sorted([l["y1"] for l in lines])
        assert ys == [0, 10]

    def test_no_border_by_default(self, mock_display):
        r = DisplayRenderer(mock_display)
        r.init()
        r.configure({"text": "Hi", "display_mode": "fixed",
                     "color": {"r": 255, "g": 255, "b": 255}, "font": "bitmap8",
                     "scroll_speed": "medium"})
        r.set_active(True)
        r.render_frame()
        lines = [i for i in mock_display.framebuffer if i["type"] == "line"]
        assert len(lines) == 0

    def test_border_color_defaults_to_dim_text_color(self, mock_display):
        r = DisplayRenderer(mock_display)
        r.init()
        r.configure({"text": "Hi", "display_mode": "fixed",
                     "color": {"r": 150, "g": 90, "b": 30}, "font": "bitmap8",
                     "scroll_speed": "medium", "border": True})
        # Default border color = text color // 3
        assert r._border_color == (50, 30, 10)

    def test_fixed_mode_skips_redundant_update(self, mock_display):
        """Fixed mode should only call update() once, then skip until dirty."""
        r = DisplayRenderer(mock_display)
        r.init()
        r.configure({"text": "Hi", "display_mode": "fixed",
                     "color": {"r": 255, "g": 255, "b": 255}, "font": "bitmap8",
                     "scroll_speed": "medium"})
        r.set_active(True)
        r.render_frame()
        count_after_first = mock_display.update_count

        r.render_frame()
        r.render_frame()
        # No additional updates — frame_dirty is False
        assert mock_display.update_count == count_after_first

        # After configure, frame becomes dirty again
        r.configure({"text": "New", "display_mode": "fixed",
                     "color": {"r": 255, "g": 255, "b": 255}, "font": "bitmap8",
                     "scroll_speed": "medium"})
        r.render_frame()
        assert mock_display.update_count == count_after_first + 1

    def test_scroll_mode_updates_every_frame(self, mock_display):
        """Scroll mode must call update() on every frame."""
        r = DisplayRenderer(mock_display)
        r.init()
        # Use long text to avoid auto-downgrade to fixed
        r.configure({"text": "ABCDEFGHIJ", "display_mode": "scroll",
                     "color": {"r": 255, "g": 255, "b": 255}, "font": "bitmap8",
                     "scroll_speed": "medium"})
        r.set_active(True)
        r.render_frame()
        r.render_frame()
        r.render_frame()
        assert mock_display.update_count == 3

    def test_short_text_scroll_auto_downgrades_to_fixed(self, mock_display):
        """Text shorter than display width should use fixed mode even if scroll requested."""
        r = DisplayRenderer(mock_display)
        r.init()
        r.configure({"text": "Hi", "display_mode": "scroll",
                     "color": {"r": 255, "g": 255, "b": 255}, "font": "bitmap8",
                     "scroll_speed": "medium"})
        # "Hi" is 16px on bitmap8 mock, display is 53px — fits
        assert r._effective_mode == "fixed"
        r.set_active(True)
        r.render_frame()
        r.render_frame()
        # Should skip second update like fixed mode
        assert mock_display.update_count == 1

    def test_long_text_scroll_stays_scroll(self, mock_display):
        """Text longer than display width must keep scrolling."""
        r = DisplayRenderer(mock_display)
        r.init()
        # 8px per char * 10 chars = 80px > 53px
        r.configure({"text": "ABCDEFGHIJ", "display_mode": "scroll",
                     "color": {"r": 255, "g": 255, "b": 255}, "font": "bitmap8",
                     "scroll_speed": "medium"})
        assert r._effective_mode == "scroll"
