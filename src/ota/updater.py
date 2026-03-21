"""OTA updater that checks GitHub for new code and updates .py files.

Stops display during update to free RAM for HTTPS communication.
Uses manifest.json in the repo to determine which files to update.
"""

import os

try:
    import ujson as json
except ImportError:
    import json

try:
    import urequests as requests
except ImportError:
    import requests

from config import config_manager


GITHUB_API_BASE = "https://api.github.com/repos"
GITHUB_RAW_BASE = "https://raw.githubusercontent.com"


def _file_exists(path):
    try:
        os.stat(path)
        return True
    except OSError:
        return False


def _ensure_dir(path):
    """Create directory and parents if they don't exist."""
    parts = path.split("/")
    current = ""
    for part in parts:
        if not part:
            continue
        current += "/" + part if current else part
        try:
            os.mkdir(current)
        except OSError:
            pass


class OTAUpdater:

    def __init__(self, system_hal, display_renderer=None):
        self._system = system_hal
        self._display = display_renderer
        self._ota_config = None

    def _load_config(self):
        self._ota_config = config_manager.load_ota_config()
        if not self._ota_config.get("repo"):
            return False
        return True

    def get_current_version(self):
        """Return the currently installed version string."""
        return config_manager.load_version().get("version", "unknown")

    async def check_for_update(self):
        """Check GitHub for a newer version.

        Returns dict with 'available' bool and 'remote_version' string.
        Does NOT perform the update.
        """
        if not self._load_config():
            return {"available": False, "error": "OTA not configured"}

        try:
            manifest = self._fetch_manifest()
            if manifest is None:
                return {"available": False, "error": "Failed to fetch manifest"}

            remote_version = manifest.get("version", "unknown")
            local_version = self.get_current_version()

            return {
                "available": remote_version != local_version,
                "local_version": local_version,
                "remote_version": remote_version,
            }
        except Exception as e:
            return {"available": False, "error": str(e)}

    async def check_and_update(self):
        """Check for update and apply if available.

        Returns status dict.
        """
        if not self._load_config():
            return {"status": "OTA not configured"}

        # Free up RAM
        free_before = self._system.collect_garbage()

        try:
            # Show updating status
            if self._display:
                self._display.show_status("Updating...")

            manifest = self._fetch_manifest()
            if manifest is None:
                return {"status": "Failed to fetch manifest"}

            remote_version = manifest.get("version", "unknown")
            local_version = self.get_current_version()

            if remote_version == local_version:
                return {"status": "Already up to date", "version": local_version}

            # Download and update files
            files = manifest.get("files", [])
            updated = 0
            errors = 0

            for file_path in files:
                success = self._update_file(file_path)
                if success:
                    updated += 1
                else:
                    errors += 1
                # Free memory between downloads
                self._system.collect_garbage()

            if errors > 0:
                return {
                    "status": "Partial update",
                    "updated": updated,
                    "errors": errors,
                    "version": remote_version,
                }

            # Save new version
            config_manager.save_version(remote_version)

            return {
                "status": "Updated",
                "updated": updated,
                "version": remote_version,
                "reboot_required": True,
            }

        except Exception as e:
            return {"status": "Error", "error": str(e)}
        finally:
            if self._display:
                self._display.clear_status()

    def _fetch_manifest(self):
        """Fetch manifest.json from GitHub."""
        repo = self._ota_config["repo"]
        branch = self._ota_config.get("branch", "main")
        app_path = self._ota_config.get("app_path", "src/")

        url = "{base}/{repo}/{branch}/{path}manifest.json".format(
            base=GITHUB_RAW_BASE,
            repo=repo,
            branch=branch,
            path=app_path,
        )

        resp = None
        try:
            resp = requests.get(url)
            if resp.status_code != 200:
                return None
            data = resp.json()
            return data
        except Exception:
            return None
        finally:
            if resp:
                resp.close()

    def _update_file(self, file_path):
        """Download a single file from GitHub and write to local storage.

        Uses tmp+rename for safe writing.
        """
        repo = self._ota_config["repo"]
        branch = self._ota_config.get("branch", "main")
        app_path = self._ota_config.get("app_path", "src/")

        url = "{base}/{repo}/{branch}/{path}{file}".format(
            base=GITHUB_RAW_BASE,
            repo=repo,
            branch=branch,
            path=app_path,
            file=file_path,
        )

        resp = None
        try:
            resp = requests.get(url)
            if resp.status_code != 200:
                return False

            content = resp.text

            if not content or len(content) == 0:
                return False

            # Ensure directory exists
            dir_path = "/".join(file_path.split("/")[:-1])
            if dir_path:
                _ensure_dir(dir_path)

            # Safe write: tmp + rename
            tmp_path = file_path + ".tmp"
            with open(tmp_path, "w") as f:
                f.write(content)

            try:
                os.rename(tmp_path, file_path)
            except OSError:
                if _file_exists(file_path):
                    os.remove(file_path)
                os.rename(tmp_path, file_path)

            return True

        except Exception:
            return False
        finally:
            if resp:
                resp.close()

    def should_check_now(self, current_hour):
        """Return True if it's time for the daily OTA check."""
        if not self._load_config():
            return False
        check_hour = self._ota_config.get("check_hour", 3)
        return current_hour == check_hour
