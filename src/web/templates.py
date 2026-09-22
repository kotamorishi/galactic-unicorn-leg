"""HTML templates for the web UI.

Pages are small HTML shells. Styling and behaviour live in cacheable static
files (web/static/app.css, web/static/app.js) served by routes.py. Each page
embeds its initial data as a JSON blob (window.D) that app.js renders from.

Render functions are async generators that yield small chunks so the page is
never built in RAM as one large string.
"""

import os

try:
    import ujson as json
except ImportError:
    import json

try:
    from config import config_manager as _cm
except ImportError:  # pragma: no cover
    _cm = None


# Directory holding app.css / app.js. MicroPython sets __file__ for modules
# imported from the filesystem; fall back to the on-device layout.
try:
    _f = __file__.replace("\\", "/")
    STATIC_DIR = (_f.rsplit("/", 1)[0] + "/static") if "/" in _f else "web/static"
except (NameError, AttributeError):  # pragma: no cover
    STATIC_DIR = "web/static"

STATIC_FILES = {
    "app.css": "text/css; charset=utf-8",
    "app.js": "application/javascript; charset=utf-8",
}

_asset_tag = None


def asset_tag():
    """Cache-busting tag for static URLs.

    Static files are served with a long max-age, so the URL must change when
    their content changes. The tag combines the installed OTA version with the
    file sizes, which also covers manual deploys that don't bump the version.
    Computed once per boot.
    """
    global _asset_tag
    if _asset_tag is None:
        parts = []
        try:
            if _cm is not None:
                parts.append(str(_cm.load_version().get("version", "")))
        except Exception:
            pass
        for name in ("app.css", "app.js"):
            try:
                st = os.stat(STATIC_DIR + "/" + name)
                parts.append("{}.{}".format(st[6], st[8]))
            except OSError:
                parts.append("0")
        tag = "-".join(p for p in parts if p)
        # isalpha/isdigit, not isalnum: MicroPython's str has no isalnum, and
        # this runs on the first yield of every page.
        _asset_tag = "".join(
            c if (c.isalpha() or c.isdigit() or c in "-.") else "_" for c in tag
        )
    return _asset_tag


def _head(title, page):
    v = asset_tag()
    return (
        '<!DOCTYPE html><html lang="en"><head><meta charset="utf-8">'
        '<meta name="viewport" content="width=device-width,initial-scale=1,viewport-fit=cover">'
        '<meta name="color-scheme" content="dark light">'
        '<title>{t}</title><link rel="icon" href="data:,"><link rel="stylesheet" href="/static/app.css?v={v}">'
        '<script src="/static/app.js?v={v}" defer></script>'
        '</head><body data-page="{p}"><main class="app">'
    ).format(t=title, v=v, p=page)


# Emitted around _json() as three separate chunks: with 20 schedules the blob is
# the largest thing on the page, and concatenating it doubles the peak allocation.
_D_OPEN = "<script>window.D="
_D_CLOSE = "</script>"


def _json(obj):
    """JSON for app.js. '<' is escaped so text can't close the script tag."""
    return json.dumps(obj).replace("<", "\\u003c")


_TAIL = (
    '</main><div class="toast" id="toast" role="status" aria-live="polite"></div>'
    "</body></html>"
)

_LOGO = (
    '<div class="logo" aria-hidden="true"><i class="l"></i><i></i><i class="l"></i><i></i>'
    '<i></i><i class="l"></i><i></i><i class="l"></i><i class="l"></i><i></i><i class="l"></i>'
    '<i></i><i></i><i class="l"></i><i></i><i class="l"></i></div>'
)


def _hex(c, default=None):
    if not isinstance(c, dict) or "r" not in c:
        return default
    return "#{:02x}{:02x}{:02x}".format(c.get("r", 0), c.get("g", 0), c.get("b", 0))


# ---------------------------------------------------------------- Main page

_MAIN_NOW = (
    '<header class="top"><div class="brand">' + _LOGO + "Galactic Unicorn</div>"
    '<a class="iconbtn" href="/settings" aria-label="Device settings"><svg class="i"><use href="#i-gear"/></svg></a></header>'
    '<div class="card"><div class="panel" id="now-panel"><div class="led" id="now-led"></div></div>'
    '<div class="now-row"><div class="clock num"><span id="clk">--:--</span><small id="clk-day"></small></div>'
    '<span class="pill" id="now-pill"><span class="d"></span><span id="now-txt"></span></span></div></div>'
)

