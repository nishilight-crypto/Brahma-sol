"""
core/auto_updater.py
====================
Cloudflare-Powered Auto-Updater for Brahma Sol.

Features:
- Queries the Cloudflare Worker edge (http://brahma-update-hub.brahma-sol.workers.dev/version)
- Zero-downtime version checking in background thread
- Atomic Windows process handoff via self-deleting batch script:
  1. Downloads latest brahma-sol_setup.exe to %TEMP%/BrahmaUpdates
  2. Spawns detached batch supervisor
  3. Quits running BrahmaSol.exe to release Windows file lock
  4. Runs installer in /SILENT mode into target directory
  5. Automatically relaunches BrahmaSol.exe
- Provides publish_update() to release new versions to the Cloudflare Edge KV store
"""

from __future__ import annotations

import os
import sys
import json
import time
import urllib.request
import urllib.error
import subprocess
import threading
from pathlib import Path
from typing import Optional, Callable, Dict, Any

CURRENT_VERSION = "2.4.1"
PRIMARY_UPDATE_URL = "http://brahma-update-hub.brahma-sol.workers.dev/version"
FALLBACK_UPDATE_URL = "https://brahma-update-hub.brahma-sol.workers.dev/version"
ADMIN_KEY = "brahma_sol_celestial_secret_2026"


