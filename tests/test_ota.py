"""Tests for ota/updater.py — version comparison and manifest parsing."""

import json
import pytest
from unittest.mock import patch, MagicMock

from ota.updater import OTAUpdater


class _FakeBody:
    """Stands in for requests' BodyStream: read(n) chunks, then b"" at EOF."""

    def __init__(self, data):
        self._data = data
        self._pos = 0

    def read(self, n=-1):
        if n < 0:
            n = len(self._data) - self._pos
        chunk = self._data[self._pos:self._pos + n]
        self._pos += len(chunk)
        return chunk

    def close(self):
        pass


def _fake_response(body, status=200):
    resp = MagicMock()
    resp.status_code = status
    resp.raw = _FakeBody(body)
    resp.close = MagicMock()
    return resp


class TestOTAVersionCheck:

    def test_should_check_at_configured_hour(self, mock_system):
        updater = OTAUpdater(mock_system)
        # Simulate configured check_hour=3
        with patch.object(updater, "_load_config", return_value=True):
            updater._ota_config = {"repo": "user/repo", "branch": "main",
                                    "app_path": "src/", "check_hour": 3}
            assert updater.should_check_now(3) is True
            assert updater.should_check_now(4) is False

    def test_should_not_check_if_not_configured(self, mock_system):
        updater = OTAUpdater(mock_system)
        assert updater.should_check_now(3) is False

    def test_get_current_version_default(self, mock_system, config_in_temp):
        updater = OTAUpdater(mock_system)
        assert updater.get_current_version() == "unknown"

    def test_get_current_version_after_save(self, mock_system, config_in_temp):
        config_in_temp.save_version("abc1234")
        updater = OTAUpdater(mock_system)
        assert updater.get_current_version() == "abc1234"


class TestManifestParsing:

    def test_fetch_manifest_builds_correct_url(self, mock_system):
        updater = OTAUpdater(mock_system)
        updater._ota_config = {
            "repo": "user/repo",
            "branch": "main",
            "app_path": "src/",
        }

        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "version": "abc1234",
            "files": ["main.py", "config/config_manager.py"],
        }
        mock_response.close = MagicMock()

        with patch("ota.updater.requests") as mock_requests:
            mock_requests.get.return_value = mock_response
            result = updater._fetch_manifest()

        assert result is not None
        assert result["version"] == "abc1234"
        assert len(result["files"]) == 2

        called_url = mock_requests.get.call_args[0][0]
        assert "user/repo" in called_url
        assert "main" in called_url
        assert "manifest.json" in called_url

    def test_fetch_manifest_returns_none_on_404(self, mock_system):
        updater = OTAUpdater(mock_system)
        updater._ota_config = {
            "repo": "user/repo", "branch": "main", "app_path": "src/",
        }

        mock_response = MagicMock()
        mock_response.status_code = 404

        with patch("ota.updater.requests") as mock_requests:
            mock_requests.get.return_value = mock_response
            result = updater._fetch_manifest()

        assert result is None

    def test_fetch_manifest_returns_none_on_exception(self, mock_system):
        updater = OTAUpdater(mock_system)
        updater._ota_config = {
            "repo": "user/repo", "branch": "main", "app_path": "src/",
        }

        with patch("ota.updater.requests") as mock_requests:
            mock_requests.get.side_effect = Exception("Network error")
            result = updater._fetch_manifest()

        assert result is None


