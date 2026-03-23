# Galactic Unicorn — API Reference

Base URL: `http://<device-ip>/`

All API endpoints accept and return JSON. Content-Type: `application/json`.

---

## Quick Start: Update display text from another device

```bash
# Show a message immediately
curl -X POST http://192.168.1.42/api/message \
  -H "Content-Type: application/json" \
  -d '{"text": "Hello from Raspberry Pi!"}'

# Show a message with color
curl -X POST http://192.168.1.42/api/message \
  -H "Content-Type: application/json" \
  -d '{"text": "ALERT!", "color": {"r": 255, "g": 0, "b": 0}}'

# Play a sound
curl -X POST http://192.168.1.42/api/sound/preview \
  -H "Content-Type: application/json" \
  -d '{"preset_id": 4, "volume": 75}'
```

### Python example (Raspberry Pi)

```python
import requests

UNICORN = "http://192.168.1.42"

# Update display message
requests.post(f"{UNICORN}/api/message", json={
    "text": "Temperature: 24.5C",
    "color": {"r": 0, "g": 255, "b": 100}
})

# Set a schedule
requests.post(f"{UNICORN}/api/schedules", json=[
    {
        "id": 1,
        "enabled": True,
        "start_time": "08:00",
        "end_time": "09:00",
        "days": ["mon", "tue", "wed", "thu", "fri"],
        "message": "GOOD MORNING",
        "color": {"r": 255, "g": 200, "b": 0},
        "sound": {"enabled": True, "preset_id": 6, "volume": 50}
    }
])

# Check current status
status = requests.get(f"{UNICORN}/api/status").json()
print(f"Time: {status['time']} {status['day']}")
print(f"Active: {status['active']}")
print(f"Message: {status['message']}")
```

---

## Endpoints

### GET /api/status

Current display state and device clock.

**Response:**

```json
{
  "active": true,
  "message": "Hello!",
  "active_end": "09:00",
  "next_start": null,
  "next_day": null,
  "time": "08:35:12",
  "day": "Mon",
  "brightness_offset": 0
}
```

| Field | Type | Description |
|-------|------|-------------|
| `active` | boolean | Whether the display is currently showing a message |
| `message` | string | Currently displayed (or next) message text |
| `active_end` | string\|null | End time of current active schedule (HH:MM), or null |
| `next_start` | string\|null | Next upcoming schedule start time, or null |
| `next_day` | string\|null | Day of next schedule ("Mon"-"Sun"), or null |
| `time` | string | Device clock (HH:MM:SS, local timezone) |
| `day` | string | Current day of week ("Mon"-"Sun") |
| `brightness_offset` | integer | Current brightness adjustment (-50 to +50) |

---

### GET /api/message

Get current global message configuration.

**Response:**

```json
{
  "text": "Hello!",
  "display_mode": "scroll",
  "scroll_speed": "medium",
  "color": {"r": 255, "g": 255, "b": 255},
  "bg_color": {"r": 0, "g": 0, "b": 0},
  "border": false,
  "border_color": {},
  "font": "bitmap8"
}
```

---

### POST /api/message

Update the display message. Only include fields you want to change — other fields are preserved.

**Request:**

```json
{
  "text": "New message"
}
```

All fields are optional. Accepted fields:

| Field | Type | Values | Default |
|-------|------|--------|---------|
| `text` | string | Max 128 characters | `"Hello!"` |
| `display_mode` | string | `"scroll"`, `"fixed"` | `"scroll"` |
| `scroll_speed` | string | `"slow"` (80ms), `"medium"` (50ms), `"fast"` (25ms) | `"medium"` |
| `color` | object | `{"r": 0-255, "g": 0-255, "b": 0-255}` | `{"r":255,"g":255,"b":255}` (white) |
| `bg_color` | object | `{"r": 0-255, "g": 0-255, "b": 0-255}` | `{"r":0,"g":0,"b":0}` (black) |
| `font` | string | `"bitmap6"`, `"bitmap8"`, `"font11"` | `"bitmap8"` |
| `border` | boolean | `true`, `false` | `false` |
| `border_color` | object | `{"r": 0-255, "g": 0-255, "b": 0-255}` | Auto (text color ÷ 3) |

**Behavior:** Saving a message immediately activates the display (shows the message). The display stays on until a schedule takes over or the device is rebooted.

**Response:** Returns the saved message config (validated).

---

### GET /api/schedules

Get all configured schedules.

**Response:**

```json
[
  {
    "id": 1,
    "enabled": true,
    "start_time": "08:00",
    "end_time": "09:00",
    "days": ["mon", "tue", "wed", "thu", "fri"],
    "message": "GOOD MORNING",
    "color": {"r": 255, "g": 200, "b": 0},
    "sound": {
      "enabled": true,
      "preset_id": 4,
      "volume": 50
    }
  }
]
```

---

### POST /api/schedules

Replace all schedules. Send the complete array — any schedule not included will be deleted.

**Request:**

```json
[
  {
    "id": 1,
    "enabled": true,
    "start_time": "08:00",
    "end_time": "09:00",
    "days": ["mon", "tue", "wed", "thu", "fri"],
    "message": "GOOD MORNING",
    "color": {"r": 255, "g": 200, "b": 0},
    "sound": {
      "enabled": true,
      "preset_id": 4,
      "volume": 50
    }
  }
]
```

Schedule fields:

