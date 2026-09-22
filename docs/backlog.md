# Backlog — decisions needed

Findings from the 2026-09-22 audit (12 dimensions, every item verified by three
adversarial reviewers) that were **not** fixed, because fixing them means making
a product or design decision rather than correcting a mistake.

Everything mechanical from the same audit is already fixed — see the commits
around `239764d`, `af32a05` and their followers. Nothing below is a regression
from those; they are pre-existing gaps.

Each item: what is wrong, what happens because of it, and the question to answer
before writing code.


## OTA safety

### Download and rename are interleaved per file, so a mid-run failure leaves a mixed-version tree — `src/ota/updater.py:116`

**Severity:** high · **Category:** data-loss

The loop at lines 116-123 downloads one file and immediately renames it into place before moving to the next. CLAUDE.md's OTA safety rule states the sequence as "download to /tmp/, verify size > 0, rename over target, then reboot" — i.e. stage everything, then commit. The code commits incrementally, so the filesystem is a mixture of old and new code at every point between file 1 and file 33, and there is no rollback: the old bytes are overwritten and nothing is retained. `errors > 0` returns `"Partial update"` (lines 125-131) with no `reboot_required`, leaving the device to keep running whatever modules it imported at boot while the disk holds a half-swapped tree. The next unrelated reboot — a power blip, the reboot button, the A+D button combo — boots that mixture.

**What it costs:** WiFi drops after 20 of 33 files are renamed into place. The new `main.py`, `web/routes.py` and `web/templates.py` are installed; `display/cjk_font.py`, `audio/player.py` and `lib/microdot.py` are still the old versions. Return value is `"Partial update"`, nothing reboots, version.json still says the old version. The user presses Reboot in the web UI an hour later and the device boots new callers against old callees — an AttributeError or TypeError at import, i.e. no display and no web server.

**Proposed direction:** Make the update all-or-nothing: loop once to download and verify every file to its `.tmp`, and only if all succeeded loop again to rename them all. On any download or verification failure, remove every `.tmp` written in this run and return without touching a single live file. `src/` is ~436KB against ~1.4MB usable flash, so staging the whole tree fits.

### 'Partial update' records nothing, so the same failing update reruns and rewrites every file nightly — `src/ota/updater.py:125`

**Severity:** high · **Category:** flash-wear

On `errors > 0` the function returns early without calling `config_manager.save_version()` (line 134), so version.json keeps the old string. `should_check_now` (lines 230-235) is purely `current_hour == check_hour`, with no record of the last attempt, and `ota_check_loop` (src/main.py:331-344) polls every 1800s — so a single check hour produces two full runs. Nothing is remembered between runs and `_update_file` never compares the downloaded bytes against what is already on disk, so every run re-downloads and re-writes all 33 files (~436KB) including the ones that already succeeded. There is no backoff and no error is logged anywhere; the only trace is the returned string, which nothing in `ota_check_loop` prints.

**What it costs:** cjk11.bin OOMs (finding 1). Result is `"Partial update"`, version.json unchanged. At 03:00 and 03:30 every single night thereafter: the display blanks (finding 11), the event loop stalls for minutes (finding 8) and all 33 files are re-downloaded and rewritten to flash. This continues indefinitely with no visible symptom other than a display that goes dark nightly, because the failure is never surfaced.

**Proposed direction:** Treat a partial result as a hard abort under the staged-commit model of finding 4 (nothing is committed, so nothing needs reconciling), skip files whose on-disk content already matches (trivial once finding 2 adds hashes), append the error to the RAM ring buffer CLAUDE.md specifies, and gate retries on a last-attempt timestamp so a persistent failure backs off instead of running twice a night forever.

### Code is fetched with no certificate verification and no signature, so a LAN MITM gets arbitrary code execution — `src/ota/updater.py:164`

**Severity:** high · **Category:** security

Both `requests.get` calls fetch executable Python over HTTPS with no verification of who answered. MicroPython's `ssl.wrap_socket`, which urequests uses, defaults to `cert_reqs=CERT_NONE` — no CA bundle is shipped in the firmware and none is configured here, so the certificate presented by whatever host answers for `raw.githubusercontent.com` is accepted unconditionally. There is no signature over the manifest and no checksum over the files (`src/manifest.json` holds only `version` and `files`), so no end-to-end check compensates. Whatever comes back is written to flash and executed at the next boot, at full privilege, with `system_hal.reset()` invoked automatically by src/main.py:340 to make it take effect.

**What it costs:** Anyone with DNS control on the network the sign is joined to — a compromised router, ARP spoofing on an untrusted WiFi, a hostile DHCP-supplied resolver — points raw.githubusercontent.com at their own host. At 03:00 the device fetches their manifest (version string bumped to force `remote_version != local_version`), writes their `main.py` and, because `errors == 0`, reboots straight into it. Nothing in the flow can detect this.

**Proposed direction:** Verify what is downloaded. Options: pin GitHub's CA or leaf certificate and pass it to the TLS layer; or sign the manifest (containing per-file hashes) with a key whose public half is baked into the firmware and refuse to install anything that fails verification. Whichever is chosen, verification must happen before the first rename.

**Decision needed:** How much trust machinery is warranted for a LAN-only sign? Certificate pinning is the smaller change but breaks silently whenever GitHub rotates its chain, which would disable OTA at exactly the moment you need it. Manifest signing survives rotation but needs a key, a release-time signing step and a plan for what happens if the key is lost. Or do you accept the current trust model and document that OTA must only be used on a trusted network?

### A truncated download passes the size>0 check and is renamed over main.py — `src/ota/updater.py:202`

**Severity:** high · **Category:** data-loss

`if not content or len(content) == 0: return False` is the only integrity check before the file is installed. A WiFi drop, a TLS session reset or a truncated CDN response makes `raw.read()` return a short body with no exception — urequests does not compare what it read against Content-Length. The partial body is non-empty, so it passes, gets written to `<file>.tmp` and renamed over the live file. There is no checksum in `src/manifest.json` (it carries only `version` and `files`) and no hash verification anywhere in the module. This is independent of any attacker: a flaky 2.4GHz link at 03:00 is enough.

**What it costs:** WiFi drops after 400 of the 1,200 bytes of `main.py` have arrived. `len(content) == 400` > 0, so the truncated file is renamed over `/main.py`. `errors` stays 0, `save_version()` runs, `reboot_required: True` is returned and main.py:340 calls `system_hal.reset()`. On boot, `main.py` raises SyntaxError mid-file, the device never starts the web server or the display, and there is no recovery path except a USB cable and a host computer.

**Proposed direction:** Verify each file before renaming. Preferred: add a per-file sha256 to manifest.json and check it with `hashlib.sha256` while streaming; a manifest generator must be written (none exists in `tools/`). Cheaper: read and compare Content-Length. The same hash also lets `_update_file` skip files whose on-disk content already matches, which removes the nightly rewrite of every file.

