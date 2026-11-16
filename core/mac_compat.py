"""
macOS compatibility layer for Brahma Sol.

Provides cross-platform replacements for the Win32 / pycaw / pywinauto /
win10toast / winreg / os.startfile calls used throughout the codebase.
Every function is safe to call on any OS: on Windows it defers to the
original behaviour where practical, on macOS it uses osascript / open /
pmset / pyobjc, and otherwise it fails soft (returns False / None).
"""
from __future__ import annotations

import os
import shutil
import subprocess
import sys
from pathlib import Path
from typing import Optional

IS_MAC = sys.platform == "darwin"
IS_WIN = os.name == "nt"

# Use as **NO_WINDOW in subprocess calls instead of creationflags=CREATE_NO_WINDOW
NO_WINDOW: dict = {"creationflags": subprocess.CREATE_NO_WINDOW} if IS_WIN else {}
CREATE_NO_WINDOW: int = getattr(subprocess, "CREATE_NO_WINDOW", 0)


def _osa(script: str, timeout: float = 10) -> str:
    """Run AppleScript and return stdout ('' on failure)."""
    try:
        r = subprocess.run(["osascript", "-e", script], capture_output=True,
                           text=True, timeout=timeout)
        return (r.stdout or "").strip()
    except Exception:
        return ""


def _esc(s: str) -> str:
    return str(s).replace("\\", "\\\\").replace('"', '\\"')


# ── Files / apps ──────────────────────────────────────────────────────────
def startfile(path: str | os.PathLike) -> bool:
    """Cross-platform os.startfile."""
    try:
        if IS_WIN:
            os.startfile(str(path))  # type: ignore[attr-defined]
        elif IS_MAC:
            subprocess.Popen(["open", str(path)])
        else:
            subprocess.Popen(["xdg-open", str(path)])
        return True
    except Exception:
        return False


def open_url(url: str) -> bool:
    return startfile(url)


def open_app(name: str) -> bool:
    """Launch an application by name (mac: `open -a`)."""
    if IS_MAC:
        r = subprocess.run(["open", "-a", name], capture_output=True)
        return r.returncode == 0
    return startfile(name)


def quit_app(name: str) -> bool:
    if IS_MAC:
        _osa(f'tell application "{_esc(name)}" to quit')
        return True
    return False


def reveal_in_finder(path: str | os.PathLike) -> bool:
    if IS_MAC:
        return subprocess.run(["open", "-R", str(path)]).returncode == 0
    if IS_WIN:
        subprocess.Popen(["explorer", "/select,", str(path)])
        return True
    return startfile(Path(path).parent)


def get_desktop_dir() -> Path:
    return Path.home() / "Desktop"


# ── Audio volume (replaces pycaw) ────────────────────────────────────────
def get_volume() -> Optional[int]:
    if IS_MAC:
        v = _osa("output volume of (get volume settings)")
        return int(v) if v.isdigit() else None
    try:
        from comtypes import CLSCTX_ALL  # type: ignore
        from pycaw.pycaw import AudioUtilities, IAudioEndpointVolume  # type: ignore
        from ctypes import cast, POINTER
        dev = AudioUtilities.GetSpeakers()
        iface = dev.Activate(IAudioEndpointVolume._iid_, CLSCTX_ALL, None)
        vol = cast(iface, POINTER(IAudioEndpointVolume))
        return int(round(vol.GetMasterVolumeLevelScalar() * 100))
    except Exception:
        return None


def set_volume(level: int) -> bool:
    level = max(0, min(100, int(level)))
    if IS_MAC:
        _osa(f"set volume output volume {level}")
        return True
    try:
        from comtypes import CLSCTX_ALL  # type: ignore
        from pycaw.pycaw import AudioUtilities, IAudioEndpointVolume  # type: ignore
        from ctypes import cast, POINTER
        dev = AudioUtilities.GetSpeakers()
        iface = dev.Activate(IAudioEndpointVolume._iid_, CLSCTX_ALL, None)
        cast(iface, POINTER(IAudioEndpointVolume)).SetMasterVolumeLevelScalar(level / 100, None)
        return True
    except Exception:
        return False


def change_volume(delta: int) -> bool:
    cur = get_volume()
    if cur is None:
        return False
    return set_volume(cur + delta)


def set_mute(mute: bool = True) -> bool:
    if IS_MAC:
        _osa(f"set volume output muted {'true' if mute else 'false'}")
        return True
    return False


def is_muted() -> Optional[bool]:
    if IS_MAC:
        return _osa("output muted of (get volume settings)") == "true"
    return None


# ── Brightness ───────────────────────────────────────────────────────────
def set_brightness(level: int) -> bool:
    """mac: uses `brightness` CLI if installed (brew install brightness),
    otherwise steps brightness keys via System Events (key codes 144/145)."""
    level = max(0, min(100, int(level)))
    if IS_MAC:
        if shutil.which("brightness"):
            return subprocess.run(["brightness", str(level / 100)]).returncode == 0
        # fallback: drop to zero then step up (16 steps on mac)
        steps = round(level / 100 * 16)
        script = ('tell application "System Events"\n'
                  'repeat 16 times\nkey code 145\nend repeat\n'
                  f'repeat {steps} times\nkey code 144\nend repeat\nend tell')
        _osa(script)
        return True
    return False


