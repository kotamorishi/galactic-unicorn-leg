# Galactic Unicorn LED Display Device — Specification v2.0

## Overview

Pimoroni Galactic Unicorn（Raspberry Pi Pico W搭載）を使用したLED表示デバイス。
ローカルネットワーク内のスマホ・PCからWebブラウザ経由で設定を行い、スケジュールに基づいてメッセージ表示と音声再生を自動実行する。

電源駆動（USB給電・常時電源）を前提とし、省電力対応は不要。

---

## Hardware

| Item | Spec |
|------|------|
| Device | Pimoroni Galactic Unicorn |
| Controller | Raspberry Pi Pico W (RP2040, Cortex-M0+ 133MHz, 264KB SRAM, 2MB Flash) |
| Display | 53 x 11 RGB LED matrix (583 pixels) |
| Audio | I2S amplifier + 1W speaker (synth engine) |
| Connectivity | WiFi 2.4GHz (CYW43439) |
| Buttons | A, B, C, D, Sleep, Volume Up/Down, Brightness Up/Down |
| Light Sensor | Phototransistor (12-bit ADC) |
| Expansion | Qw/ST (Qwiic/STEMMA QT) I2C x2 |
| Power | Micro-USB (always-on) |
| Dimensions | 331 x 79 mm |

## Software

| Item | Technology |
|------|------------|
| Language | MicroPython |
| Firmware | Pimoroni custom MicroPython v1.24.3 (`pico_w_galactic-v1.24.3-micropython.uf2`) |
| Web framework | microdot (embedded, 1566 lines) |
| Async | uasyncio (cooperative multitasking) |
| Time | NTP sync → built-in RTC |

---

## Features

### F-01: Message Display

LEDマトリクスにテキストメッセージを表示する。

| Item | Spec |
|------|------|
| Display modes | Fixed (centered) / Scroll (right-to-left) |
| Scroll speeds | Slow (80ms/px), Medium (50ms/px), Fast (25ms/px) |
| Text color | RGB (0-255 per channel) |
| Fonts | bitmap6 (small, Y-offset 3), bitmap8 (normal, Y-offset 2) |
| Max text length | 128 characters |
| Scroll loop | Resets to right edge after text exits left |

### F-02: Scheduled Display

スケジュールに基づいてメッセージの表示タイミングを制御する。各スケジュールに個別のメッセージを設定可能。

| Item | Spec |
|------|------|
| Time range | Start time — End time (HH:MM) |
| Overnight support | Yes (e.g., 22:00 — 06:00) |
| Weekday filter | Mon — Sun (multiple selectable) |
| Per-schedule message | Each schedule has its own message text (max 128 chars) |
| Fallback message | If schedule message is empty, global message (Message section) is used |
| Multiple schedules | Supported. First matching active schedule wins |
| Enable/disable | Per-schedule toggle without deletion |
| Schedule check interval | Every 60 seconds |
| Timezone | Configurable UTC offset (-12 to +14). Applied to NTP-synced RTC |
| Off behavior | LEDs off when no schedule is active |

### F-03: Audio Playback

スケジュール開始時に音を再生する。

| Item | Spec |
|------|------|
| Trigger | Schedule start time (once per schedule activation) |
| Source | 20 built-in synth presets |
| Per-schedule sound | Each schedule selects a preset and volume |
| Volume | Per-schedule (25/50/75/100%) + master volume (0-100%) |
| Preview | Web UI から試聴可能 |
| Engine | SID-style synth with ADSR envelope |
| Waveforms | Square, Sine, Triangle, Sawtooth, Noise |

#### Sound Presets

