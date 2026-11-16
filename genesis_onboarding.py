"""
genesis_onboarding.py
=====================
Brahma SOL Genesis Onboarding Experience.
Exact Thursday Agent frontend architecture adapted for Brahma SOL:
1. Spatial Architecture: Center-left ASCII Orb presence, cascading captions, right-hand step execution.
2. Authentic ASCII Orb Canvas: Driven by Thursday's glyph matrix (RAMP) and domain-warped turbulence noise.
3. 1-Click Ollama Engine Download, silent installer & background daemon starter.
4. 1-Click Local Model Pulling (Qwen 2.5 7B & 3B) with real-time download streaming.
5. 100% Local Neural Voice via Kokoro-82M ('am_lewis' & 'hm_omega').
6. Subagents configuration & seamless connection into Brahma SOL.
"""

from __future__ import annotations

import os
import sys
import json
import time
import shutil
import urllib.request
import urllib.error
import subprocess
import threading
from pathlib import Path
from typing import Optional, Callable, Dict, Any, List

from PyQt6.QtCore import (
    Qt, QObject, pyqtSignal, pyqtSlot, QUrl, QTimer, QPoint, QSize
)
from PyQt6.QtGui import QColor, QFont, QIcon, QPainter, QRegion, QCursor
from PyQt6.QtWidgets import QWidget, QVBoxLayout, QApplication

from PyQt6.QtWebEngineWidgets import QWebEngineView
from PyQt6.QtWebEngineCore import QWebEngineSettings, QWebEnginePage
from PyQt6.QtWebChannel import QWebChannel

BASE_DIR = Path(__file__).resolve().parent
OLLAMA_API_BASE = "http://127.0.0.1:11434"
OLLAMA_DOWNLOAD_URL = "https://ollama.com/download/OllamaSetup.exe"
RECOMMENDED_MODEL = "qwen2.5:7b"
LIGHTWEIGHT_MODEL = "qwen2.5:3b"


# =============================================================================
# 1. OLLAMA ENGINE & MODEL MANAGER
# =============================================================================