**Decision needed:** Which integrity mechanism do you want: a per-file sha256 in manifest.json (strongest, and it also enables skip-if-unchanged, but needs a new manifest-generator tool in tools/ and a release step that always runs it), or a Content-Length comparison (no build-step change, but it depends on the frozen urequests exposing response headers, which varies by firmware build)?

### check_and_update contains no await, so 'Updating...' never renders and the event loop stalls for the whole run — `src/ota/updater.py:85`

**Severity:** medium · **Category:** async-blocking

`check_and_update` is declared `async` but there is not a single `await` in its body (lines 85-147): `_fetch_manifest` and `_update_file` are plain synchronous functions doing blocking socket I/O. On a single-threaded asyncio runtime this monopolises the loop from the first `requests.get` to the last. The concrete, verifiable consequence: `self._display.show_status("Updating...")` at line 99 only sets `_status_text` and `_frame_dirty`; the actual pixels are pushed by `display_loop` in src/main.py, which never gets a turn, so the status message the code exists to show is never displayed — the LEDs hold the stale previous frame for the entire multi-minute run and then `clear_status()` in the `finally` erases it. The web server and button loop are equally frozen, and a run triggered from `/api/ota/check` (src/web/routes.py:348) delays that HTTP response for the full duration. This contradicts CLAUDE.md's "All long-running operations must be async" and "Keep individual async tasks short — yield often".

**What it costs:** User clicks "Check for updates" in the web UI. 33 HTTPS downloads run back to back with the loop parked inside them. The display keeps showing the previous message instead of "Updating...", the settings page stops responding, physical buttons do nothing, and the browser sits on a pending request until the run finishes.

**Proposed direction:** Insert `await asyncio.sleep_ms(0)` after `show_status()` and between iterations of the file loop, so the display, web server and button loop get a turn between downloads. Guard the same change with a `self._busy` flag checked and set at entry: once awaits exist, the nightly `ota_check_loop` run and a web-triggered run can interleave and two writers will collide on the same `.tmp` paths.


## Blocking the event loop

### Blocking time.sleep in connect_sta/sync_ntp freezes the whole asyncio loop for up to ~46s — `src/hal/real.py:160`

**Severity:** high · **Category:** async-blocking

`RealNetwork.connect_sta` busy-waits with `time.sleep(1)` inside `while not self._wlan.isconnected():` (real.py:156-161), and `RealNetwork.sync_ntp` (real.py:230-242) calls `ntptime.settime()` with a 10s timeout up to 3 times with `time.sleep(2)` between attempts. Both are reached from inside the event loop: `main.py:459 asyncio.create_task(wifi_monitor_loop())` -> `WiFiManager.check_connection` -> `_attempt_reconnect` (manager.py:150, timeout_s=10) and, on success, `self.sync_ntp()` (manager.py:158). Note `RECONNECT_DELAYS` is never used for timing (`get_reconnect_delay` has no callers), so `_attempt_reconnect` runs on every 30s check while the link is down. `MockNetwork.connect_sta`/`sync_ntp` return instantly (mock.py:152, mock.py:191), so no PC test can ever observe the stall. CLAUDE.md: "never `time.sleep()` in the main loop as it blocks everything" and "切断中もスケジュール表示は継続".

**What it costs:** Router reboots. wifi_monitor_loop calls _attempt_reconnect; connect_sta busy-waits 10s with time.sleep(1) -> display_loop, web server and scheduler get no CPU, so the LED scroll freezes for ~10s out of every 30s. When the AP comes back, the following sync_ntp can block a further ~36s (3 x 10s ntptime timeout + 2 x 2s sleep) with the panel frozen mid-frame.

**Proposed direction:** Make the network HAL's waiting paths cooperative: call `wlan.connect()` and return immediately (the monitor already re-polls `isconnected()` on its next tick), or add `async def connect_sta_async/sync_ntp_async` that `await asyncio.sleep_ms(...)` and use those from `wifi_monitor_loop`, keeping the blocking versions only for the pre-loop boot sequence (main.py:96-102).

**Decision needed:** Do you want the network HAL to gain async variants (ripples into WiFiManager and the boot path), or is a fire-and-forget `wlan.connect()` plus the existing 30s polling acceptable? The ntptime call itself cannot be made non-blocking without an async SNTP client — is a shorter timeout/1 attempt from the monitor task the trade you want?

### scan_networks blocks the event loop for seconds inside an HTTP handler — `src/hal/real.py:213`

**Severity:** medium · **Category:** async-blocking

`scan_networks` does an unconditional `time.sleep(2)` — even when `was_active` was already True and nothing needed settling — followed by a blocking `wlan.scan()` (typically another 2-4s). It is called synchronously from two async handlers: `setup_page` (src/web/routes.py:56) and `api_wifi_scan` (src/web/routes.py:250). In AP mode it also toggles STA_IF up and down (`wlan.active(True)` / `active(False)`) on the same radio the AP is serving.

**What it costs:** A phone joins the setup AP and loads `http://192.168.4.1/setup`. The handler blocks the single thread for 4-6s before the first byte is written: the captive DNS task (src/wifi/captive_dns.py, 50ms poll) misses every query in that window, the AP radio is off channel scanning, and the phone's captive-portal fetch frequently times out and gives up on the portal. The user then presses Rescan (`/api/wifi/scan`), repeating the freeze. In STA mode the same call freezes the LED scroll for several seconds on every settings-page rescan.

**Proposed direction:** Move `time.sleep(2)` inside `if not was_active:` so an already-active interface is not penalised, and make the handlers cooperative — run the scan once at AP start and serve `/setup` from that cached list, or have `api_wifi_scan` `await asyncio.sleep_ms(0)`-yield around a scan performed without the extra sleep. At minimum the unconditional 2s must go; it is pure dead wait on the common path.

### sync_ntp blocks the event loop for up to ~34 seconds — `src/hal/real.py:233`

**Severity:** medium · **Category:** async-blocking

`sync_ntp` sets `ntptime.timeout = 10` and then makes up to 3 blocking `ntptime.settime()` calls with `time.sleep(2)` between them — worst case 3*10 + 2*2 = 34s of hard block, and at least 4s of `time.sleep` whenever it fails. It is called from inside the event loop twice: the hourly re-sync (src/wifi/manager.py:123) and after every successful reconnect (src/wifi/manager.py:158), both reached from `wifi_monitor_loop` (main.py:325).

**What it costs:** The LAN is up but the upstream NTP server is unreachable (ISP outage, DNS failure, blocked port 123). Once an hour the device freezes solid for ~34s: the LED scroll stops mid-message, the web UI times out, buttons are dead, and the scheduler misses a tick. On the reconnect path this stacks with the 10s blocking `connect_sta`, giving a ~44s freeze every time WiFi flaps. There is no watchdog anywhere in src/ (grep for WDT/watchdog returns nothing), so nothing recovers the device — it just stalls.

**Proposed direction:** One attempt per call with `ntptime.timeout = 3`, and delete the retry loop and `time.sleep(2)` — the hourly tick and the post-reconnect call already are the retries. Keep the try/except and the failure log. If retries are still wanted, make the function async and `await asyncio.sleep(2)`. (Adding the hardware watchdog CLAUDE.md asks for would turn these stalls into resets, so it must come after this fix, not before.)

