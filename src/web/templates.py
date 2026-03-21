"""Minimal HTML templates for the web UI.

Templates are string functions to minimize RAM usage.
All pages share a common layout with navigation.
CSS is embedded — no external files to reduce HTTP requests.
Design: clean, white-based, minimal.
"""

try:
    import ujson as json
except ImportError:
    import json


def _layout(title, body, active_nav=""):
    """Wrap body content in the common page layout."""
    return """<!DOCTYPE html>
<html><head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>{title} - Galactic Unicorn</title>
<style>
*{{margin:0;padding:0;box-sizing:border-box}}
body{{font-family:-apple-system,system-ui,"Segoe UI",Roboto,sans-serif;background:#f5f5f7;color:#1d1d1f;max-width:480px;margin:0 auto;padding:16px;font-size:14px;line-height:1.5}}

header{{margin-bottom:20px}}
header h1{{font-size:20px;font-weight:600;letter-spacing:-0.3px}}
header p{{font-size:12px;color:#86868b;margin-top:2px}}

nav{{display:flex;gap:2px;margin-bottom:24px;background:#fff;border-radius:10px;padding:3px;box-shadow:0 1px 3px rgba(0,0,0,0.08)}}
nav a{{flex:1;text-align:center;padding:8px 4px;color:#86868b;text-decoration:none;border-radius:8px;font-size:12px;font-weight:500;transition:all 0.2s}}
nav a:hover{{color:#1d1d1f}}
nav a.on{{background:#1d1d1f;color:#fff}}

.section{{background:#fff;border-radius:12px;padding:16px;margin-bottom:12px;box-shadow:0 1px 3px rgba(0,0,0,0.06)}}
.section h2{{font-size:13px;font-weight:600;text-transform:uppercase;letter-spacing:0.5px;color:#86868b;margin-bottom:12px}}

label{{display:block;font-size:12px;font-weight:500;color:#86868b;margin:12px 0 4px}}
label:first-child{{margin-top:0}}

input[type=text],input[type=number],input[type=time],input[type=password],select{{
 width:100%;padding:10px 12px;background:#f5f5f7;border:1px solid #e5e5e7;color:#1d1d1f;border-radius:8px;font-size:14px;font-family:inherit;outline:none;transition:border 0.2s}}
input:focus,select:focus{{border-color:#007aff}}

input[type=color]{{width:44px;height:36px;padding:2px;border:1px solid #e5e5e7;border-radius:8px;cursor:pointer;background:#f5f5f7}}

input[type=range]{{width:100%;height:4px;-webkit-appearance:none;appearance:none;background:#e5e5e7;border-radius:2px;outline:none;margin:8px 0}}
input[type=range]::-webkit-slider-thumb{{-webkit-appearance:none;width:20px;height:20px;background:#007aff;border-radius:50%;cursor:pointer}}

input[type=checkbox]{{width:18px;height:18px;accent-color:#007aff;cursor:pointer;vertical-align:middle}}

.btn{{display:inline-block;padding:10px 20px;border:none;border-radius:8px;font-size:14px;font-weight:500;font-family:inherit;cursor:pointer;transition:opacity 0.2s}}
.btn:active{{opacity:0.7}}
.btn-primary{{background:#007aff;color:#fff}}
.btn-secondary{{background:#f5f5f7;color:#1d1d1f;border:1px solid #e5e5e7}}
.btn-danger{{background:#ff3b30;color:#fff}}
.btn-sm{{padding:6px 14px;font-size:12px}}
.btn-block{{display:block;width:100%;text-align:center}}
.actions{{display:flex;gap:8px;margin-top:16px;flex-wrap:wrap}}

.row{{display:flex;gap:12px;align-items:center}}
.row>*{{flex:1}}

.check-row{{display:flex;align-items:center;gap:8px;padding:8px 0}}
.check-row label{{margin:0;color:#1d1d1f;font-size:14px;font-weight:400}}

.days-row{{display:flex;gap:6px;flex-wrap:wrap;margin:4px 0}}
.day-tag{{display:flex;align-items:center;gap:3px;font-size:12px;color:#1d1d1f}}
.day-tag input{{width:15px;height:15px}}

.sched-card{{border:1px solid #e5e5e7;border-radius:10px;padding:14px;margin-bottom:10px}}
.sched-card.disabled{{opacity:0.5}}
.sched-header{{display:flex;justify-content:space-between;align-items:center;margin-bottom:8px}}
.sched-header span{{font-weight:600;font-size:14px}}

.preset-row{{display:flex;justify-content:space-between;align-items:center;padding:10px 0;border-bottom:1px solid #f0f0f2}}
.preset-row:last-child{{border-bottom:none}}
.preset-name{{font-size:14px}}
.preset-cat{{font-size:11px;color:#86868b;margin-left:4px}}

.info-row{{display:flex;justify-content:space-between;padding:8px 0;border-bottom:1px solid #f0f0f2;font-size:14px}}
.info-row:last-child{{border-bottom:none}}
.info-label{{color:#86868b}}
.info-value{{font-weight:500;text-align:right}}

.range-row{{display:flex;align-items:center;gap:10px}}
.range-row input{{flex:1}}
.range-row span{{min-width:36px;text-align:right;font-size:13px;color:#86868b;font-variant-numeric:tabular-nums}}

.toast{{font-size:12px;color:#34c759;margin-top:8px;min-height:16px}}
.toast.err{{color:#ff3b30}}
</style>
</head><body>
<header>
<h1>{title}</h1>
<p>Galactic Unicorn</p>
</header>
<nav>
<a href="/" {n0}>Home</a>
<a href="/message" {n1}>Message</a>
<a href="/schedule" {n2}>Schedule</a>
<a href="/sound" {n3}>Sound</a>
<a href="/system" {n4}>System</a>
</nav>
{body}
<script>
function api(m,u,d){{return fetch(u,{{method:m,headers:{{'Content-Type':'application/json'}},body:d?JSON.stringify(d):undefined}}).then(function(r){{return r.json()}})}}
function toast(id,msg,err){{var e=document.getElementById(id);e.textContent=msg;e.className=err?'toast err':'toast';if(!err)setTimeout(function(){{e.textContent=''}},3000)}}
</script>
</body></html>""".format(
        title=title,
        body=body,
        n0='class="on"' if active_nav == "home" else "",
        n1='class="on"' if active_nav == "message" else "",
        n2='class="on"' if active_nav == "schedule" else "",
        n3='class="on"' if active_nav == "sound" else "",
        n4='class="on"' if active_nav == "system" else "",
    )