| Field | Type | Values | Default |
|-------|------|--------|---------|
| `id` | integer | Unique ID | Required |
| `enabled` | boolean | `true`, `false` | `true` |
| `start_time` | string | `"HH:MM"` (00:00-23:59) | `"00:00"` |
| `end_time` | string | `"HH:MM"` (00:00-23:59) | `"23:59"` |
| `days` | array | `["mon","tue","wed","thu","fri","sat","sun"]` | All days |
| `message` | string | Max 128 chars. Empty = use global message | `""` |
| `color` | object | `{"r","g","b"}` or `{}` for global color | `{}` |
| `sound.enabled` | boolean | `true`, `false` | `false` |
| `sound.preset_id` | integer | 1-20 (see Sound Presets) | `1` |
| `sound.volume` | integer | 0-100 | `50` |

**Notes:**
- Overnight ranges work (e.g., `"start_time": "22:00", "end_time": "06:00"`)
- When a schedule becomes active, its message/color override the global settings
- Sound plays 3 times with 1-second pauses when a schedule starts
- First matching schedule wins (no overlapping)

**Response:** Returns the saved schedules array (validated).

---

### POST /api/sound/preview

Play a sound preset immediately.

**Request:**

```json
{
  "preset_id": 4,
  "volume": 75
}
```

| Field | Type | Values | Default |
|-------|------|--------|---------|
| `preset_id` | integer | 1-20 | `1` |
| `volume` | integer | 0-100 | `50` |

**Response:** `{"status": "ok"}`

---

### GET /api/sound/presets

List all available sound presets.

**Response:**

```json
[
  {"id": 1, "name": "Simple Beep", "category": "notification"},
  {"id": 2, "name": "Double Beep", "category": "notification"},
  ...
]
```

Preset list:

| ID | Category | Name |
|----|----------|------|
| 1 | notification | Simple Beep |
| 2 | notification | Double Beep |
| 3 | notification | Triple Beep |
| 4 | notification | Rising Chime |
| 5 | notification | Falling Chime |
| 6 | notification | Three-tone Chime |
| 7 | alarm | Alarm (Low) |
| 8 | alarm | Alarm (High) |
| 9 | alarm | Siren |
| 10 | alarm | Urgent Alert |
| 11 | melody | Westminster Chime |
| 12 | melody | Do Re Mi Fa |
| 13 | melody | Fanfare |
| 14 | melody | Music Box |
| 15 | sfx | Coin |
| 16 | sfx | Power Up |
| 17 | sfx | Level Up |
| 18 | sfx | Error |
| 19 | sfx | Success |
| 20 | sfx | Click |

---

### POST /api/system/brightness

Set brightness offset for auto-brightness adjustment.

The device auto-adjusts brightness based on the ambient light sensor (0.2-0.8 range). This offset adjusts on top of that.

**Request:**

```json
{
  "brightness_offset": 20
}
```

| Field | Type | Values | Default |
|-------|------|--------|---------|
| `brightness_offset` | integer | -50 to +50 | `0` |

**Final brightness** = auto (0.2-0.8 from sensor) + offset/100. Clamped to 0.05-1.0.

**Response:** `{"brightness_offset": 20}`

---

### POST /api/system/volume

Set master audio volume.

**Request:**

```json
{
  "volume": 75
}
```

| Field | Type | Values | Default |
|-------|------|--------|---------|
| `volume` | integer | 0-100 | `50` |

**Response:** `{"volume": 75}`

---

### POST /api/system/timezone

Set timezone offset from UTC.

**Request:**

```json
{
  "timezone_offset": -7
}
```

| Field | Type | Values | Default |
|-------|------|--------|---------|
| `timezone_offset` | integer | -12 to +14 | `9` (JST) |

**Response:** `{"timezone_offset": -7}`

---

### GET /api/wifi/scan

Scan for available WiFi networks.

**Response:**

```json
[
  {"ssid": "MyNetwork", "rssi": -45},
  {"ssid": "Neighbor", "rssi": -72}
]
```

Sorted by signal strength (strongest first).

---

### POST /api/wifi/connect

Save WiFi credentials and reboot into STA mode.

**Request:**

```json
{
  "ssid": "MyNetwork",
  "password": "mypassword"
}
```

**Response:** `{"status": "saved", "message": "WiFi saved. Rebooting..."}`

**Note:** Device reboots 2 seconds after this response. The connection will be lost.

---

### POST /api/ota/check

Check for and apply OTA updates from GitHub.

**Request:** None (empty body)

**Response:**

```json
{
  "status": "Updated",
  "updated": 5,
  "version": "abc1234",
  "reboot_required": true
}
```

Possible `status` values: `"Already up to date"`, `"Updated"`, `"Partial update"`, `"Error"`, `"OTA not configured"`.

---

### POST /api/system/reboot

Reboot the device.

**Request:** None (empty body)

**Response:** `{"status": "rebooting"}`

**Note:** Device reboots 1 second after this response.

---

## Error Responses

All error responses follow this format:

```json
{
  "error": "Description of the error"
}
```

HTTP status codes:
- `200` — Success
- `400` — Bad request (invalid JSON, missing required field)
- `500` — Internal server error (with error message in response)

---

## Notes for External Integration

- **No authentication** — anyone on the local network can call these APIs
- **HTTP only** — no HTTPS
- **One connection at a time** — the Pico W can handle 1-2 concurrent connections
- **Response time** — typically 100-500ms. WiFi scan and OTA check may take longer
- **Message persistence** — saved to flash, survives reboot
- **Rate limiting** — no built-in rate limiting. Avoid sending more than 1 request per second