| # | Category | Name | Description |
|---|----------|------|-------------|
| 01 | Notification | Simple Beep | Single 880Hz square beep |
| 02 | Notification | Double Beep | Two 880Hz square beeps |
| 03 | Notification | Triple Beep | Three 880Hz square beeps |
| 04 | Notification | Rising Chime | 523→784Hz sine progression |
| 05 | Notification | Falling Chime | 784→523Hz sine progression |
| 06 | Notification | Three-tone Chime | 523→659→784Hz sine (Do-Mi-Sol) |
| 07 | Alarm | Alarm (Low) | 330Hz repeated square pulses |
| 08 | Alarm | Alarm (High) | 1047Hz repeated square pulses |
| 09 | Alarm | Siren | 660↔880Hz sawtooth oscillation |
| 10 | Alarm | Urgent Alert | 1200Hz rapid square bursts |
| 11 | Melody | Westminster Chime | 659→523→587→392Hz (time chime) |
| 12 | Melody | Do Re Mi Fa | 523→587→659→698Hz ascending |
| 13 | Melody | Fanfare | 523→659→784→1047Hz victory |
| 14 | Melody | Music Box | 784→659→784Hz gentle sine |
| 15 | SFX | Coin | 988→1319Hz game coin |
| 16 | SFX | Power Up | 392→1047Hz ascending 5-note |
| 17 | SFX | Level Up | 523→1319Hz ascending arpeggio |
| 18 | SFX | Error | 200→150Hz descending sawtooth |
| 19 | SFX | Success | 523→659→1047Hz bright completion |
| 20 | SFX | Click | 1500Hz noise burst |

### F-04: WiFi Initial Setup (Captive Portal)

初回起動時またはWiFi未設定時にAPモードを起動し、キャプティブポータルでWiFi設定を行う。

| Item | Spec |
|------|------|
| AP SSID | `GalacticUnicorn-Setup` |
| AP Password | `unicorn1` (WPA2) |
| AP IP | 192.168.4.1 |
| Captive portal | DNS server redirects all queries to AP IP |
| Platform detection | iOS (`/hotspot-detect.html`), Android (`/generate_204`, `/gen_204`), Windows (`/connecttest.txt`, `/redirect`) |
| Setup URL | `http://192.168.4.1/setup` |
| WiFi scan | Scans available networks, displayed in dropdown |
| Manual entry | "Enter manually..." option shows SSID text input |
| Save flow | Save credentials → 2-second delay → automatic reboot into STA mode |
| LED during AP mode | Cyan scrolling text: "WiFi: GalacticUnicorn-Setup Pass: unicorn1 Open: http://192.168.4.1" |
| Re-setup | A+D buttons long press (5 seconds) → delete WiFi config → reboot into AP mode |

### F-05: Web Server (Configuration UI)

デバイス上で常時稼働するHTTPサーバー。

| Item | Spec |
|------|------|
| Protocol | HTTP (port 80) |
| Framework | microdot (async, streaming response) |
| Responsive | Mobile + Desktop |
| Authentication | None (local network only) |
| HTML delivery | Streaming async generator (max ~2KB per chunk) for low RAM usage |

#### Pages

**Main Page (`/`)**

Single-page design with 4 sections:

1. **Now** — Real-time status
   - Server clock (HH:MM:SS + weekday), updated every 1 second via polling
   - Display state: "Displaying" (green) with end time, or "Off" with next schedule
   - Currently displayed message text

2. **Message** — Global message settings
   - Text input (primary, always visible)
   - Save button → immediately shows on LED
   - Collapsible "Options": display mode, scroll speed, font, color picker

3. **Schedule** — Schedule list
   - Each card shows: checkbox (enable/disable) + message text + time range + days
   - Tap to expand edit panel: message, start/end time, weekday checkboxes, sound toggle with preset picker and volume, preview button, remove button
   - "Add schedule" + "Save" buttons
   - Save updates display immediately, re-renders schedule list from API response

4. **Quick Settings**
   - Brightness slider (0-100%, instant apply)
   - Volume slider (0-100%, instant apply)

5. **Footer** — link to Device Settings

**Device Settings Page (`/settings`)**

- WiFi info: status, SSID, IP, signal strength
- Collapsible "Change WiFi": scan dropdown, manual entry, password, connect + rescan
- Device info: version, free memory, NTP sync status
- Timezone selector (UTC-12 to UTC+14, instant save)
- Check for updates button
- Reboot button
- Back link to main page

**WiFi Setup Page (`/setup`)**

- Initial setup only (AP mode)
- WiFi scan dropdown + manual entry + password
- Connect → save + reboot

#### API Endpoints

