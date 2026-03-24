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
        self._scroll_interval_ms = 50
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
        # Bitmap mode
        self._bitmap_data = None
        self._bitmap_width = 0
        self._bitmap_format = "mono"
        self._bitmap_color = (255, 255, 255)
        self._bitmap_bg_color = (0, 0, 0)

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
        self._scroll_interval_ms = SCROLL_SPEED_MS.get(self._scroll_speed, 50)
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

    def set_bitmap(self, width, height, fmt, data, color, bg_color, mode, speed):
        """Set bitmap data for display.

        Args:
            width: bitmap width in pixels
            height: must be 11
            fmt: "mono" or "rgb"
            data: bytearray (already decoded from base64)
            color: (r, g, b) foreground for mono
            bg_color: (r, g, b) background
            mode: "scroll" or "fixed"
            speed: "slow", "medium", "fast"
        """
        self._bitmap_data = data
        self._bitmap_width = width
        self._bitmap_format = fmt
        self._bitmap_color = color
        self._bitmap_bg_color = bg_color
        self._mode = mode
        self._scroll_speed = speed
        self._scroll_interval_ms = SCROLL_SPEED_MS.get(speed, 50)
        self._effective_mode = mode
        if mode == "scroll" and width <= self._display.WIDTH:
            self._effective_mode = "fixed"
        self._scroll_x = self._display.WIDTH
        self._scroll_cycle = width + SCROLL_GAP
        self._frame_dirty = True
        self._pen_dirty = True
        self._active = True
        self._manual_active = True

    def clear_bitmap(self):
        """Clear bitmap data and return to text mode."""
        self._bitmap_data = None
        self._frame_dirty = True

    def show_status(self, text):
        """Show a temporary status message (e.g., 'Updating...')."""
        self._status_text = text
        self._frame_dirty = True

    def clear_status(self):
        """Clear status message and return to normal display."""
        self._status_text = None
        self._frame_dirty = True

    def get_scroll_interval_ms(self):
        """Return the cached scroll update interval in ms."""
        return self._scroll_interval_ms

    def render_frame(self):
        """Render one frame to the display.

        For scroll mode, advances the scroll position by 1 pixel.
        For fixed/status/inactive modes, skips redraw if nothing changed.
        Call this at the interval returned by get_scroll_interval_ms().
        """
        # Bitmap mode takes priority
        if self._bitmap_data is not None and self._active:
            if self._effective_mode == "fixed" and not self._frame_dirty:
                return
            self._display.clear()
            if self._effective_mode == "scroll":
                self._render_bitmap_scroll()
            else:
                self._render_bitmap_fixed()
                self._frame_dirty = False
            self._display.update()
            return
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

    def _render_scroll(self):
        """Render scrolling text, advancing 1px per frame.

        Guards inlined to avoid 3 bound-method allocations per frame.
        """
        display = self._display
        # Inline _draw_border
        if self._border:
            display.set_pen(*self._border_color)
            self._pen_dirty = True
            display.draw_line(0, 0, display.WIDTH - 1, 0)
            display.draw_line(0, display.HEIGHT - 1, display.WIDTH - 1, display.HEIGHT - 1)
        # Inline _ensure_font
        if not self._font_set:
            display.set_font(self._get_font_arg())
            self._font_set = True
        # Inline _ensure_pen
        if self._pen_dirty:
            display.set_pen(*self._color)
            self._pen_dirty = False
        display.draw_text(self._text, self._scroll_x, self._y_offset)

        self._scroll_x -= 1
        if self._scroll_x < -self._scroll_cycle:
            self._scroll_x = display.WIDTH
            if self._on_scroll_cycle:
                self._on_scroll_cycle()

    def _render_fixed(self):
        """Render fixed (non-scrolling) text, centered horizontally.

        Guards inlined for consistency with _render_scroll.
        """
        display = self._display
        if self._border:
            display.set_pen(*self._border_color)
            self._pen_dirty = True
            display.draw_line(0, 0, display.WIDTH - 1, 0)
            display.draw_line(0, display.HEIGHT - 1, display.WIDTH - 1, display.HEIGHT - 1)
        if not self._font_set:
            display.set_font(self._get_font_arg())
            self._font_set = True
        if self._pen_dirty:
            display.set_pen(*self._color)
            self._pen_dirty = False
        display.draw_text(self._text, self._fixed_x, self._y_offset)

    # --- Bitmap rendering ---

    def _bitmap_get_pixel(self, bx, by):
        """Get mono pixel value (for tests/external use, not hot path)."""
        if bx < 0 or bx >= self._bitmap_width or by < 0 or by >= 11:
            return False
        row_bytes = (self._bitmap_width + 7) // 8
        byte_idx = by * row_bytes + (bx >> 3)
        return bool(self._bitmap_data[byte_idx] & (0x80 >> (bx & 7)))

    # Performance-critical: uses local variables and inlined pixel access
    # to minimize attribute lookups and method calls per frame.

    def _render_bitmap_frame(self, offset_x):
        """Render bitmap at given x offset. Inlined for performance."""
        display = self._display
        data = self._bitmap_data
        bw = self._bitmap_width
        dw = display.WIDTH
        dh = display.HEIGHT
        is_mono = self._bitmap_format == "mono"

        # Background
        bg = self._bitmap_bg_color
        if bg[0] | bg[1] | bg[2]:
            display.set_pen(bg[0], bg[1], bg[2])
            display.draw_rectangle(0, 0, dw, dh)

        if is_mono:
            # Set pen once for all rows
            fc = self._bitmap_color
            display.set_pen(fc[0], fc[1], fc[2])
            row_bytes = (bw + 7) // 8
            x_range = range(dw)

            for y in range(dh):
                row_base = y * row_bytes
                span_start = -1
                for sx in x_range:
                    bx = sx - offset_x
                    # Inline bit test — no method call
                    if 0 <= bx < bw:
                        byte_idx = row_base + (bx >> 3)
                        if data[byte_idx] & (0x80 >> (bx & 7)):
                            if span_start < 0:
                                span_start = sx
                            continue
                    if span_start >= 0:
                        display.pixel_span(span_start, y, sx - span_start)
                        span_start = -1
                if span_start >= 0:
                    display.pixel_span(span_start, y, dw - span_start)
        else:
            # RGB: inline pixel reads, no tuple allocation
            last_r = last_g = last_b = -1
            draw_pixel = display.draw_pixel
            set_pen = display.set_pen
            x_range = range(dw)

            for y in range(dh):
                for sx in x_range:
                    bx = sx - offset_x
                    if 0 <= bx < bw:
                        idx = (y * bw + bx) * 3
                        r = data[idx]
                        g = data[idx + 1]
                        b = data[idx + 2]
                        if r | g | b:  # skip black pixels (no tuple creation)
                            if r != last_r or g != last_g or b != last_b:
                                set_pen(r, g, b)
                                last_r, last_g, last_b = r, g, b
                            draw_pixel(sx, y)

    def _render_bitmap_scroll(self):
        """Render scrolling bitmap, advancing 1px per frame."""
        self._render_bitmap_frame(self._scroll_x)
        self._scroll_x -= 1
        if self._scroll_x < -self._scroll_cycle:
            self._scroll_x = self._display.WIDTH
            if self._on_scroll_cycle:
                self._on_scroll_cycle()

    def _render_bitmap_fixed(self):
        """Render fixed bitmap, centered horizontally."""
        offset_x = (self._display.WIDTH - self._bitmap_width) // 2
        if offset_x < 0:
            offset_x = 0
        self._render_bitmap_frame(offset_x)