_MAIN_MSG = (
    '<div class="card"><div class="card-h"><h2>MESSAGE</h2><span class="hint">Used when a schedule has no text</span></div>'
    '<div class="inp-wrap"><input class="inp" id="msg" maxlength="128" placeholder="Type a message" aria-label="Message">'
    '<span class="count num" id="msg-count"></span></div>'
    '<div class="field" style="margin-top:22px"><span class="lbl">Color</span><div class="sw" id="msg-sw"></div></div>'
    '<button class="disclose" id="opt-t" aria-expanded="false" aria-controls="opt"><svg class="i" style="width:14px;height:14px"><use href="#i-chev"/></svg>Display options</button>'
    '<div id="opt" hidden>'
    '<div class="field"><span class="lbl">Mode</span><div class="seg" data-k="display_mode"><button data-v="scroll">Scroll</button><button data-v="fixed">Fixed</button></div></div>'
    '<div class="field"><span class="lbl">Scroll speed</span><div class="seg" data-k="scroll_speed"><button data-v="slow">Slow</button><button data-v="medium">Medium</button><button data-v="fast">Fast</button></div></div>'
    '<div class="field"><span class="lbl">Font size</span><div class="seg" data-k="font"><button data-v="bitmap6">Small</button><button data-v="bitmap8">Normal</button><button data-v="font11">Large</button></div></div>'
    "</div>"
    '<div class="acts"><button class="btn primary grow" id="msg-save">Update display</button></div></div>'
)

_MAIN_SCHED = (
    '<div class="card"><div class="card-h"><h2>SCHEDULE</h2><span class="hint" id="sc-sum"></span></div>'
    '<div class="tl" id="tl" aria-label="Week overview"></div><div id="sc-list"></div>'
    '<button class="add" id="sc-add"><svg class="i"><use href="#i-plus"/></svg>Add schedule</button></div>'
)

_MAIN_QUICK = (
    '<div class="card"><div class="card-h"><h2>QUICK SETTINGS</h2></div>'
    '<div class="field" style="margin-top:0"><label for="q-br">Brightness <span style="font-weight:400">&middot; auto + adjust</span></label>'
    '<div class="range"><svg class="i muted"><use href="#i-sun"/></svg><input type="range" id="q-br" min="-50" max="50" value="0"><output id="q-br-v" class="num"></output></div></div>'
    '<div class="field"><label for="q-vol">Volume</label>'
    '<div class="range"><svg class="i muted"><use href="#i-vol"/></svg><input type="range" id="q-vol" min="0" max="100" value="50"><output id="q-vol-v" class="num"></output></div></div></div>'
    '<div class="savebar" id="savebar" role="region" aria-label="Unsaved changes"><div class="savebar-in">'
    '<span id="savebar-txt">Unsaved changes</span><button class="btn ghost sm" id="sc-discard">Discard</button>'
    '<button class="btn primary sm" id="sc-save">Save</button></div></div>'
)


async def render_main_page(config, presets, status):
    msg = config.get("message", {})
    system = config.get("system", {})
    yield _head("Galactic Unicorn", "main")
    yield _MAIN_NOW
    yield _MAIN_MSG
    yield _MAIN_SCHED
    yield _MAIN_QUICK
    yield _D_OPEN
    yield _json({
        "msg": {
            "text": msg.get("text", ""),
            "display_mode": msg.get("display_mode", "scroll"),
            "scroll_speed": msg.get("scroll_speed", "medium"),
            "font": msg.get("font", "bitmap8"),
            "color": _hex(msg.get("color"), "#ffffff"),
        },
        "sch": config.get("schedules", []),
        "presets": [p["name"] for p in presets],
        "status": status,
        "bo": system.get("brightness_offset", 0),
    })
    yield _D_CLOSE
    yield _TAIL


# ------------------------------------------------------------ Settings page