def change_brightness(up: bool, steps: int = 2) -> bool:
    if IS_MAC:
        code = 144 if up else 145
        _osa(f'tell application "System Events" to repeat {steps} times\nkey code {code}\nend repeat')
        return True
    return False


# ── Media keys ───────────────────────────────────────────────────────────
def media_key(action: str) -> bool:
    """action: playpause | next | previous. Targets Spotify/Music if running."""
    if not IS_MAC:
        return False
    cmd = {"playpause": "playpause", "play": "play", "pause": "pause",
           "next": "next track", "previous": "previous track"}.get(action)
    if not cmd:
        return False
    for app in ("Spotify", "Music"):
        running = _osa(f'application "{app}" is running')
        if running == "true":
            _osa(f'tell application "{app}" to {cmd}')
            return True
    return False


# ── System power ─────────────────────────────────────────────────────────
def lock_screen() -> bool:
    if IS_MAC:
        _osa('tell application "System Events" to keystroke "q" using {control down, command down}')
        return True
    return False


def sleep_display() -> bool:
    if IS_MAC:
        return subprocess.run(["pmset", "displaysleepnow"]).returncode == 0
    return False


def sleep_system() -> bool:
    if IS_MAC:
        _osa('tell application "System Events" to sleep')
        return True
    return False


def shutdown() -> bool:
    if IS_MAC:
        _osa('tell application "System Events" to shut down')
        return True
    return False


def restart() -> bool:
    if IS_MAC:
        _osa('tell application "System Events" to restart')
        return True
    return False


def empty_trash() -> bool:
    if IS_MAC:
        _osa('tell application "Finder" to empty trash')
        return True
    return False


def toggle_dark_mode(enable: Optional[bool] = None) -> bool:
    if IS_MAC:
        val = "not dark mode" if enable is None else ("true" if enable else "false")
        _osa(f'tell application "System Events" to tell appearance preferences to set dark mode to {val}')
        return True
    return False


def set_wifi(on: bool) -> bool:
    if IS_MAC:
        return subprocess.run(["networksetup", "-setairportpower", "en0",
                               "on" if on else "off"]).returncode == 0
    return False


# ── Notifications (replaces win10toast) ──────────────────────────────────
def notify(title: str, message: str, duration: int = 5) -> bool:
    if IS_MAC:
        _osa(f'display notification "{_esc(message)}" with title "{_esc(title)}"')
        return True
    try:
        from win10toast import ToastNotifier  # type: ignore
        ToastNotifier().show_toast(title, message, duration=duration, threaded=True)
        return True
    except Exception:
        return False


# ── Wallpaper ────────────────────────────────────────────────────────────
def set_wallpaper(path: str | os.PathLike) -> bool:
    p = str(Path(path).resolve())
    if IS_MAC:
        _osa(f'tell application "System Events" to tell every desktop to set picture to "{_esc(p)}"')
        return True
    if IS_WIN:
        import ctypes
        ctypes.windll.user32.SystemParametersInfoW(20, 0, p, 3)  # type: ignore
        return True
    return False


# ── Clipboard ────────────────────────────────────────────────────────────
def get_clipboard() -> str:
    try:
        import pyperclip
        return pyperclip.paste() or ""
    except Exception:
        if IS_MAC:
            try:
                return subprocess.run(["pbpaste"], capture_output=True, text=True).stdout
            except Exception:
                pass
    return ""


def set_clipboard(text: str) -> bool:
    try:
        import pyperclip
        pyperclip.copy(text)
        return True
    except Exception:
        if IS_MAC:
            subprocess.run(["pbcopy"], input=text, text=True)
            return True
    return False


# ── Windows / focus (replaces pygetwindow / pywinauto / GetForegroundWindow) ─
def get_active_app() -> str:
    """Name of the frontmost application (e.g. 'Safari')."""
    if IS_MAC:
        try:
            from AppKit import NSWorkspace  # type: ignore
            app = NSWorkspace.sharedWorkspace().frontmostApplication()
            return str(app.localizedName() or "")
        except Exception:
            return _osa('tell application "System Events" to get name of first '
                        'application process whose frontmost is true')
    return ""


