# CLAUDE.md - Galactic Unicorn LED Display Device

## Project Overview

Pimoroni Galactic Unicorn (Raspberry Pi Pico W) を使用したLED表示デバイスのファームウェア開発プロジェクト。
ローカルネットワーク内からWebブラウザで設定し、スケジュールに基づいてメッセージ表示・音声再生を自動実行する。

- 仕様書: `docs/specification.md`
- 調査資料: `docs/galactic-unicorn-feasibility-study.md`

## Hardware

- **Device**: Pimoroni Galactic Unicorn
- **Controller**: Raspberry Pi Pico W (RP2040, Cortex-M0+ 133MHz, 264KB SRAM, 2MB Flash)
- **Display**: 53x11 RGB LED matrix
- **Audio**: I2S amp + 1W speaker (SID-style synth engine)
- **Connectivity**: WiFi 2.4GHz (CYW43439)
- **Buttons**: A, B, C, D, Sleep, Volume Up/Down, Brightness Up/Down
- **Power**: USB (always-on, no battery optimization needed)
- **Storage**: 2MB QSPI Flash (non-volatile). ~1.4MB usable as FAT filesystem after firmware. Write endurance ~100K cycles — avoid frequent writes.
- **RTC**: Built-in but volatile (loses time on power off). NTP sync required on every boot.

## Firmware

- **File**: `pico_w_galactic-v1.24.3-micropython.uf2`
- **Source**: https://github.com/pimoroni/unicorn/releases/tag/v1.24.3
- **Type**: Pimoroni custom MicroPython (without filesystem — clean install)
- **Note**: `pico2_w_` variants are for Pico 2 W (not our device). `-with-filesystem` variants include sample code (not needed).

## Tech Stack

- **Language**: MicroPython
- **Firmware**: Pimoroni custom MicroPython (pre-installed on device)
- **Web framework**: microdot
- **Async**: asyncio (cooperative multitasking)
- **Time**: NTP sync → RTC
- **Display API**: PicoGraphics (`galactic_unicorn` module)
- **Audio API**: GalacticUnicorn synth engine

## Critical Constraints

These are hard limits of the hardware. Violating them will cause crashes or undefined behavior.

- **RAM**: ~192KB available to MicroPython. All allocations (HTML templates, JSON parsing, network buffers, framebuffer) share this pool. Always prefer streaming over buffering. Minimize string concatenation. Use `gc.collect()` proactively before large allocations.
- **Flash**: 2MB total shared with firmware. Keep `.py` files small. Do not store large static assets.
- **Single-threaded**: MicroPython runs on one core (second core drives LED PIO). Use `asyncio` for concurrency — never `time.sleep()` in the main loop as it blocks everything.
- **No filesystem journaling**: Power loss during file write can corrupt data. Write to a temp file first, then rename (atomic on FAT).
- **Flash write endurance**: ~100K cycles per sector. Never write config on every request — batch or debounce. Avoid writing in loops. Log to RAM, not Flash.
- **WiFi + Display init order**: Initialize GalacticUnicorn before WiFi to avoid known conflicts.

## Project Structure

```
galactic-unicorn-leg/
├── CLAUDE.md
├── LICENSE
├── .gitignore
├── docs/
│   ├── specification.md          # Full specification
│   └── galactic-unicorn-feasibility-study.md
├── src/                          # MicroPython app code (deployed to Pico W)
│   ├── main.py                   # Entry point (boot → wifi → app)
│   ├── boot.py                   # MicroPython boot config
│   ├── manifest.json             # OTA update file manifest
│   ├── hal/                      # Hardware Abstraction Layer
│   │   ├── interfaces.py         # Abstract interfaces
│   │   ├── real.py               # Real hardware (GalacticUnicorn)
│   │   └── mock.py               # Mock for PC testing
│   ├── config/                   # Configuration management
│   ├── display/                  # LED matrix display logic
│   ├── audio/                    # Sound presets and playback
│   ├── web/                      # microdot web server and UI
│   ├── scheduler/                # Time-based schedule execution
│   ├── ota/                      # OTA update from GitHub
│   └── lib/                      # Third-party libraries (microdot, etc.)
└── tests/                        # PC-side tests (pytest, CPython)
    ├── conftest.py               # Shared fixtures (mock HAL, temp config files)
    ├── test_config/              # Config read/write, validation, corruption recovery
    ├── test_scheduler/           # Time range matching, weekday filter, edge cases
    ├── test_web/                 # API endpoints, input validation, HTML responses
    ├── test_ota/                 # Version comparison, manifest parsing, download logic
    └── test_audio/               # Preset data structure validation
```

## Design Principles

### Safety First (IoT Device)
- **Watchdog timer**: Use hardware watchdog to auto-recover from hangs. Reset if main loop stalls.
- **Graceful degradation**: If WiFi fails, continue displaying last known schedule. If NTP fails, use RTC (may drift). Never let a subsystem failure crash the whole device.
- **Safe file writes**: Always write config to `.tmp` then `os.rename()`. Never write directly to active config files.
- **Input validation**: Validate all Web UI inputs on the server side. Never trust client data. Sanitize text for display (length limits, character filtering).
- **Memory safety**: Call `gc.collect()` before heavy operations. Monitor free memory with `gc.mem_free()`. If memory is critically low, skip non-essential operations (e.g., OTA check).

