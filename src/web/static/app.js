/* Galactic Unicorn web UI. Served from /static/app.js (cached).
   Each page embeds its data as window.D; body[data-page] selects the init. */
(function () {
'use strict';
var D = window.D || {};
var DAYS = ['mon', 'tue', 'wed', 'thu', 'fri', 'sat', 'sun'];
var DL = ['M', 'T', 'W', 'T', 'F', 'S', 'S'];
var DN = ['Mon', 'Tue', 'Wed', 'Thu', 'Fri', 'Sat', 'Sun'];
var SWATCHES = ['#ffffff', '#ffd9a0', '#ff2a2a', '#ff7a00', '#ffd400', '#20e060', '#00d8ff', '#3060ff', '#a040ff', '#ff3fa0'];
var ELL = '\u2026', DASH = '\u2013', DOT = ' \u00b7 ';

/* ---------- helpers ---------- */
function $(s, r) { return (r || document).querySelector(s); }
function $$(s, r) { return Array.prototype.slice.call((r || document).querySelectorAll(s)); }
function clone(o) { return JSON.parse(JSON.stringify(o)); }
function esc(s) { return String(s == null ? '' : s).replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;').replace(/"/g, '&quot;'); }
function mins(t) { var p = String(t).split(':'); return (+p[0]) * 60 + (+p[1]); }
function inRange(c, a, b) { return a <= b ? (c >= a && c <= b) : (c >= a || c <= b); }
function dur(a, b) { var d = b - a; if (d <= 0) d += 1440; var h = Math.floor(d / 60), m = d % 60; return ((h ? h + 'h ' : '') + (m ? m + 'm' : '')).trim() || '0m'; }
function sortDays(d) { return DAYS.filter(function (x) { return d.indexOf(x) >= 0; }); }
function daysLabel(d) {
  var s = d.join(',');
  if (d.length === 7 || !d.length) return 'Every day';
  if (s === 'mon,tue,wed,thu,fri') return 'Weekdays';
  if (s === 'sat,sun') return 'Weekends';
  return d.map(function (x) { return DN[DAYS.indexOf(x)]; }).join(', ');
}
function toHex(c) {
  if (!c || c.r == null) return '';
  return '#' + [c.r, c.g, c.b].map(function (v) { return ('0' + (v | 0).toString(16)).slice(-2); }).join('');
}
function toRgb(h) {
  if (!h || h.length < 7) return {};
  return { r: parseInt(h.substr(1, 2), 16), g: parseInt(h.substr(3, 2), 16), b: parseInt(h.substr(5, 2), 16) };
}
function icon(id, st) { return '<svg class="i"' + (st ? ' style="' + st + '"' : '') + '><use href="#i-' + id + '"/></svg>'; }

function api(method, url, data) {
  return fetch(url, {
    method: method,
    headers: { 'Content-Type': 'application/json' },
    body: data !== undefined ? JSON.stringify(data) : undefined
  }).then(function (r) {
    return r.json().then(function (j) {
      if (!r.ok || (j && j.error)) throw new Error((j && j.error) || ('HTTP ' + r.status));
      return j;
    });
  });
}

var tt;
function toast(msg, err) {
  var t = $('#toast'); if (!t) return;
  t.textContent = msg; t.className = 'toast on' + (err ? ' err' : '');
  clearTimeout(tt);
  tt = setTimeout(function () { t.className = 'toast' + (err ? ' err' : ''); }, err ? 3500 : 2200);
}
function fail(e) { toast('Failed: ' + (e && e.message ? e.message : 'no response'), 1); }

function disclose(t, p, onOpen) {
  var b = $(t), pn = $(p);
  b.onclick = function () {
    var o = b.getAttribute('aria-expanded') !== 'true';
    b.setAttribute('aria-expanded', o); pn.hidden = !o;
    if (o && onOpen) onOpen();
  };
}
function segSet(seg, v) { $$('button', seg).forEach(function (b) { b.setAttribute('aria-pressed', b.dataset.v === String(v)); }); }

/* Color swatches. allowAuto adds a "use message color" choice (value ''). */
function swatches(el, cur, onPick, autoColor) {
  var h = '';
  if (autoColor) h += '<button class="auto" data-c="" aria-label="Same as message color" title="Same as message color" aria-pressed="' + (!cur) + '"><i style="background:' + autoColor + '"></i></button>';
  h += SWATCHES.map(function (c) { return '<button style="background:' + c + '" data-c="' + c + '" aria-label="Color ' + c + '" aria-pressed="' + (c === cur) + '"></button>'; }).join('');
  var custom = !!cur && SWATCHES.indexOf(cur) < 0;
  h += '<button class="custom" aria-label="Custom color" aria-pressed="' + custom + '"' + (custom ? ' style="background:' + cur + '"' : '') + '><input type="color" value="' + (cur || '#ffffff') + '" aria-label="Pick custom color"></button>';
  el.innerHTML = h;
  el.onclick = function (e) {
    var b = e.target.closest('button[data-c]'); if (!b) return;
    onPick(b.dataset.c); swatches(el, b.dataset.c, onPick, autoColor);
  };
  $('input', el).oninput = function () {
    var v = this.value, cb = $('.custom', el);
    onPick(v); cb.style.background = v;
    $$('button', el).forEach(function (x) { x.setAttribute('aria-pressed', x === cb); });
  };
}

/* SVG sprite injected once so the HTML stays small. */
var SPRITE = '<svg width="0" height="0" style="position:absolute" aria-hidden="true">' +
  '<symbol id="i-gear" viewBox="0 0 24 24"><circle cx="12" cy="12" r="3"/><path d="M19.4 15a1.7 1.7 0 0 0 .3 1.8l.1.1a2 2 0 1 1-2.8 2.8l-.1-.1a1.7 1.7 0 0 0-1.8-.3 1.7 1.7 0 0 0-1 1.5V21a2 2 0 1 1-4 0v-.1a1.7 1.7 0 0 0-1.1-1.5 1.7 1.7 0 0 0-1.8.3l-.1.1a2 2 0 1 1-2.8-2.8l.1-.1a1.7 1.7 0 0 0 .3-1.8 1.7 1.7 0 0 0-1.5-1H3a2 2 0 1 1 0-4h.1a1.7 1.7 0 0 0 1.5-1.1 1.7 1.7 0 0 0-.3-1.8l-.1-.1a2 2 0 1 1 2.8-2.8l.1.1a1.7 1.7 0 0 0 1.8.3H9a1.7 1.7 0 0 0 1-1.5V3a2 2 0 1 1 4 0v.1a1.7 1.7 0 0 0 1 1.5 1.7 1.7 0 0 0 1.8-.3l.1-.1a2 2 0 1 1 2.8 2.8l-.1.1a1.7 1.7 0 0 0-.3 1.8V9a1.7 1.7 0 0 0 1.5 1H21a2 2 0 1 1 0 4h-.1a1.7 1.7 0 0 0-1.5 1z"/></symbol>' +
  '<symbol id="i-chev" viewBox="0 0 24 24"><path d="M9 6l6 6-6 6"/></symbol>' +
  '<symbol id="i-back" viewBox="0 0 24 24"><path d="M15 6l-6 6 6 6"/></symbol>' +
  '<symbol id="i-bell" viewBox="0 0 24 24"><path d="M6 8a6 6 0 0 1 12 0c0 7 3 9 3 9H3s3-2 3-9"/><path d="M10.3 21a1.9 1.9 0 0 0 3.4 0"/></symbol>' +
  '<symbol id="i-clock" viewBox="0 0 24 24"><circle cx="12" cy="12" r="9"/><path d="M12 7v5l3 2"/></symbol>' +
  '<symbol id="i-play" viewBox="0 0 24 24"><path d="M7 5l12 7-12 7z"/></symbol>' +
  '<symbol id="i-plus" viewBox="0 0 24 24"><path d="M12 5v14M5 12h14"/></symbol>' +
  '<symbol id="i-arrow" viewBox="0 0 24 24"><path d="M5 12h14M13 6l6 6-6 6"/></symbol>' +
  '<symbol id="i-alert" viewBox="0 0 24 24"><path d="M12 9v4M12 17h.01"/><path d="M10.3 3.9L1.8 18a2 2 0 0 0 1.7 3h17a2 2 0 0 0 1.7-3L13.7 3.9a2 2 0 0 0-3.4 0z"/></symbol>' +
  '<symbol id="i-sun" viewBox="0 0 24 24"><circle cx="12" cy="12" r="4"/><path d="M12 2v2M12 20v2M4.9 4.9l1.4 1.4M17.7 17.7l1.4 1.4M2 12h2M20 12h2M4.9 19.1l1.4-1.4M17.7 6.3l1.4-1.4"/></symbol>' +
  '<symbol id="i-vol" viewBox="0 0 24 24"><path d="M11 5L6 9H3v6h3l5 4z"/><path d="M15.5 8.5a5 5 0 0 1 0 7M18.5 5.5a9 9 0 0 1 0 13"/></symbol>' +
  '</svg>';

/* ---------- Wi-Fi picker (settings + setup) ---------- */
function bars(r) {
  var n = r == null ? 0 : r > -60 ? 4 : r > -70 ? 3 : r > -80 ? 2 : 1;
  return '<span class="sig">' + [1, 2, 3, 4].map(function (i) { return '<i' + (i <= n ? ' class="on"' : '') + '></i>'; }).join('') + '</span>';
}
function wifiPicker(initial) {
  var list = $('#net-list'), sel = null;
  function render(nets) {
    var seen = {}, uniq = [];
    (nets || []).forEach(function (n) { if (n.ssid && !seen[n.ssid]) { seen[n.ssid] = 1; uniq.push(n); } });
    uniq.sort(function (a, b) { return (b.rssi || -999) - (a.rssi || -999); });
    list.innerHTML = (uniq.length ? '' : '<div class="empty-state">No networks found. Try Rescan.</div>') +
      uniq.map(function (n) { return '<button class="net" data-n="' + esc(n.ssid) + '" aria-pressed="' + (n.ssid === sel) + '"><span class="n">' + esc(n.ssid) + '</span><span class="rs num">' + (n.rssi != null ? n.rssi + ' dBm' : '') + '</span>' + bars(n.rssi) + '</button>'; }).join('') +
      '<button class="net" data-other="1" aria-pressed="' + (sel === '') + '"><span class="n" style="color:var(--link)">Other network' + ELL + '</span></button>';
  }
  list.onclick = function (e) {
    var b = e.target.closest('.net'); if (!b) return;
    sel = b.dataset.other ? '' : b.dataset.n;
    $$('.net', list).forEach(function (x) { x.setAttribute('aria-pressed', x === b); });
    $('#ssid-row').hidden = sel !== '';
    if (sel === '') $('#ssid').focus(); else $('#pw').focus();
  };
  function scan() {
    list.innerHTML = '<div class="empty-state">Scanning' + ELL + '</div>';
    api('GET', '/api/wifi/scan').then(render).catch(function (e) { render([]); fail(e); });
  }
  $('#wf-scan').onclick = scan;
  $('#wf-connect').onclick = function () {
    var ssid = sel === '' ? $('#ssid').value.trim() : sel;
    if (!ssid) { toast('Choose a network first', 1); return; }
    var btn = this; btn.disabled = true;
    api('POST', '/api/wifi/connect', { ssid: ssid, password: $('#pw').value }).then(function () {
      toast('Saved ' + DASH + ' restarting to join ' + ssid);
    }).catch(function (e) { btn.disabled = false; fail(e); });
  };
  if (initial) render(initial);
  return scan;
}
function pwToggles() {
  $$('[data-pw]').forEach(function (b) {
    b.onclick = function () {
      var i = document.getElementById(b.dataset.pw), s = i.type === 'password';
      i.type = s ? 'text' : 'password'; b.textContent = s ? 'Hide' : 'Show';
    };
  });
}

/* ================= Main page ================= */
function initMain() {
  var M = D.msg || {}, P = D.presets || [], ST = D.status || {};
  var saved = norm(D.sch || []), S = clone(saved), openId = null;
  var stAt = Date.now();

  function norm(list) {
    return list.map(function (s) {
      s = clone(s);
      if (!s.days || !s.days.length) s.days = DAYS.slice();
      s.sound = s.sound || { enabled: false, preset_id: 1, volume: 50 };
      if (!s.color || s.color.r == null) s.color = {};
      s.message = s.message || '';
      return s;
    });
  }
  function byId(id) { for (var i = 0; i < S.length; i++) if (S[i].id === id) return S[i]; }
  function colorOf(s) { return toHex(s.color) || M.color; }

  /* ---- now / clock (device time, ticked locally between polls) ---- */
  function devNow() {
    var t = ST.time && ST.time.indexOf(':') > 0 ? ST.time.split(':') : null;
    var wd = DN.indexOf(ST.day);
    if (!t || wd < 0) return null;
    var sec = (+t[0]) * 3600 + (+t[1]) * 60 + (+t[2] || 0) + Math.floor((Date.now() - stAt) / 1000);
    wd = (wd + Math.floor(sec / 86400)) % 7; sec = sec % 86400;
    return { m: Math.floor(sec / 60), wd: wd, hh: ('0' + Math.floor(sec / 3600)).slice(-2), mm: ('0' + Math.floor(sec / 60) % 60).slice(-2) };
  }
  function renderNow() {
    var n = devNow(), p = $('#now-panel'), led = $('#now-led');
    $('#clk').textContent = n ? n.hh + ':' + n.mm : '--:--';
    $('#clk-day').textContent = n ? DN[n.wd] : '';
    var txt, col;
    if (ST.active) { txt = ST.message; col = toHex(ST.color) || M.color; }
    else { txt = $('#msg').value || M.text; col = M.color; }
    if (led.textContent !== txt) led.textContent = txt;
    led.style.color = col;
    p.classList.toggle('off', !ST.active);
    p.classList.toggle('fixed', M.display_mode === 'fixed');
    led.style.animationDuration = { slow: '14s', medium: '9s', fast: '5s' }[M.scroll_speed] || '9s';
    $('#now-pill').className = 'pill' + (ST.active ? ' on' : '');
    var nx = '';
    if (!ST.active && ST.next_start) {
      var nd = DN.indexOf(ST.next_day);
      nx = n && nd === n.wd && mins(ST.next_start) > n.m ? 'today' : n && nd === (n.wd + 1) % 7 ? 'tomorrow' : (ST.next_day || '');
    }
    $('#now-txt').textContent = ST.active ? (ST.active_end ? 'On until ' + ST.active_end : 'On') :
      ST.next_start ? 'Off' + DOT + 'next ' + nx + ' ' + ST.next_start : 'Off' + DOT + 'nothing scheduled';
  }
  function refreshStatus() {
    return api('GET', '/api/status').then(function (s) {
      ST = s; stAt = Date.now(); renderNow(); renderTL();
      if ('brightness_offset' in s && !brBusy) setRange('#q-br', s.brightness_offset);
    }).catch(function () {});
  }

  /* ---- message ---- */
  var mi = $('#msg');
  mi.value = M.text || '';
  function cnt() { $('#msg-count').textContent = mi.value.length + '/128'; }
  cnt();
  mi.oninput = function () { cnt(); renderNow(); };
  mi.onkeydown = function (e) { if (e.key === 'Enter') $('#msg-save').click(); };
  swatches($('#msg-sw'), M.color, function (c) { M.color = c; renderNow(); renderList(); });
  $$('#opt .seg').forEach(function (seg) {
    segSet(seg, M[seg.dataset.k]);
    seg.onclick = function (e) {
      var b = e.target.closest('button'); if (!b) return;
      M[seg.dataset.k] = b.dataset.v; segSet(seg, b.dataset.v); renderNow();
    };
  });
  disclose('#opt-t', '#opt');
  $('#msg-save').onclick = function () {
    var btn = this, text = mi.value.trim();
    if (!text) { toast('Message is empty', 1); mi.focus(); return; }
    btn.disabled = true;
    api('POST', '/api/message', {
      text: text, display_mode: M.display_mode, scroll_speed: M.scroll_speed,
      font: M.font, color: toRgb(M.color)
    }).then(function (r) {
      M.text = r.text; mi.value = r.text; cnt(); toast('Display updated'); return refreshStatus();
    }).catch(fail).then(function () { btn.disabled = false; });
  };

  /* ---- week timeline ---- */
  function renderTL() {
    var n = devNow();
    var h = '<div class="tl-hours"><i></i><div><span style="left:0">0</span><span style="left:25%">6</span><span style="left:50%">12</span><span style="left:75%">18</span><span style="left:100%">24</span></div></div>';
    DAYS.forEach(function (d, di) {
      h += '<div class="tl-row' + (n && di === n.wd ? ' today' : '') + '"><b>' + DL[di] + '</b><div class="tl-track">';
      S.forEach(function (s) {
        if (s.days.indexOf(d) < 0) return;
        var a = mins(s.start_time), b = mins(s.end_time);
        /* Overnight ranges match on the same weekday (see scheduler.is_time_in_range). */
        var segs = a <= b ? [[a, b]] : [[a, 1440], [0, b]];
        segs.forEach(function (g) {
          h += '<span class="tl-blk' + (s.enabled ? '' : ' off') + '" data-id="' + s.id + '" title="' + esc(s.message || M.text) + ' ' + s.start_time + DASH + s.end_time + '" style="left:' + (g[0] / 14.4) + '%;width:' + ((g[1] - g[0]) / 14.4) + '%;background:' + colorOf(s) + '"></span>';
        });
      });
      if (n && di === n.wd) h += '<span class="tl-now" style="left:' + (n.m / 14.4) + '%"></span>';
      h += '</div></div>';
    });
    $('#tl').innerHTML = h;
    var on = S.filter(function (s) { return s.enabled; }).length;
    $('#sc-sum').textContent = S.length ? on + ' of ' + S.length + ' active' : '';
  }
  $('#tl').onclick = function (e) { var b = e.target.closest('.tl-blk'); if (b) toggleOpen(+b.dataset.id, true); };

  /* ---- schedule list ---- */
  function overlaps(s) {
    var out = [];
    S.forEach(function (o) {
      if (o === s || !o.enabled || !s.enabled) return;
      if (!s.days.some(function (d) { return o.days.indexOf(d) >= 0; })) return;
      var a = mins(s.start_time), b = mins(s.end_time), c = mins(o.start_time), d = mins(o.end_time);
      if (inRange(a, c, d) || inRange(b, c, d) || inRange(c, a, b) || inRange(d, a, b)) out.push(o);
    });
    return out;
  }
  function renderList() {
    var L = $('#sc-list');
    if (!S.length) { L.innerHTML = '<div class="empty-state">No schedules yet. Add one to show a message at set times.</div>'; renderTL(); return; }
    L.innerHTML = S.map(function (s) {
      var open = s.id === openId, col = colorOf(s);
      var h = '<div class="sc' + (open ? ' open' : '') + (s.enabled ? '' : ' off') + '" data-id="' + s.id + '">';
      h += '<div class="sc-head"><button class="sc-main" data-act="open" aria-expanded="' + open + '"><span class="sc-dot" style="background:' + col + ';color:' + col + '"></span><span style="min-width:0"><span class="sc-t' + (s.message ? '' : ' empty') + '">' + (s.message ? esc(s.message) : 'Uses default message') + '</span>';
      h += '<span class="sc-m"><span class="num">' + icon('clock') + s.start_time + DASH + s.end_time + '</span><span>' + daysLabel(s.days) + '</span>' + (s.sound.enabled ? '<span>' + icon('bell') + esc(P[s.sound.preset_id - 1] || '') + '</span>' : '') + '</span></span></button>';
      h += '<label class="switch" aria-label="Enabled"><input type="checkbox" data-act="en"' + (s.enabled ? ' checked' : '') + '><span></span></label></div>';
      if (open) h += editor(s);
      return h + '</div>';
    }).join('');
    if (openId != null) { var el = $('.sc[data-id="' + openId + '"]'); if (el) bindEditor(el, byId(openId)); }
    renderTL();
  }
  function editor(s) {
    var ov = overlaps(s), a = mins(s.start_time), b = mins(s.end_time);
    var h = '<div class="sc-body">';
    if (ov.length) h += '<div class="warn">' + icon('alert') + '<span>Overlaps with \u201c' + esc(ov[0].message || 'default message') + '\u201d. When schedules overlap, the one higher in the list is shown.</span></div>';
    h += '<div class="field"><label>Message</label><input class="inp" data-f="message" maxlength="128" value="' + esc(s.message) + '" placeholder="Leave empty to use the default message"></div>';
    h += '<div class="field"><span class="lbl">Color</span><div class="sw" data-f="color"></div></div>';
    h += '<div class="field"><span class="lbl">Time</span><div class="times"><input class="inp" type="time" data-f="start_time" value="' + s.start_time + '" aria-label="Start"><svg class="i"><use href="#i-arrow"/></svg><input class="inp" type="time" data-f="end_time" value="' + s.end_time + '" aria-label="End"></div>';
    h += '<div class="dur">' + dur(a, b) + (b < a ? '<span class="badge">Overnight</span>' : '') + '</div></div>';
    h += '<div class="field"><span class="lbl">Days</span><div class="days">' + DAYS.map(function (d, i) { return '<button data-day="' + d + '" aria-label="' + DN[i] + '" aria-pressed="' + (s.days.indexOf(d) >= 0) + '">' + DL[i] + '</button>'; }).join('') + '</div>';
    h += '<div class="quick"><button data-q="wk">Weekdays</button><button data-q="we">Weekends</button><button data-q="all">Every day</button></div>';
    if (!s.days.length) h += '<div class="warn">' + icon('alert') + '<span>Pick at least one day.</span></div>';
    h += '</div><div class="field"><div class="snd"><span style="font-weight:550">Play a sound at start</span><label class="switch"><input type="checkbox" data-f="snd"' + (s.sound.enabled ? ' checked' : '') + '><span></span></label></div>';
    if (s.sound.enabled) {
      h += '<div class="grid2" style="margin-top:10px"><select class="inp" data-f="preset" aria-label="Sound">' + P.map(function (p, i) { return '<option value="' + (i + 1) + '"' + (s.sound.preset_id === i + 1 ? ' selected' : '') + '>' + esc(p) + '</option>'; }).join('') + '</select><button class="btn ghost" data-act="play">' + icon('play', 'width:14px;height:14px') + 'Preview</button></div>';
      h += '<div class="field" style="margin-top:10px"><div class="seg" data-f="vol">' + [25, 50, 75, 100].map(function (v) { return '<button data-v="' + v + '" aria-pressed="' + (s.sound.volume === v) + '">' + v + '%</button>'; }).join('') + '</div></div>';
    }
    h += '</div><div class="acts"><button class="btn danger sm" data-act="del">Delete schedule</button><span class="grow"></span><button class="btn ghost sm" data-act="open">Done</button></div></div>';
    return h;
  }
  function bindEditor(el, s) {
    swatches($('[data-f=color]', el), toHex(s.color), function (c) {
      s.color = toRgb(c); dirty();
      var d = $('.sc-dot', el), col = colorOf(s); d.style.background = col; d.style.color = col; renderTL();
    }, M.color);
    var mf = $('[data-f=message]', el);
    mf.oninput = function () {
      s.message = this.value; dirty();
      var t = $('.sc-t', el); t.textContent = this.value || 'Uses default message'; t.classList.toggle('empty', !this.value);
    };
    mf.onchange = renderList;
    ['start_time', 'end_time'].forEach(function (k) {
      $('[data-f=' + k + ']', el).onchange = function () { if (this.value) s[k] = this.value.slice(0, 5); dirty(); renderList(); };
    });
  }
  function toggleOpen(id, force) {
    openId = (openId === id && !force) ? null : id; renderList();
    var el = openId != null && $('.sc[data-id="' + id + '"]');
    if (el && el.scrollIntoView) el.scrollIntoView({ block: 'nearest', behavior: 'smooth' });
  }
  $('#sc-list').addEventListener('click', function (e) {
    var card = e.target.closest('.sc'); if (!card) return;
    var id = +card.dataset.id, s = byId(id);
    var t = e.target.closest('[data-act],[data-day],[data-q],[data-v]'); if (!t || !s) return;
    var act = t.dataset.act;
    if (act === 'open') { toggleOpen(id); return; }
    if (act === 'en') return;
    if (act === 'del') { if (confirm('Delete this schedule?')) { S = S.filter(function (x) { return x.id !== id; }); openId = null; dirty(); renderList(); } return; }
    if (act === 'play') { api('POST', '/api/sound/preview', { preset_id: s.sound.preset_id, volume: s.sound.volume }).catch(fail); return; }
    if (t.dataset.day) { var d = t.dataset.day, i = s.days.indexOf(d); if (i >= 0) s.days.splice(i, 1); else s.days.push(d); s.days = sortDays(s.days); dirty(); renderList(); return; }
    if (t.dataset.q) { s.days = { wk: DAYS.slice(0, 5), we: ['sat', 'sun'], all: DAYS.slice() }[t.dataset.q]; dirty(); renderList(); return; }
    if (t.dataset.v && t.closest('[data-f=vol]')) { s.sound.volume = +t.dataset.v; dirty(); renderList(); }
  });
  $('#sc-list').addEventListener('change', function (e) {
    var card = e.target.closest('.sc'); if (!card) return;
    var s = byId(+card.dataset.id), f = e.target.dataset; if (!s) return;
    if (f.act === 'en') { s.enabled = e.target.checked; dirty(); renderList(); }
    else if (f.f === 'snd') { s.sound.enabled = e.target.checked; dirty(); renderList(); }
    else if (f.f === 'preset') { s.sound.preset_id = +e.target.value; dirty(); renderList(); }
  });
  $('#sc-add').onclick = function () {
    var id = S.concat(saved).reduce(function (m, s) { return Math.max(m, s.id | 0); }, 0) + 1;
    S.push({ id: id, enabled: true, start_time: '08:00', end_time: '09:00', days: DAYS.slice(0, 5), message: '', color: {}, sound: { enabled: false, preset_id: 1, volume: 50 } });
    openId = id; dirty(); renderList();
    var el = $('.sc[data-id="' + id + '"]');
    if (el) { el.scrollIntoView({ block: 'center', behavior: 'smooth' }); $('[data-f=message]', el).focus({ preventScroll: true }); }
  };

  /* Unsaved-changes bar: edits are batched into one POST (one flash write). */
  function dirty() {
    var d = JSON.stringify(S) !== JSON.stringify(saved), bad = S.some(function (s) { return !s.days.length; });
    $('#savebar').classList.toggle('on', d);
    $('#sc-save').disabled = bad;
    $('#savebar-txt').textContent = bad ? 'Pick days for every schedule' : 'Unsaved changes';
  }
  $('#sc-save').onclick = function () {
    var btn = this; btn.disabled = true;
    api('POST', '/api/schedules', S).then(function (r) {
      saved = norm(r); S = clone(saved); dirty(); renderList(); toast('Schedules saved'); return refreshStatus();
    }).catch(fail).then(function () { btn.disabled = false; dirty(); });
  };
  $('#sc-discard').onclick = function () { S = clone(saved); openId = null; dirty(); renderList(); };
  window.addEventListener('beforeunload', function (e) {
    if (JSON.stringify(S) !== JSON.stringify(saved)) { e.preventDefault(); e.returnValue = ''; }
  });

  /* ---- quick settings (debounced; brightness is persisted, so wait longer) ---- */
  var brBusy = false;
  function setRange(id, v) {
    var r = $(id); r.value = v;
    r.style.setProperty('--p', ((r.value - r.min) / (r.max - r.min) * 100) + '%');
    $(id + '-v').textContent = id === '#q-br' ? ((+v > 0 ? '+' : '') + v + '%') : v + '%';
  }
  function bindRange(id, delay, send) {
    var r = $(id), t;
    r.oninput = function () {
      setRange(id, r.value); if (id === '#q-br') brBusy = true;
      clearTimeout(t);
      t = setTimeout(function () { send(+r.value).catch(fail).then(function () { brBusy = false; }); }, delay);
    };
  }
  setRange('#q-br', D.bo || 0); setRange('#q-vol', 50);
  bindRange('#q-br', 1000, function (v) { return api('POST', '/api/system/brightness', { brightness_offset: v }); });
  bindRange('#q-vol', 300, function (v) { return api('POST', '/api/system/volume', { volume: v }); });

  renderList(); renderNow();
  setInterval(renderNow, 15000);
  setInterval(function () { if (!document.hidden) refreshStatus(); }, 60000);
  document.addEventListener('visibilitychange', function () { if (!document.hidden) refreshStatus(); });
}

/* ================= Settings page ================= */
function initSettings() {
  var w = D.wifi || {};
  $('#wf-pill').className = 'pill' + (w.connected ? ' on' : '');
  $('#wf-state').textContent = w.connected ? 'Connected' : 'Disconnected';
  $('#wf-ssid').textContent = w.ssid || '-';
  $('#wf-ip').textContent = w.ip || '-';
  $('#wf-rssi').innerHTML = w.rssi != null ? '<span style="color:var(--ok)">' + bars(w.rssi) + '</span> <span class="num">' + esc(w.rssi) + ' dBm</span>' : '-';
  var ntp = $('#ntp');
  ntp.textContent = w.ntp ? 'Synced via NTP' : 'Not synced';
  ntp.style.color = w.ntp ? 'var(--ok)' : 'var(--warn)';
  $('#ver').textContent = D.version || 'unknown';
  $('#mem').textContent = D.free_kb != null ? D.free_kb + ' KB free' : '-';

  var scan = wifiPicker(null), scanned = false;
  disclose('#wifi-t', '#wifi-chg', function () { if (!scanned) { scanned = true; scan(); } });
  pwToggles();

  var tz = $('#tz');
  for (var h = -12; h <= 14; h++) {
    var o = document.createElement('option');
    o.value = h; o.textContent = 'UTC' + (h >= 0 ? '+' : '\u2212') + Math.abs(h);
    if (h === D.tz) o.selected = true;
    tz.appendChild(o);
  }
  tz.onchange = function () {
    api('POST', '/api/system/timezone', { timezone_offset: +tz.value }).then(function () { toast('Timezone saved'); clock(); }).catch(fail);
  };
  function clock() {
    api('GET', '/api/status').then(function (s) { $('#set-clk').textContent = (s.time || '--:--').slice(0, 5) + ' ' + (s.day || ''); }).catch(function () {});
  }
  clock(); setInterval(function () { if (!document.hidden) clock(); }, 30000);

  $('#ota').onclick = function () {
    var btn = this; btn.disabled = true; toast('Checking for updates' + ELL);
    api('POST', '/api/ota/check').then(function (r) { toast(r.status || 'Done'); }).catch(fail).then(function () { btn.disabled = false; });
  };
  $('#reboot').onclick = function () {
    if (!confirm('Reboot the display? It will be offline for about 20 seconds.')) return;
    api('POST', '/api/system/reboot').then(function () { toast('Rebooting' + ELL); }).catch(fail);
  };
}

/* ================= Setup page (captive portal) ================= */
function initSetup() {
  wifiPicker(D.nets || []);
  pwToggles();
}

function boot() {
  document.body.insertAdjacentHTML('afterbegin', SPRITE);
  var p = document.body.dataset.page;
  if (p === 'main') initMain();
  else if (p === 'settings') initSettings();
  else if (p === 'setup') initSetup();
}
if (document.readyState === 'loading') document.addEventListener('DOMContentLoaded', boot); else boot();
})();
