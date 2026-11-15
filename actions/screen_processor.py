from core.user_paths import get_user_data_dir
import base64
import io
import json
import os
import sys
import time
import threading
import cv2
import mss
import mss.tools
from pathlib import Path

try:
    import PIL.Image
    _PIL_OK = True
except ImportError:
    _PIL_OK = False

def get_base_dir():
    if getattr(sys, "frozen", False):
        return Path(sys.executable).parent
    return Path(__file__).resolve().parent.parent

BASE_DIR        = get_base_dir()
API_CONFIG_PATH = get_user_data_dir() / "config" / "api_keys.json"

IMG_MAX_W = 640
IMG_MAX_H = 360
JPEG_Q    = 60

SYSTEM_PROMPT = (
    "You are Brahma AI - Lite, an open-source assistant. "
    "Analyze images with technical precision and intelligence. "
    "Help the user in a way they can understand — don't be overly complex. "
    "Be concise, smart, and helpful like Brahma AI, personal assistant to User. "
    "Respond in 2-3 short sentences. Speed is priority. "
    "Address the user as 'sir' for a tone of respect."
)

def _get_camera_index() -> int:
    try:
        if API_CONFIG_PATH.exists():
            with open(API_CONFIG_PATH, "r", encoding="utf-8") as f:
                cfg = json.load(f)
            if "camera_index" in cfg:
                return int(cfg["camera_index"])
    except Exception:
        pass

    print("[Camera] [FIND] No camera index in config. Auto-detecting...")
    best_index = 0

    for idx in range(6):
        cap = cv2.VideoCapture(idx, cv2.CAP_DSHOW)
        if not cap.isOpened():
            cap.release()
            continue
        for _ in range(5):
            cap.read()
        ret, frame = cap.read()
        cap.release()
        if ret and frame is not None and frame.mean() > 5:
            best_index = idx
            print(f"[Camera] [OK] Camera found at index {idx} - saving to config.")
            break
        else:
            print(f"[Camera] [WARN] Index {idx}: no valid frame.")

    try:
        cfg = {}
        if API_CONFIG_PATH.exists():
            with open(API_CONFIG_PATH, "r", encoding="utf-8") as f:
                cfg = json.load(f)
        cfg["camera_index"] = best_index
        with open(API_CONFIG_PATH, "w", encoding="utf-8") as f:
            json.dump(cfg, f, indent=4)
        print(f"[Camera] [SAVE] Camera index {best_index} saved to config.")
    except Exception as e:
        print(f"[Camera] [WARN] Could not save camera index: {e}")

    return best_index


def _to_jpeg(img_bytes: bytes) -> bytes:
    if not _PIL_OK:
        return img_bytes
    img = PIL.Image.open(io.BytesIO(img_bytes)).convert("RGB")
    resample = getattr(PIL.Image, "Resampling", PIL.Image).BILINEAR
    img.thumbnail([IMG_MAX_W, IMG_MAX_H], resample)
    buf = io.BytesIO()
    img.save(buf, format="JPEG", quality=JPEG_Q, optimize=False)
    return buf.getvalue()


def _capture_screenshot() -> bytes:
    try:
        if _PIL_OK:
            from PIL import ImageGrab
            img = ImageGrab.grab(all_screens=True).convert("RGB")
            resample = getattr(PIL.Image, "Resampling", PIL.Image).BILINEAR
            img.thumbnail([IMG_MAX_W, IMG_MAX_H], resample)
            buf = io.BytesIO()
            img.save(buf, format="JPEG", quality=JPEG_Q, optimize=False)
            return buf.getvalue()
        else:
            raise RuntimeError("PIL not available")
    except Exception as e:
        print(f"[ScreenProcess] PIL ImageGrab failed ({e}). Falling back to mss.")
        with mss.mss() as sct:
            monitors = getattr(sct, "monitors", []) or []
            if len(monitors) > 1:
                monitor = monitors[1]
            elif monitors:
                monitor = monitors[0]
            else:
                raise RuntimeError("No monitors were detected for screen capture.")
            shot = sct.grab(monitor)
            png_bytes = mss.tools.to_png(shot.rgb, shot.size)
        return _to_jpeg(png_bytes)


def _capture_camera() -> bytes:
    camera_index = _get_camera_index()
    cap = cv2.VideoCapture(camera_index, cv2.CAP_DSHOW)
    if not cap.isOpened():
        cap = cv2.VideoCapture(camera_index)
    if not cap.isOpened():
        raise RuntimeError(f"Webcam could not be opened on device index {camera_index}. Please check webcam privacy permissions in Windows Settings.")
    for _ in range(5):
        cap.read()
    ret, frame = cap.read()
    cap.release()
    if not ret or frame is None:
        raise RuntimeError("Could not capture camera frame.")
    if _PIL_OK:
        rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
        img = PIL.Image.fromarray(rgb)
        img.thumbnail([IMG_MAX_W, IMG_MAX_H], PIL.Image.BILINEAR)
        buf = io.BytesIO()
        img.save(buf, format="JPEG", quality=JPEG_Q, optimize=False)
        return buf.getvalue()
    _, buf = cv2.imencode(".jpg", frame, [cv2.IMWRITE_JPEG_QUALITY, JPEG_Q])
    return buf.tobytes()