def render_index():
    body = """<div class="section">
<h2>Welcome</h2>
<p>Configure your LED display using the tabs above.</p>
<p style="margin-top:8px;font-size:13px;color:#86868b">Set a message, create schedules, choose alert sounds, and manage device settings.</p>
</div>"""
    return _layout("Home", body, "home")


def render_message_page(message):
    color = message.get("color", {})
    color_hex = "#{:02x}{:02x}{:02x}".format(
        color.get("r", 255), color.get("g", 255), color.get("b", 255))
    body = """<div class="section">
<h2>Display Message</h2>

<label>Message Text</label>
<input type="text" id="msg-text" value="{text}" maxlength="128" placeholder="Enter your message">

<div class="row" style="margin-top:0">
<div>
<label>Mode</label>
<select id="msg-mode">
<option value="scroll" {sel_scroll}>Scroll</option>
<option value="fixed" {sel_fixed}>Fixed</option>
</select>
</div>
<div>
<label>Speed</label>
<select id="msg-speed">
<option value="slow" {sel_slow}>Slow</option>
<option value="medium" {sel_medium}>Medium</option>
<option value="fast" {sel_fast}>Fast</option>
</select>
</div>
</div>

<div class="row" style="margin-top:0">
<div>
<label>Font</label>
<select id="msg-font">
<option value="bitmap6" {sel_f6}>Small (6px)</option>
<option value="bitmap8" {sel_f8}>Normal (8px)</option>
</select>
</div>
<div>
<label>Color</label>
<input type="color" id="msg-color" value="{color_hex}">
</div>
</div>

<div class="actions">
<button class="btn btn-primary" onclick="saveMsg()">Save</button>
</div>
<div id="msg-toast" class="toast"></div>
</div>
<script>
function saveMsg(){{
 var c=document.getElementById('msg-color').value;
 var r=parseInt(c.substr(1,2),16),g=parseInt(c.substr(3,2),16),b=parseInt(c.substr(5,2),16);
 api('POST','/api/message',{{
  text:document.getElementById('msg-text').value,
  display_mode:document.getElementById('msg-mode').value,
  scroll_speed:document.getElementById('msg-speed').value,
  color:{{r:r,g:g,b:b}},
  font:document.getElementById('msg-font').value
 }}).then(function(){{toast('msg-toast','Settings saved')}})
 .catch(function(){{toast('msg-toast','Save failed',true)}});
}}
</script>""".format(
        text=_escape_html(message.get("text", "")),
        color_hex=color_hex,
        sel_scroll='selected' if message.get("display_mode") == "scroll" else "",
        sel_fixed='selected' if message.get("display_mode") == "fixed" else "",
        sel_slow='selected' if message.get("scroll_speed") == "slow" else "",
        sel_medium='selected' if message.get("scroll_speed") == "medium" else "",
        sel_fast='selected' if message.get("scroll_speed") == "fast" else "",
        sel_f6='selected' if message.get("font") == "bitmap6" else "",
        sel_f8='selected' if message.get("font") == "bitmap8" else "",
    )
    return _layout("Message", body, "message")


