"""Minimal HTML templates for the web UI.

Templates are string functions to minimize RAM usage.
All pages share a common layout with navigation.
CSS is inline and minimal for the 2MB flash constraint.
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
<title>{title}</title>
<style>
*{{margin:0;padding:0;box-sizing:border-box}}
body{{font-family:system-ui,sans-serif;background:#1a1a2e;color:#eee;max-width:480px;margin:0 auto;padding:8px}}
nav{{display:flex;gap:4px;margin-bottom:12px;flex-wrap:wrap}}
nav a{{padding:6px 10px;background:#16213e;color:#aac;text-decoration:none;border-radius:4px;font-size:13px}}
nav a.active{{background:#0f3460;color:#fff}}
h1{{font-size:18px;margin-bottom:10px;color:#e94560}}
.card{{background:#16213e;padding:12px;border-radius:6px;margin-bottom:10px}}
label{{display:block;font-size:13px;color:#aac;margin:6px 0 2px}}
input[type=text],input[type=number],input[type=time],input[type=password],select{{
 width:100%;padding:6px;background:#0f3460;border:1px solid #333;color:#fff;border-radius:4px;font-size:14px}}
input[type=color]{{width:48px;height:32px;padding:0;border:none;background:none;cursor:pointer}}
input[type=range]{{width:100%}}
button{{padding:8px 16px;background:#e94560;color:#fff;border:none;border-radius:4px;cursor:pointer;font-size:14px;margin:4px 2px}}
button.secondary{{background:#0f3460}}
button:active{{opacity:0.7}}
.toggle{{display:flex;align-items:center;gap:8px}}
.toggle input{{width:auto}}
.schedule-item{{border:1px solid #333;padding:8px;border-radius:4px;margin:6px 0}}
.days{{display:flex;gap:4px;flex-wrap:wrap}}
.days label{{display:inline-flex;align-items:center;gap:2px;font-size:12px}}
.days input{{width:auto}}
.status{{font-size:12px;color:#7f8;margin:4px 0}}
.error{{color:#f77}}
.preset-list{{max-height:200px;overflow-y:auto}}
.preset-item{{padding:4px 8px;border-bottom:1px solid #222;display:flex;justify-content:space-between;align-items:center}}
</style>
</head><body>
<h1>{title}</h1>
<nav>
<a href="/" {nav_home}>Home</a>
<a href="/message" {nav_msg}>Message</a>
<a href="/schedule" {nav_sched}>Schedule</a>
<a href="/sound" {nav_sound}>Sound</a>
<a href="/system" {nav_sys}>System</a>
</nav>
{body}
<script>
function api(method,url,data){{
 return fetch(url,{{
  method:method,
  headers:{{'Content-Type':'application/json'}},
  body:data?JSON.stringify(data):undefined
 }}).then(r=>r.json());
}}
</script>
</body></html>""".format(
        title=title,
        body=body,
        nav_home='class="active"' if active_nav == "home" else "",
        nav_msg='class="active"' if active_nav == "message" else "",
        nav_sched='class="active"' if active_nav == "schedule" else "",
        nav_sound='class="active"' if active_nav == "sound" else "",
        nav_sys='class="active"' if active_nav == "system" else "",
    )


def render_index():
    body = """<div class="card">
<p>Galactic Unicorn LED Display</p>
<p style="margin-top:8px;font-size:13px;color:#aac">
Use the navigation above to configure your display.</p>
</div>"""
    return _layout("Galactic Unicorn", body, "home")


def render_message_page(message):
    color = message.get("color", {})
    color_hex = "#{:02x}{:02x}{:02x}".format(
        color.get("r", 255), color.get("g", 255), color.get("b", 255))
    body = """<div class="card">
<label>Text</label>
<input type="text" id="msg-text" value="{text}" maxlength="128">
<label>Display Mode</label>
<select id="msg-mode">
<option value="scroll" {sel_scroll}>Scroll</option>
<option value="fixed" {sel_fixed}>Fixed</option>
</select>
<label>Scroll Speed</label>
<select id="msg-speed">
<option value="slow" {sel_slow}>Slow</option>
<option value="medium" {sel_medium}>Medium</option>
<option value="fast" {sel_fast}>Fast</option>
</select>
<label>Color</label>
<input type="color" id="msg-color" value="{color_hex}">
<label>Font</label>
<select id="msg-font">
<option value="bitmap6" {sel_f6}>bitmap6 (small)</option>
<option value="bitmap8" {sel_f8}>bitmap8 (normal)</option>
</select>
<button onclick="saveMessage()" style="margin-top:10px">Save</button>
<div id="msg-status" class="status"></div>
</div>
<script>
function saveMessage(){{
 var c=document.getElementById('msg-color').value;
 var r=parseInt(c.substr(1,2),16),g=parseInt(c.substr(3,2),16),b=parseInt(c.substr(5,2),16);
 api('POST','/api/message',{{
  text:document.getElementById('msg-text').value,
  display_mode:document.getElementById('msg-mode').value,
  scroll_speed:document.getElementById('msg-speed').value,
  color:{{r:r,g:g,b:b}},
  font:document.getElementById('msg-font').value
 }}).then(function(){{document.getElementById('msg-status').textContent='Saved!'}});
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
    return _layout("Message Settings", body, "message")


def render_schedule_page(schedules):
    items = ""
    for s in schedules:
        days_checks = ""
        for d in ["mon", "tue", "wed", "thu", "fri", "sat", "sun"]:
            checked = "checked" if d in s.get("days", []) else ""
            days_checks += '<label><input type="checkbox" data-day="{d}" {ck}>{d}</label>'.format(
                d=d, ck=checked)
        sound = s.get("sound", {})
        items += """<div class="schedule-item" data-id="{id}">
