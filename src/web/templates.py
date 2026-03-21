"""HTML templates for the web UI.

Design: 2 pages + setup. Clean, white, minimal.
All CSS embedded. No external files.
"""

try:
    import ujson as json
except ImportError:
    import json


_CSS = """*{margin:0;padding:0;box-sizing:border-box}
body{font-family:-apple-system,system-ui,"Segoe UI",sans-serif;background:#f2f2f7;color:#1c1c1e;max-width:460px;margin:0 auto;padding:16px 12px;font-size:15px;line-height:1.4;-webkit-font-smoothing:antialiased}
h1{font-size:22px;font-weight:700;margin-bottom:16px}
.s{background:#fff;border-radius:12px;padding:16px;margin-bottom:12px}
.s h2{font-size:11px;font-weight:600;text-transform:uppercase;letter-spacing:0.8px;color:#8e8e93;margin-bottom:10px}
.status-on{color:#34c759;font-weight:600}
.status-off{color:#8e8e93}
.status-msg{font-size:17px;font-weight:600;margin:4px 0 2px;word-break:break-word}
.status-sub{font-size:13px;color:#8e8e93}
label{display:block;font-size:13px;color:#8e8e93;margin:10px 0 4px;font-weight:500}
input[type=text],input[type=password],input[type=time],select{width:100%;padding:10px 12px;background:#f2f2f7;border:1.5px solid #e5e5ea;border-radius:10px;font-size:15px;font-family:inherit;color:#1c1c1e;outline:none}
input:focus,select:focus{border-color:#007aff}
input[type=color]{width:40px;height:36px;padding:2px;border:1.5px solid #e5e5ea;border-radius:8px;background:#f2f2f7;cursor:pointer}
input[type=range]{width:100%;-webkit-appearance:none;appearance:none;height:6px;background:#e5e5ea;border-radius:3px;outline:none}
input[type=range]::-webkit-slider-thumb{-webkit-appearance:none;width:22px;height:22px;background:#fff;border:1.5px solid #d1d1d6;border-radius:50%;cursor:pointer;box-shadow:0 1px 3px rgba(0,0,0,0.15)}
input[type=checkbox]{width:18px;height:18px;accent-color:#007aff;vertical-align:middle;cursor:pointer}
.btn{display:inline-block;padding:10px 20px;border:none;border-radius:10px;font-size:15px;font-weight:500;font-family:inherit;cursor:pointer;text-decoration:none;text-align:center}
.btn:active{opacity:0.7}
.bp{background:#007aff;color:#fff}
.bs{background:#f2f2f7;color:#007aff}
.bd{background:#f2f2f7;color:#ff3b30}
.bsm{padding:7px 14px;font-size:13px}
.acts{display:flex;gap:8px;margin-top:12px;flex-wrap:wrap}
.row2{display:flex;gap:10px}
.row2>*{flex:1}
.rng{display:flex;align-items:center;gap:10px}
.rng input{flex:1}
.rng span{min-width:36px;text-align:right;font-size:13px;color:#8e8e93;font-variant-numeric:tabular-nums}
details{margin-top:8px}
summary{font-size:13px;color:#007aff;cursor:pointer;font-weight:500;list-style:none;-webkit-user-select:none;user-select:none}
summary::-webkit-details-marker{display:none}
summary::before{content:"\\25B6\\FE0E ";font-size:10px}
details[open]>summary::before{content:"\\25BC\\FE0E "}
.sc{border:1px solid #e5e5ea;border-radius:10px;padding:12px;margin-bottom:8px}
.sc-head{display:flex;justify-content:space-between;align-items:center}
.sc-head label{margin:0;font-size:15px;color:#1c1c1e;font-weight:500;display:flex;align-items:center;gap:6px}
.sc-time{font-size:14px;color:#1c1c1e;margin:6px 0 2px}
.sc-days{font-size:12px;color:#8e8e93}
.sc-sound{font-size:12px;color:#8e8e93;margin-top:2px}
.days-row{display:flex;gap:4px;flex-wrap:wrap;margin:4px 0}
.dt{display:flex;align-items:center;gap:3px;font-size:13px;padding:4px 0}
.dt input{width:15px;height:15px}
.ir{display:flex;justify-content:space-between;padding:10px 0;border-bottom:1px solid #f2f2f7;font-size:15px}
.ir:last-child{border-bottom:none}
.ir-l{color:#8e8e93}
.ir-v{font-weight:500}
.toast{font-size:13px;color:#34c759;min-height:18px;margin-top:6px}
.toast.err{color:#ff3b30}
.footer{text-align:center;padding:16px 0 8px}
.footer a{color:#8e8e93;font-size:13px;text-decoration:none}
.clock{font-size:28px;font-weight:300;font-variant-numeric:tabular-nums;letter-spacing:1px;color:#1c1c1e}
.clock-day{font-size:13px;color:#8e8e93;margin-left:6px;font-weight:400;letter-spacing:0}"""

