"""Display renderer for LED matrix text display.

Supports fixed text display and horizontal scrolling.
Designed to be called from an async loop.
"""

SCROLL_SPEED_MS = {
    "slow": 80,
    "medium": 50,
    "fast": 25,
}

# Gap in pixels between end of text and re-entry from right during scroll
SCROLL_GAP = 20

# Actual pixel height of each font (used for vertical centering)
FONT_HEIGHT = {
    "bitmap6": 6,
    "bitmap8": 8,
    "font11": 11,
}

# Custom font data (loaded lazily to save RAM)
def _get_font11():
    """Load font11 bytearray on first use via binary file."""
    from display.font11_data import get_font
    return get_font()


class DisplayRenderer:

    def __init__(self, display_hal):
        self._display = display_hal
        self._text = ""
        self._mode = "scroll"
        self._scroll_speed = "medium"
        self._color = (255, 255, 255)
        self._bg_color = (0, 0, 0)
        self._has_bg = False
        self._border = False
        self._border_color = (80, 80, 80)
        self._font = "bitmap8"
        self._scroll_x = 0
        self._text_width = 0
        self._scroll_cycle = 0
        self._fixed_x = 0
        self._y_offset = 1
        self._font_set = False
        self._pen_dirty = True
        self._frame_dirty = True
        self._active = False
        self._manual_active = False
        self._status_text = None
        self._on_scroll_cycle = None

    def init(self, skip_hw_init=False):
        if not skip_hw_init:
            self._display.init()

    def configure(self, message_config):
        """Apply message config from app settings.

        Args:
            message_config: dict with text, display_mode, scroll_speed, color, bg_color, font
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
        bg = message_config.get("bg_color", {})
        self._bg_color = (
            bg.get("r", 0),
            bg.get("g", 0),
            bg.get("b", 0),
        )
        self._has_bg = self._bg_color != (0, 0, 0)
        self._border = message_config.get("border", False)
        bc = message_config.get("border_color", {})
        if bc:
            self._border_color = (
                bc.get("r", 80),
                bc.get("g", 80),
                bc.get("b", 80),
            )
        else:
            # Default: dim version of text color
            self._border_color = (
                self._color[0] // 3,
                self._color[1] // 3,
                self._color[2] // 3,
            )
        # Calculate Y offset for vertical centering
        fh = FONT_HEIGHT.get(self._font, 8)
        self._y_offset = (self._display.HEIGHT - fh) // 2
        self._frame_dirty = True
        self._pen_dirty = True
        self._reset_scroll()

    def _get_font_arg(self):
        """Return the font argument for set_font (string or bytearray)."""
        if self._font == "font11":
            return _get_font11()
        return self._font

    def _reset_scroll(self):
        """Reset scroll position and cache layout calculations."""
        self._scroll_x = self._display.WIDTH
        self._display.set_font(self._get_font_arg())
        self._font_set = True
        self._text_width = self._display.measure_text(self._text, 1)
        # Total scroll distance before wrap: text exits left + gap before re-entry
        self._scroll_cycle = self._text_width + SCROLL_GAP
        # Auto-downgrade: if text fits on screen, use fixed even if scroll requested
        self._effective_mode = self._mode
        if self._mode == "scroll" and self._text_width <= self._display.WIDTH:
            self._effective_mode = "fixed"
        # Cache fixed-mode X position
        x = (self._display.WIDTH - self._text_width) // 2
        self._fixed_x = x if x >= 0 else 0

    def set_active(self, active, manual=False):
        """Enable or disable display output.

        Args:
            active: True to enable, False to disable
            manual: True if triggered by user action (won't be overridden by scheduler)
        """
        if manual:
            self._manual_active = active
        if active != self._active:
            self._frame_dirty = True
            if active:
                self._reset_scroll()
                # Read sensor when display activates (for fixed mode)
                if self._on_scroll_cycle:
                    self._on_scroll_cycle()
        self._active = active

    def on_scroll_cycle(self, callback):
        """Register callback() called at the start of each scroll cycle.

        Called when text wraps around, before the new cycle renders.
        Right side of display is clear at this moment (good for sensor reads).
        """
        self._on_scroll_cycle = callback

    def show_status(self, text):
        """Show a temporary status message (e.g., 'Updating...')."""
        self._status_text = text
        self._frame_dirty = True

    def clear_status(self):
        """Clear status message and return to normal display."""
        self._status_text = None
        self._frame_dirty = True

    def get_scroll_interval_ms(self):
        """Return the scroll update interval in ms."""
        return SCROLL_SPEED_MS.get(self._scroll_speed, 50)

    def render_frame(self):
        """Render one frame to the display.

        For scroll mode, advances the scroll position by 1 pixel.
        For fixed/status/inactive modes, skips redraw if nothing changed.
        Call this at the interval returned by get_scroll_interval_ms().
        """
        if self._status_text:
            if not self._frame_dirty:
                return
            self._display.clear()
            self._pen_dirty = True
            self._render_status()
            self._frame_dirty = False
        elif self._active:
            # Scroll mode must redraw every frame; fixed mode only when dirty
            if self._effective_mode == "fixed" and not self._frame_dirty:
                return
            if self._has_bg:
                self._display.set_pen(*self._bg_color)
                self._display.draw_rectangle(0, 0, self._display.WIDTH, self._display.HEIGHT)
                self._pen_dirty = True
            else:
                self._display.clear()
            if self._effective_mode == "scroll":
                self._render_scroll()
            else:
                self._render_fixed()
                self._frame_dirty = False
        else:
            if not self._frame_dirty:
                return
            self._display.clear()
            self._pen_dirty = True
            self._frame_dirty = False

        self._display.update()

    def _render_status(self):
        """Render status text centered on display."""
        self._display.set_font("bitmap6")
        self._font_set = False  # Status uses different font; mark dirty
        self._display.set_pen(100, 100, 255)
        width = self._display.measure_text(self._status_text, 1)
        x = (self._display.WIDTH - width) // 2
        fh = FONT_HEIGHT.get("bitmap6", 6)
        y = (self._display.HEIGHT - fh) // 2
        self._display.draw_text(self._status_text, x, y)

    def _ensure_font(self):
        """Set font only if it changed (e.g., after status text used bitmap6)."""
        if not self._font_set:
            self._display.set_font(self._get_font_arg())
            self._font_set = True

    def _draw_border(self):
        """Draw 1px accent lines at top and bottom edges of the display."""
        if not self._border:
            return
        self._display.set_pen(*self._border_color)
        self._pen_dirty = True
        self._display.draw_line(0, 0, self._display.WIDTH - 1, 0)
        self._display.draw_line(0, self._display.HEIGHT - 1,
                                self._display.WIDTH - 1, self._display.HEIGHT - 1)

    def _ensure_pen(self):
        """Set text color pen only if it was changed by bg fill or border."""
        if self._pen_dirty:
            self._display.set_pen(*self._color)
            self._pen_dirty = False

    def _render_scroll(self):
        """Render scrolling text, advancing 1px per frame."""
        self._draw_border()
        self._ensure_font()
        self._ensure_pen()
        self._display.draw_text(self._text, self._scroll_x, self._y_offset)

        self._scroll_x -= 1
        # Wrap after text has fully exited left + gap
        if self._scroll_x < -self._scroll_cycle:
            self._scroll_x = self._display.WIDTH
            # Fire callback at cycle start — right side is clear for sensor
            if self._on_scroll_cycle:
                self._on_scroll_cycle()

    def _render_fixed(self):
        """Render fixed (non-scrolling) text, centered horizontally."""
        self._draw_border()
        self._ensure_font()
        self._ensure_pen()
        self._display.draw_text(self._text, self._fixed_x, self._y_offset)
