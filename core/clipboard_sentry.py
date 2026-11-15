"""
Clipboard Sentry for Brahma AI.
Monitors the Windows clipboard in the background for actionable technical content:
- Tracebacks / Exceptions
- JSON structures
- URLs or SQL queries
- Code snippets
Notifies Brahma so it can offer quick contextual assistance.

Thread-safe and hardened against Win32 ctypes heap corruption (0xC0000374).
"""

import sys
import time
import threading
import json
import re
from typing import Optional, Callable

_GLOBAL_CLIP_LOCK = threading.Lock()


def safe_get_clipboard_text() -> str:
    """Safely reads clipboard text without heap corruption or concurrent lock issues."""
    with _GLOBAL_CLIP_LOCK:
        if sys.platform == "win32":
            try:
                import win32clipboard
                import win32con

                opened = False
                for _ in range(5):
                    try:
                        win32clipboard.OpenClipboard()
                        opened = True
                        break
                    except Exception:
                        time.sleep(0.02)

                if opened:
                    try:
                        if win32clipboard.IsClipboardFormatAvailable(win32con.CF_UNICODETEXT):
                            data = win32clipboard.GetClipboardData(win32con.CF_UNICODETEXT)
                            return str(data) if data else ""
                        elif win32clipboard.IsClipboardFormatAvailable(win32con.CF_TEXT):
                            data = win32clipboard.GetClipboardData(win32con.CF_TEXT)
                            if isinstance(data, bytes):
                                return data.decode("utf-8", errors="ignore")
                            return str(data) if data else ""
                    finally:
                        try:
                            win32clipboard.CloseClipboard()
                        except Exception:
                            pass
                    return ""
            except ImportError:
                pass
            except Exception:
                pass

        try:
            import pyperclip
            val = pyperclip.paste()
            return str(val) if val else ""
        except Exception:
            return ""


def safe_set_clipboard_text(text: str) -> None:
    """Safely copies text to clipboard without heap corruption."""
    with _GLOBAL_CLIP_LOCK:
        if sys.platform == "win32":
            try:
                import win32clipboard
                import win32con

                opened = False
                for _ in range(5):
                    try:
                        win32clipboard.OpenClipboard()
                        opened = True
                        break
                    except Exception:
                        time.sleep(0.02)

                if opened:
                    try:
                        win32clipboard.EmptyClipboard()
                        win32clipboard.SetClipboardData(win32con.CF_UNICODETEXT, str(text))
                    finally:
                        try:
                            win32clipboard.CloseClipboard()
                        except Exception:
                            pass
                    return
            except ImportError:
                pass
            except Exception:
                pass

        try:
            import pyperclip
            pyperclip.copy(str(text))
        except Exception:
            pass


def patch_pyperclip() -> None:
    """Patches pyperclip to use safe thread-locked win32clipboard calls on Windows."""
    try:
        import pyperclip
        pyperclip.paste = safe_get_clipboard_text
        pyperclip.copy = safe_set_clipboard_text
    except Exception:
        pass


# Automatically patch pyperclip when this module is imported
patch_pyperclip()


class ClipboardSentry:
    def __init__(self, callback: Optional[Callable[[str, str], None]] = None):
        self._callback = callback
        self._running = False
        self._thread: Optional[threading.Thread] = None
        self._last_clip = ""

    def start(self):
        if self._running:
            return
        self._running = True
        self._thread = threading.Thread(target=self._monitor_loop, daemon=True, name="ClipboardSentryWorker")
        self._thread.start()

    def stop(self):
        self._running = False

    def _classify_content(self, text: str) -> Optional[str]:
        text = text.strip()
        if len(text) < 15:
            return None

        # Check for python / node / java traceback
        if "Traceback (most recent call last):" in text or "Exception:" in text or ("Error:" in text and "\n" in text):
            return "error_traceback"

        # Check for JSON
        if (text.startswith("{") and text.endswith("}")) or (text.startswith("[") and text.endswith("]")):
            try:
                json.loads(text)
                return "json_data"
            except Exception:
                pass

        # Check for SQL queries
        if re.search(r"^\s*(SELECT|INSERT|UPDATE|DELETE|CREATE|ALTER|DROP)\s+", text, re.IGNORECASE):
            return "sql_query"

        # Check for YouTube URL
        if re.search(r"(https?://)?(www\.)?(youtube\.com/watch\?v=|youtu\.be/)[a-zA-Z0-9_-]+", text):
            return "youtube_url"

        # Check for GitHub repository URL
        if re.search(r"(https?://)?(www\.)?github\.com/[a-zA-Z0-9_.-]+/[a-zA-Z0-9_.-]+", text):
            return "github_url"

        # Check for code blocks
        if any(keyword in text for keyword in ["def ", "class ", "function ", "import ", "const ", "let ", "var "]) and "\n" in text:
            return "code_snippet"

        return None

    def _monitor_loop(self):
        try:
            self._last_clip = (safe_get_clipboard_text() or "").strip()
        except Exception:
            self._last_clip = ""

        while self._running:
            time.sleep(1.8)
            try:
                current = (safe_get_clipboard_text() or "").strip()
                if current and current != self._last_clip:
                    self._last_clip = current
                    category = self._classify_content(current)
                    if category and self._callback:
                        self._callback(category, current)
            except Exception:
                pass