class AutoUpdater:
    def __init__(self, current_version: str = CURRENT_VERSION):
        self.current_version = current_version
        self.update_info: Optional[Dict[str, Any]] = None
        self._is_checking = False
        self._is_downloading = False

    def is_newer_version(self, remote_ver: str) -> bool:
        """Compares semver strings e.g. '2.1.0' > '2.0.0'."""
        try:
            r_parts = [int(p) for p in remote_ver.strip().lstrip("v").split(".")]
            c_parts = [int(p) for p in self.current_version.strip().lstrip("v").split(".")]
            return r_parts > c_parts
        except Exception:
            return False

    def check_for_updates(self, timeout: float = 6.0) -> Optional[Dict[str, Any]]:
        """Queries the Cloudflare update hub for newer releases."""
        if sys.platform == "darwin":
            return None  # self-update disabled on macOS port
        if self._is_checking:
            return None
        self._is_checking = True
        try:
            urls = [PRIMARY_UPDATE_URL, FALLBACK_UPDATE_URL]
            for url in urls:
                try:
                    req = urllib.request.Request(
                        url,
                        headers={"User-Agent": f"BrahmaSol/{self.current_version}"}
                    )
                    with urllib.request.urlopen(req, timeout=timeout) as resp:
                        if resp.status == 200:
                            data = json.loads(resp.read().decode("utf-8"))
                            remote_version = data.get("version", "0.0.0")
                            if self.is_newer_version(remote_version):
                                self.update_info = data
                                print(f"[AutoUpdater] 🔔 New version detected: v{remote_version} (Current: v{self.current_version})")
                                return data
                            else:
                                print(f"[AutoUpdater] ✅ Up to date (v{self.current_version}).")
                                return None
                except Exception:
                    continue
        finally:
            self._is_checking = False
        return None

    def check_in_background(self, on_update_found: Optional[Callable[[Dict[str, Any]], None]] = None):
        """Asynchronously checks for updates without blocking main thread."""
        def _worker():
            info = self.check_for_updates()
            if info and on_update_found:
                on_update_found(info)

        t = threading.Thread(target=_worker, daemon=True, name="brahma-autoupdate-checker")
        t.start()

    def download_and_apply(
        self,
        progress_callback: Optional[Callable[[int, str], None]] = None,
        on_complete: Optional[Callable[[], None]] = None
    ) -> bool:
        """Downloads the installer and executes the Windows silent hot-swap handoff."""
        if sys.platform == "darwin":
            return False  # self-update disabled on macOS port
        if not self.update_info:
            return False
        if self._is_downloading:
            return False
        self._is_downloading = True

        download_url = self.update_info.get("download_url")
        if not download_url:
            print("[AutoUpdater] ⚠️ No download URL in update manifest.")
            self._is_downloading = False
            return False

        temp_dir = Path(os.environ.get("TEMP", ".")) / "BrahmaUpdates"
        temp_dir.mkdir(parents=True, exist_ok=True)
        installer_path = temp_dir / "brahma-sol_setup_update.exe"

        print(f"[AutoUpdater] 🚀 Downloading update from {download_url} to {installer_path}...")

        def _reporthook(block_num, block_size, total_size):
            if total_size > 0 and progress_callback:
                pct = min(100, int((block_num * block_size / total_size) * 100))
                mb_down = round((block_num * block_size) / (1024 * 1024), 1)
                mb_total = round(total_size / (1024 * 1024), 1)
                progress_callback(pct, f"Downloading Brahma Sol: {mb_down} MB / {mb_total} MB ({pct}%)")

        try:
            urllib.request.urlretrieve(download_url, str(installer_path), reporthook=_reporthook)
            print("[AutoUpdater] ✅ Download complete. Initiating in-place upgrade...")
            if on_complete:
                on_complete()
            self._execute_windows_swap(installer_path)
            return True
        except Exception as e:
            print(f"[AutoUpdater] ⚠️ Download failed: {e}")
            self._is_downloading = False
            return False

    def _execute_windows_swap(self, installer_path: Path):
        """
        Launches a detached script that waits for Brahma Sol to quit,
        executes the installer, and relaunches Brahma Sol.
        Cross-platform: batch script on Windows, shell script on macOS/Linux.
        """
        current_exe = sys.executable
        if getattr(sys, 'frozen', False):
            install_dir = Path(current_exe).resolve().parent
            target_exe = current_exe
        else:
            local_app = os.environ.get("LOCALAPPDATA", "")
            if sys.platform == "darwin":
                install_dir = Path.home() / "Library" / "Application Support" / "BrahmaSol"
                target_exe = str(install_dir / "Brahma Sol.app" / "Contents" / "MacOS" / "Brahma Sol")
            else:
                install_dir = Path(local_app) / "Programs" / "BrahmaSol"
                target_exe = str(install_dir / "BrahmaSol.exe")

        pid = os.getpid()

        if sys.platform == "darwin":
            shell_script = installer_path.parent / "apply_update.sh"
            script_content = f"""#!/bin/bash
# Brahma Sol Updater — macOS
echo "[BRAHMA SOL] Waiting for application to exit..."
sleep 1

while kill -0 {pid} 2>/dev/null; do
    sleep 1
done

echo "[BRAHMA SOL] Installing update silently into: \"{install_dir}\"...
open -W "{installer_path}"

echo "[BRAHMA SOL] Relaunching Brahma Sol...
open "{target_exe}"

sleep 2
rm -f "$0"
exit 0
"""
            shell_script.write_text(script_content, encoding="utf-8")
            shell_script.chmod(0o755)
            flags = subprocess.CREATE_NEW_PROCESS_GROUP | subprocess.DETACHED_PROCESS if os.name == "nt" else 0
            subprocess.Popen(["/bin/bash", str(shell_script)], creationflags=flags)
        else:
            install_dir = Path(local_app) / "Programs" / "BrahmaSol"
            target_exe = str(install_dir / "BrahmaSol.exe")

            pid = os.getpid()
            batch_script = installer_path.parent / "apply_update.bat"

            script_content = f"""@echo off
setlocal enabledelayedexpansion
title Brahma Sol Updater
echo [BRAHMA SOL] Waiting for application to exit...
timeout /t 1 /nobreak > nul

:wait_loop
tasklist /fi "PID eq {pid}" | find "{pid}" > nul
if %ERRORLEVEL% equ 0 (
    timeout /t 1 /nobreak > nul
    goto wait_loop
)

echo [BRAHMA SOL] Installing update silently into: "{install_dir}"...
"{installer_path}" /SILENT /DIR="{install_dir}"

echo [BRAHMA SOL] Relaunching Brahma Sol...
start "" "{target_exe}"

timeout /t 2 /nobreak > nul
del "%~f0"
exit
"""
            batch_script.write_text(script_content, encoding="utf-8")

            flags = subprocess.CREATE_NEW_PROCESS_GROUP | subprocess.DETACHED_PROCESS if os.name == "nt" else 0
            subprocess.Popen(["cmd.exe", "/c", str(batch_script)], creationflags=flags)

        # Terminate current app cleanly and unconditionally (avoid thread SystemExit)
        time.sleep(0.5)
        os._exit(0)

    @classmethod
    def publish_update_to_cloudflare(
        cls,
        version: str,
        download_url: str,
        changelog: str,
        name: str = "Brahma Sol - Celestial Edition",
        admin_key: str = ADMIN_KEY
    ) -> Dict[str, Any]:
        """Publishes a new release to the Cloudflare Worker update hub."""
        payload = {
            "version": version,
            "name": name,
            "release_date": time.strftime("%Y-%m-%d"),
            "changelog": changelog,
            "download_url": download_url,
            "mandatory": False
        }
        data = json.dumps(payload).encode("utf-8")
        req = urllib.request.Request(
            "http://brahma-update-hub.brahma-sol.workers.dev/api/set-version",
            data=data,
            headers={
                "Content-Type": "application/json",
                "X-Admin-Key": admin_key,
                "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) BrahmaSolUpdateManager/2.0"
            }
        )
        with urllib.request.urlopen(req, timeout=15) as resp:
            return json.loads(resp.read().decode("utf-8"))


    # Alias
    publish_release = publish_update_to_cloudflare


# Global singleton
auto_updater = AutoUpdater()