### WiFi scan handlers block the asyncio loop for 4+ seconds and freeze the LED scroll — `src/web/routes.py:250`

**Severity:** medium · **Category:** async-blocking

`networks = app.ctx["wifi_manager"].scan_networks()` is a plain synchronous call inside an async handler (same at routes.py:56 for the /setup page). It reaches RealNetwork.scan_networks (src/hal/real.py:205-228), which does `time.sleep(2)` (line 213) and then a blocking `wlan.scan()` (line 214) — several more seconds. CLAUDE.md: "never time.sleep() in the main loop as it blocks everything". While it runs, display_loop (src/main.py:281) cannot render a frame, alert_loop cannot expire an alert, and no other HTTP request is served. Separately, in AP mode `was_active` is False so the handler toggles STA_IF active/inactive around the scan on the single CYW43 radio while the phone is associated to the AP. Secondary, mechanical bug in the same path: the `time.sleep(2)` "allow time for scan after activation" runs even when the interface was already active (normal STA mode), so every Rescan from the settings page pays 2 s for nothing.

**What it costs:** User taps Rescan on /settings (or loads /setup): the LED message visibly stalls mid-scroll for 4+ seconds and the device answers no other request during that window. In AP mode the same scan can drop the phone's association to GalacticUnicorn-Setup, so the setup page's fetch never completes.

**Proposed direction:** Mechanical half now: move `time.sleep(2)` inside the `if not was_active:` branch in src/hal/real.py:210-213. Then decide how to stop the freeze (see judgment question).

**Decision needed:** MicroPython offers no awaitable wlan.scan(), so the freeze cannot simply be awaited away. Which do you want: (a) accept the stall but show a 'Scanning...' status on the LED and document it, (b) run the scan on the second core via _thread, or (c) drop the on-demand scan and let users type the SSID (the ssid-row input already exists in both templates)?

### Scheduled sounds are fired as unguarded tasks that can overlap and garble each other — `src/main.py:186`

**Severity:** low · **Category:** async-concurrency

`on_schedule_start` does a fire-and-forget `asyncio.create_task(player.play_preset(..., count=3))`. `AudioPlayer.play_preset` (src/audio/player.py:19-35) has no re-entrancy guard: each run calls `self._audio.set_volume(...)` and then drives synth channel 0 note by note, and `RealAudio.play_sequence` (hal/real.py:113-132) calls `ch.trigger_release()` on the shared channel after each note. Two concurrent runs therefore fight over the same channel and global volume. `count=3, gap_ms=1000` widens one trigger to several seconds, so overlaps are now easy. Other entry points into the same coroutine: `/api/call` (routes.py:191) and `/api/sound/preview` (routes.py:172).

**What it costs:** A schedule with a sound starts at 08:00 (3 repeats, ~6 s of audio). At 08:00:02 the ESP32 button POSTs /api/call, which awaits `play_preset` for the same channel. The two loops interleave: one coroutine's `trigger_release()` cuts the other's note short, the volume flips between the two settings, and a note can be left sounding after the shorter sequence ends.

**Proposed direction:** Add a busy flag to AudioPlayer: set `self._busy = True` at the top of `play_preset`, return immediately (or call `self.stop()` and take over) if it is already set, and clear it in a `finally`. That fixes every caller at once rather than each call site.


## Boot and availability policy

### A transient WiFi failure at boot drops the device into AP mode forever — no scheduler, no STA retry — `src/main.py:96`

**Severity:** high · **Category:** availability

`boot_wifi()` returns False whenever `wifi_mgr.start_sta()` fails (line 95-98), even though a valid `wifi_config.json` exists, and `main()` then starts neither `scheduler_loop()`, `wifi_monitor_loop()` nor `ota_check_loop()` (lines 457-460). Nothing retries STA afterwards: `WiFiManager.check_connection()` returns immediately unless `self._mode == "sta"` (manager.py:117-118), and that loop is not running anyway. The device is stuck as a setup access point until someone physically power-cycles it. This contradicts CLAUDE.md WiFi Resilience ("再接続失敗後は5分待機してリトライサイクル再開。APモードには遷移しない" and "切断中もスケジュール表示は継続").

**What it costs:** Power outage: the sign and the router restart together. `connect_sta(..., timeout_s=30)` runs before the router finishes booting and fails. The sign starts "GalacticUnicorn-Setup", scrolls setup instructions, and stays there indefinitely — no schedules, no display, no OTA — even though its WiFi comes back 20 seconds later.

**Proposed direction:** Distinguish "no config" from "config present but connect failed". With config present: keep the scheduler, display and wifi monitor running on the RTC as CLAUDE.md requires, and retry STA in the background (or reboot after N failed cycles) instead of entering AP mode. AP mode should be reserved for `not config_manager.wifi_config_exists()`.

**Decision needed:** On a boot-time STA failure with saved credentials: retry STA forever in the background while running schedules offline, or retry for N minutes and only then fall back to AP mode so the user can fix the credentials? A device that never shows the setup AP is unrecoverable if the password actually changed.

### Boot is not wrapped in try/except: any init exception drops the device to the REPL forever — `src/main.py:476`

**Severity:** high · **Category:** boot-resilience

Everything CLAUDE.md calls "initialization" runs unprotected. Module scope lines 50-70 (`from web.server import create_app`, `DisplayRenderer(...)`, `renderer.init(...)`, `AudioPlayer(...).init()`) and the whole body of `main()` (`boot_wifi()` at line 421, `load_config()` at 423, `create_app()` at 440, `await app.start_server(...)` at 470) have no handler. The only guard is `except KeyboardInterrupt` at line 477. CLAUDE.md: "Boot must always succeed: main.py must be resilient. Wrap all initialization in try/except."

**What it costs:** On a real Pico W, `network.WLAN.connect()` intermittently raises `OSError: Wifi Internal Error`. `RealNetwork.connect_sta` (src/hal/real.py:155) does not catch it -> propagates through `wifi_mgr.start_sta()` -> `boot_wifi()` -> `main()` -> `asyncio.run()`. MicroPython prints a traceback and drops to the REPL: LEDs blank, no web server, no AP, no watchdog to reset. The sign is dead until someone physically unplugs it, and the same fault repeats on the next boot. Same outcome if `app.start_server` raises `EADDRINUSE` after a soft reset, or if any `.py`/`.bin` file is corrupt after a partial OTA (SyntaxError at import).

**Proposed direction:** Wrap `boot_wifi()`/`load_config()` in try/except so a failure degrades to AP mode + DEFAULT_APP_CONFIG instead of aborting, and wrap the `asyncio.run(main())` call at line 476 in `except Exception` that prints the traceback and calls `system_hal.reset()` after a short delay, so a hard failure self-recovers instead of parking at the REPL.

### A transient boot-time WiFi failure traps the device in AP mode forever — `src/main.py:97`

