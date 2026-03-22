"""HTML templates for the web UI.

Streaming design: each render function is an async generator that yields
small HTML chunks. This avoids building the entire page in RAM at once.
"""

try:
    import ujson as json
except ImportError:
    import json


_HEAD = '<!DOCTYPE html><html><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>{}</title><style>'
_CSS1 = """*{margin:0;padding:0;box-sizing:border-box}
body{font-family:-apple-system,system-ui,sans-serif;background:#f2f2f7;color:#1c1c1e;max-width:460px;margin:0 auto;padding:16px 12px;font-size:15px;line-height:1.4}
h1{font-size:22px;font-weight:700;margin-bottom:16px}
.s{background:#fff;border-radius:12px;padding:16px;margin-bottom:12px}
.s h2{font-size:11px;font-weight:600;text-transform:uppercase;letter-spacing:.8px;color:#8e8e93;margin-bottom:10px}
.status-on{color:#34c759;font-weight:600}.status-off{color:#8e8e93}
.status-msg{font-size:17px;font-weight:600;margin:4px 0 2px;word-break:break-word}
.status-sub{font-size:13px;color:#8e8e93}
label{display:block;font-size:13px;color:#8e8e93;margin:10px 0 4px;font-weight:500}
input[type=text],input[type=password],input[type=time],select{width:100%;padding:10px 12px;background:#f2f2f7;border:1.5px solid #e5e5ea;border-radius:10px;font-size:15px;font-family:inherit;color:#1c1c1e;outline:none}
input:focus,select:focus{border-color:#007aff}
input[type=color]{width:40px;height:36px;padding:2px;border:1.5px solid #e5e5ea;border-radius:8px;background:#f2f2f7}
input[type=range]{width:100%;-webkit-appearance:none;height:6px;background:#e5e5ea;border-radius:3px;outline:none}
input[type=range]::-webkit-slider-thumb{-webkit-appearance:none;width:22px;height:22px;background:#fff;border:1.5px solid #d1d1d6;border-radius:50%;box-shadow:0 1px 3px rgba(0,0,0,.15)}
input[type=checkbox]{width:18px;height:18px;accent-color:#007aff;vertical-align:middle}"""
_CSS2 = """.btn{display:inline-block;padding:10px 20px;border:none;border-radius:10px;font-size:15px;font-weight:500;font-family:inherit;cursor:pointer;text-decoration:none}
.btn:active{opacity:.7}.bp{background:#007aff;color:#fff}.bs{background:#f2f2f7;color:#007aff}.bd{background:#f2f2f7;color:#ff3b30}.bsm{padding:7px 14px;font-size:13px}
.acts{display:flex;gap:8px;margin-top:12px;flex-wrap:wrap}
.row2{display:flex;gap:10px}.row2>*{flex:1}
.rng{display:flex;align-items:center;gap:10px}.rng input{flex:1}.rng span{min-width:36px;text-align:right;font-size:13px;color:#8e8e93}
details{margin-top:8px}summary{font-size:13px;color:#007aff;cursor:pointer;font-weight:500;list-style:none}
summary::-webkit-details-marker{display:none}summary::before{content:"\\25B6\\FE0E ";font-size:10px}details[open]>summary::before{content:"\\25BC\\FE0E "}
.sc{border:1px solid #e5e5ea;border-radius:10px;padding:12px;margin-bottom:8px}
.sc-head label{margin:0;font-size:15px;color:#1c1c1e;font-weight:500;display:flex;align-items:center;gap:6px}
.sc-days{font-size:12px;color:#8e8e93}
.days-row{display:flex;gap:4px;flex-wrap:wrap;margin:4px 0}
.dt{display:flex;align-items:center;gap:3px;font-size:13px;padding:4px 0}.dt input{width:15px;height:15px}
.ir{display:flex;justify-content:space-between;padding:10px 0;border-bottom:1px solid #f2f2f7;font-size:15px}.ir:last-child{border-bottom:none}.ir-l{color:#8e8e93}.ir-v{font-weight:500}
.toast{font-size:13px;color:#34c759;min-height:18px;margin-top:6px}.toast.err{color:#ff3b30}
.footer{text-align:center;padding:16px 0 8px}.footer a{color:#8e8e93;font-size:13px;text-decoration:none}
.clock{font-size:28px;font-weight:300;font-variant-numeric:tabular-nums;letter-spacing:1px}.clock-day{font-size:13px;color:#8e8e93;margin-left:6px;font-weight:400;letter-spacing:0}"""

