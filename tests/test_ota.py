"""Tests for ota/updater.py — version comparison and manifest parsing."""

import json
import pytest
from unittest.mock import patch, MagicMock

from ota.updater import OTAUpdater


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

        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.text = "print('hello')"
        mock_response.close = MagicMock()

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

    def test_update_file_creates_directories(self, mock_system, temp_dir):
        updater = OTAUpdater(mock_system)
        updater._ota_config = {
            "repo": "user/repo", "branch": "main", "app_path": "src/",
        }

        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.text = "content"
        mock_response.close = MagicMock()

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

        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.text = ""
        mock_response.close = MagicMock()

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
