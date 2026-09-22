"""Web UI tests: pages, static assets and the status API.

Runs the real microdot app (with mock HAL) on a local port in a background
thread and talks to it over HTTP.
"""

import asyncio
import json
import os
import re
import socket
import sys
import threading
import time

import pytest

httpx = pytest.importorskip("httpx")

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "tools"))


def _free_port():
    s = socket.socket()
    s.bind(("127.0.0.1", 0))
    port = s.getsockname()[1]
    s.close()
    return port


@pytest.fixture
def server(config_in_temp, tmp_path):
    from preview_server import build_app
    app = build_app(str(tmp_path), sample=True)
    port = _free_port()
    loop = asyncio.new_event_loop()

    def run():
        asyncio.set_event_loop(loop)
        loop.run_until_complete(app.start_server(host="127.0.0.1", port=port))

    t = threading.Thread(target=run, daemon=True)
    t.start()
    base = "http://127.0.0.1:{}".format(port)
    for _ in range(50):
        try:
            httpx.get(base + "/api/status", timeout=0.5)
            break
        except httpx.HTTPError:
            time.sleep(0.05)
    yield base
    loop.call_soon_threadsafe(app.shutdown)
    t.join(timeout=2)


def _page_data(html):
    m = re.search(r"<script>window\.D=(.*?)</script>", html, re.S)
    assert m, "page must embed window.D"
    return json.loads(m.group(1))


class TestPages:
    def test_main_page_shell(self, server):
        r = httpx.get(server + "/")
        assert r.status_code == 200
        assert 'data-page="main"' in r.text
        assert re.search(r'href="/static/app\.css\?v=[\w.-]+"', r.text)
        assert re.search(r'src="/static/app\.js\?v=[\w.-]+"', r.text)
        d = _page_data(r.text)
        assert d["msg"]["color"].startswith("#")
        assert len(d["presets"]) == 20
        assert len(d["sch"]) == 4
        assert d["status"]["time"].count(":") == 2

    def test_data_cannot_break_out_of_script(self, server):
        httpx.post(server + "/api/message", json={"text": "</script><b>x"})
        r = httpx.get(server + "/")
        assert "</script><b>x" not in r.text
        assert _page_data(r.text)["msg"]["text"] == "</script><b>x"

    def test_settings_page(self, server):
        r = httpx.get(server + "/settings")
        assert r.status_code == 200
        d = _page_data(r.text)
        assert set(d) >= {"wifi", "version", "free_kb", "tz"}

    def test_setup_page(self, server):
        r = httpx.get(server + "/setup")
        assert r.status_code == 200
        assert "nets" in _page_data(r.text)


class TestStatic:
    @pytest.mark.parametrize("name,ctype", [("app.css", "text/css"), ("app.js", "application/javascript")])
    def test_served_with_cache_header(self, server, name, ctype):
        r = httpx.get(server + "/static/" + name + "?v=1")
        assert r.status_code == 200
        assert r.headers["content-type"].startswith(ctype)
        assert "max-age=" in r.headers.get("cache-control", "")
        assert len(r.content) > 1000

    @pytest.mark.parametrize("path", ["/static/nope.js", "/static/..%2Froutes.py", "/static/templates.py"])
    def test_only_whitelisted_files(self, server, path):
        assert httpx.get(server + path).status_code == 404

    def test_static_files_are_ascii(self):
        # OTA writes files as text; keep them plain ASCII.
        from web.templates import STATIC_DIR, STATIC_FILES
        for name in STATIC_FILES:
            with open(os.path.join(STATIC_DIR, name), "rb") as f:
                f.read().decode("ascii")

    def test_static_files_in_manifest(self):
        from web.templates import STATIC_FILES
        path = os.path.join(os.path.dirname(__file__), "..", "src", "manifest.json")
        with open(path) as f:
            files = json.load(f)["files"]
        for name in STATIC_FILES:
            assert "web/static/" + name in files