def render_schedule_page(schedules):
    items = ""
    for s in schedules:
        days_tags = ""
        for d in ["mon", "tue", "wed", "thu", "fri", "sat", "sun"]:
            checked = "checked" if d in s.get("days", []) else ""
            days_tags += '<span class="day-tag"><input type="checkbox" data-day="{d}" {ck}>{dl}</span>'.format(
                d=d, ck=checked, dl=d.capitalize())
        sound = s.get("sound", {})
        disabled_cls = "" if s.get("enabled") else " disabled"
        items += """<div class="sched-card{dcls}" data-id="{id}">
<div class="sched-header">
<span>Schedule #{id}</span>
<div><input type="checkbox" class="sched-enable" {enabled}></div>
</div>
<div class="row">
<div><label>Start</label><input type="time" class="sched-start" value="{start}"></div>
<div><label>End</label><input type="time" class="sched-end" value="{end}"></div>
</div>
<label>Days</label>
<div class="days-row">{days}</div>
<div class="check-row" style="margin-top:4px">
<input type="checkbox" class="sched-sound-en" {sound_en}>
<label>Sound (Preset #{preset_id}, Volume {vol}%)</label>
</div>
<div class="actions">
<button class="btn btn-danger btn-sm" onclick="delSched({id})">Remove</button>
</div>
</div>""".format(
            id=s.get("id", 0),
            dcls=disabled_cls,
            enabled="checked" if s.get("enabled") else "",
            start=s.get("start_time", "00:00"),
            end=s.get("end_time", "23:59"),
            days=days_tags,
            sound_en="checked" if sound.get("enabled") else "",
            preset_id=sound.get("preset_id", 1),
            vol=sound.get("volume", 50),
        )

    body = """<div class="section">
<h2>Schedules</h2>
<div id="scheds">{items}</div>
<div class="actions">
<button class="btn btn-secondary" onclick="addSched()">Add Schedule</button>
<button class="btn btn-primary" onclick="saveScheds()">Save All</button>
</div>
<div id="sched-toast" class="toast"></div>
</div>
<script>
var nid={next_id};
function addSched(){{
 nid++;
 var h='<div class="sched-card" data-id="'+nid+'">';
 h+='<div class="sched-header"><span>Schedule #'+nid+'</span><div><input type="checkbox" class="sched-enable" checked></div></div>';
 h+='<div class="row"><div><label>Start</label><input type="time" class="sched-start" value="08:00"></div>';
 h+='<div><label>End</label><input type="time" class="sched-end" value="09:00"></div></div>';
 h+='<label>Days</label><div class="days-row">';
 ['mon','tue','wed','thu','fri','sat','sun'].forEach(function(d){{
  h+='<span class="day-tag"><input type="checkbox" data-day="'+d+'" checked>'+d.charAt(0).toUpperCase()+d.slice(1)+'</span>';
 }});
 h+='</div><div class="check-row" style="margin-top:4px"><input type="checkbox" class="sched-sound-en"><label>Sound (Preset #1, Volume 50%)</label></div>';
 h+='<div class="actions"><button class="btn btn-danger btn-sm" onclick="delSched('+nid+')">Remove</button></div></div>';
 document.getElementById('scheds').insertAdjacentHTML('beforeend',h);
}}
function delSched(id){{var e=document.querySelector('[data-id="'+id+'"]');if(e)e.remove()}}
function saveScheds(){{
 var a=[];
 document.querySelectorAll('.sched-card').forEach(function(el){{
  var days=[];
  el.querySelectorAll('[data-day]').forEach(function(cb){{if(cb.checked)days.push(cb.dataset.day)}});
  a.push({{
   id:parseInt(el.dataset.id),
   enabled:el.querySelector('.sched-enable').checked,
   start_time:el.querySelector('.sched-start').value,
   end_time:el.querySelector('.sched-end').value,
   days:days,
   sound:{{enabled:el.querySelector('.sched-sound-en')?el.querySelector('.sched-sound-en').checked:false,preset_id:1,volume:50}}
  }});
 }});
 api('POST','/api/schedules',a)
 .then(function(){{toast('sched-toast','Schedules saved')}})
 .catch(function(){{toast('sched-toast','Save failed',true)}});
}}
</script>""".format(
        items=items,
        next_id=max([s.get("id", 0) for s in schedules]) if schedules else 0,
    )
    return _layout("Schedule", body, "schedule")