def _speak_local(text: str):
    """Speaks using local Kokoro neural TTS, fallback to SAPI if unavailable."""
    try:
        from core.kokoro_tts_engine import KokoroTTSEngine
        engine = KokoroTTSEngine.get_instance()
        if engine.is_available:
            engine.speak(text, block=False)
            return
    except Exception:
        pass
    def _worker():
        try:
            import win32com.client
            import pythoncom
            pythoncom.CoInitialize()
            voice = win32com.client.Dispatch("SAPI.SpVoice")
            voice.Speak(text)
        except Exception as e:
            print(f"[ScreenProcess] SAPI speech error: {e}")
    threading.Thread(target=_worker, daemon=True).start()


def screen_process(
    parameters:     dict,
    response:       str | None = None,
    player=None,
    session_memory=None,
    image_bytes:    bytes | None = None,
    speak=None,
) -> bool:
    user_text = (parameters or {}).get("text") or (parameters or {}).get("user_text", "")
    user_text = (user_text or "").strip()
    if not user_text:
        user_text = "Describe what you see in detail, sir."

    angle = (parameters or {}).get("angle", "screen").lower().strip()
    print(f"[ScreenProcess] [LOCAL VISION] angle={angle!r}  text={user_text!r}")

    def _screen_failure(message: str) -> bool:
        print(f"[ScreenProcess] [FAIL] {message}")
        if player and hasattr(player, "update_task_workspace"):
            try:
                player.update_task_workspace(
                    status="Visual analysis failed",
                    output=message,
                    percent=0,
                )
            except Exception:
                pass
        if player and hasattr(player, "write_log"):
            player.write_log(f"System Event: {message}")
        if player and hasattr(player, "set_scanning") and angle != "camera":
            player.set_scanning(False, "")
        if speak:
            speak(message)
        else:
            _speak_local(message)
        return False

    if player and hasattr(player, "set_scanning") and angle != "camera":
        player.set_scanning(True, "SCANNING SCREEN")

    try:
        if angle == "camera":
            image_bytes = _capture_camera()
            print("[ScreenProcess] [CAMERA] Camera frame captured")
        elif angle in ("active_window", "window") or (parameters or {}).get("target") == "active_window":
            from core.window_context import capture_active_window_screenshot
            image_bytes = capture_active_window_screenshot()
            if not image_bytes:
                image_bytes = _capture_screenshot()
            print("[ScreenProcess] [WINDOW] Active window captured")
        else:
            if not image_bytes:
                image_bytes = _capture_screenshot()
                print("[ScreenProcess] [SCREEN] Screen captured")
    except Exception as e:
        print(f"[ScreenProcess] [ERR] Capture error: {e}")
        return _screen_failure(f"Failed to capture visual frame: {e}")

    if not image_bytes:
        return _screen_failure("Screen or camera capture returned empty data.")

    # Foreground window title enrichment
    if angle != "camera":
        try:
            from core.window_context import get_foreground_window_info
            w_info = get_foreground_window_info()
            if w_info and w_info.get("title"):
                w_title = w_info.get("title", "").strip()
                if w_title and "brahma" not in w_title.lower():
                    context_tag = f"\n[User's Active Focused Window: {w_title}]"
                    if context_tag not in user_text:
                        user_text += context_tag
        except Exception:
            pass

    try:
        b64 = base64.b64encode(image_bytes).decode("utf-8")
        from llm_client import client as ai_client
        
        full_prompt = f"{SYSTEM_PROMPT}\n\nUser Question: {user_text}"
        analysis = ai_client.vision(prompt=full_prompt, image_b64=b64)
        
        if not analysis:
            return _screen_failure("Vision analysis returned no response from AI models.")

        analysis = analysis.strip()
        print(f"[ScreenProcess] [VISION RESULT]: {analysis}")

        if player and hasattr(player, "set_scanning"):
            player.set_scanning(False, "")

        if player and hasattr(player, "update_task_workspace"):
            workspace_title = "Webcam Inspection" if angle == "camera" else "Screen Analysis"
            player.update_task_workspace(
                title=workspace_title,
                status="Analysis Complete",
                output=analysis,
                percent=100
            )

        if player and hasattr(player, "write_log"):
            player.write_log(f"Brahma Sol: {analysis}")

        if speak:
            speak(analysis)
        else:
            _speak_local(analysis)

        return True

    except Exception as e:
        print(f"[ScreenProcess] [ERR] Vision analysis error: {e}")
        return _screen_failure(f"Vision analysis error: {e}")


def warmup_session(player=None):
    pass
