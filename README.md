# Galactic Unicorn LED Display

A scheduled LED message display with web-based configuration, built on the [Pimoroni Galactic Unicorn](https://shop.pimoroni.com/products/space-unicorns?variant=40842033561683) (Raspberry Pi Pico W).

Configure messages, schedules, and alert sounds from any phone or PC on your local network — no app install required.

## Features

- **Scrolling & fixed text** on a 53x11 RGB LED matrix
- **Time-based scheduling** — set start/end times and weekdays for each message
- **20 built-in sound presets** — notifications, alarms, melodies, and sound effects via the onboard speaker
- **Web UI** — responsive browser interface for all settings (mobile & desktop)
- **WiFi setup via captive portal** — on first boot, the device creates its own hotspot for configuration
- **OTA updates** — automatically pulls new code from GitHub once a day
- **Auto-reconnect** — recovers from WiFi drops with exponential backoff

## Hardware

| Component | Detail |
|-----------|--------|
| Device | Pimoroni Galactic Unicorn |
| Controller | Raspberry Pi Pico W (RP2040, 133MHz, 264KB SRAM, 2MB Flash) |
| Display | 53 x 11 RGB LED matrix (583 pixels) |
| Audio | I2S amplifier + 1W speaker |
| Connectivity | WiFi 2.4GHz |
| Power | USB (always-on) |

## Getting Started

### 1. Flash the firmware

Download the Pimoroni custom MicroPython firmware:

**[pico_w_galactic-v1.24.3-micropython.uf2](https://github.com/pimoroni/unicorn/releases/tag/v1.24.3)**

1. Hold the **BOOTSEL** button on the Pico W and plug in the USB cable
2. Drag the `.uf2` file to the `RPI-RP2` drive that appears
3. The device will reboot automatically

### 2. Deploy the code

Copy all files from `src/` to the Pico W filesystem using [Thonny](https://thonny.org/) or [mpremote](https://docs.micropython.org/en/latest/reference/mpremote.html):

```bash
# Using mpremote
mpremote connect auto fs cp -r src/ :
```

### 3. First boot — WiFi setup

1. Power on the device — the LED will scroll setup instructions
2. Connect to the `GalacticUnicorn-Setup` WiFi network (password: `unicorn1`)
3. Open a browser and go to `http://192.168.4.1/setup`
4. Select your home WiFi and enter the password
5. The device will save the credentials, connect, and sync the clock via NTP

### 4. Configure

Open a browser and go to the device's IP address (shown briefly on the LED display after connecting). From there you can:

- Set the display message, color, font, and scroll speed
- Create schedules with time ranges and weekday filters
- Choose alert sounds and adjust volume
- Manage WiFi and system settings

## Project Structure

```
galactic-unicorn-leg/
├── src/                  # MicroPython code (deployed to Pico W)
│   ├── main.py           # Entry point
│   ├── boot.py           # Boot config
│   ├── manifest.json     # OTA file manifest
│   ├── hal/              # Hardware Abstraction Layer
│   ├── config/           # JSON config management
│   ├── display/          # LED matrix rendering
│   ├── audio/            # Sound presets & playback
│   ├── web/              # HTTP server & UI
│   ├── scheduler/        # Time-based scheduling
│   ├── ota/              # GitHub OTA updater
│   └── lib/              # Third-party libs (microdot)
├── tests/                # PC-side tests (pytest)
└── docs/                 # Specification & research
```

## Development

### Prerequisites

- Python 3.9+
- pytest

### Running tests

Tests run entirely on your PC using mock hardware — no device needed.

```bash
pip install pytest
pytest tests/ -v
```

88 tests cover: config validation, schedule matching, audio preset data integrity, display rendering, and OTA logic.

### Architecture

All hardware access goes through the **HAL (Hardware Abstraction Layer)**:

- `hal/real.py` — talks to the actual Galactic Unicorn hardware
- `hal/mock.py` — fake implementation for PC-based testing

This separation allows developing and testing most of the codebase without the physical device.

### OTA Updates

The device checks GitHub once daily (default 3:00 AM) for code changes:

1. Fetches `manifest.json` from the repo
2. Compares the version hash with the locally stored version
3. Downloads changed `.py` files one by one
4. Writes each file atomically (tmp + rename)
5. Reboots with the new code

To configure OTA, create `ota_config.json` on the device:

```json
{
  "repo": "your-username/galactic-unicorn-leg",
  "branch": "main",
  "app_path": "src/",
  "check_hour": 3
}
```

### Factory Reset

Press and hold **A + D** buttons simultaneously for 5 seconds. This erases the WiFi config and reboots into AP setup mode.

## License

See [LICENSE](LICENSE).
