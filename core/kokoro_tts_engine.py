
"""
core/kokoro_tts_engine.py
Production-grade Kokoro-82M Text-to-Speech Engine for Brahma SOL.

Features:
- Offline, fully local speech synthesis using Kokoro-82M ONNX Runtime.
- Hardware-adaptive execution with multi-threaded CPU acceleration.
- Default British English male voice: 'bm_lewis'.
- Default Hindi male voice: 'hm_omega'.
- Automatic multilingual routing (English vs Devanagari text).
- Strict serialized speech queue: completely eliminates dual/overlapping voices.
- Instant preemption & cancellation on user interrupt via monotonic generation IDs.
- Thread-safe singleton with lifecycle callbacks (on_start, on_finish).
- Emergency fallback to Windows SAPI male voice if runtime error occurs.
"""

from __future__ import annotations

import os
os.environ["ONNX_PROVIDER"] = "CPUExecutionProvider"
os.environ["ORT_DISABLE_DIRECTML"] = "1"

import logging
import queue
import re
import sys
import threading
import time
import urllib.request
from pathlib import Path
from typing import Any, Callable, List, Optional, Tuple

import numpy as np

logger = logging.getLogger("KokoroTTSEngine")

# Default voice constants
DEFAULT_ENGLISH_VOICE = "bm_lewis"
DEFAULT_HINDI_VOICE = "hm_omega"
DEFAULT_SAMPLE_RATE = 24000