| Method | Path | Request Body | Response | Description |
|--------|------|-------------|----------|-------------|
| GET | `/api/status` | — | `{active, message, active_end, next_start, next_day, time, day}` | Current display status + server time |
| GET | `/api/message` | — | message config object | Get global message |
| POST | `/api/message` | `{text, display_mode, scroll_speed, color:{r,g,b}, font}` | validated message | Set global message + activate display |
| GET | `/api/schedules` | — | schedule array | Get all schedules |
| POST | `/api/schedules` | schedule array | validated schedule array | Set all schedules |
| POST | `/api/sound/preview` | `{preset_id, volume}` | `{status:"ok"}` | Preview a sound preset |
| GET | `/api/sound/presets` | — | `[{id, name, category}]` | List all presets |
| POST | `/api/system/brightness` | `{brightness}` | `{brightness}` | Set LED brightness (0-100) |
| POST | `/api/system/volume` | `{volume}` | `{volume}` | Set master volume (0-100) |
| POST | `/api/system/timezone` | `{timezone_offset}` | `{timezone_offset}` | Set timezone (-12 to +14) |
| GET | `/api/wifi/scan` | — | `[{ssid, rssi}]` | Scan WiFi networks |
| POST | `/api/wifi/connect` | `{ssid, password}` | `{status:"saved"}` | Save WiFi + reboot |
| POST | `/api/ota/check` | — | `{status, updated, errors, version}` | Check and apply OTA update |
| POST | `/api/system/reboot` | — | `{status:"rebooting"}` | Reboot (1s delayed) |

### F-06: OTA Auto-Update

GitHubリポジトリの最新コードを定期的にチェックし、`.py` ファイルを自動更新する。

| Item | Spec |
|------|------|
| Target | `.py` files listed in `manifest.json` |
| Not updated | Firmware (UF2), config files (`wifi_config.json`, `app_config.json`) |
| Check frequency | Daily at configured hour (default 3:00 AM) |
| Check interval | Every 30 minutes (triggers only at configured hour) |
| Check method | Fetch `manifest.json` from `raw.githubusercontent.com`, compare version |
| Download | One file at a time, write to `.tmp` then `os.rename()` |
| Memory | Display and scheduler paused during update to free RAM for HTTPS |
| Post-update | Save version → automatic reboot |
| Manual trigger | "Check for updates" button on Device Settings page |
| Update display | "Updating..." shown on LED during update |
| Failure: API unreachable | Skip, retry next cycle |
| Failure: download error | Skip file, continue with remaining. Next update re-downloads all |
| Failure: boot after update | A+D long press → AP mode for manual recovery |

#### manifest.json (in repository)

```json
{
  "version": "0.1.0",
  "files": [
    "main.py",
    "boot.py",
    "hal/__init__.py",
    "hal/interfaces.py",
    "hal/real.py",
    "hal/mock.py",
    "config/__init__.py",
    "config/config_manager.py",
    "display/__init__.py",
    "display/renderer.py",
    "audio/__init__.py",
    "audio/presets.py",
    "audio/player.py",
    "scheduler/__init__.py",
    "scheduler/scheduler.py",
    "wifi/__init__.py",
    "wifi/manager.py",
    "wifi/captive_dns.py",
    "web/__init__.py",
    "web/server.py",
    "web/routes.py",
    "web/templates.py",
    "ota/__init__.py",
    "ota/updater.py",
    "lib/__init__.py",
    "lib/microdot.py"
  ]
}
```

#### ota_config.json (on device)

```json
{
  "repo": "username/galactic-unicorn-leg",
  "branch": "main",
  "app_path": "src/",
  "check_hour": 3
}
```

---

## Physical Buttons

| Button | Action |
|--------|--------|
| A (short press) | Show IP address on LED for 5 seconds |
| B (short press) | Show configured WiFi SSID on LED for 5 seconds |
| A + D (hold 5 seconds) | Delete WiFi config and reboot into AP setup mode |
| C | Not used |
| Sleep | Not used |
| Volume Up/Down | Not used (volume controlled via Web UI) |
| Brightness Up/Down | Not used (brightness controlled via Web UI) |

---

## Boot Sequence