<div class="toggle"><input type="checkbox" {enabled} onchange="toggleSchedule({id},this.checked)"><b>Schedule #{id}</b></div>
<label>Start</label><input type="time" class="sched-start" value="{start}">
<label>End</label><input type="time" class="sched-end" value="{end}">
<label>Days</label><div class="days">{days}</div>
<label>Sound</label>
<div class="toggle"><input type="checkbox" class="sched-sound-en" {sound_en}>Enabled (Preset #{preset_id}, Vol:{vol}%)</div>
<button class="secondary" onclick="deleteSchedule({id})">Delete</button>
</div>""".format(
            id=s.get("id", 0),
            enabled="checked" if s.get("enabled") else "",
            start=s.get("start_time", "00:00"),
            end=s.get("end_time", "23:59"),
            days=days_checks,
            sound_en="checked" if sound.get("enabled") else "",
            preset_id=sound.get("preset_id", 1),
            vol=sound.get("volume", 50),
        )

    body = """<div class="card">
<div id="schedules">{items}</div>
<button onclick="addSchedule()" style="margin-top:8px">Add Schedule</button>
<button onclick="saveSchedules()" style="margin-top:8px">Save All</button>
<div id="sched-status" class="status"></div>
</div>
<script>
var nextId={next_id};
function addSchedule(){{
 nextId++;
 var html='<div class="schedule-item" data-id="'+nextId+'">';
 html+='<div class="toggle"><input type="checkbox" checked><b>Schedule #'+nextId+'</b></div>';
 html+='<label>Start</label><input type="time" class="sched-start" value="08:00">';
 html+='<label>End</label><input type="time" class="sched-end" value="09:00">';
 html+='<label>Days</label><div class="days">';
 ["mon","tue","wed","thu","fri","sat","sun"].forEach(function(d){{
  html+='<label><input type="checkbox" data-day="'+d+'" checked>'+d+'</label>';
 }});
 html+='</div>';
 html+='<label>Sound</label><div class="toggle"><input type="checkbox" class="sched-sound-en">Enabled (Preset #1, Vol:50%)</div>';
 html+='<button class="secondary" onclick="deleteSchedule('+nextId+')">Delete</button></div>';
 document.getElementById('schedules').insertAdjacentHTML('beforeend',html);
}}
function deleteSchedule(id){{
 var el=document.querySelector('[data-id="'+id+'"]');
 if(el)el.remove();
}}
function toggleSchedule(id,en){{}}
function saveSchedules(){{
 var items=document.querySelectorAll('.schedule-item');
 var scheds=[];
 items.forEach(function(el){{
  var days=[];
  el.querySelectorAll('[data-day]').forEach(function(cb){{if(cb.checked)days.push(cb.dataset.day)}});
  var s={{
   id:parseInt(el.dataset.id),
   enabled:el.querySelector('.toggle input').checked,
   start_time:el.querySelector('.sched-start').value,
   end_time:el.querySelector('.sched-end').value,
   days:days,
   sound:{{
    enabled:el.querySelector('.sched-sound-en')?el.querySelector('.sched-sound-en').checked:false,
    preset_id:1,volume:50
   }}
  }};
  scheds.push(s);
 }});
 api('POST','/api/schedules',scheds).then(function(){{
  document.getElementById('sched-status').textContent='Saved!';
 }});
}}
</script>""".format(
        items=items,
        next_id=max([s.get("id", 0) for s in schedules]) if schedules else 0,
    )
    return _layout("Schedule Settings", body, "schedule")


def render_sound_page(presets):
    items = ""
    for p in presets:
        items += '<div class="preset-item"><span>#{id} {name} ({cat})</span><button class="secondary" onclick="preview({id})">Play</button></div>'.format(
            id=p["id"], name=_escape_html(p["name"]), cat=p["category"])
    body = """<div class="card">
<label>Volume</label>
<input type="range" id="snd-vol" min="0" max="100" value="50">
<span id="snd-vol-label">50%</span>
<label style="margin-top:8px">Presets</label>
<div class="preset-list">{items}</div>
</div>
<script>
document.getElementById('snd-vol').oninput=function(){{
 document.getElementById('snd-vol-label').textContent=this.value+'%';
}};
function preview(id){{
 api('POST','/api/sound/preview',{{preset_id:id,volume:parseInt(document.getElementById('snd-vol').value)}});
}}
</script>""".format(items=items)
    return _layout("Sound Settings", body, "sound")


def render_system_page(wifi_status, system_config, version):
    body = """<div class="card">
<h2 style="font-size:15px;margin-bottom:8px">WiFi</h2>
<p>Status: {connected}</p>
<p>SSID: {ssid}</p>
<p>IP: {ip}</p>
<p>Signal: {rssi} dBm</p>
<p>NTP: {ntp}</p>
<button class="secondary" onclick="location.href='/wifi-setup'" style="margin-top:6px">WiFi Settings</button>
</div>
<div class="card">
<h2 style="font-size:15px;margin-bottom:8px">Display</h2>
<label>Brightness</label>
<input type="range" id="sys-bright" min="0" max="100" value="{brightness}">
<span id="sys-bright-label">{brightness}%</span>
</div>
<div class="card">
<h2 style="font-size:15px;margin-bottom:8px">System</h2>
<p>Version: {version}</p>
<button class="secondary" onclick="checkOta()">Check for Updates</button>
<button class="secondary" onclick="reboot()">Reboot</button>
<div id="sys-status" class="status"></div>
</div>
<script>
document.getElementById('sys-bright').oninput=function(){{
 document.getElementById('sys-bright-label').textContent=this.value+'%';
 api('POST','/api/system/brightness',{{brightness:parseInt(this.value)}});
}};
function checkOta(){{
 document.getElementById('sys-status').textContent='Checking...';
 api('POST','/api/ota/check').then(function(r){{
  document.getElementById('sys-status').textContent=r.status||r.error||'Done';
 }});
}}
function reboot(){{
 if(confirm('Reboot device?'))api('POST','/api/system/reboot');
}}
</script>""".format(
        connected="Connected" if wifi_status.get("connected") else "Disconnected",
        ssid=_escape_html(str(wifi_status.get("ssid", "-"))),
        ip=wifi_status.get("ip", "-"),
        rssi=wifi_status.get("rssi", "-"),
        ntp="Synced" if wifi_status.get("ntp_synced") else "Not synced",
        brightness=system_config.get("brightness", 50),
        version=_escape_html(str(version.get("version", "unknown"))),
    )
    return _layout("System Settings", body, "system")


def render_wifi_setup_page(networks):
    options = ""
    for n in networks:
        options += '<option value="{ssid}">{ssid} ({rssi} dBm)</option>'.format(
            ssid=_escape_html(n["ssid"]), rssi=n["rssi"])
    body = """<div class="card">
<h2 style="font-size:15px;margin-bottom:8px">WiFi Setup</h2>
<label>Network</label>
<select id="wifi-ssid">{options}<option value="">Other...</option></select>
<label>Or enter SSID manually</label>
<input type="text" id="wifi-ssid-manual" placeholder="SSID">
<label>Password</label>
<input type="password" id="wifi-pass">
<button onclick="connectWifi()" style="margin-top:10px">Connect</button>
<button class="secondary" onclick="scanWifi()">Rescan</button>
<div id="wifi-status" class="status"></div>
</div>
<script>
function connectWifi(){{
 var ssid=document.getElementById('wifi-ssid-manual').value||document.getElementById('wifi-ssid').value;
 var pass=document.getElementById('wifi-pass').value;
 document.getElementById('wifi-status').textContent='Connecting...';
 api('POST','/api/wifi/connect',{{ssid:ssid,password:pass}}).then(function(r){{
  if(r.ip){{document.getElementById('wifi-status').textContent='Connected! IP: '+r.ip;}}
  else{{document.getElementById('wifi-status').textContent=r.error||'Failed';
   document.getElementById('wifi-status').className='error';}}
 }});
}}
function scanWifi(){{
 api('GET','/api/wifi/scan').then(function(nets){{
  var sel=document.getElementById('wifi-ssid');
  sel.innerHTML='';
  nets.forEach(function(n){{
   sel.innerHTML+='<option value="'+n.ssid+'">'+n.ssid+' ('+n.rssi+' dBm)</option>';
  }});
  sel.innerHTML+='<option value="">Other...</option>';
 }});
}}
</script>""".format(options=options)
    return _layout("WiFi Setup", body, "")


def _escape_html(s):
    """Basic HTML escaping."""
    return s.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;").replace('"', "&quot;")