**Severity:** medium · **Category:** spec-deviation

`boot_wifi` falls back to AP mode on any STA failure, including a transient one, and returns False. `main()` then starts `scheduler_loop`, `wifi_monitor_loop` and `ota_check_loop` only `if sta_connected` (lines 457-460). So in AP mode there is no STA retry at all and no path back — the device stays in setup mode until a human power-cycles it. CLAUDE.md states "再接続失敗後は5分待機してリトライサイクル再開。APモードには遷移しない", and spec F-04 scopes AP mode to 初回起動時またはWiFi未設定時 — neither covers a device that already has valid saved credentials.

**What it costs:** Power outage. Router and Pico W come back together; the Pico is up in ~2s, the router's WAN/DHCP takes 60-90s. `start_sta()` times out at 30s with perfectly valid saved credentials, AP mode starts, and the sign spends the rest of the day scrolling "WiFi: GalacticUnicorn-Setup ..." instead of running its schedules — with no NTP, no web UI on the LAN, and no automatic recovery. This is the most likely real-world failure mode for an always-on USB device.

**Proposed direction:** Requires a policy choice before coding — see the judgment question. Whichever is chosen, `wifi_config_exists()` being True must not lead to an indefinite AP state.

**Decision needed:** When saved WiFi credentials exist but the boot connect fails, which recovery policy do you want? (a) retry STA N times with the existing backoff before ever starting AP mode; (b) start AP mode for the user but also run wifi_monitor_loop so STA reconnects in the background and the device self-heals; or (c) start AP mode and auto-reboot after e.g. 10 minutes if no one has completed setup. (b) keeps setup reachable but runs AP+STA concurrently on one radio; (a) delays the setup portal by minutes on a genuinely wrong password.

### No RAM error ring buffer: every failure is a print() nobody can read — `src/main.py:289`

**Severity:** medium · **Category:** silent-failure

CLAUDE.md, Reliability: "No silent failures: Log errors to a small ring buffer in RAM (not flash — avoid wear). Expose via Web UI system page." `grep -rn "error_log\|LOG_BUFFER\|def log" src/` finds nothing. Every handler in main.py (lines 258, 273, 289, 307, 317, 327, 342, 413) and in routes.py/updater.py writes to stdout, which goes to a USB serial port that an always-on wall-mounted sign has nobody attached to.

**What it costs:** The scheduler starts throwing every minute (e.g. corrupt RTC read), or the OTA fails nightly, or the light sensor read errors on every scroll cycle. The device keeps running in a degraded state and there is no way, from the web UI or anywhere else, to discover that anything is wrong — the operator only sees "the sign behaves oddly".

**Proposed direction:** Add a ~20-entry RAM ring buffer module (list + write index, append `(uptime_ms, msg)`), replace the `print(...)` calls in the except blocks with a call to it (keep the print too), and add a `GET /api/system/log` endpoint plus a section on the web UI system page.

**Decision needed:** How many entries should the ring hold given the ~192KB RAM budget, and where in the refreshed web UI should the log surface (system tab section, or a separate page)?

### No hardware watchdog anywhere — CLAUDE.md requires one to recover from hangs — `src/main.py:419`

**Severity:** medium · **Category:** missing-watchdog

`grep -rn "watchdog\|WDT" src/` returns nothing. CLAUDE.md, Design Principles/Safety First: "Watchdog timer: Use hardware watchdog to auto-recover from hangs. Reset if main loop stalls." No `machine.WDT` is ever constructed and no task feeds one.

**What it costs:** Any event-loop stall — a blocking socket in microdot, the blocking `time.sleep(1)` reconnect path, or a task dying on an unhandled exception — leaves the device wedged with no recovery. Combined with finding 1 (boot exception -> REPL), the only remedy for any hang on an unattended always-on sign is a manual power cycle.

**Proposed direction:** Create `machine.WDT(timeout=8000)` (RP2040 max ~8.3 s) after the display/WiFi init, and feed it from a dedicated short async task. Do NOT feed it from inside the OTA task; instead decide explicitly how to keep it fed (or deliberately allow a reset) while `check_and_update()` blocks the loop on HTTPS downloads.

**Decision needed:** What counts as "alive" for the feeder (a single heartbeat task, or a liveness flag each loop must set), and what happens during the multi-second blocking OTA download and the 30 s blocking WiFi connect — feed through them, or accept a watchdog reset there?

### Exponential backoff and the 5-minute pause are dead code — retries are a flat 30s — `src/wifi/manager.py:140`

**Severity:** medium · **Category:** spec-deviation

`RECONNECT_DELAYS = [5, 10, 20, 40, 60]` and `RECONNECT_PAUSE = 300` are read only by `get_reconnect_delay()`, which grep shows has zero callers anywhere in src/ or tests/. Actual timing is owned by two fixed 30s gates: `wifi_monitor_loop`'s `await asyncio.sleep(30)` (main.py:328) and the `CHECK_INTERVAL_S` gate at line 127. The exhaustion branch at lines 140-144 resets `_reconnect_attempt = 0` and returns, which skips exactly one 30s tick — not the 5-minute pause CLAUDE.md and docs/specification.md:320 both specify. Net behaviour: a reconnect attempt roughly every 30s forever, never 5->10->20->40->60, never a 300s pause.

**What it costs:** The upstream router is down for hours. Instead of backing off to one attempt per 5 minutes, the device hammers `wlan.connect()` every 30s indefinitely. Each attempt blocks the event loop for the full 10s timeout (see the connect_sta finding), so the display stalls a third of the time for the entire outage, and the radio never gets the quiet period the spec promises.

**Proposed direction:** Let the backoff drive the loop: in `wifi_monitor_loop`, sleep `wifi_mgr.get_reconnect_delay()` when disconnected and 30 when connected, and delete the redundant `CHECK_INTERVAL_S` gate at lines 127-129 so `check_connection` acts on every call. In `_attempt_reconnect`, keep `_reconnect_attempt` at `len(RECONNECT_DELAYS)` for one cycle so `get_reconnect_delay()` returns `RECONNECT_PAUSE`, then reset — rather than resetting immediately and burning a wasted skip cycle.


## Audio

### play_preset overwrites the master volume, clobbering the user's volume slider — `src/audio/player.py:31`

**Severity:** medium · **Category:** correctness

`play_preset` implements per-preset volume by writing the global master volume (`self._audio.set_volume(volume_percent / 100.0)`) and never restores it. The same knob is the user-facing master volume written by `/api/system/volume` (routes.py:242) and shown by the UI slider, which is not persisted and is reset to 50 on every page load (app.js:385). So every scheduled or previewed sound permanently redefines "master volume", and the UI then displays a value the device does not have.

**What it costs:** User sets the slider to 80 (gu volume 0.8). At 08:00 a schedule with sound volume 25 fires -> master becomes 0.25 and stays there. The next sound triggered by the ESP32 button (/api/call default volume 50) plays at 0.5 while the UI still shows 50/80, and nothing ever returns the device to the user's setting.

