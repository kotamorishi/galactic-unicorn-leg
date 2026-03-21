"""Display renderer for LED matrix text display.

Supports fixed text display and horizontal scrolling.
Designed to be called from an async loop.
"""

SCROLL_SPEED_MS = {
    "slow": 80,
    "medium": 50,
    "fast": 25,
}

# Y offset to vertically center text for each font
FONT_Y_OFFSET = {
    "bitmap6": 3,
    "bitmap8": 2,
}


class DisplayRenderer:

    def __init__(self, display_hal):
        self._display = display_hal
        self._text = ""
        self._mode = "scroll"
        self._scroll_speed = "medium"
        self._color = (255, 255, 255)
        self._font = "bitmap8"
        self._scroll_x = 0
        self._text_width = 0
        self._active = False
        self._status_text = None

    def init(self, skip_hw_init=False):
        if not skip_hw_init:
            self._display.init()

    def configure(self, message_config):
        """Apply message config from app settings.

        Args:
            message_config: dict with text, display_mode, scroll_speed, color, font
        """
        self._text = message_config.get("text", "")
        self._mode = message_config.get("display_mode", "scroll")
        self._scroll_speed = message_config.get("scroll_speed", "medium")
        color = message_config.get("color", {})
        self._color = (
            color.get("r", 255),
            color.get("g", 255),
            color.get("b", 255),
        )
        self._font = message_config.get("font", "bitmap8")
        self._reset_scroll()

    def _reset_scroll(self):
        """Reset scroll position to start (off-screen right)."""
        self._scroll_x = self._display.WIDTH
        self._display.set_font(self._font)
        self._text_width = self._display.measure_text(self._text, 1)

    def set_active(self, active):
        """Enable or disable display output."""
        if active and not self._active:
            self._reset_scroll()
        self._active = active

    def show_status(self, text):
        """Show a temporary status message (e.g., 'Updating...')."""
        self._status_text = text

    def clear_status(self):
        """Clear status message and return to normal display."""
        self._status_text = None

    def get_scroll_interval_ms(self):
        """Return the scroll update interval in ms."""
        return SCROLL_SPEED_MS.get(self._scroll_speed, 50)

    def render_frame(self):
        """Render one frame to the display.

        For scroll mode, advances the scroll position by 1 pixel.
        Call this at the interval returned by get_scroll_interval_ms().
        """
        self._display.clear()

        if self._status_text:
            self._render_status()
        elif self._active:
            if self._mode == "scroll":
                self._render_scroll()
            else:
                self._render_fixed()
        # If not active and no status, display stays cleared (LEDs off)

        self._display.update()

    def _render_status(self):
        """Render status text centered on display."""
        self._display.set_font("bitmap6")
        self._display.set_pen(100, 100, 255)
        width = self._display.measure_text(self._status_text, 1)
        x = (self._display.WIDTH - width) // 2
        y = FONT_Y_OFFSET.get("bitmap6", 3)
        self._display.draw_text(self._status_text, x, y)

    def _render_scroll(self):
        """Render scrolling text, advancing 1px per frame."""
        self._display.set_font(self._font)
        self._display.set_pen(*self._color)
        y = FONT_Y_OFFSET.get(self._font, 2)
        self._display.draw_text(self._text, self._scroll_x, y)

        self._scroll_x -= 1
        # When text has fully scrolled off left side, reset to right
        if self._scroll_x < -self._text_width:
            self._scroll_x = self._display.WIDTH

    def _render_fixed(self):
        """Render fixed (non-scrolling) text, centered horizontally."""
        self._display.set_font(self._font)
        self._display.set_pen(*self._color)
        y = FONT_Y_OFFSET.get(self._font, 2)
        width = self._display.measure_text(self._text, 1)
        x = (self._display.WIDTH - width) // 2
        if x < 0:
            x = 0
        self._display.draw_text(self._text, x, y)