class OllamaManager:
    @staticmethod
    def get_ollama_path() -> Optional[Path]:
        which_path = shutil.which("ollama")
        if which_path:
            return Path(which_path)
        candidates = [
            Path(os.environ.get("LOCALAPPDATA", "")) / "Programs" / "Ollama" / "ollama.exe",
            Path(os.environ.get("ProgramFiles", "")) / "Ollama" / "ollama.exe",
            Path(os.environ.get("ProgramFiles(x86)", "")) / "Ollama" / "ollama.exe",
            # macOS
            Path("/usr/local/bin/ollama"),
            Path("/opt/homebrew/bin/ollama"),
            Path("/Applications/Ollama.app/Contents/MacOS/Ollama"),
        ]
        for c in candidates:
            if c.exists():
                return c
        return None

    @classmethod
    def is_installed(cls) -> bool:
        return cls.get_ollama_path() is not None

    @classmethod
    def is_running(cls) -> bool:
        try:
            req = urllib.request.Request(f"{OLLAMA_API_BASE}/api/tags", method="GET")
            with urllib.request.urlopen(req, timeout=1.5) as resp:
                return resp.status == 200
        except Exception:
            return False

    @classmethod
    def get_installed_models(cls) -> List[str]:
        try:
            req = urllib.request.Request(f"{OLLAMA_API_BASE}/api/tags", method="GET")
            with urllib.request.urlopen(req, timeout=2.0) as resp:
                if resp.status == 200:
                    data = json.loads(resp.read().decode("utf-8"))
                    return [m.get("name", "") for m in data.get("models", [])]
        except Exception:
            pass
        return []

    @classmethod
    def start_service_async(cls, callback: Callable[[bool, str], None]):
        def _worker():
            if cls.is_running():
                callback(True, "Ollama service is already operational.")
                return
            exe = cls.get_ollama_path()
            if not exe:
                callback(False, "Ollama executable not found on system.")
                return

            DETACHED = 0x00000008 | 0x00000200 | 0x08000000
            try:
                subprocess.Popen([str(exe), "serve"], creationflags=DETACHED, close_fds=True)
            except Exception as exc:
                callback(False, f"Failed to spawn Ollama daemon: {exc}")
                return

            for _ in range(24):
                time.sleep(0.5)
                if cls.is_running():
                    callback(True, "Ollama daemon connected successfully.")
                    return
            callback(False, "Timeout waiting for Ollama service to respond.")

        threading.Thread(target=_worker, daemon=True, name="OllamaStartWorker").start()

    @classmethod
    def download_and_install_ollama_async(
        cls,
        progress_cb: Callable[[int, str], None],
        finish_cb: Callable[[bool, str], None]
    ):
        def _worker():
            try:
                temp_dir = Path(os.environ.get("TEMP", "."))
                installer_path = temp_dir / "OllamaSetup.exe"

                progress_cb(5, "Contacting official Ollama distribution server...")
                req = urllib.request.Request(
                    OLLAMA_DOWNLOAD_URL,
                    headers={"User-Agent": "Brahma-SOL-Genesis/1.0 (Windows NT 10.0)"}
                )

                with urllib.request.urlopen(req, timeout=60) as response:
                    total_size = int(response.headers.get("content-length", 0))
                    downloaded = 0
                    block_size = 64 * 1024

                    with open(installer_path, "wb") as out_file:
                        while True:
                            chunk = response.read(block_size)
                            if not chunk:
                                break
                            out_file.write(chunk)
                            downloaded += len(chunk)
                            if total_size > 0:
                                pct = min(90, int((downloaded / total_size) * 85) + 5)
                                mb_done = downloaded / (1024 * 1024)
                                mb_tot = total_size / (1024 * 1024)
                                progress_cb(pct, f"Downloading installer: {mb_done:.1f} MB / {mb_tot:.1f} MB ({pct}%)")

                progress_cb(92, "Executing silent Windows setup...")
                proc = subprocess.run([str(installer_path), "/silent"], check=False)
                if proc.returncode != 0:
                    finish_cb(False, f"Installer exited with code {proc.returncode}")
                    return

                progress_cb(96, "Launching local Ollama service daemon...")
                cls.start_service_async(lambda success, msg: finish_cb(success, msg))
            except Exception as exc:
                finish_cb(False, f"Download/Installation failed: {exc}")

        threading.Thread(target=_worker, daemon=True, name="OllamaInstallerWorker").start()

    @classmethod
    def pull_model_stream_async(
        cls,
        model_name: str,
        progress_cb: Callable[[int, str], None],
        finish_cb: Callable[[bool, str], None]
    ):
        def _worker():
            try:
                if not cls.is_running():
                    cls.start_service_async(lambda s, m: None)
                    time.sleep(2.0)

                progress_cb(5, f"Requesting manifest for {model_name}...")
                url = f"{OLLAMA_API_BASE}/api/pull"
                payload = json.dumps({"name": model_name}).encode("utf-8")
                req = urllib.request.Request(
                    url,
                    data=payload,
                    headers={"Content-Type": "application/json"}
                )

                with urllib.request.urlopen(req, timeout=1800) as resp:
                    for line in resp:
                        if not line:
                            continue
                        try:
                            data = json.loads(line.decode("utf-8"))
                            status = data.get("status", "")
                            total = data.get("total", 0)
                            completed = data.get("completed", 0)

                            if total > 0:
                                pct = int((completed / total) * 100)
                                mb_done = completed / (1024 * 1024)
                                mb_tot = total / (1024 * 1024)
                                progress_cb(pct, f"{status}: {mb_done:.1f} MB / {mb_tot:.1f} MB ({pct}%)")
                            elif status:
                                progress_cb(50, status)

                            if status == "success":
                                finish_cb(True, f"Model {model_name} successfully installed & ready!")
                                return
                        except Exception:
                            pass
                finish_cb(True, f"Model {model_name} installation completed.")
            except Exception as exc:
                finish_cb(False, f"Model download error: {exc}")

        threading.Thread(target=_worker, daemon=True, name="OllamaPullWorker").start()