class KokoroTTSEngine:
    _instance: Optional["KokoroTTSEngine"] = None
    _init_lock = threading.Lock()

    @classmethod
    def get_instance(cls, **kwargs) -> "KokoroTTSEngine":
        with cls._init_lock:
            if cls._instance is None:
                cls._instance = KokoroTTSEngine(**kwargs)
            return cls._instance

    def __init__(
        self,
        model_dir: Optional[str] = None,
        english_voice: str = DEFAULT_ENGLISH_VOICE,
        hindi_voice: str = DEFAULT_HINDI_VOICE,
        speed: float = 1.0,
    ):
        self.english_voice = english_voice
        self.hindi_voice = hindi_voice
        self.speed = speed
        self._is_speaking = False
        self._speech_lock = threading.Lock()

        # Strict concurrency & cancellation controls
        self._queue: queue.Queue = queue.Queue()
        self._gen_id = 0
        self._gen_lock = threading.Lock()
        self._cancel_event = threading.Event()
        self._infer_lock = threading.Lock()

        # Determine model assets directory
        if model_dir:
            self.model_dir = Path(model_dir)
        else:
            candidates = [
                Path(__file__).resolve().parent.parent / "assets" / "tts" / "kokoro",
                Path(sys.executable).resolve().parent / "assets" / "tts" / "kokoro",
                Path(sys.executable).resolve().parent / "_internal" / "assets" / "tts" / "kokoro",
                Path(getattr(sys, '_MEIPASS', '')) / "assets" / "tts" / "kokoro",
                Path(getattr(sys, '_MEIPASS', '')) / "_internal" / "assets" / "tts" / "kokoro",
                Path(os.path.expandvars(r"%LOCALAPPDATA%\Programs\BrahmaSol\_internal\assets\tts\kokoro")),
                Path(os.path.expandvars(r"%LOCALAPPDATA%\Programs\BrahmaSol\assets\tts\kokoro")),
            ]
            self.model_dir = next((p for p in candidates if (p / "kokoro-v1.0.onnx").exists()), candidates[0])

        self.model_path = self.model_dir / "kokoro-v1.0.onnx"
        self.voices_path = self.model_dir / "voices-v1.0.bin"

        self._kokoro = None
        self._available_voices: List[str] = []
        self._initialized = False
        self._init_error: Optional[str] = None

        # Try to initialize Kokoro engine
        self._initialize()

        # Dedicated background speech queue worker thread
        self._worker_thread = threading.Thread(
            target=self._speech_queue_worker,
            daemon=True,
            name="KokoroTTSQueueWorker"
        )
        self._worker_thread.start()

    def _initialize(self) -> bool:
        if self._initialized and self._kokoro is not None:
            return True

        if not self.model_path.exists() or not self.voices_path.exists():
            # Check secondary search for voices_path
            for parent_cand in [
                Path(__file__).resolve().parent.parent,
                Path(sys.executable).resolve().parent,
                Path(sys.executable).resolve().parent / "_internal",
                Path(getattr(sys, '_MEIPASS', '')),
                Path(getattr(sys, '_MEIPASS', '')) / "_internal"
            ]:
                cand_koko = parent_cand / "assets" / "tts" / "kokoro"
                if (cand_koko / "kokoro-v1.0.onnx").exists() and (cand_koko / "voices-v1.0.bin").exists():
                    self.model_dir = cand_koko
                    self.model_path = cand_koko / "kokoro-v1.0.onnx"
                    self.voices_path = cand_koko / "voices-v1.0.bin"
                    break

        if not self.model_path.exists() or not self.voices_path.exists():
            try:
                self.model_dir.mkdir(parents=True, exist_ok=True)
                if not self.model_path.exists():
                    print("[KokoroTTS] 📥 Downloading Kokoro ONNX neural weights (310 MB)...", flush=True)
                    url = "https://github.com/thewh1teagle/kokoro-onnx/releases/download/model-files-v1.0/kokoro-v1.0.onnx"
                    urllib.request.urlretrieve(url, str(self.model_path))
                if not self.voices_path.exists():
                    print("[KokoroTTS] 📥 Downloading voice profiles (26 MB)...", flush=True)
                    url = "https://github.com/thewh1teagle/kokoro-onnx/releases/download/model-files-v1.0/voices-v1.0.bin"
                    urllib.request.urlretrieve(url, str(self.voices_path))
            except Exception as dl_err:
                print(f"[KokoroTTS] ⚠️ Auto-download notice: {dl_err}", flush=True)

        if not self.model_path.exists() or not self.voices_path.exists():
            self._init_error = f"Model assets missing at {self.model_dir}"
            logger.warning("[KokoroTTS] %s", self._init_error)
            print(f"[KokoroTTS] ⚠️ {self._init_error}", flush=True)
            return False

        try:
            import onnxruntime as ort
            from kokoro_onnx import Kokoro
            from kokoro_onnx.config import EspeakConfig

            # Resolve espeak-ng paths robustly
            espeak_lib = None
            espeak_data = None
            try:
                import espeakng_loader
                espeak_lib = espeakng_loader.get_library_path()
                espeak_data = espeakng_loader.get_data_path()
            except Exception:
                pass

            if not espeak_lib or not os.path.exists(espeak_lib) or not espeak_data or not os.path.exists(espeak_data):
                cand_dirs = [
                    Path(__file__).resolve().parent.parent / "espeakng_loader",
                    Path(sys.executable).resolve().parent / "_internal" / "espeakng_loader",
                    Path(sys.executable).resolve().parent / "espeakng_loader",
                    Path(getattr(sys, '_MEIPASS', '')) / "espeakng_loader",
                    Path(getattr(sys, '_MEIPASS', '')) / "_internal" / "espeakng_loader",
                    Path(os.path.expandvars(r"%LOCALAPPDATA%\Programs\BrahmaSol\_internal\espeakng_loader")),
                ]
                for cd in cand_dirs:
                    cand_dll = cd / "espeak-ng.dll"
                    cand_dat = cd / "espeak-ng-data"
                    if cand_dll.exists() and cand_dat.exists():
                        espeak_lib = str(cand_dll)
                        espeak_data = str(cand_dat)
                        break

            espeak_cfg = EspeakConfig(
                lib_path=espeak_lib,
                data_path=espeak_data
            )

            # Initialize clean, battle-tested Kokoro session explicitly on CPU
            # To prevent DirectML / GPU ConvTranspose kernel operator crashes and heap corruption
            session_options = ort.SessionOptions()
            session_options.graph_optimization_level = ort.GraphOptimizationLevel.ORT_ENABLE_ALL
            sess = ort.InferenceSession(
                str(self.model_path),
                sess_options=session_options,
                providers=["CPUExecutionProvider"]
            )
            self._kokoro = Kokoro.from_session(
                session=sess,
                voices_path=str(self.voices_path),
                espeak_config=espeak_cfg
            )
            self._available_voices = self._kokoro.get_voices()
            self._initialized = True
            logger.info("[KokoroTTS] Initialized successfully. Available voices: %d", len(self._available_voices))
            print(f"[KokoroTTS] ✅ Kokoro-82M neural voice engine active ({len(self._available_voices)} voices, voice: {self.english_voice})", flush=True)
            return True
        except Exception as exc:
            self._init_error = str(exc)
            logger.error("[KokoroTTS] Initialization error: %s", exc, exc_info=True)
            print(f"[KokoroTTS] ⚠️ Initialization error: {exc}", flush=True)
            return False

    @property
    def is_available(self) -> bool:
        return self._initialized and self._kokoro is not None

    def is_speaking(self) -> bool:
        return self._is_speaking

    def get_available_voices(self) -> List[str]:
        return list(self._available_voices)

    def set_voices(self, english_voice: Optional[str] = None, hindi_voice: Optional[str] = None):
        if english_voice:
            self.english_voice = english_voice
        if hindi_voice:
            self.hindi_voice = hindi_voice

    def set_speed(self, speed: float):
        self.speed = max(0.5, min(2.0, float(speed)))

    def stop(self):
        """Immediately interrupts speech synthesis and audio playback."""
        with self._gen_lock:
            self._gen_id += 1
            self._cancel_event.set()

        try:
            import sounddevice as sd
            sd.stop()
        except Exception:
            pass

        # Drain pending queue
        while not self._queue.empty():
            try:
                item = self._queue.get_nowait()
                self._queue.task_done()
                if item and len(item) >= 3 and item[2]:  # on_finish
                    try:
                        item[2]()
                    except Exception:
                        pass
            except Exception:
                break

        self._is_speaking = False

    def segment_text(self, text: str) -> List[Tuple[str, str, str]]:
        """
        Splits text into language-coherent segments.
        Returns a list of (segment_text, voice_name, lang_code).
        Merges adjacent sentences in the same language.
        """
        text = (text or "").strip()
        if not text:
            return []

        # Split along sentence boundaries (. ! ? । \n)
        raw_parts = re.split(r'([.!?।\n]+)', text)
        sentences: List[Tuple[str, bool]] = []
        i = 0
        while i < len(raw_parts):
            body = raw_parts[i].strip()
            punct = raw_parts[i + 1].strip() if i + 1 < len(raw_parts) else ""
            if body:
                combined = f"{body} {punct}".strip()
                is_hindi = any('\u0900' <= ch <= '\u097f' for ch in combined)
                sentences.append((combined, is_hindi))
            i += 2

        if not sentences:
            is_hindi = any('\u0900' <= ch <= '\u097f' for ch in text)
            sentences = [(text, is_hindi)]

        # Cluster adjacent sentences of the same language
        clusters: List[Tuple[str, str, str]] = []
        cur_texts: List[str] = []
        cur_is_hindi: Optional[bool] = None

        for s_text, is_hi in sentences:
            if cur_is_hindi is None:
                cur_is_hindi = is_hi
                cur_texts.append(s_text)
            elif cur_is_hindi == is_hi:
                cur_texts.append(s_text)
            else:
                merged = " ".join(cur_texts)
                voice = self.hindi_voice if cur_is_hindi else self.english_voice
                lang = "hi" if cur_is_hindi else "en-gb"
                clusters.append((merged, voice, lang))
                cur_texts = [s_text]
                cur_is_hindi = is_hi

        if cur_texts and cur_is_hindi is not None:
            merged = " ".join(cur_texts)
            voice = self.hindi_voice if cur_is_hindi else self.english_voice
            lang = "hi" if cur_is_hindi else "en-gb"
            clusters.append((merged, voice, lang))

        return clusters

    def _speech_queue_worker(self):
        """Single dedicated worker consuming speech tasks sequentially."""
        while True:
            try:
                item = self._queue.get()
                if item is None:
                    break
                text, on_start, on_finish, gen_id = item

                with self._gen_lock:
                    if gen_id != self._gen_id:
                        self._queue.task_done()
                        if on_finish:
                            try:
                                on_finish()
                            except Exception:
                                pass
                        continue

                self._process_speech_job(text, on_start, on_finish, gen_id)
                self._queue.task_done()
            except Exception as exc:
                logger.error("[KokoroTTS] Worker loop error: %s", exc, exc_info=True)
                time.sleep(0.05)

    def _process_speech_job(
        self,
        text: str,
        on_start: Optional[Callable[[], None]],
        on_finish: Optional[Callable[[], None]],
        gen_id: int
    ):
        with self._speech_lock:
            self._is_speaking = True
            started_fired = False
            try:
                if not self.is_available:
                    if not self._initialize():
                        logger.warning("[KokoroTTS] Kokoro unavailable. Falling back to SAPI male.")
                        self._fallback_sapi(text, on_start, on_finish)
                        return

                segments = self.segment_text(text)
                if not segments:
                    return

                import sounddevice as sd

                # Synthesize and play each segment pipelined
                for seg_text, voice, lang in segments:
                    with self._gen_lock:
                        if gen_id != self._gen_id or self._cancel_event.is_set():
                            break

                    # Fire on_start callback right before first audio plays
                    if not started_fired:
                        started_fired = True
                        if on_start:
                            try:
                                on_start()
                            except Exception as exc:
                                logger.error("[KokoroTTS] on_start callback error: %s", exc)

                    try:
                        # Generate audio samples safely serialized
                        with self._infer_lock:
                            samples, sr = self._kokoro.create(
                                seg_text,
                                voice=voice,
                                speed=self.speed,
                                lang=lang
                            )
                    except (Exception, BaseException) as synth_err:
                        logger.error("[KokoroTTS] Segment synthesis error (%s): %s", voice, synth_err)
                        print(f"[KokoroTTS] Segment synthesis error ({voice}): {synth_err}", flush=True)
                        continue

                    with self._gen_lock:
                        if gen_id != self._gen_id or self._cancel_event.is_set():
                            break

                    if samples is not None and len(samples) > 0:
                        samples_arr = np.ascontiguousarray(samples, dtype=np.float32)
                        print(f"[KokoroTTS] 🔊 Speaking segment aloud ({len(samples_arr)} samples @ {sr}Hz, voice: {voice})...", flush=True)
                        sd.play(samples_arr, sr)
                        duration = len(samples_arr) / float(sr)
                        start_time = time.monotonic()
                        interrupted = False
                        while (time.monotonic() - start_time) < duration:
                            with self._gen_lock:
                                if gen_id != self._gen_id or self._cancel_event.is_set():
                                    interrupted = True
                                    try:
                                        sd.stop()
                                    except Exception:
                                        pass
                                    break
                            time.sleep(0.025)

                        if not interrupted:
                            try:
                                sd.wait()
                            except Exception:
                                pass

            except Exception as exc:
                logger.error("[KokoroTTS] Execution error: %s. Falling back to SAPI male.", exc, exc_info=True)
                self._fallback_sapi(text, on_start, on_finish)
            finally:
                with self._gen_lock:
                    self._cancel_event.clear()
                self._is_speaking = False
                if on_finish:
                    try:
                        on_finish()
                    except Exception as f_err:
                        logger.error("[KokoroTTS] on_finish callback error: %s", f_err)

    def speak(
        self,
        text: str,
        on_start: Optional[Callable[[], None]] = None,
        on_finish: Optional[Callable[[], None]] = None,
        block: bool = False,
        interrupt: bool = False,
    ):
        """
        Vocalizes text using Kokoro-82M via serialized, non-overlapping speech queue.
        Supports preemption / instant cancellation when interrupt=True.
        """
        text = (text or "").strip()
        if not text:
            if on_finish:
                try:
                    on_finish()
                except Exception:
                    pass
            return

        if interrupt:
            self.stop()

        with self._gen_lock:
            self._cancel_event.clear()
            gen_id = self._gen_id

        done_event = threading.Event() if block else None

        def _wrapped_finish():
            if on_finish:
                try:
                    on_finish()
                except Exception:
                    pass
            if done_event:
                done_event.set()

        self._queue.put((text, on_start, _wrapped_finish, gen_id))

        if block and done_event:
            done_event.wait()

    def _fallback_sapi(
        self,
        text: str,
        on_start: Optional[Callable[[], None]] = None,
        on_finish: Optional[Callable[[], None]] = None
    ):
        """Emergency fallback using Windows SAPI male voice (strictly male)."""
        try:
            if on_start:
                try:
                    on_start()
                except Exception:
                    pass

            try:
                import pythoncom
                pythoncom.CoInitialize()
            except Exception:
                pass

            from actions.attention_monitor import _speak_sapi_male
            _speak_sapi_male(text)
        except Exception as sapi_err:
            logger.error("[KokoroTTS] SAPI fallback failed: %s", sapi_err)
        finally:
            if on_finish:
                try:
                    on_finish()
                except Exception:
                    pass