_JS = """function api(m,u,d){return fetch(u,{method:m,headers:{'Content-Type':'application/json'},body:d?JSON.stringify(d):undefined}).then(function(r){return r.json()})}
function toast(id,msg,err){var e=document.getElementById(id);if(!e)return;e.textContent=msg;e.className=err?'toast err':'toast';if(!err)setTimeout(function(){e.textContent=''},3000)}
function esc(s){var d=document.createElement('div');d.textContent=s;return d.innerHTML}"""


def _page(title, body):
    return '<!DOCTYPE html><html><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>{t}</title><style>{c}</style></head><body><h1>{t}</h1>{b}<script>{j}</script></body></html>'.format(
        t=title, b=body, c=_CSS, j=_JS)


def render_main_page(config, presets, status):
    msg = config.get("message", {})
    schedules = config.get("schedules", [])
    system = config.get("system", {})
    color = msg.get("color", {})
    color_hex = "#{:02x}{:02x}{:02x}".format(
        color.get("r", 255), color.get("g", 255), color.get("b", 255))

    # Status section
    time_str = status.get("time", "--:--:--")
    day_str = status.get("day", "")
    clock_html = '<div class="clock"><span id="clock-time">{time}</span><span class="clock-day" id="clock-day">{day}</span></div>'.format(
        time=time_str, day=day_str)

    if status.get("active"):
        status_html = '{clock}<div class="status-on" id="st-label">Displaying</div><div class="status-msg" id="st-msg">{msg}</div><div class="status-sub" id="st-sub">Until {end}</div>'.format(
            clock=clock_html, msg=_esc(status.get("message", "")), end=status.get("active_end", ""))
    elif status.get("next_start"):
        status_html = '{clock}<div class="status-off" id="st-label">Off</div><div class="status-msg" id="st-msg">{msg}</div><div class="status-sub" id="st-sub">Next: {day} {time}</div>'.format(
            clock=clock_html, msg=_esc(status.get("message", "")), day=status.get("next_day", ""), time=status.get("next_start", ""))
    else:
        status_html = '{clock}<div class="status-off" id="st-label">Off</div><div class="status-msg" id="st-msg">{msg}</div><div class="status-sub" id="st-sub">No schedules set</div>'.format(
            clock=clock_html, msg=_esc(status.get("message", "")))

    # Schedule items
    sched_items = ""
    for s in schedules:
        days_str = ", ".join([d.capitalize() for d in s.get("days", [])])
        sound = s.get("sound", {})
        sound_name = ""
        if sound.get("enabled"):
            for p in presets:
                if p["id"] == sound.get("preset_id", 0):
                    sound_name = p["name"]
                    break

        # Expanded edit area
        days_checks = ""
        for d in ["mon", "tue", "wed", "thu", "fri", "sat", "sun"]:
            ck = "checked" if d in s.get("days", []) else ""
            days_checks += '<span class="dt"><input type="checkbox" data-day="{d}" {ck}>{dl}</span>'.format(
                d=d, ck=ck, dl=d.capitalize())

        preset_opts = ""
        for p in presets:
            sel = "selected" if p["id"] == sound.get("preset_id", 1) else ""
            preset_opts += '<option value="{id}" {sel}>{name}</option>'.format(
                id=p["id"], sel=sel, name=_esc(p["name"]))

        chk = "checked" if s.get("enabled") else ""
        sound_chk = "checked" if sound.get("enabled") else ""

        sched_items += """<div class="sc" data-id="{id}">
<div class="sc-head"><label><input type="checkbox" class="sc-en" {chk}><span class="sc-time">{start} - {end}</span></label></div>
<div class="sc-days">{days_str}</div>
{sound_line}
<details><summary>Edit</summary>
<div class="row2" style="margin-top:8px"><div><label>Start</label><input type="time" class="sc-start" value="{start}"></div><div><label>End</label><input type="time" class="sc-end" value="{end}"></div></div>
<label>Days</label><div class="days-row">{days_checks}</div>
<label style="display:flex;align-items:center;gap:6px;color:#1c1c1e;margin-top:8px"><input type="checkbox" class="sc-snd-en" {sound_chk}> Sound</label>
<div class="row2"><div><label>Preset</label><select class="sc-preset">{preset_opts}</select></div><div><label>Volume</label><select class="sc-vol"><option value="25" {v25}>25%</option><option value="50" {v50}>50%</option><option value="75" {v75}>75%</option><option value="100" {v100}>100%</option></select></div></div>
<button class="btn bs bsm" onclick="playSnd(this)" style="margin-top:8px">Preview sound</button>
<div class="acts"><button class="btn bd bsm" onclick="delSc({id})">Remove</button></div>
</details></div>""".format(
            id=s.get("id", 0),
            chk=chk,
            start=s.get("start_time", "00:00"),
            end=s.get("end_time", "23:59"),
            days_str=days_str if days_str else "Every day",
            sound_line='<div class="sc-sound">Sound: {}</div>'.format(_esc(sound_name)) if sound_name else "",
            days_checks=days_checks,
            sound_chk=sound_chk,
            preset_opts=preset_opts,
            v25="selected" if sound.get("volume", 50) == 25 else "",
            v50="selected" if sound.get("volume", 50) == 50 else "",
            v75="selected" if sound.get("volume", 50) == 75 else "",
            v100="selected" if sound.get("volume", 50) == 100 else "",
        )

    body = """<div class="s">
<h2>Now</h2>
{status}
</div>

<div class="s">
<h2>Message</h2>
<input type="text" id="msg-text" value="{text}" maxlength="128" placeholder="Enter message">
<div class="acts"><button class="btn bp" onclick="saveMsg()">Save</button></div>
<div id="msg-toast" class="toast"></div>
<details style="margin-top:10px"><summary>Options</summary>
<div class="row2" style="margin-top:8px">
<div><label>Mode</label><select id="msg-mode"><option value="scroll" {sel_scroll}>Scroll</option><option value="fixed" {sel_fixed}>Fixed</option></select></div>
<div><label>Speed</label><select id="msg-speed"><option value="slow" {sel_slow}>Slow</option><option value="medium" {sel_medium}>Medium</option><option value="fast" {sel_fast}>Fast</option></select></div>
</div>
<div class="row2">
<div><label>Font</label><select id="msg-font"><option value="bitmap6" {sel_f6}>Small</option><option value="bitmap8" {sel_f8}>Normal</option></select></div>
<div><label>Color</label><input type="color" id="msg-color" value="{color_hex}"></div>
</div>
</details>
</div>

<div class="s">
<h2>Schedule</h2>
<div id="scheds">{sched_items}</div>
<div class="acts">
<button class="btn bs" onclick="addSc()">Add schedule</button>
<button class="btn bp" onclick="saveSc()">Save</button>
</div>
<div id="sc-toast" class="toast"></div>
</div>

<div class="s">
<h2>Quick Settings</h2>
<label>Brightness</label>
<div class="rng"><input type="range" id="q-bright" min="0" max="100" value="{brightness}" oninput="setBright(this.value)"><span id="q-bright-v">{brightness}%</span></div>
<label>Volume</label>
<div class="rng"><input type="range" id="q-vol" min="0" max="100" value="50" oninput="setVol(this.value)"><span id="q-vol-v">50%</span></div>
</div>

<div class="footer"><a href="/settings">Device Settings</a></div>

<script>
function saveMsg(){{
 var c=document.getElementById('msg-color').value;
 api('POST','/api/message',{{
  text:document.getElementById('msg-text').value,
  display_mode:document.getElementById('msg-mode').value,
  scroll_speed:document.getElementById('msg-speed').value,
  color:{{r:parseInt(c.substr(1,2),16),g:parseInt(c.substr(3,2),16),b:parseInt(c.substr(5,2),16)}},
  font:document.getElementById('msg-font').value
 }}).then(function(){{toast('msg-toast','Saved')}}).catch(function(){{toast('msg-toast','Failed',1)}});
}}
var nid={next_id};
function addSc(){{
 nid++;
 var h='<div class="sc" data-id="'+nid+'"><div class="sc-head"><label><input type="checkbox" class="sc-en" checked><span class="sc-time">08:00 - 09:00</span></label></div><div class="sc-days">Every day</div>';
 h+='<details open><summary>Edit</summary><div class="row2" style="margin-top:8px"><div><label>Start</label><input type="time" class="sc-start" value="08:00"></div><div><label>End</label><input type="time" class="sc-end" value="09:00"></div></div>';
 h+='<label>Days</label><div class="days-row">';
 ['mon','tue','wed','thu','fri','sat','sun'].forEach(function(d){{h+='<span class="dt"><input type="checkbox" data-day="'+d+'" checked>'+d.charAt(0).toUpperCase()+d.slice(1)+'</span>'}});
 h+='</div><label style="display:flex;align-items:center;gap:6px;color:#1c1c1e;margin-top:8px"><input type="checkbox" class="sc-snd-en"> Sound</label>';
 h+='<div class="row2"><div><label>Preset</label><select class="sc-preset">{popts}</select></div><div><label>Volume</label><select class="sc-vol"><option value="25">25%</option><option value="50" selected>50%</option><option value="75">75%</option><option value="100">100%</option></select></div></div>';
 h+='<button class="btn bs bsm" onclick="playSnd(this)" style="margin-top:8px">Preview sound</button>';
 h+='<div class="acts"><button class="btn bd bsm" onclick="delSc('+nid+')">Remove</button></div></details></div>';
 document.getElementById('scheds').insertAdjacentHTML('beforeend',h);
}}
function delSc(id){{var e=document.querySelector('[data-id="'+id+'"]');if(e)e.remove()}}
function saveSc(){{
 var a=[];
 document.querySelectorAll('.sc').forEach(function(el){{
  var days=[];el.querySelectorAll('[data-day]').forEach(function(c){{if(c.checked)days.push(c.dataset.day)}});
  a.push({{id:parseInt(el.dataset.id),enabled:el.querySelector('.sc-en').checked,start_time:el.querySelector('.sc-start').value,end_time:el.querySelector('.sc-end').value,days:days,sound:{{enabled:el.querySelector('.sc-snd-en')?el.querySelector('.sc-snd-en').checked:false,preset_id:parseInt(el.querySelector('.sc-preset')?el.querySelector('.sc-preset').value:1),volume:parseInt(el.querySelector('.sc-vol')?el.querySelector('.sc-vol').value:50)}}}});
 }});
 api('POST','/api/schedules',a).then(function(){{toast('sc-toast','Saved')}}).catch(function(){{toast('sc-toast','Failed',1)}});
}}
function playSnd(btn){{
 var el=btn.closest('.sc');
 var pid=parseInt(el.querySelector('.sc-preset').value);
 var vol=parseInt(el.querySelector('.sc-vol').value);
 api('POST','/api/sound/preview',{{preset_id:pid,volume:vol}});
}}
function setBright(v){{document.getElementById('q-bright-v').textContent=v+'%';api('POST','/api/system/brightness',{{brightness:parseInt(v)}})}}
function setVol(v){{document.getElementById('q-vol-v').textContent=v+'%';api('POST','/api/system/volume',{{volume:parseInt(v)}})}}
(function pollStatus(){{
 api('GET','/api/status').then(function(s){{
  if(s.time)document.getElementById('clock-time').textContent=s.time;
  if(s.day)document.getElementById('clock-day').textContent=s.day;
  var lbl=document.getElementById('st-label');
  var sub=document.getElementById('st-sub');
  if(s.active){{lbl.textContent='Displaying';lbl.className='status-on';sub.textContent='Until '+s.active_end}}
  else if(s.next_start){{lbl.textContent='Off';lbl.className='status-off';sub.textContent='Next: '+s.next_day+' '+s.next_start}}
  else{{lbl.textContent='Off';lbl.className='status-off';sub.textContent='No schedules set'}}
  document.getElementById('st-msg').textContent=s.message||'';
 }}).catch(function(){{}});
 setTimeout(pollStatus,1000);
}})();
</script>""".format(
        status=status_html,
        text=_esc(msg.get("text", "")),
        color_hex=color_hex,
        sel_scroll='selected' if msg.get("display_mode") == "scroll" else "",
        sel_fixed='selected' if msg.get("display_mode") == "fixed" else "",
        sel_slow='selected' if msg.get("scroll_speed") == "slow" else "",
        sel_medium='selected' if msg.get("scroll_speed") == "medium" else "",
        sel_fast='selected' if msg.get("scroll_speed") == "fast" else "",
        sel_f6='selected' if msg.get("font") == "bitmap6" else "",
        sel_f8='selected' if msg.get("font") == "bitmap8" else "",
        sched_items=sched_items,
        next_id=max([s.get("id", 0) for s in schedules]) if schedules else 0,
        brightness=system.get("brightness", 50),
        popts=_preset_options(presets, 1),
    )
    return _page("Galactic Unicorn", body)