def render_sound_page(presets):
    items = ""
    for p in presets:
        items += '<div class="preset-row"><div><span class="preset-name">{name}</span><span class="preset-cat">{cat}</span></div><button class="btn btn-secondary btn-sm" onclick="preview({id})">Play</button></div>'.format(
            id=p["id"], name=_escape_html(p["name"]), cat=p["category"])
    body = """<div class="section">
<h2>Sound Presets</h2>
<label>Preview Volume</label>
<div class="range-row">
<input type="range" id="snd-vol" min="0" max="100" value="50">
<span id="snd-vol-label">50%</span>
</div>
</div>
<div class="section">
<h2>Presets</h2>
{items}
</div>
<script>
document.getElementById('snd-vol').oninput=function(){{
 document.getElementById('snd-vol-label').textContent=this.value+'%';
}};
function preview(id){{
 api('POST','/api/sound/preview',{{preset_id:id,volume:parseInt(document.getElementById('snd-vol').value)}});
}}
</script>""".format(items=items)
    return _layout("Sound", body, "sound")


def render_system_page(wifi_status, system_config, version):
    body = """<div class="section">
<h2>WiFi</h2>
<div class="info-row"><span class="info-label">Status</span><span class="info-value">{connected}</span></div>
<div class="info-row"><span class="info-label">Network</span><span class="info-value">{ssid}</span></div>
<div class="info-row"><span class="info-label">IP Address</span><span class="info-value">{ip}</span></div>
<div class="info-row"><span class="info-label">Signal</span><span class="info-value">{rssi} dBm</span></div>
<div class="info-row"><span class="info-label">Time Sync</span><span class="info-value">{ntp}</span></div>
<div class="actions">
<a href="/wifi-setup" class="btn btn-secondary btn-sm">WiFi Settings</a>
</div>
</div>

<div class="section">
<h2>Display</h2>
<label>Brightness</label>
<div class="range-row">
<input type="range" id="sys-bright" min="0" max="100" value="{brightness}">
<span id="bright-label">{brightness}%</span>
</div>
</div>

<div class="section">
<h2>Device</h2>
<div class="info-row"><span class="info-label">Version</span><span class="info-value">{version}</span></div>
<div class="actions">
<button class="btn btn-secondary btn-sm" onclick="checkOta()">Check for Updates</button>
<button class="btn btn-secondary btn-sm" onclick="reboot()">Reboot</button>
</div>
<div id="sys-toast" class="toast"></div>
</div>
<script>
document.getElementById('sys-bright').oninput=function(){{
 document.getElementById('bright-label').textContent=this.value+'%';
 api('POST','/api/system/brightness',{{brightness:parseInt(this.value)}});
}};
function checkOta(){{
 toast('sys-toast','Checking for updates...');
 api('POST','/api/ota/check').then(function(r){{
  toast('sys-toast',r.status||r.error||'Done');
 }}).catch(function(){{toast('sys-toast','Check failed',true)}});
}}
function reboot(){{if(confirm('Reboot the device?'))api('POST','/api/system/reboot')}}
</script>""".format(
        connected="Connected" if wifi_status.get("connected") else "Disconnected",
        ssid=_escape_html(str(wifi_status.get("ssid", "-"))),
        ip=wifi_status.get("ip", "-"),
        rssi=wifi_status.get("rssi", "-"),
        ntp="Synced" if wifi_status.get("ntp_synced") else "Not synced",
        brightness=system_config.get("brightness", 50),
        version=_escape_html(str(version.get("version", "unknown"))),
    )
    return _layout("System", body, "system")