### Reliability
- **Boot must always succeed**: `main.py` must be resilient. Wrap all initialization in try/except. If app config is corrupted, start with defaults. If WiFi config is missing/invalid, enter AP mode.
- **No silent failures**: Log errors to a small ring buffer in RAM (not flash — avoid wear). Expose via Web UI system page.
- **OTA safety**: Never overwrite a file that is currently being imported. Update sequence: download to `/tmp/`, verify size > 0, rename over target, then reboot.

### Maintainability
- **Separation of concerns**: Each module (`display/`, `audio/`, `web/`, `scheduler/`, `ota/`) is independent. Communicate via shared state or simple callbacks — no circular imports.
- **Minimal dependencies**: Only `microdot` as external dependency. Keep `lib/` small.
- **Config-driven**: Behavior is controlled by JSON config files, not hardcoded values. Sound presets are data (dicts), not code.
- **Consistent error handling pattern**: Use `try/except` with specific exceptions. Always log the error context. Return sensible defaults on failure.

## Coding Guidelines for MicroPython

### Memory
- Prefer `const()` for constants (compiled away, zero RAM)
- Use `micropython.const()` for module-level constants
- Avoid large string literals in functions — they consume RAM on each call
- Use `b""` bytes instead of `""` strings where possible (smaller on MicroPython)
- Prefer pre-allocated buffers over dynamic allocation in loops
- HTML templates should be read from files, not embedded as string literals

### Async
- All long-running operations must be `async`
- Use `await asyncio.sleep_ms(N)` instead of `time.sleep()`
- Keep individual async tasks short — yield often
- Web server, display loop, scheduler, and OTA check all run as concurrent async tasks

### File I/O
- Always use `with open(...) as f:` pattern
- For config writes: write to `filename.tmp`, then `os.rename("filename.tmp", "filename")`
- Keep JSON config files small — parse on demand, don't cache large structures in RAM
- Use `ujson` (MicroPython built-in) for JSON operations

### Web UI
- HTML/CSS/JS must be minimal — every byte counts against RAM/Flash
- Inline critical CSS, no external CSS frameworks
- Use vanilla JS only — no frameworks
- Compress where possible — minify HTML before deploying
- API endpoints return JSON; pages return minimal HTML

### Naming Conventions
- Files: `snake_case.py`
- Classes: `PascalCase`
- Functions/methods: `snake_case`
- Constants: `UPPER_SNAKE_CASE`
- Private: prefix with `_`

## Key APIs Reference

### Display
```python
from galactic import GalacticUnicorn
from picographics import PicoGraphics, DISPLAY_GALACTIC_UNICORN

gu = GalacticUnicorn()
graphics = PicoGraphics(display=DISPLAY_GALACTIC_UNICORN)

# Draw
graphics.set_font("bitmap8")
graphics.set_pen(graphics.create_pen(r, g, b))
graphics.text("msg", x, y, -1, scale)
graphics.clear()
gu.update(graphics)  # Push framebuffer to LEDs
```

### Audio
```python
channel = gu.synth_channel(0)
channel.configure(
    waveforms=GalacticUnicorn.WAVEFORM_SQUARE,
    frequency=440, volume=0.5,
    attack=0.1, decay=0.1, sustain=0.8, release=0.5
)
gu.set_volume(0.5)
channel.trigger_attack()
gu.play_synth()
# Later: channel.trigger_release() / gu.stop_playing()
```

### WiFi
```python
import network
wlan = network.WLAN(network.STA_IF)
wlan.active(True)
wlan.connect(ssid, password)

# AP mode
ap = network.WLAN(network.AP_IF)
ap.config(essid="GalacticUnicorn-Setup")
ap.active(True)
```

### NTP
```python
import ntptime
ntptime.settime()  # Syncs to RTC
```

## Testing

### Philosophy
- PC上（CPython + pytest）でテスト可能な範囲を最大化し、実機テストは最小限にする
- HAL（Hardware Abstraction Layer）でハードウェア依存を分離し、モックに差し替え可能にする

### Run tests
```bash
cd /Users/kota/workspace/galactic-unicorn-leg
pip install pytest httpx  # httpx is for web API testing
pytest tests/ -v
```

### What runs on PC (no device needed)
- **config/**: JSON読み書き、バリデーション、破損復旧
- **scheduler/**: 時間範囲判定、曜日フィルタ、日またぎ、境界値
- **web/**: 全APIエンドポイント、入力バリデーション、HTMLレスポンス（microdotはCPythonで動作）
- **ota/**: バージョン比較、マニフェスト解析、ダウンロードロジック（HTTPモック）
- **audio/presets.py**: プリセットデータの構造・値範囲検証

### What requires the device
- LED表示の視認確認、音声再生、WiFi AP/STA、物理ボタン、長時間稼働

## WiFi Resilience

- 30秒ごとに接続監視。切断時は指数バックオフで自動再接続（5s→10s→20s→40s→60s、最大5回）
- 再接続失敗後は5分待機してリトライサイクル再開。APモードには遷移しない
- 切断中もスケジュール表示は継続（RTC基準）。再接続後にNTP即時再同期

## Features (F-01 through F-06)

1. **F-01 Message Display** — Text on LED matrix (fixed/scroll, color, font)
2. **F-02 Scheduled Display** — Time range + weekday triggers
3. **F-03 Audio Playback** — 20 synth presets, triggered on schedule start
4. **F-04 WiFi Setup** — AP mode captive portal on first boot
5. **F-05 Web Server** — microdot HTTP server for all settings
6. **F-06 OTA Update** — Daily GitHub check, download `.py` files only. Display stops during update to free RAM for HTTPS.

See `docs/specification.md` for full details.