def render_settings_page(wifi_status, version, free_mem):
    body = """<div class="s">
<h2>WiFi</h2>
<div class="ir"><span class="ir-l">Status</span><span class="ir-v">{connected}</span></div>
<div class="ir"><span class="ir-l">Network</span><span class="ir-v">{ssid}</span></div>
<div class="ir"><span class="ir-l">IP Address</span><span class="ir-v">{ip}</span></div>
<div class="ir"><span class="ir-l">Signal</span><span class="ir-v">{rssi} dBm</span></div>
<details style="margin-top:8px"><summary>Change WiFi</summary>
<label>Network</label>
<select id="wifi-ssid"><option value="">Scanning...</option></select>
<label>Password</label>
<input type="password" id="wifi-pass" placeholder="WiFi password">
<div class="acts">
<button class="btn bp bsm" onclick="connectWifi()">Connect</button>
<button class="btn bs bsm" onclick="scanWifi()">Rescan</button>
</div>
<div id="wifi-toast" class="toast"></div>
</details>
</div>

<div class="s">
<h2>Device</h2>
<div class="ir"><span class="ir-l">Version</span><span class="ir-v">{version}</span></div>
<div class="ir"><span class="ir-l">Free Memory</span><span class="ir-v">{mem} KB</span></div>
<div class="ir"><span class="ir-l">Time Sync</span><span class="ir-v">{ntp}</span></div>
<div class="acts">
<button class="btn bs bsm" onclick="checkOta()">Check for updates</button>
<button class="btn bs bsm" onclick="reboot()">Reboot</button>
</div>
<div id="sys-toast" class="toast"></div>
</div>

<div class="footer"><a href="/">Back</a></div>

<script>
scanWifi();
function scanWifi(){{
 api('GET','/api/wifi/scan').then(function(nets){{
  var s=document.getElementById('wifi-ssid');s.innerHTML='';
  nets.forEach(function(n){{var o=document.createElement('option');o.value=n.ssid;o.textContent=n.ssid+' ('+n.rssi+' dBm)';s.appendChild(o)}});
  var o=document.createElement('option');o.value='';o.textContent='Enter manually...';s.appendChild(o);
 }}).catch(function(){{}});
}}
function connectWifi(){{
 var ssid=document.getElementById('wifi-ssid').value;
 var pw=document.getElementById('wifi-pass').value;
 if(!ssid){{toast('wifi-toast','Select a network',1);return}}
 toast('wifi-toast','Connecting...');
 api('POST','/api/wifi/connect',{{ssid:ssid,password:pw}}).then(function(r){{
  if(r.ip)toast('wifi-toast','Connected! IP: '+r.ip);
  else toast('wifi-toast',r.error||'Failed',1);
 }}).catch(function(){{toast('wifi-toast','Failed',1)}});
}}
function checkOta(){{
 toast('sys-toast','Checking...');
 api('POST','/api/ota/check').then(function(r){{toast('sys-toast',r.status||r.error||'Done')}}).catch(function(){{toast('sys-toast','Failed',1)}});
}}
function reboot(){{if(confirm('Reboot device?'))api('POST','/api/system/reboot')}}
</script>""".format(
        connected="Connected" if wifi_status.get("connected") else "Disconnected",
        ssid=_esc(str(wifi_status.get("ssid", "-"))),
        ip=wifi_status.get("ip", "-"),
        rssi=wifi_status.get("rssi", "-"),
        version=_esc(str(version.get("version", "unknown"))),
        mem=free_mem // 1024 if free_mem else "-",
        ntp="Synced" if wifi_status.get("ntp_synced") else "Not synced",
    )
    return _page("Device Settings", body)