```
1. boot.py: gc.collect()
2. Hardware init: GalacticUnicorn → PicoGraphics → Audio → Network → Buttons → System
3. Component init: DisplayRenderer → AudioPlayer → Scheduler → WiFiManager → CaptiveDNS → OTAUpdater
4. WiFi boot:
   ├── wifi_config.json exists?
   │   ├── NO  → Show "Starting..." → AP mode + captive DNS
   │   │         LED scrolls: "WiFi: GalacticUnicorn-Setup  Pass: unicorn1  Open: http://192.168.4.1"
   │   └── YES → Show "WiFi..." → Connect (30s timeout)
   │             ├── FAIL → AP mode (same as above)
   │             └── OK   → Show "NTP Sync..." → NTP sync → Show IP (green, 2s)
   │
5. Load config: app_config.json → configure display, scheduler, timezone
   (Skip display config in AP mode to preserve setup scroll text)
6. Start async tasks:
   ├── display_loop          (every 25-80ms depending on scroll speed)
   ├── button_check_loop     (every 200ms)
   ├── scheduler_loop        (every 60s)        [STA mode only]
   ├── wifi_monitor_loop     (every 30s)        [STA mode only]
   ├── ota_check_loop        (every 30min)      [STA mode only]
   └── captive_dns           (every 50ms)       [AP mode only]
7. Start web server on 0.0.0.0:80 (blocking)
```

---

## WiFi Connection Management

| Item | Spec |
|------|------|
| Connection monitor | Every 30 seconds |
| Reconnect backoff | 5s → 10s → 20s → 40s → 60s (5 attempts) |
| After max retries | 5-minute pause, then restart cycle |
| During disconnection | Schedules continue (RTC-based), web server unavailable, OTA skipped |
| After reconnection | NTP re-sync immediately |
| NTP sync interval | Every 1 hour |
| Tick overflow safety | `time.ticks_diff()` used for all timing calculations (safe beyond 12.4 days) |

---

## Data Storage

### Config Files (on device flash)

| File | Purpose | Written by |
|------|---------|-----------|
| `wifi_config.json` | WiFi SSID + password | Setup page, WiFi change |
| `app_config.json` | Message, schedules, system settings | All settings APIs |
| `ota_config.json` | OTA repository + branch + check hour | Manual configuration |
| `version.json` | Current installed version hash | OTA updater |

All config writes use **atomic tmp+rename** pattern (`file.tmp` → `os.rename()`) to prevent corruption on power loss.

### app_config.json Structure

```json
{
  "message": {
    "text": "Hello!",
    "display_mode": "scroll",
    "scroll_speed": "medium",
    "color": {"r": 255, "g": 255, "b": 255},
    "font": "bitmap8"
  },
  "schedules": [
    {
      "id": 1,
      "enabled": true,
      "start_time": "08:00",
      "end_time": "09:00",
      "days": ["mon", "tue", "wed", "thu", "fri"],
      "message": "Good morning!",
      "sound": {
        "enabled": true,
        "preset_id": 4,
        "volume": 50
      }
    }
  ],
  "system": {
    "brightness": 50,
    "timezone_offset": 9
  }
}
```

### Validation Rules

| Field | Rule |
|-------|------|
| `message.text` | String, max 128 chars, truncated if longer |
| `message.display_mode` | "scroll" or "fixed", defaults to "scroll" |
| `message.scroll_speed` | "slow", "medium", or "fast", defaults to "medium" |
| `message.color.r/g/b` | Integer 0-255, clamped |
| `message.font` | "bitmap6" or "bitmap8", defaults to "bitmap8" |
| `schedule.start_time/end_time` | "HH:MM" format, invalid → "00:00", hours clamped 0-23, minutes clamped 0-59 |
| `schedule.days` | Array of "mon"-"sun", invalid entries filtered out |
| `schedule.message` | String, max 128 chars |
| `schedule.sound.preset_id` | Integer 1-20, clamped |
| `schedule.sound.volume` | Integer 0-100, clamped |
| `system.brightness` | Integer 0-100, clamped |
| `system.timezone_offset` | Integer -12 to +14, clamped |
| Corrupt/missing config | Falls back to defaults, never crashes |