# =============================================================================
# 2. QWEBCHANNEL PYTHON BRIDGE
# =============================================================================

class GenesisBridge(QObject):
    def __init__(self, window: GenesisOnboardingWindow):
        super().__init__()
        self.win = window
        self._muted = False

    @pyqtSlot()
    def requestStatus(self):
        installed = OllamaManager.is_installed()
        running = OllamaManager.is_running()
        models = OllamaManager.get_installed_models() if running else []
        status = {
            "installed": installed,
            "running": running,
            "models": models
        }
        self.win.dispatch_js(f"window.onOllamaStatus({json.dumps(status)});")

    @pyqtSlot()
    def installOllama(self):
        def _prog(pct: int, txt: str):
            clean = txt.replace("'", "\\'")
            self.win.dispatch_js(f"window.onOllamaInstallProgress({pct}, '{clean}');")

        def _done(ok: bool, msg: str):
            clean = msg.replace("'", "\\'")
            self.win.dispatch_js(f"window.onOllamaInstallFinished({str(ok).lower()}, '{clean}');")

        OllamaManager.download_and_install_ollama_async(_prog, _done)

    @pyqtSlot()
    def startOllama(self):
        def _done(ok: bool, msg: str):
            self.requestStatus()

        OllamaManager.start_service_async(_done)

    @pyqtSlot(str)
    def pullModel(self, model_name: str):
        def _prog(pct: int, txt: str):
            clean = txt.replace("'", "\\'")
            self.win.dispatch_js(f"window.onModelDownloadProgress({pct}, '{clean}');")

        def _done(ok: bool, msg: str):
            clean = msg.replace("'", "\\'")
            self.win.dispatch_js(f"window.onModelDownloadFinished({str(ok).lower()}, '{clean}');")

        OllamaManager.pull_model_stream_async(model_name, _prog, _done)

    @pyqtSlot(str)
    def testVoice(self, voice_id: str):
        try:
            from core.kokoro_tts_engine import KokoroTTSEngine
            engine = KokoroTTSEngine.get_instance()
            if engine.is_available:
                engine.speak(
                    "Hello! I am Brahma SOL. My neural voice is running completely locally on your computer.",
                    voice=voice_id,
                    block=False,
                    interrupt=True
                )
        except Exception as exc:
            print(f"[GenesisBridge] Voice test error: {exc}", flush=True)

    @pyqtSlot(str)
    def speakScript(self, text: str):
        if self._muted:
            return
        try:
            from core.kokoro_tts_engine import KokoroTTSEngine
            engine = KokoroTTSEngine.get_instance()
            if engine.is_available:
                engine.speak(text, block=False, interrupt=True)
        except Exception:
            pass

    @pyqtSlot(bool)
    def setMuted(self, muted: bool):
        self._muted = bool(muted)
        if self._muted:
            try:
                from core.kokoro_tts_engine import KokoroTTSEngine
                KokoroTTSEngine.get_instance().stop()
            except Exception:
                pass

    @pyqtSlot()
    def completeGenesis(self):
        self.win.finish_onboarding()


# =============================================================================
# 3. GENESIS ONBOARDING WIDGET (EMBEDDED IN APP) & STANDALONE WINDOW
# =============================================================================