def render_wifi_setup_page(networks):
    options = ""
    for n in networks:
        options += '<option value="{ssid}">{ssid} ({rssi} dBm)</option>'.format(
            ssid=_escape_html(n["ssid"]), rssi=n["rssi"])
    body = """<div class="section">
<h2>WiFi Setup</h2>

<label>Select Network</label>
<select id="wifi-ssid">{options}<option value="">Enter manually...</option></select>

<label>Or type SSID</label>
<input type="text" id="wifi-ssid-manual" placeholder="Network name">

<label>Password</label>
<input type="password" id="wifi-pass" placeholder="WiFi password">

<div class="actions">
<button class="btn btn-primary" onclick="connectWifi()">Connect</button>
<button class="btn btn-secondary" onclick="scanWifi()">Rescan</button>
</div>
<div id="wifi-toast" class="toast"></div>
</div>
<script>
function connectWifi(){{
 var ssid=document.getElementById('wifi-ssid-manual').value||document.getElementById('wifi-ssid').value;
 var pw=document.getElementById('wifi-pass').value;
 if(!ssid){{toast('wifi-toast','Please select or enter a network',true);return}}
 toast('wifi-toast','Connecting...');
 api('POST','/api/wifi/connect',{{ssid:ssid,password:pw}}).then(function(r){{
  if(r.ip)toast('wifi-toast','Connected! IP: '+r.ip);
  else toast('wifi-toast',r.error||'Connection failed',true);
 }}).catch(function(){{toast('wifi-toast','Connection failed',true)}});
}}
function scanWifi(){{
 toast('wifi-toast','Scanning...');
 api('GET','/api/wifi/scan').then(function(nets){{
  var sel=document.getElementById('wifi-ssid');
  sel.innerHTML='';
  nets.forEach(function(n){{
   sel.innerHTML+='<option value="'+n.ssid+'">'+n.ssid+' ('+n.rssi+' dBm)</option>';
  }});
  sel.innerHTML+='<option value="">Enter manually...</option>';
  toast('wifi-toast','Found '+nets.length+' networks');
 }}).catch(function(){{toast('wifi-toast','Scan failed',true)}});
}}
</script>""".format(options=options)
    return _layout("WiFi Setup", body, "")


def _escape_html(s):
    """Basic HTML escaping."""
    return s.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;").replace('"', "&quot;")