def render_setup_page(networks):
    options = ""
    for n in networks:
        options += '<option value="{ssid}">{ssid} ({rssi} dBm)</option>'.format(
            ssid=_esc(n["ssid"]), rssi=n["rssi"])
    body = """<div class="s">
<p style="color:#8e8e93;margin-bottom:16px">Select your WiFi network to get started.</p>
<label>Network</label>
<select id="wifi-ssid">{options}<option value="">Enter manually...</option></select>
<label>Password</label>
<input type="password" id="wifi-pass" placeholder="WiFi password">
<div class="acts"><button class="btn bp" onclick="connectWifi()">Connect</button></div>
<div id="wifi-toast" class="toast"></div>
</div>
<script>
function connectWifi(){{
 var ssid=document.getElementById('wifi-ssid').value;
 var pw=document.getElementById('wifi-pass').value;
 if(!ssid){{toast('wifi-toast','Select a network',1);return}}
 toast('wifi-toast','Connecting...');
 api('POST','/api/wifi/connect',{{ssid:ssid,password:pw}}).then(function(r){{
  if(r.status=='saved')toast('wifi-toast','WiFi saved! Rebooting device...');
  else toast('wifi-toast',r.error||'Failed',1);
 }}).catch(function(){{toast('wifi-toast','Failed',1)}});
}}
</script>""".format(options=options)
    return _page("Welcome", body)


def _esc(s):
    """Basic HTML escaping."""
    return s.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;").replace('"', "&quot;")


def _preset_options(presets, selected_id):
    """Generate <option> tags for preset dropdown."""
    r = ""
    for p in presets:
        sel = "selected" if p["id"] == selected_id else ""
        r += '<option value="{id}" {sel}>{name}</option>'.format(
            id=p["id"], sel=sel, name=_esc(p["name"]))
    return r
