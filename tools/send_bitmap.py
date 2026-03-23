#!/usr/bin/env python3
"""Render text (including Japanese) to bitmap and send to Galactic Unicorn.

Requirements:
    pip install requests Pillow

Usage:
    python3 send_bitmap.py "こんにちは世界！"
    python3 send_bitmap.py "会議は15時から" --color 0,255,128
    python3 send_bitmap.py "HELLO" --mode fixed
    python3 send_bitmap.py --clear

Font:
    Place a Japanese-capable TTF font (e.g., NotoSansJP-Regular.ttf) in the
    same directory, or specify with --font.
"""

import argparse
import base64
import os
import requests
from PIL import Image, ImageDraw, ImageFont

DISPLAY_HEIGHT = 11
DEFAULT_DEVICE = "http://192.168.1.42"


def render_to_mono_bitmap(text, font_path, font_size=10):
    """Render text to a 1-bit monochrome bitmap at DISPLAY_HEIGHT px."""
    font = ImageFont.truetype(font_path, font_size)

    # Measure text width
    bbox = font.getbbox(text)
    text_width = bbox[2] - bbox[0] + 2
    text_height = bbox[3] - bbox[1]

    # Render to 1-bit image
    img = Image.new("1", (text_width, DISPLAY_HEIGHT), 0)
    draw = ImageDraw.Draw(img)
    y_offset = (DISPLAY_HEIGHT - text_height) // 2 - bbox[1]
    draw.text((0, y_offset), text, fill=1, font=font)

    # Find actual used width (trim trailing blank columns)
    width = img.width
    pixels = img.load()
    while width > 1:
        col_empty = all(pixels[width - 1, y] == 0 for y in range(DISPLAY_HEIGHT))
        if not col_empty:
            break
        width -= 1
    width += 1  # 1px trailing space

    # Pack to mono bitmap bytes (MSB first, row-padded)
    row_bytes = (width + 7) // 8
    bitmap = bytearray(row_bytes * DISPLAY_HEIGHT)
    for y in range(DISPLAY_HEIGHT):
        for x in range(width):
            if pixels[x, y]:
                bitmap[y * row_bytes + x // 8] |= (1 << (7 - x % 8))

    return width, bitmap


def find_font(font_arg):
    """Find a suitable font file."""
    if font_arg and os.path.exists(font_arg):
        return font_arg

    # Try common Japanese font paths
    candidates = [
        "NotoSansJP-Regular.ttf",
        "NotoSansCJK-Regular.ttc",
        "/usr/share/fonts/opentype/noto/NotoSansCJK-Regular.ttc",
        "/usr/share/fonts/noto-cjk/NotoSansCJK-Regular.ttc",
        "/System/Library/Fonts/ヒラギノ角ゴシック W3.ttc",
        "/System/Library/Fonts/Hiragino Sans GB.ttc",
    ]
    for path in candidates:
        if os.path.exists(path):
            return path

    # Fallback to default
    return "NotoSansJP-Regular.ttf"


def main():
    parser = argparse.ArgumentParser(description="Send text bitmap to Galactic Unicorn")
    parser.add_argument("text", nargs="?", help="Text to display")
    parser.add_argument("--device", default=DEFAULT_DEVICE, help="Device URL")
    parser.add_argument("--color", default="255,200,0", help="R,G,B foreground color")
    parser.add_argument("--bg", default="0,0,0", help="R,G,B background color")
    parser.add_argument("--mode", default="scroll", choices=["scroll", "fixed"])
    parser.add_argument("--speed", default="medium", choices=["slow", "medium", "fast"])
    parser.add_argument("--font", default=None, help="Path to TTF font file")
    parser.add_argument("--size", type=int, default=10, help="Font size (default: 10)")
    parser.add_argument("--clear", action="store_true", help="Clear bitmap, return to text mode")
    args = parser.parse_args()

    if args.clear:
        resp = requests.delete("{}/api/bitmap".format(args.device))
        print("Clear:", resp.json())
        return

    if not args.text:
        parser.error("text is required (or use --clear)")

    font_path = find_font(args.font)
    print("Using font:", font_path)

    width, bitmap = render_to_mono_bitmap(args.text, font_path, args.size)
    print("Bitmap: {}x{} ({} bytes)".format(width, DISPLAY_HEIGHT, len(bitmap)))

    r, g, b = [int(x) for x in args.color.split(",")]
    br, bg_val, bb = [int(x) for x in args.bg.split(",")]

    payload = {
        "width": width,
        "height": DISPLAY_HEIGHT,
        "format": "mono",
        "color": {"r": r, "g": g, "b": b},
        "bg_color": {"r": br, "g": bg_val, "b": bb},
        "display_mode": args.mode,
        "scroll_speed": args.speed,
        "data": base64.b64encode(bitmap).decode("ascii"),
    }

    resp = requests.post("{}/api/bitmap".format(args.device), json=payload)
    print("Response:", resp.json())


if __name__ == "__main__":
    main()