def get_active_window_title() -> str:
    if IS_MAC:
        try:
            import Quartz  # type: ignore
            front = get_active_app()
            wins = Quartz.CGWindowListCopyWindowInfo(
                Quartz.kCGWindowListOptionOnScreenOnly | Quartz.kCGWindowListExcludeDesktopElements,
                Quartz.kCGNullWindowID)
            for w in wins or []:
                if w.get("kCGWindowOwnerName") == front and w.get("kCGWindowLayer", 1) == 0:
                    return str(w.get("kCGWindowName") or front)
            return front
        except Exception:
            return get_active_app()
    if IS_WIN:
        try:
            import ctypes
            u = ctypes.windll.user32  # type: ignore
            h = u.GetForegroundWindow()
            n = u.GetWindowTextLengthW(h)
            buf = ctypes.create_unicode_buffer(n + 1)
            u.GetWindowTextW(h, buf, n + 1)
            return buf.value
        except Exception:
            return ""
    return ""


def list_window_titles() -> list[str]:
    if IS_MAC:
        try:
            import Quartz  # type: ignore
            wins = Quartz.CGWindowListCopyWindowInfo(
                Quartz.kCGWindowListOptionOnScreenOnly, Quartz.kCGNullWindowID)
            out = []
            for w in wins or []:
                if w.get("kCGWindowLayer", 1) == 0:
                    owner = w.get("kCGWindowOwnerName") or ""
                    name = w.get("kCGWindowName") or ""
                    out.append(f"{owner} - {name}" if name else owner)
            return out
        except Exception:
            return []
    try:
        import pygetwindow as gw  # type: ignore
        return [t for t in gw.getAllTitles() if t]
    except Exception:
        return []


def focus_app(name: str) -> bool:
    if IS_MAC:
        _osa(f'tell application "{_esc(name)}" to activate')
        return True
    try:
        import pygetwindow as gw  # type: ignore
        w = gw.getWindowsWithTitle(name)
        if w:
            w[0].activate()
            return True
    except Exception:
        pass
    return False


def minimize_all() -> bool:
    """Show desktop."""
    if IS_MAC:
        # F11 / Mission Control 'show desktop' = key code 103
        _osa('tell application "System Events" to key code 103')
        return True
    return False


def get_idle_seconds() -> float:
    if IS_MAC:
        try:
            import Quartz  # type: ignore
            return float(Quartz.CGEventSourceSecondsSinceLastEventType(
                Quartz.kCGEventSourceStateCombinedSessionState, Quartz.kCGAnyInputEventType))
        except Exception:
            return 0.0
    if IS_WIN:
        try:
            import ctypes

            class LASTINPUTINFO(ctypes.Structure):
                _fields_ = [("cbSize", ctypes.c_uint), ("dwTime", ctypes.c_uint)]
            li = LASTINPUTINFO()
            li.cbSize = ctypes.sizeof(li)
            ctypes.windll.user32.GetLastInputInfo(ctypes.byref(li))  # type: ignore
            return (ctypes.windll.kernel32.GetTickCount() - li.dwTime) / 1000.0  # type: ignore
        except Exception:
            return 0.0
    return 0.0


# ── Text-to-speech fallback (replaces SAPI) ──────────────────────────────
def say(text: str, voice: Optional[str] = None, block: bool = False):
    if IS_MAC:
        cmd = ["say"] + (["-v", voice] if voice else []) + [text]
        if block:
            subprocess.run(cmd)
            return None
        return subprocess.Popen(cmd)
    return None


# ── Typing into an app ───────────────────────────────────────────────────
def type_text(text: str) -> bool:
    if IS_MAC:
        _osa(f'tell application "System Events" to keystroke "{_esc(text)}"')
        return True
    try:
        import pyautogui
        pyautogui.typewrite(text, interval=0.01)
        return True
    except Exception:
        return False


def open_text_editor_and_type(text: str) -> bool:
    """mac equivalent of 'open notepad and type ...' using TextEdit."""
    if IS_MAC:
        _osa('tell application "TextEdit"\nactivate\nmake new document\n'
             f'set text of front document to "{_esc(text)}"\nend tell')
        return True
    return False


# Map Windows app names → mac app names
APP_ALIASES = {
    "notepad": "TextEdit", "wordpad": "TextEdit", "calculator": "Calculator",
    "calc": "Calculator", "explorer": "Finder", "file explorer": "Finder",
    "cmd": "Terminal", "powershell": "Terminal", "terminal": "Terminal",
    "task manager": "Activity Monitor", "taskmgr": "Activity Monitor",
    "control panel": "System Settings", "settings": "System Settings",
    "paint": "Preview", "mspaint": "Preview", "snipping tool": "Screenshot",
    "edge": "Microsoft Edge", "chrome": "Google Chrome", "firefox": "Firefox",
    "whatsapp": "WhatsApp", "spotify": "Spotify", "discord": "Discord",
    "vscode": "Visual Studio Code", "vs code": "Visual Studio Code", "code": "Visual Studio Code",
    "word": "Microsoft Word", "excel": "Microsoft Excel", "powerpoint": "Microsoft PowerPoint",
    "outlook": "Microsoft Outlook", "teams": "Microsoft Teams", "music": "Music",
    "mail": "Mail", "camera": "Photo Booth", "photos": "Photos", "clock": "Clock",
}


def mac_app_name(name: str) -> str:
    return APP_ALIASES.get(name.strip().lower(), name)