class GenesisOnboardingWidget(QWidget):
    """
    Native in-app Genesis Onboarding view that embeds directly inside
    Brahma Sol's main window (QStackedWidget) matching the app's light theme.
    """
    genesis_completed = pyqtSignal()

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setStyleSheet("background: transparent; border: none;")

        root = QVBoxLayout(self)
        root.setContentsMargins(0, 0, 0, 0)
        root.setSpacing(0)

        # WebEngine View
        self._web = QWebEngineView(self)
        self._page = QWebEnginePage(self._web)
        self._web.setPage(self._page)
        self._page.setBackgroundColor(QColor(0, 0, 0, 0))

        settings = self._web.settings()
        settings.setAttribute(QWebEngineSettings.WebAttribute.LocalContentCanAccessRemoteUrls, True)
        settings.setAttribute(QWebEngineSettings.WebAttribute.LocalContentCanAccessFileUrls, True)
        settings.setAttribute(QWebEngineSettings.WebAttribute.JavascriptEnabled, True)
        settings.setAttribute(QWebEngineSettings.WebAttribute.Accelerated2dCanvasEnabled, True)
        settings.setAttribute(QWebEngineSettings.WebAttribute.WebGLEnabled, True)

        # Setup QWebChannel Bridge
        self._channel = QWebChannel(self._page)
        self._bridge = GenesisBridge(self)
        self._channel.registerObject("pyBridge", self._bridge)
        self._page.setWebChannel(self._channel)

        root.addWidget(self._web)

        # Load Genesis HTML
        html_file = BASE_DIR / "assets" / "genesis" / "index.html"
        self._web.load(QUrl.fromLocalFile(str(html_file.resolve())))

    def dispatch_js(self, js_code: str):
        """Thread-safe dispatching to QWebEngine on Qt GUI main thread."""
        QTimer.singleShot(0, lambda: self._page.runJavaScript(js_code))

    def finish_onboarding(self):
        try:
            from memory.config_manager import save_setting
            save_setting("onboarding_completed", True)
        except Exception:
            pass

        self.genesis_completed.emit()


class GenesisOnboardingWindow(QWidget):
    """
    Standalone floating host window kept for backwards compatibility
    and external testing harness.
    """
    genesis_completed = pyqtSignal()

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Brahma SOL — Genesis Onboarding")
        self.setWindowFlags(
            Qt.WindowType.FramelessWindowHint |
            Qt.WindowType.WindowStaysOnTopHint |
            Qt.WindowType.Tool
        )
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground, True)
        self.resize(1020, 700)

        screen = QApplication.primaryScreen()
        if screen:
            geo = screen.availableGeometry()
            self.move(
                (geo.width() - self.width()) // 2,
                (geo.height() - self.height()) // 2
            )

        root = QVBoxLayout(self)
        root.setContentsMargins(0, 0, 0, 0)
        root.setSpacing(0)

        self._widget = GenesisOnboardingWidget(self)
        self._widget.genesis_completed.connect(self._on_done)
        root.addWidget(self._widget)

        self._drag_pos: Optional[QPoint] = None

    def _on_done(self):
        self.genesis_completed.emit()
        self.close()

    def dispatch_js(self, js_code: str):
        self._widget.dispatch_js(js_code)

    def finish_onboarding(self):
        self._widget.finish_onboarding()

    def mousePressEvent(self, event):
        if event.button() == Qt.MouseButton.LeftButton and event.position().y() <= 40:
            self._drag_pos = event.globalPosition().toPoint() - self.frameGeometry().topLeft()
            event.accept()
        else:
            super().mousePressEvent(event)

    def mouseMoveEvent(self, event):
        if self._drag_pos is not None and event.buttons() == Qt.MouseButton.LeftButton:
            self.move(event.globalPosition().toPoint() - self._drag_pos)
            event.accept()
        else:
            super().mouseMoveEvent(event)

    def mouseReleaseEvent(self, event):
        self._drag_pos = None
        super().mouseReleaseEvent(event)


# Global Singleton Reference
_genesis_window: Optional[GenesisOnboardingWindow] = None

def show_genesis_onboarding(parent=None, on_completed: Optional[Callable[[], None]] = None) -> GenesisOnboardingWindow:
    global _genesis_window
    if _genesis_window is None:
        _genesis_window = GenesisOnboardingWindow(parent)

    if on_completed:
        _genesis_window.genesis_completed.connect(on_completed)

    _genesis_window.show()
    _genesis_window.raise_()
    _genesis_window.activateWindow()
    return _genesis_window