class TestFileUpdate:

    def test_update_file_writes_content(self, mock_system, temp_dir):
        updater = OTAUpdater(mock_system)
        updater._ota_config = {
            "repo": "user/repo", "branch": "main", "app_path": "src/",
        }

        mock_response = _fake_response(b"print('hello')")

        import os
        original_cwd = os.getcwd()
        os.chdir(str(temp_dir))
        try:
            with patch("ota.updater.requests") as mock_requests:
                mock_requests.get.return_value = mock_response
                result = updater._update_file("test_file.py")

            assert result is True
            with open("test_file.py") as f:
                assert f.read() == "print('hello')"
        finally:
            os.chdir(original_cwd)

    def test_update_file_preserves_binary_bytes(self, mock_system, temp_dir):
        """font11.bin and cjk11.bin go through OTA; text mode would mangle them."""
        updater = OTAUpdater(mock_system)
        updater._ota_config = {
            "repo": "user/repo", "branch": "main", "app_path": "src/",
        }

        # Bytes that a text-mode round trip does not survive
        blob = bytes(range(256)) + b"\r\n\x00\xff"
        mock_response = _fake_response(blob)

        import os
        original_cwd = os.getcwd()
        os.chdir(str(temp_dir))
        try:
            with patch("ota.updater.requests") as mock_requests:
                mock_requests.get.return_value = mock_response
                assert updater._update_file("display/font11.bin") is True
            with open("display/font11.bin", "rb") as f:
                assert f.read() == blob
        finally:
            os.chdir(original_cwd)

    def test_update_file_creates_directories(self, mock_system, temp_dir):
        updater = OTAUpdater(mock_system)
        updater._ota_config = {
            "repo": "user/repo", "branch": "main", "app_path": "src/",
        }

        mock_response = _fake_response(b"content")

        import os
        original_cwd = os.getcwd()
        os.chdir(str(temp_dir))
        try:
            with patch("ota.updater.requests") as mock_requests:
                mock_requests.get.return_value = mock_response
                result = updater._update_file("subdir/nested/file.py")

            assert result is True
            assert os.path.exists("subdir/nested/file.py")
        finally:
            os.chdir(original_cwd)

    def test_update_file_fails_on_empty_content(self, mock_system, temp_dir):
        updater = OTAUpdater(mock_system)
        updater._ota_config = {
            "repo": "user/repo", "branch": "main", "app_path": "src/",
        }

        mock_response = _fake_response(b"")

        import os
        original_cwd = os.getcwd()
        os.chdir(str(temp_dir))
        try:
            with patch("ota.updater.requests") as mock_requests:
                mock_requests.get.return_value = mock_response
                result = updater._update_file("empty.py")

            assert result is False
        finally:
            os.chdir(original_cwd)


class TestDownloadStreaming:
    """cjk11.bin is 136KB; buffering a whole file was impossible on a 192KB heap."""

    def _updater(self, mock_system):
        u = OTAUpdater(mock_system)
        u._ota_config = {"repo": "user/repo", "branch": "main", "app_path": "src/"}
        return u

    def test_never_holds_the_whole_file_in_memory(self, mock_system, temp_dir):
        from ota import updater as updater_mod

        blob = bytes(i % 256 for i in range(136 * 1024))
        resp = _fake_response(blob)
        reads = []
        raw_read = resp.raw.read

        def counting_read(n=-1):
            reads.append(n)
            return raw_read(n)

        resp.raw.read = counting_read

        import os
        cwd = os.getcwd()
        os.chdir(str(temp_dir))
        try:
            with patch("ota.updater.requests") as mock_requests:
                mock_requests.get.return_value = resp
                assert self._updater(mock_system)._update_file("display/cjk11.bin") is True
            with open("display/cjk11.bin", "rb") as f:
                assert f.read() == blob
        finally:
            os.chdir(cwd)

        assert reads, "file was not read in chunks"
        assert max(reads) == updater_mod.DOWNLOAD_CHUNK
        assert len(reads) > 200, "136KB should take many chunks, not one read"

    def test_failed_download_leaves_no_tmp_file(self, mock_system, temp_dir):
        resp = _fake_response(b"")

        def boom(n=-1):
            raise OSError("connection reset")

        resp.raw.read = boom

        import os
        cwd = os.getcwd()
        os.chdir(str(temp_dir))
        try:
            with patch("ota.updater.requests") as mock_requests:
                mock_requests.get.return_value = resp
                assert self._updater(mock_system)._update_file("main.py") is False
            assert not os.path.exists("main.py.tmp"), "half-written .tmp left behind"
            assert not os.path.exists("main.py"), "partial file renamed over the target"
        finally:
            os.chdir(cwd)

    def test_requests_get_has_a_timeout(self, mock_system, temp_dir):
        """No timeout means a mid-download WiFi drop hangs the only thread forever."""
        from ota import updater as updater_mod

        resp = _fake_response(b"x")
        import os
        cwd = os.getcwd()
        os.chdir(str(temp_dir))
        try:
            with patch("ota.updater.requests") as mock_requests:
                mock_requests.get.return_value = resp
                self._updater(mock_system)._update_file("main.py")
                _, kwargs = mock_requests.get.call_args
                assert kwargs.get("timeout") == updater_mod.HTTP_TIMEOUT_S
        finally:
            os.chdir(cwd)