**Proposed direction:** Pick one owner of `gu.set_volume`: either scale the preset volume into the note dicts and leave master alone, or save/restore the master around playback in play_preset.

**Decision needed:** Should per-schedule volume be relative to the master slider (preset_vol x master) with the slider persisted in config, or should the master slider be removed and preset volume be absolute?

### Concurrent play_preset calls collide on synth channel 0; /api/call holds the request for the whole playback — `src/audio/player.py:32`

**Severity:** medium · **Category:** concurrency

`play_preset` has no mutual exclusion, and both `/api/sound/preview` (routes.py:171) and `/api/call` (routes.py:192) `await` it inline inside the handler, while `on_schedule_start` runs it as a background task with count=3 (main.py:186-191). Every preset note uses channel 0 (no preset sets "channel"), so two overlapping runs interleave `configure()`/`trigger_attack()`/`trigger_release()` on the same channel and clobber the global volume: one task's `trigger_release()` (real.py:129) silences the other task's note. Awaiting inline also keeps the HTTP request open for the full sequence — count is capped at 10 (routes.py:170/186), so preset 9 (Siren, 1200ms) x10 with the 1000ms default gap holds the connection ~21s. No test can see any of this: `MockAudio.play_sequence` (mock.py:115-128) contains no `await` at all, so it returns before the event loop can interleave anything.

**What it costs:** ESP32 tap button POSTs /api/call; its HTTP client times out after a few seconds while the handler is still awaiting 21s of playback, so it retries. The retry's play_preset re-enters with the same channel 0: notes are cut short by the other task's trigger_release and the master volume is re-set mid-sequence, producing garbled audio instead of the alert.

**Proposed direction:** Return immediately from the routes with `asyncio.create_task(player.play_preset(...))` (same pattern main.py:186 already uses) and guard re-entry in `AudioPlayer` with a single `asyncio.Lock` or an `_playing` flag. If you choose cancel-on-new-request, also wrap the note loop in `real.py:115-132` with `try/finally: ch.trigger_release()`, otherwise a cancel between attack and release leaves the note sustaining forever.

**Decision needed:** When a second sound arrives mid-playback: drop it (simplest), queue it, or cancel and replace the current one? Also should /api/call answer 200 immediately instead of after the sound finishes?


## Scheduling semantics

### Scheduler executes schedules against a never-synced clock (2021-01-01) with no validity gate — `src/scheduler/scheduler.py:129`

**Severity:** medium · **Category:** time-sync

`check()` takes whatever `get_current_time()` returns and acts on it. There is no notion of "the clock has never been set". On the RP2040 the power-on clock is 2021-01-01 00:00 UTC (verified in micropython ports/rp2/main.c:117 for v1.24.x), i.e. Friday, so with the default +9 offset an unsynced device believes it is Friday 09:00 JST and counts forward from there. CLAUDE.md requires graceful degradation with "no silent failures"; today the failure is silent — the UI shows the fake time as if it were real (routes.py:369-380) and sounds fire at arbitrary wall-clock moments.

**What it costs:** WiFi credentials are correct but the NTP server is unreachable (ISP outage / blocked UDP 123). The device boots believing it is Friday 09:00. A schedule set for "fri 09:00–09:05, sound on" triggers immediately at boot, then the device drifts through a fake Friday/Saturday for as long as it stays up, showing scheduled messages at the wrong times every day.

**Proposed direction:** Add a validity gate in `check()`: read `year` from `get_current_time()` and if `year < 2024` skip schedule evaluation (fall back to the default message) or at minimum skip the `on_schedule_start` sound trigger, and expose the unsynced state in the status API so the Web UI can show it.

**Decision needed:** With an unsynced clock, should the sign show the default message and stay silent, or keep running schedules on the fake clock (current behaviour)? The sound trigger in particular is the disruptive part.

### Overnight ranges are cut at midnight by the weekday filter, and fire the start sound twice — `src/scheduler/scheduler.py:137`

**Severity:** medium · **Category:** scheduling-semantics

`check()` filters on the *current* weekday (`if not is_day_match(weekday, sched.get("days", []))`) and only then calls `is_time_in_range`, which wraps across midnight (line 41: `return current >= start or current <= end`). The two are incompatible: a wrapping range is evaluated against the day it is *currently* in, not the day it started. docs/specification.md:61 claims "Overnight support | Yes (e.g., 22:00 — 06:00)" and scheduler.py:27 says "Handles overnight ranges"; neither holds once a day filter is set. src/web/static/app.js:244 documents the actual behaviour ("Overnight ranges match on the same weekday") and the timeline draws two blocks on one row, so the UI and engine agree with each other but not with the spec.

**What it costs:** Schedule: days=["sat"], 22:00–06:00, sound enabled. Saturday 00:00 the range already matches (current <= end) so the schedule activates and `on_schedule_start` fires — the alarm sounds at midnight Saturday, which the user never configured. It stops at 06:01, activates again at 22:00 (second sound of the day), then dies at Sunday 00:00 instead of running to Sunday 06:00. Only a schedule with all 7 days selected behaves as "overnight".

**Proposed direction:** Anchor a wrapping range to its start day: when `end < start`, match either (weekday in days AND current >= start) or (previous weekday in days AND current <= end). Requires updating the app.js timeline (line 240-248) to draw the tail on the following row and the comment at app.js:244.

**Decision needed:** Should an overnight window belong to the day it starts on (Sat 22:00 → Sun 06:00 for days=["sat"]), or stay as today's split window? The former is what the spec promises but changes the meaning of every already-saved overnight schedule and requires a UI change.


## Web UI and API

### /api/schedules persists an unbounded schedule list to flash — `src/web/routes.py:151`

**Severity:** medium · **Category:** validation

`if not isinstance(data, list)` is the only check on the array; there is no cap on its length before `config["schedules"] = data` and `config_manager.save_app_config(config)` write it to flash. _validate_schedule expands each entry to a full dict (~200 bytes serialised) regardless of how sparse the input was. The bloated file is then re-read and re-validated by load_app_config on every page render (routes.py:33), every /api/status poll (routes.py:102) and at boot (src/main.py:129), and the whole list is serialised into the page's window.D blob (templates.py:167) — the exact allocation that commit d921c88 ("fix memory allocation failure") was chunking around. templates.py:79 documents the intended ceiling ("with 20 schedules the blob is the largest thing on the page"); nothing enforces it, and app.js's Add button (app.js:346) has no limit either.