_JS_COMMON = """function api(m,u,d){return fetch(u,{method:m,headers:{'Content-Type':'application/json'},body:d?JSON.stringify(d):undefined}).then(function(r){return r.json()})}
function toast(id,msg,err){var e=document.getElementById(id);if(!e)return;e.textContent=msg;e.className=err?'toast err':'toast';if(!err)setTimeout(function(){e.textContent=''},3000)}
function esc(s){var d=document.createElement('div');d.textContent=s;return d.innerHTML}"""


def _head(title):
    return _HEAD.format(title)


def _mid(title):
    return '</style></head><body><h1>{}</h1>'.format(title)


def _foot(js=""):
    return '<script>{}{}</script></body></html>'.format(_JS_COMMON, js)


async def render_main_page(config, presets, status):
    msg = config.get("message", {})
    schedules = config.get("schedules", [])
    system = config.get("system", {})
    color = msg.get("color", {})
    ch = "#{:02x}{:02x}{:02x}".format(color.get("r", 255), color.get("g", 255), color.get("b", 255))

    # Head
    yield _head("Galactic Unicorn")
    yield _CSS1
    yield _CSS2
    yield _mid("Galactic Unicorn")

    # Status section
    t = status.get("time", "--:--:--")
    d = status.get("day", "")
    yield '<div class="s"><h2>Now</h2><div class="clock"><span id="clock-time">{}</span><span class="clock-day" id="clock-day">{}</span></div>'.format(t, d)
    if status.get("active"):
        yield '<div class="status-on" id="st-label">Displaying</div><div class="status-msg" id="st-msg">{}</div><div class="status-sub" id="st-sub">Until {}</div></div>'.format(
            _esc(status.get("message", "")), status.get("active_end", ""))
    elif status.get("next_start"):
        yield '<div class="status-off" id="st-label">Off</div><div class="status-msg" id="st-msg">{}</div><div class="status-sub" id="st-sub">Next: {} {}</div></div>'.format(
            _esc(status.get("message", "")), status.get("next_day", ""), status.get("next_start", ""))
    else:
        yield '<div class="status-off" id="st-label">Off</div><div class="status-msg" id="st-msg">{}</div><div class="status-sub" id="st-sub">No schedules set</div></div>'.format(
            _esc(status.get("message", "")))

    # Message section
    yield '<div class="s"><h2>Message</h2><input type="text" id="msg-text" value="{}" maxlength="128" placeholder="Enter message"><div class="acts"><button class="btn bp" onclick="saveMsg()">Save</button></div><div id="msg-toast" class="toast"></div>'.format(_esc(msg.get("text", "")))
    yield '<details style="margin-top:10px"><summary>Options</summary><div class="row2" style="margin-top:8px"><div><label>Mode</label><select id="msg-mode"><option value="scroll" {}>Scroll</option><option value="fixed" {}>Fixed</option></select></div><div><label>Speed</label><select id="msg-speed"><option value="slow" {}>Slow</option><option value="medium" {}>Medium</option><option value="fast" {}>Fast</option></select></div></div>'.format(
        'selected' if msg.get("display_mode") == "scroll" else "",
        'selected' if msg.get("display_mode") == "fixed" else "",
        'selected' if msg.get("scroll_speed") == "slow" else "",
        'selected' if msg.get("scroll_speed") == "medium" else "",
        'selected' if msg.get("scroll_speed") == "fast" else "")
    yield '<div class="row2"><div><label>Font</label><select id="msg-font"><option value="bitmap6" {}>Small (6px)</option><option value="bitmap8" {}>Normal (8px)</option><option value="font11" {}>Large (11px)</option></select></div><div><label>Color</label><input type="color" id="msg-color" value="{}"></div></div></details></div>'.format(
        'selected' if msg.get("font") == "bitmap6" else "",
        'selected' if msg.get("font") == "bitmap8" else "",
        'selected' if msg.get("font") == "font11" else "",
        ch)

    # Schedule section — data passed via JS variable, not HTML data-* attributes
    yield '<div class="s"><h2>Schedule</h2><div id="scheds"></div><div class="acts"><button class="btn bs" onclick="addSc()">Add schedule</button><button class="btn bp" onclick="saveSc()">Save</button></div><div id="sc-toast" class="toast"></div></div>'

    # Compact schedule data as JS arrays: [id,start,end,enabled,sndEn,preset,vol,message,color]
    sd = []
    for s in schedules:
        snd = s.get("sound", {})
        sc_color = s.get("color", {})
        color_hex = ""
        if sc_color and (sc_color.get("r", 0) or sc_color.get("g", 0) or sc_color.get("b", 0)):
            color_hex = "#{:02x}{:02x}{:02x}".format(sc_color.get("r", 255), sc_color.get("g", 255), sc_color.get("b", 255))
        sd.append("[{},{},{},{},{},{},{},{},{}]".format(
            s.get("id", 0),
            '"' + s.get("start_time", "00:00") + '"',
            '"' + s.get("end_time", "23:59") + '"',
            1 if s.get("enabled") else 0,
            1 if snd.get("enabled") else 0,
            snd.get("preset_id", 1),
            snd.get("volume", 50),
            '"' + _esc(s.get("message", "")) + '"',
            '"' + color_hex + '"',
        ))
    dd = []
    for s in schedules:
        dd.append('"' + ",".join(s.get("days", [])) + '"')
    sched_data = "[" + ",".join(sd) + "]"
    days_data = "[" + ",".join(dd) + "]"

    # Quick settings
    br = system.get("brightness", 50)
    yield '<div class="s"><h2>Quick Settings</h2><label>Brightness</label><div class="rng"><input type="range" id="q-bright" min="0" max="100" value="{}" oninput="setBright(this.value)"><span id="q-bright-v">{}%</span></div><label>Volume</label><div class="rng"><input type="range" id="q-vol" min="0" max="100" value="50" oninput="setVol(this.value)"><span id="q-vol-v">50%</span></div></div>'.format(br, br)
    yield '<div class="footer"><a href="/settings">Device Settings</a></div>'

    # Preset data as compact JS array
    pa = "[" + ",".join(['[{},"{}"]'.format(p["id"], _esc(p["name"])) for p in presets]) + "]"
    nid = max([s.get("id", 0) for s in schedules]) if schedules else 0

    # JS in chunks to avoid large string allocation
    yield '<script>' + _JS_COMMON
    yield '\nvar P={},nid={},S={},SD={};'.format(pa, nid, sched_data, days_data)
    yield """
function popts(sel,sid){sel.innerHTML='';P.forEach(function(p){var o=document.createElement('option');o.value=p[0];o.textContent=p[1];if(p[0]==sid)o.selected=true;sel.appendChild(o)})}
function saveMsg(){var c=document.getElementById('msg-color').value;api('POST','/api/message',{text:document.getElementById('msg-text').value,display_mode:document.getElementById('msg-mode').value,scroll_speed:document.getElementById('msg-speed').value,color:{r:parseInt(c.substr(1,2),16),g:parseInt(c.substr(3,2),16),b:parseInt(c.substr(5,2),16)},font:document.getElementById('msg-font').value}).then(function(){toast('msg-toast','Saved')}).catch(function(){toast('msg-toast','Failed',1)})}"""
    yield """
function scEdit(el){if(el.querySelector('details'))return;var d=el.dataset;var h='<details open><summary>Edit</summary><label style="margin-top:8px">Message</label><input type="text" class="sc-msg" value="'+esc(d.msg||'')+'" maxlength="128" placeholder="Message for this schedule"><div class="row2" style="margin-top:0"><div><label>Color</label><input type="color" class="sc-color" value="'+(d.color||'#ffffff')+'"></div></div><div class="row2" style="margin-top:0"><div><label>Start</label><input type="time" class="sc-start" value="'+d.start+'"></div><div><label>End</label><input type="time" class="sc-end" value="'+d.end+'"></div></div><label>Days</label><div class="days-row">';var ds=(d.days||'').split(',');['mon','tue','wed','thu','fri','sat','sun'].forEach(function(x){h+='<span class="dt"><input type="checkbox" data-day="'+x+'" '+(ds.indexOf(x)>=0?'checked':'')+'>'+x.charAt(0).toUpperCase()+x.slice(1)+'</span>'});h+='</div><label style="display:flex;align-items:center;gap:6px;color:#1c1c1e;margin-top:8px"><input type="checkbox" class="sc-snd-en" '+(d.sndEn=="1"?"checked":"")+'>Sound</label><div class="row2"><div><label>Preset</label><select class="sc-preset"></select></div><div><label>Volume</label><select class="sc-vol"><option value="25">25%</option><option value="50">50%</option><option value="75">75%</option><option value="100">100%</option></select></div></div><button class="btn bs bsm" onclick="playSnd(this)" style="margin-top:8px">Preview</button><div class="acts"><button class="btn bd bsm" onclick="delSc('+d.id+')">Remove</button></div></details>';el.insertAdjacentHTML('beforeend',h);popts(el.querySelector('.sc-preset'),parseInt(d.preset));var vs=el.querySelector('.sc-vol');if(vs)vs.value=d.vol}
function renderSc(){var c=document.getElementById('scheds');c.innerHTML='';S.forEach(function(s,i){var id=s[0],st=s[1],en=s[2],on=s[3],se=s[4],pi=s[5],vo=s[6],msg=s[7]||'',col=s[8]||'',ds=SD[i];var dd=ds?ds.split(',').map(function(x){return x.charAt(0).toUpperCase()+x.slice(1)}).join(', '):'Every day';var el=document.createElement('div');el.className='sc';el.dataset.id=id;el.dataset.start=st;el.dataset.end=en;el.dataset.en=on;el.dataset.sndEn=se;el.dataset.preset=pi;el.dataset.vol=vo;el.dataset.days=ds;el.dataset.msg=msg;el.dataset.color=col;var title=msg?esc(msg):'(no message)';var cdot=col?'<span style="display:inline-block;width:10px;height:10px;border-radius:50%;background:'+col+';margin-right:6px;vertical-align:middle"></span>':'';el.innerHTML='<div class="sc-head"><label><input type="checkbox" class="sc-en" '+(on?'checked':'')+'>'+cdot+' <span style="font-weight:600">'+title+'</span></label></div><div class="sc-days" style="color:#8e8e93;font-size:12px">'+st+' - '+en+' / '+dd+'</div>';el.querySelector('.sc-head').addEventListener('click',function(e){if(e.target.type!='checkbox')scEdit(el)});c.appendChild(el);if(id>nid)nid=id})}
renderSc()"""
    yield """
function addSc(){nid++;var el=document.createElement('div');el.className='sc';el.dataset.id=nid;el.dataset.start='08:00';el.dataset.end='09:00';el.dataset.en='1';el.dataset.sndEn='0';el.dataset.preset='1';el.dataset.vol='50';el.dataset.days='mon,tue,wed,thu,fri,sat,sun';el.dataset.msg='';el.dataset.color='';el.innerHTML='<div class="sc-head"><label><input type="checkbox" class="sc-en" checked><span>08:00 - 09:00</span></label></div><div class="sc-days">Every day</div>';document.getElementById('scheds').appendChild(el);scEdit(el)}
function delSc(id){var e=document.querySelector('[data-id="'+id+'"]');if(e)e.remove()}
function parseColor(hex){if(!hex||hex.length<7)return{};return{r:parseInt(hex.substr(1,2),16),g:parseInt(hex.substr(3,2),16),b:parseInt(hex.substr(5,2),16)}}
function saveSc(){var a=[];document.querySelectorAll('.sc').forEach(function(el){var d=el.dataset;var days=[];el.querySelectorAll('[data-day]').forEach(function(c){if(c.checked)days.push(c.dataset.day)});var st=el.querySelector('.sc-start'),en=el.querySelector('.sc-end'),mg=el.querySelector('.sc-msg'),cc=el.querySelector('.sc-color'),se=el.querySelector('.sc-snd-en'),sp=el.querySelector('.sc-preset'),sv=el.querySelector('.sc-vol');a.push({id:parseInt(d.id),enabled:el.querySelector('.sc-en').checked,start_time:st?st.value:d.start,end_time:en?en.value:d.end,days:days.length?days:d.days.split(','),message:mg?mg.value:(d.msg||''),color:parseColor(cc?cc.value:(d.color||'')),sound:{enabled:se?se.checked:d.sndEn=="1",preset_id:parseInt(sp?sp.value:d.preset),volume:parseInt(sv?sv.value:d.vol)}})});api('POST','/api/schedules',a).then(function(saved){S=[];SD=[];saved.forEach(function(s){var snd=s.sound||{},sc=s.color||{};var ch=(sc.r||sc.g||sc.b)?'#'+('0'+sc.r.toString(16)).slice(-2)+('0'+sc.g.toString(16)).slice(-2)+('0'+sc.b.toString(16)).slice(-2):'';S.push([s.id,s.start_time,s.end_time,s.enabled?1:0,snd.enabled?1:0,snd.preset_id||1,snd.volume||50,s.message||'',ch]);SD.push((s.days||[]).join(','))});renderSc();toast('sc-toast','Saved')}).catch(function(){toast('sc-toast','Failed',1)})}
function playSnd(btn){var el=btn.closest('.sc');api('POST','/api/sound/preview',{preset_id:parseInt(el.querySelector('.sc-preset').value),volume:parseInt(el.querySelector('.sc-vol').value)})}
function setBright(v){document.getElementById('q-bright-v').textContent=v+'%';api('POST','/api/system/brightness',{brightness:parseInt(v)})}
function setVol(v){document.getElementById('q-vol-v').textContent=v+'%';api('POST','/api/system/volume',{volume:parseInt(v)})}"""
    yield """
(function poll(){api('GET','/api/status').then(function(s){if(s.time)document.getElementById('clock-time').textContent=s.time;if(s.day)document.getElementById('clock-day').textContent=s.day;var l=document.getElementById('st-label'),u=document.getElementById('st-sub');if(s.active){l.textContent='Displaying';l.className='status-on';u.textContent='Until '+s.active_end}else if(s.next_start){l.textContent='Off';l.className='status-off';u.textContent='Next: '+s.next_day+' '+s.next_start}else{l.textContent='Off';l.className='status-off';u.textContent='No schedules set'}document.getElementById('st-msg').textContent=s.message||''}).catch(function(){});setTimeout(poll,1000)})()
</script></body></html>"""