class TestStatusApi:
    def test_status_includes_color_and_time(self, server):
        s = httpx.get(server + "/api/status").json()
        assert {"active", "message", "color", "time", "day"} <= set(s)
        assert set(s["color"]) == {"r", "g", "b"}

    def test_active_schedule_color(self, server):
        # Schedule covering the whole day on every day -> active, with its own color.
        httpx.post(server + "/api/schedules", json=[{
            "id": 1, "enabled": True, "start_time": "00:00", "end_time": "23:59",
            "days": [], "message": "ALL DAY", "color": {"r": 1, "g": 2, "b": 3},
            "sound": {"enabled": False, "preset_id": 1, "volume": 50},
        }])
        s = httpx.get(server + "/api/status").json()
        assert s["active"] is True
        assert s["message"] == "ALL DAY"
        assert s["color"] == {"r": 1, "g": 2, "b": 3}


class TestPageStreaming:
    """Guards the properties the page shell is supposed to have on 192KB of RAM."""

    @staticmethod
    def _chunks(config):
        """Collect what render_main_page actually yields, without a socket."""
        from web.templates import render_main_page

        async def collect():
            out = []
            async for chunk in render_main_page(config, [], []):
                out.append(chunk)
            return out

        return asyncio.new_event_loop().run_until_complete(collect())

    def test_data_blob_is_its_own_chunk(self, config_in_temp):
        """The JSON blob must not be concatenated with the script tags.

        With 20 schedules it is the largest thing on the page; building
        "<script>" + blob + "</script>" doubles the peak allocation.
        """
        from config import config_manager

        config = config_manager.load_app_config()
        config["schedules"] = [
            {
                "id": i,
                "enabled": True,
                "start_time": "08:00",
                "end_time": "09:00",
                "days": ["mon"],
                "message": "schedule number {}".format(i),
                "color": {},
                "sound": {"enabled": False, "preset_id": 1, "volume": 50},
            }
            for i in range(20)
        ]
        chunks = self._chunks(config)
        assert "<script>window.D=" in chunks
        blob = max(chunks, key=len)
        assert blob.startswith("{") and blob.endswith("}")
        # Everything else stays small; only the data blob scales with config size
        others = [c for c in chunks if c is not blob]
        assert max(len(c) for c in others) < 3000

    def test_japanese_text_survives_the_page(self, server):
        """ujson on the device emits raw UTF-8; the '<' escape must not mangle it."""
        text = "本日は18時まで営業中です"
        httpx.post(server + "/api/message", json={"text": text})
        r = httpx.get(server + "/")
        assert _page_data(r.text)["msg"]["text"] == text


class TestStaticAssets:
    def test_cache_tag_changes_when_a_file_changes(self, config_in_temp, tmp_path):
        """A same-size edit must still bust a 30-day cache, so size alone is not enough."""
        import web.templates as templates

        static = tmp_path / "static"
        static.mkdir()
        (static / "app.css").write_text("a{color:red}")
        (static / "app.js").write_text("var a=1")
        original_dir, original_tag = templates.STATIC_DIR, templates._asset_tag
        try:
            templates.STATIC_DIR = str(static)
            templates._asset_tag = None
            first = templates.asset_tag()
            time.sleep(1.1)  # FAT mtime resolution
            (static / "app.js").write_text("var a=2")  # same byte count
            templates._asset_tag = None
            assert templates.asset_tag() != first
        finally:
            templates.STATIC_DIR, templates._asset_tag = original_dir, original_tag


class TestRenderFailureIsVisible:
    def test_a_broken_page_generator_says_so(self, server, monkeypatch):
        """Headers are already sent, so the route try/except cannot help."""
        import web.templates as templates

        def boom(*a, **k):
            raise RuntimeError("kaboom")

        monkeypatch.setattr(templates, "asset_tag", boom)
        r = httpx.get(server + "/")
        assert "render error" in r.text
        assert "kaboom" in r.text