async def render_settings_page(wifi_status, version, free_mem, system_config=None):
    if system_config is None:
        system_config = {}
    yield _head("Device settings", "settings")
    yield (
        '<a class="back" href="/"><svg class="i"><use href="#i-back"/></svg>Back</a>'
        '<h1 class="h1">Device settings</h1>'
        '<div class="card"><div class="card-h"><h2>WI-FI</h2><span class="pill" id="wf-pill"><span class="d"></span><span id="wf-state"></span></span></div>'
        '<div class="rows"><div class="row"><span class="k">Network</span><span class="v" id="wf-ssid"></span></div>'
        '<div class="row"><span class="k">IP address</span><span class="v num" id="wf-ip"></span></div>'
        '<div class="row"><span class="k">Signal</span><span class="v" id="wf-rssi"></span></div></div>'
        '<button class="disclose" id="wifi-t" aria-expanded="false" aria-controls="wifi-chg"><svg class="i" style="width:14px;height:14px"><use href="#i-chev"/></svg>Change network</button>'
        '<div id="wifi-chg" hidden><div class="field"><div id="net-list"></div></div>'
        '<div class="field" id="ssid-row" hidden><label for="ssid">Network name</label><input class="inp" id="ssid" placeholder="SSID" autocapitalize="off" autocomplete="off"></div>'
        '<div class="field"><label for="pw">Password</label><div class="pw"><input class="inp" id="pw" type="password" placeholder="Wi-Fi password"><button data-pw="pw">Show</button></div></div>'
        '<div class="acts"><button class="btn primary" id="wf-connect">Connect</button><button class="btn ghost" id="wf-scan">Rescan</button></div></div></div>'
    )
    yield (
        '<div class="card"><div class="card-h"><h2>TIME</h2></div>'
        '<div class="rows"><div class="row"><span class="k">Clock</span><span class="v num" id="set-clk">--:--</span></div>'
        '<div class="row"><span class="k">Time sync</span><span class="v" id="ntp"></span></div></div>'
        '<div class="field"><label for="tz">Timezone</label><select class="inp" id="tz"></select></div></div>'
        '<div class="card"><div class="card-h"><h2>DEVICE</h2></div>'
        '<div class="rows"><div class="row"><span class="k">Version</span><span class="v num" id="ver"></span></div>'
        '<div class="row"><span class="k">Free memory</span><span class="v num" id="mem"></span></div></div>'
        '<div class="acts"><button class="btn ghost grow" id="ota">Check for updates</button></div></div>'
        '<div class="card danger-zone"><button class="btn ghost" id="reboot" style="color:var(--danger)">Reboot device</button></div>'
    )
    yield _D_OPEN
    yield _json({
        "wifi": {
            "connected": bool(wifi_status.get("connected")),
            "ssid": wifi_status.get("ssid") or "",
            "ip": wifi_status.get("ip") or "",
            "rssi": wifi_status.get("rssi"),
            "ntp": bool(wifi_status.get("ntp_synced")),
        },
        "version": str(version.get("version", "unknown")),
        "free_kb": (free_mem // 1024) if free_mem else None,
        "tz": system_config.get("timezone_offset", 9),
    })
    yield _D_CLOSE
    yield _TAIL


# --------------------------------------------------- Setup (captive portal)

async def render_setup_page(networks):
    yield _head("Welcome", "setup")
    yield (
        '<div class="welcome"><div class="steps"><i class="on"></i><i></i></div>'
        '<div class="panel"><div class="led" style="color:#ffb224">HELLO!</div></div>'
        '<h1 class="h1" style="margin-bottom:0">Let&rsquo;s get online</h1>'
        "<p>Pick the Wi-Fi network this display should join.</p></div>"
        '<div class="card"><div class="card-h"><h2>NETWORKS</h2><button class="btn ghost sm" id="wf-scan">Rescan</button></div>'
        '<div id="net-list"></div>'
        '<div class="field" id="ssid-row" hidden><label for="ssid">Network name</label><input class="inp" id="ssid" placeholder="SSID" autocapitalize="off" autocomplete="off"></div>'
        '<div class="field"><label for="pw">Password</label><div class="pw"><input class="inp" id="pw" type="password" placeholder="Wi-Fi password"><button data-pw="pw">Show</button></div></div>'
        '<div class="acts"><button class="btn primary grow" id="wf-connect">Connect</button></div></div>'
        '<p class="hint" style="text-align:center">Only 2.4 GHz networks are supported.</p>'
    )
    nets = []
    for n in networks:
        try:
            nets.append({"ssid": n["ssid"], "rssi": n.get("rssi")})
        except (KeyError, TypeError, AttributeError):
            pass
    yield _D_OPEN
    yield _json({"nets": nets})
    yield _D_CLOSE
    yield _TAIL