async def render_settings_page(wifi_status, version, free_mem, system_config=None):
    if system_config is None:
        system_config = {}
    tz = system_config.get("timezone_offset", 9)
    yield _head("Device Settings")
    yield _CSS1
    yield _CSS2
    yield _mid("Device Settings")

    yield '<div class="s"><h2>WiFi</h2>'
    yield '<div class="ir"><span class="ir-l">Status</span><span class="ir-v">{}</span></div>'.format("Connected" if wifi_status.get("connected") else "Disconnected")
    yield '<div class="ir"><span class="ir-l">Network</span><span class="ir-v">{}</span></div>'.format(_esc(str(wifi_status.get("ssid", "-"))))
    yield '<div class="ir"><span class="ir-l">IP Address</span><span class="ir-v">{}</span></div>'.format(wifi_status.get("ip", "-"))
    yield '<div class="ir"><span class="ir-l">Signal</span><span class="ir-v">{} dBm</span></div>'.format(wifi_status.get("rssi", "-"))
    yield '<details style="margin-top:8px"><summary>Change WiFi</summary><label>Network</label><select id="wifi-ssid" onchange="togManual()"><option value="">Scanning...</option></select><div id="manual-row" style="display:none"><label>Network name</label><input type="text" id="wifi-ssid-manual" placeholder="SSID"></div><label>Password</label><input type="password" id="wifi-pass" placeholder="WiFi password"><div class="acts"><button class="btn bp bsm" onclick="connectWifi()">Connect</button><button class="btn bs bsm" onclick="scanWifi()">Rescan</button></div><div id="wifi-toast" class="toast"></div></details></div>'

    yield '<div class="s"><h2>Device</h2>'
    yield '<div class="ir"><span class="ir-l">Version</span><span class="ir-v">{}</span></div>'.format(_esc(str(version.get("version", "unknown"))))
    yield '<div class="ir"><span class="ir-l">Free Memory</span><span class="ir-v">{} KB</span></div>'.format(free_mem // 1024 if free_mem else "-")
    yield '<div class="ir"><span class="ir-l">Time Sync</span><span class="ir-v">{}</span></div>'.format("Synced" if wifi_status.get("ntp_synced") else "Not synced")

    # Timezone selector
    tz_opts = ""
    for h in range(-12, 15):
        sign = "+" if h >= 0 else ""
        sel = "selected" if h == tz else ""
        tz_opts += '<option value="{}" {}>UTC{}{}</option>'.format(h, sel, sign, h)
    yield '<label>Timezone</label><select id="sys-tz" onchange="setTz(this.value)">'
    yield tz_opts
    yield '</select>'

    yield '<div class="acts"><button class="btn bs bsm" onclick="checkOta()">Check for updates</button><button class="btn bs bsm" onclick="reboot()">Reboot</button></div><div id="sys-toast" class="toast"></div></div>'
    yield '<div class="footer"><a href="/">Back</a></div>'

    yield '<script>' + _JS_COMMON
    yield """
scanWifi();
function scanWifi(){api('GET','/api/wifi/scan').then(function(nets){var s=document.getElementById('wifi-ssid');s.innerHTML='';nets.forEach(function(n){var o=document.createElement('option');o.value=n.ssid;o.textContent=n.ssid+' ('+n.rssi+' dBm)';s.appendChild(o)});var o=document.createElement('option');o.value='';o.textContent='Enter manually...';s.appendChild(o)}).catch(function(){})}
function togManual(){document.getElementById('manual-row').style.display=document.getElementById('wifi-ssid').value===''?'block':'none'}"""
    yield """
function connectWifi(){var sel=document.getElementById('wifi-ssid');var m=document.getElementById('wifi-ssid-manual');var ssid=sel.value||(m?m.value:'');var pw=document.getElementById('wifi-pass').value;if(!ssid){toast('wifi-toast','Enter a network name',1);return}toast('wifi-toast','Saving...');api('POST','/api/wifi/connect',{ssid:ssid,password:pw}).then(function(r){if(r.status=='saved')toast('wifi-toast','WiFi saved! Rebooting...');else toast('wifi-toast',r.error||'Failed',1)}).catch(function(){toast('wifi-toast','Failed',1)})}
function checkOta(){toast('sys-toast','Checking...');api('POST','/api/ota/check').then(function(r){toast('sys-toast',r.status||r.error||'Done')}).catch(function(){toast('sys-toast','Failed',1)})}
function setTz(v){api('POST','/api/system/timezone',{timezone_offset:parseInt(v)}).then(function(){toast('sys-toast','Timezone saved')}).catch(function(){toast('sys-toast','Failed',1)})}
function reboot(){if(confirm('Reboot device?'))api('POST','/api/system/reboot')}
</script></body></html>"""


async def render_setup_page(networks):
    yield _head("Welcome")
    yield _CSS1
    yield _CSS2
    yield _mid("Welcome")
    yield '<div class="s"><p style="color:#8e8e93;margin-bottom:16px">Select your WiFi network to get started.</p><label>Network</label><select id="wifi-ssid" onchange="togManual()">'
    for n in networks:
        yield '<option value="{}">{} ({} dBm)</option>'.format(_esc(n["ssid"]), _esc(n["ssid"]), n["rssi"])
    yield '<option value="">Enter manually...</option></select><div id="manual-row" style="display:none"><label>Network name</label><input type="text" id="wifi-ssid-manual" placeholder="SSID"></div><label>Password</label><input type="password" id="wifi-pass" placeholder="WiFi password"><div class="acts"><button class="btn bp" onclick="connectWifi()">Connect</button></div><div id="wifi-toast" class="toast"></div></div>'
    yield '<script>' + _JS_COMMON
    yield """
function togManual(){document.getElementById('manual-row').style.display=document.getElementById('wifi-ssid').value===''?'block':'none'}
function connectWifi(){var sel=document.getElementById('wifi-ssid');var m=document.getElementById('wifi-ssid-manual');var ssid=sel.value||(m?m.value:'');var pw=document.getElementById('wifi-pass').value;if(!ssid){toast('wifi-toast','Enter a network name',1);return}toast('wifi-toast','Saving...');api('POST','/api/wifi/connect',{ssid:ssid,password:pw}).then(function(r){if(r.status=='saved')toast('wifi-toast','WiFi saved! Rebooting...');else toast('wifi-toast',r.error||'Failed',1)}).catch(function(){toast('wifi-toast','Failed',1)})}
</script></body></html>"""


def _esc(s):
    return s.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;").replace('"', "&quot;")