---

## Architecture

### Project Structure

```
src/
├── main.py              # Entry point + async event loop
├── boot.py              # MicroPython boot (gc.collect)
├── manifest.json        # OTA file manifest
├── hal/                 # Hardware Abstraction Layer
│   ├── interfaces.py    # Abstract interfaces (Display, Audio, Network, Buttons, System)
│   ├── real.py          # Real Galactic Unicorn implementation
│   └── mock.py          # PC testing mocks
├── config/
│   └── config_manager.py  # JSON config CRUD with atomic writes + validation
├── display/
│   └── renderer.py      # LED text renderer (fixed/scroll/status modes)
├── audio/
│   ├── presets.py       # 20 synth preset definitions
│   └── player.py        # Preset playback via HAL
├── scheduler/
│   └── scheduler.py     # Time-range + weekday matching with timezone
├── wifi/
│   ├── manager.py       # STA/AP management, auto-reconnect, NTP
│   └── captive_dns.py   # DNS server for captive portal
├── web/
│   ├── server.py        # microdot app factory
│   ├── routes.py        # API + page routes
│   └── templates.py     # Streaming HTML templates (async generators)
├── ota/
│   └── updater.py       # GitHub OTA updater
└── lib/
    └── microdot.py      # Web framework (third-party)
```

### Design Principles

- **HAL separation**: All hardware access via abstract interfaces → testable on PC
- **Streaming HTML**: Templates yield small chunks (~2KB max) to avoid memory allocation failures
- **Atomic config writes**: tmp file + rename to prevent corruption on power loss
- **Cooperative async**: All long-running operations use asyncio; never block the event loop unnecessarily
- **Graceful degradation**: WiFi failure → continue displaying; config corruption → use defaults; exception in any loop → log and continue
- **Overflow-safe timing**: `time.ticks_diff()` for all tick arithmetic (safe beyond 12.4 days)
- **Client-side rendering**: Schedule data and presets sent as compact JS arrays, rendered in browser to minimize server memory

---

## Testing

### Test Suite

101 tests running on PC (CPython + pytest). No device required.

| Test File | Count | Coverage |
|-----------|-------|----------|
| `test_imports.py` | 13 | All source modules import without SyntaxError |
| `test_config.py` | 18 | Config CRUD, validation, corruption recovery, atomic writes |
| `test_scheduler.py` | 22 | Time ranges (normal, overnight, boundaries), weekday filter, timezone, start trigger dedup |
| `test_audio.py` | 14 | All 20 presets: structure, required keys, waveforms, frequency/volume/ADSR ranges |
| `test_display.py` | 9 | Fixed/scroll rendering, wrap-around, status overlay, centering, active/inactive |
| `test_ota.py` | 8 | Version comparison, manifest URL, 404 handling, file write, directory creation |

### Run Tests

```bash
pip install pytest
pytest tests/ -v
```

### What Requires Device Testing

- LED visual rendering and color accuracy
- Audio playback and volume
- WiFi AP/STA mode switching
- Captive portal detection on various phones
- Physical button responsiveness
- Long-term stability (24h+ uptime)
- OTA end-to-end (GitHub → device)

---

## Constraints

| Item | Detail |
|------|--------|
| RAM | ~192KB usable. HTML streaming, gc.collect() before page render, presets as data not code |
| Flash | 2MB shared with firmware. ~1.4MB usable. Write endurance ~100K cycles |
| Display | 53x11 pixels. ~6-8 visible characters at once |
| WiFi | 2.4GHz only, no 5GHz, no Bluetooth |
| HTTP only | No HTTPS for web UI (local network assumption) |
| Single user | Web server handles 1-2 concurrent connections |
| RTC volatile | Loses time on power off → NTP required on every boot |
| No image support | No JPEG/PNG decoding. Text and procedural graphics only |

---

## Future Expansion (Out of Scope)

- Multiple message rotation within a schedule
- Graphic/animation display
- External API integration (weather, news, etc.)
- mDNS (`http://unicorn.local`)
- Firmware (UF2) OTA update
- Authentication for web UI
- HTTPS support