**What it costs:** POST /api/schedules with ~350 minimal objects (fits microdot's 16KB body limit) → app_config.json grows to ~70KB. Every subsequent GET / must hold that parsed config plus its JSON blob in a ~192KB heap, so the page render fails with MemoryError; because the file is persistent, a reboot does not clear it — load_app_config at boot has to parse it too.

**Proposed direction:** Add `MAX_SCHEDULES = 20` (matching the templates.py:79 assumption) and return 400 when `len(data) > MAX_SCHEDULES`, before load/modify/save.

### /api/system/volume takes any value straight to the amp, and the setting has no effect — `src/web/routes.py:242`

**Severity:** medium · **Category:** validation

`app.ctx["audio_player"]._audio.set_volume(volume / 100.0)` uses `volume = data.get("volume", 50)` with no type or range check, and reaches through the player into its private HAL handle. RealAudio.set_volume (src/hal/real.py:137-138) passes the float straight to `gu.set_volume()`, which expects 0.0-1.0. Beyond the range problem, the value is not persisted anywhere (there is no `volume` key in DEFAULT_APP_CONFIG) and AudioPlayer.play_preset unconditionally overwrites it on every sound: `self._audio.set_volume(volume_percent / 100.0)` (src/audio/player.py:31). So the Quick Settings volume slider (app.js:387) is discarded by the next scheduled sound, preview or /api/call, and by any reboot — the control does not do what the UI says it does.

**What it costs:** POST /api/system/volume {"volume": 5000} → 200 and gu.set_volume(50.0) on hardware documented for 0.0-1.0. And in normal use: user drags the volume slider to 20%, then a schedule with sound fires → play_preset sets the amp back to the schedule's own 50%, so the slider had no effect at all.

**Proposed direction:** Clamp first: `volume = _clamp_int(data.get("volume", 50), 0, 100)` → 400 on a non-numeric value, and call `app.ctx["audio_player"].set_volume(...)` through a public method rather than `._audio`. Then decide the master-volume semantics (see judgment question).

**Decision needed:** Should the Quick Settings volume be a persisted master level that multiplies each preset's volume (play_preset would use master * preset/100 and config would gain a system.volume key), or should the slider be removed from the UI because per-sound volume is the real control?

### Quick Settings volume slider has no lasting effect and shows a fabricated value — `src/web/static/app.js:387`

**Severity:** medium · **Category:** dead-control

`bindRange('#q-vol', 300, ...)` POSTs to `/api/system/volume`, which does `app.ctx["audio_player"]._audio.set_volume(volume / 100.0)` (routes.py:242) — the GalacticUnicorn master volume. But `AudioPlayer.play_preset` unconditionally calls `self._audio.set_volume(volume_percent / 100.0)` on entry (src/audio/player.py:31) using the per-schedule / per-preview volume, and `play_preset` is the only path that produces sound (grep for `set_volume` finds no other caller; the physical volume buttons are not wired either). So the master value set by the slider is discarded by the very next sound. Separately, line 385 does `setRange('#q-vol', 50)` — a hardcoded literal. Nothing is persisted and no API returns the current volume, even though `AudioInterface.get_volume()` exists (src/hal/real.py:140). The slider therefore always reads 50 regardless of the device's real state.

**What it costs:** User drags Volume to 100 (toast-free success), then a schedule fires at 08:00 with sound volume 25 → `play_preset` calls `set_volume(0.25)` and the chime plays quiet. Every later sound also ignores the slider. Reloading the page shows the slider back at 50 with no write having happened.

**Proposed direction:** Decide the volume model, then make the UI reflect it. Either (a) store a master volume in `config["system"]`, have `play_preset` multiply the preset volume by it instead of overwriting, and return it from `/api/status` so `setRange('#q-vol', ...)` uses a real value; or (b) drop the slider from `_MAIN_QUICK` (templates.py:142-143) and the `/api/system/volume` route, since per-schedule volume already exists.

**Decision needed:** Should the Quick Settings volume be a persisted master gain that scales each preset's volume (extra flash write per change), or should the control be removed in favour of the existing per-schedule volume?

### Handler errors are printed to serial only — no RAM ring buffer, no way to see them in the UI — `src/web/routes.py:41`

**Severity:** low · **Category:** observability

Every handler's error path is `print("...error:", e)` (routes.py:41, 139, 159, 174, 195, 216, 232, 245, 278, 331, 351), and the same pattern is used by all the async loops in src/main.py. Nothing keeps the errors, and the settings page has no log view (templates.py:195-205 renders only version and free memory). CLAUDE.md, Reliability: "No silent failures: Log errors to a small ring buffer in RAM (not flash — avoid wear). Expose via Web UI system page." A grep across src confirms no ring buffer exists. On an always-on device with no serial console attached, a recurring failure (NTP, OTA, scheduler) is invisible.

**What it costs:** A schedule silently stops firing because of a scheduler exception. The user opens /settings and sees Wi-Fi connected, a version and free memory — no indication anything failed. Diagnosing it requires plugging in USB and catching the next occurrence live.

**Proposed direction:** Add a tiny shared logger (a list capped at ~20 entries with a module-level index) used by these except blocks, a GET /api/system/logs endpoint returning it, and a section on the settings page that renders it.

**Decision needed:** Is the ~1-2KB of RAM plus the extra endpoint and settings-page section worth spending now, and how many entries should the ring keep?

### Overlapping /api/call requests interleave on the same synth channel — `src/web/routes.py:192`

**Severity:** low · **Category:** concurrency

`await app.ctx["audio_player"].play_preset(preset_id, volume, count=count)` with the new count parameter runs for count x (sequence + 1000 ms gap) — up to ~30 s at count=10 (src/audio/player.py:32-35). To answer the review question directly: this does NOT block the event loop or the display — microdot serves each connection in its own asyncio task and RealAudio.play_sequence awaits asyncio.sleep_ms between notes (src/hal/real.py:127,132). The defect is that there is no guard against a second overlapping invocation: two concurrent play_preset coroutines both call set_volume and both drive `synth_channel(0)`, and each note's `ch.trigger_release()` (src/hal/real.py:128-129) releases the channel the other one is mid-note on. show_alert() is also simply re-entered, restarting the scroll and pushing out _alert_until.

**What it costs:** The ESP32 tap button is pressed twice within the ~6 s of a default count=3 ring (a double tap, or a retry because the first response is held until playback ends): the two rings cut each other's notes on channel 0 and the volume flips between the two requests' values, producing clipped/garbled audio instead of the alert chime.

**Proposed direction:** Guard the endpoint with a module-level 'playing' flag (or an asyncio.Lock) in AudioPlayer so a second call is handled per the chosen policy; also consider responding 200 immediately and running playback with create_task so the ESP32 client does not hold the connection for 30 s.

**Decision needed:** When a call arrives while a ring is still playing, should it be ignored (return 409/200 'busy'), restart the ring, or queue behind it? And should /api/call answer immediately and play in the background instead of holding the HTTP connection for the whole ring?

### Status reports Off while a manually-pushed message is lit on the LEDs — `src/web/routes.py:438`

**Severity:** low · **Category:** state-mismatch

`_get_display_status` derives `active` purely from whether a schedule matches the current time. But `api_set_message` (line 133) ends with `display_renderer.set_active(True, manual=True)`, and `main.on_no_schedule` refuses to turn the display off while `renderer._manual_active` is set. So after "Update display" the panel is physically lit indefinitely while `/api/status` keeps returning `active: false`. app.js then dims the preview (`p.classList.toggle('off', !ST.active)`, line 188) and the pill reads "Off · next … " or "Off · nothing scheduled" (line 197-198). The same applies after `POST /api/bitmap`, which sets `_manual_active = True` in `renderer.set_bitmap` (src/display/renderer.py:229).

**What it costs:** No schedules configured. User types "HELLO" and taps "Update display". The sign scrolls HELLO. `refreshStatus()` runs immediately afterwards and the card greys out the preview and reports "Off · nothing scheduled" — the user believes the update did not take, and taps again.

**Proposed direction:** Expose the renderer's real output state in the status dict (e.g. add `"on": renderer.is_on()` backed by `_active`/`_manual_active`, alongside the existing schedule-derived `active`), and have app.js drive the `.off` class and the pill from that, keeping `active`/`active_end`/`next_start` for the schedule text.

**Decision needed:** Should the status pill report the physical display state (lit vs dark, including manual overrides) or stay a schedule-only indicator, and should a manual override be surfaced as its own state such as "On · manual"?


## Docs vs code

### api-reference promises 10 extended glyphs (Æ © etc.) that the CJK path now renders blank — `docs/api-reference.md:533`

**Severity:** low · **Category:** doc-contradicts-code

docs/api-reference.md:528-533 claims `PicoGraphics built-in fonts. 105 characters total:` with `| Extended | Æ Ø Å æ ø å Þ þ © ° | 10 |`, and line 548 adds `- Extended characters (Æ, ©, ° etc.) may render as uppercase equivalents`. Every one of those 10 codepoints is above U+007E, and src/display/cjk_font.py:22-27 routes any such message away from the PicoGraphics fonts entirely: `for ch in text: if ord(ch) > 0x7E: return True`, consumed by src/display/renderer.py:128 `if not cjk_font.needs_bitmap(self._text): return False`. The k8x12 glyph store does not carry them — decoding src/display/cjk11.bin (7170 fixed 19-byte records) shows U+00B0 present but U+00A9, U+00C5, U+00C6, U+00D8 and U+00DE absent — so src/display/cjk_font.py:69-70 emits blanks: `for _ in range(MISSING_WIDTH): columns.append(0)`. The 10 extended slots that tools/ttf_to_picographics.py:19-22 still builds into font11.bin are now unreachable.

**What it costs:** `POST /api/message {"text": "CAFÉ ©2026"}` (or any of the 10 documented extended chars) used to draw the glyph from bitmap8/font11. It now takes the CJK bitmap path and draws a 4px blank gap for `©`, and the rest of the ASCII in the same message silently switches to the k8x12 8px/4px metrics instead of the selected font.

**Proposed direction:** Either (a) exempt the 10 supported codepoints in src/display/cjk_font.py:needs_bitmap (e.g. skip the `> 0x7E` trigger for the EXTENDED_CODEPOINTS set) so they keep using the PicoGraphics fonts; or (b) trim docs/api-reference.md:528-535 to ASCII U+0020-U+007E (95 chars), delete line 548, and drop EXTENDED_CODEPOINTS from tools/ttf_to_picographics.py.

**Decision needed:** Keep the 10 extended Latin glyphs working by exempting them from the CJK bitmap trigger, or accept that anything above U+007E goes through k8x12 and delete the extended-character promise from the docs and the font builder?

### api-reference claims border applies to Japanese messages; the bitmap path never draws a border — `docs/api-reference.md:568`

**Severity:** low · **Category:** doc-contradicts-code

docs/api-reference.md:568 says `- The `font` setting is ignored for these messages; colour, background, border, mode and speed all still apply`. Colour, background, mode and speed do survive (src/display/renderer.py:136-137 `self._bitmap_color = self._color` / `self._bitmap_bg_color = self._bg_color`, with `_mode` and `_scroll_interval_ms` already set at renderer.py:75-77). Border does not. The border lines are drawn only in the text renderers — src/display/renderer.py:319-322 in `_render_scroll` and renderer.py:345-349 in `_render_fixed` — and src/display/renderer.py:258-268 dispatches CJK messages to `_render_bitmap_scroll`/`_render_bitmap_fixed` instead, whose shared `_render_bitmap_frame` (renderer.py:371-435) never reads `self._border` or `self._border_color`.

**What it costs:** A user enables `border: true` with a white bg_color, sees the 1px accent lines on an English message, then switches the text to 「お知らせ」 and the borders vanish with no error and nothing in the docs to explain it.

**Proposed direction:** Simplest correct fix: drop `border` from the list at docs/api-reference.md:568 and add "the border setting is not drawn for these messages". If borders should work there instead, add the two `draw_line` calls to `_render_bitmap_frame` — but note that also gives `/api/bitmap` content a border, since `set_bitmap` (renderer.py:198) never clears `_border`.

**Decision needed:** Should border support be added to the bitmap render path (which would also start drawing borders over /api/bitmap uploads), or should the doc simply state that border does not apply to Japanese/bitmap messages?

### Spec "LEDs off when no schedule is active" is false after a manual message post — `docs/specification.md:69`

**Severity:** low · **Category:** doc-contradicts-code

docs/specification.md:69 says `| Off behavior | LEDs off when no schedule is active |`. That holds only while nothing was activated manually. src/web/routes.py:133 marks a posted message manual — `app.ctx["display_renderer"].set_active(True, manual=True)` — which sets `self._manual_active = True` (src/display/renderer.py:180-181), and src/main.py:196-198 then refuses to turn the panel off: `def on_no_schedule(): if not renderer._manual_active: renderer.set_active(False)`. So a message saved from the web UI stays lit indefinitely with zero schedules configured. docs/api-reference.md:144 states the real behaviour (`The display stays on until a schedule takes over or the device is rebooted`), so the two docs disagree.

**What it costs:** A user reads spec:69, expects the panel to go dark outside schedule windows, saves a message from the web UI to test it, and the sign then stays lit 24/7. Nothing in the spec explains why, and there is no UI control to clear the manual flag short of a reboot or DELETE /api/bitmap.

**Proposed direction:** Change docs/specification.md:69 to `| Off behavior | LEDs off when no schedule is active, unless a message was saved from the web UI (manual activation stays on until a schedule takes over or the device reboots) |`, matching docs/api-reference.md:144. Two related code smells, outside this docs area: src/main.py:462-464 (`if not config.get("schedules"): renderer.set_active(True)`) is dead — the first scheduler_loop tick calls on_no_schedule and switches it straight back off, since that call omits `manual=True`; and src/main.py:230-234 `_restore_after_alert` clears `_manual_active` then calls `sched.check()`, so any /api/call alert permanently darkens a manually posted message.

### Documented WiFi exponential backoff (5/10/20/40/60s + 5-min pause) is never implemented — `docs/specification.md:319`

**Severity:** low · **Category:** doc-contradicts-code

docs/specification.md:319-320 claims `| Reconnect backoff | 5s → 10s → 20s → 40s → 60s (5 attempts) |` and `| After max retries | 5-minute pause, then restart cycle |`. CLAUDE.md:219-220 repeats it (`切断時は指数バックオフで自動再接続（5s→10s→20s→40s→60s、最大5回）` / `再接続失敗後は5分待機してリトライサイクル再開`), and CLAUDE.md is auto-loaded as project rules. No delay is ever applied. src/wifi/manager.py:10-11 defines `RECONNECT_DELAYS = [5, 10, 20, 40, 60]` and `RECONNECT_PAUSE = 300`, but the only consumer is src/wifi/manager.py:162 `get_reconnect_delay()`, which `grep -rn get_reconnect_delay src tests` shows has zero callers. `_attempt_reconnect` (manager.py:138) uses `RECONNECT_DELAYS` only for its length: manager.py:140-144 `if self._reconnect_attempt >= len(RECONNECT_DELAYS): self._reconnect_attempt = 0; return`. The real cadence is the fixed 30s gate at manager.py:127 (`if ticks_diff(current_ms, self._last_check_ms) < CHECK_INTERVAL_S * 1000: return`) driven by src/main.py:328 `await asyncio.sleep(30)`.

**What it costs:** The router reboots and stays down for 10 minutes. Docs predict 5 attempts over ~2 minutes then a 5-minute quiet period. Actual behaviour: `connect_sta(..., timeout_s=10)` fires roughly every 30-40s forever, with one skipped cycle after every 5th failure — ~18 connection attempts instead of 5, and no 5-minute pause. Anyone debugging reconnect timing from the docs measures numbers that never occur.

**Proposed direction:** Either (a) make the code match: track a deadline and gate `_attempt_reconnect` on `RECONNECT_DELAYS[self._reconnect_attempt]` / `RECONNECT_PAUSE`, using the existing `get_reconnect_delay()`; or (b) make the docs match: rewrite docs/specification.md:319-320 and CLAUDE.md:219-220 as "retry every 30s while disconnected" and delete the unused `RECONNECT_DELAYS`/`RECONNECT_PAUSE`/`get_reconnect_delay()`.

**Decision needed:** Do you want real exponential backoff with the 5-minute pause implemented in wifi/manager.py, or should the docs (spec:319-320 and CLAUDE.md:219-220) be corrected to the actual flat 30s retry and the unused constants deleted?


## Other

### Auto-brightness never updates in fixed mode, freezing the panel at activation-time brightness — `src/display/renderer.py:186`

**Severity:** medium · **Category:** stale-sensor

`_on_scroll_cycle` (registered as `main._update_auto_brightness`, src/main.py:276) is invoked from exactly two places: the scroll wrap in `_render_scroll`/`_render_bitmap_scroll`, and the False->True transition in `set_active`:

```python
        if active != self._active:
            self._frame_dirty = True
            if active:
                self._reset_scroll()
                # Read sensor when display activates (for fixed mode)
                if self._on_scroll_cycle:
                    self._on_scroll_cycle()
```

The comment shows the fixed-mode hole was known and patched only for the activation instant. In fixed mode nothing ever calls it again, and fixed mode is the *common* case because `_reset_scroll()` auto-downgrades any text narrower than the 53px panel (renderer.py:166) — "OPEN", a clock, or up to six 8px kanji. Grep confirms the only other callers of `_update_auto_brightness` are the brightness buttons (main.py:400,407), the `/api/system/brightness` endpoint (routes.py:213) and a single call in `main()` (main.py:450). There is no periodic task.

**What it costs:** A short always-on message such as "OPEN" or "営業中" auto-downgrades to fixed mode. The light sensor is read once when the display activates, e.g. at boot in the morning, and never again. At night the panel is still at daytime brightness (and vice versa) indefinitely. The advertised auto-brightness silently does nothing for short messages.

**Proposed direction:** Read the sensor on a cadence instead of only on scroll wrap. Smallest change outside the renderer: add a periodic task in main.py that calls `_update_auto_brightness()` (and drop the `set_active` special case, or keep it for immediate response on activation). Alternatively have `render_frame()` fire the callback when N ms have elapsed since the last fire, which covers both modes uniformly.

**Decision needed:** How often should the light sensor be polled in fixed mode — a fixed interval (e.g. every 30-60s in a small async task) or a time-based trigger inside render_frame that replaces the scroll-cycle hook entirely? A too-short interval makes the panel visibly flicker between brightness steps as the sensor jitters, so the cadence (and whether to smooth the reading) is a tuning call.

### gu.play_synth() is started on every note and stop_playing() is never called by anyone — `src/hal/real.py:111`

**Severity:** medium · **Category:** resource-leak

`play_tone` calls `self._gu.play_synth()` (real.py:111) for every note, and nothing ever stops the engine: `RealAudio.stop()` (real.py:134) and `AudioPlayer.stop()` (player.py:37) have zero callers anywhere in src (grep for `player.stop`/`audio.stop` finds only the definitions). So from the first sound after boot until the next reboot the audio DMA/IRQ keeps running on the same core that runs MicroPython, the web server and the display loop.

**What it costs:** Device boots, one schedule fires a beep at 08:00. From then on the audio engine runs 24/7 on a 133MHz M0+: the sample IRQ competes with display_loop and microdot for the rest of the device's uptime, even though no sound plays.

**Proposed direction:** At the end of `play_sequence`, after the final `trigger_release()`, `await asyncio.sleep_ms(int(max_release_s * 1000))` then `self._gu.stop_playing()` — or drop the dead `stop()` methods and document that leaving the engine running is intentional.

**Decision needed:** Pimoroni's own demos leave play_synth() running, and stopping/restarting the engine per sound can pop the speaker. Do you want stop-after-release (quiet core, possible click) or keep it always-on and delete the unused stop() methods?

### Missing or duplicate schedule ids silently suppress the on_schedule_start sound — `src/config/config_manager.py:103`

**Severity:** low · **Category:** validation

`_validate_schedule` defaults a missing `id` to 0 (line 103) and never checks uniqueness across the list built at line 186. The scheduler uses `id` as the sole key for start-transition detection: `scheduler.py:145 sched_id = sched.get("id", 0)` and `scheduler.py:154 if sched_id != self._last_active_id:` gates the `on_schedule_start` callback, which is what triggers the sound (main.py:182-192). Two schedules sharing an id are indistinguishable to that check. The bundled web UI always assigns unique ids from 1 (app.js:345), so this only bites configs written by another client — but the config layer is the place that is supposed to guarantee it.

**What it costs:** A client posts `[{"start_time":"08:00","end_time":"09:00",...},{"start_time":"09:00","end_time":"10:00",...}]` with no `id` fields. Both are stored with id 0. At 09:00 the first schedule ends and the second becomes active in the same check; `sched_id (0) != self._last_active_id (0)` is False, so `on_schedule_start` never fires and the second schedule's sound never plays. Every subsequent back-to-back handover between the two is silent too.

**Proposed direction:** Assign unique ids while validating in `_validate_app_config` (around line 186): track a `seen` set, and for any entry whose id is 0 or already present, assign `max(seen) + 1`. The web UI adopts the ids from the save response (`saved = norm(r)` at app.js:362), so renumbering is safe.
