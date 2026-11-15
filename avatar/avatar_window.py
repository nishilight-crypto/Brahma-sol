"""
avatar/avatar_window.py
=======================
Always-On-Top, Transparent Desktop 3D Avatar Window for Brahma Sol.

Hosts the WebGL Three.js viewport in a frameless, transparent QWebEngineView.
Handles:
1. True desktop alpha transparency & 60 FPS Three.js WebGL rendering.
2. Direct communication via QWebChannel and runJavaScript.
3. Autonomous Desktop Roaming, continuous locomotion & turn kinematics.
4. Interactive dragging with airborne reactions and impact landing physics.
5. Intelligent behavior state machine, posture transitions (Standing, Sitting, Sleeping).
6. Subtle global cursor tracking across the entire desktop.
7. Right-click desktop context menu for instant pet commands & toggles.
8. File drop perception and dashboard toggle events.
"""

from __future__ import annotations

import os
import sys
import time
from pathlib import Path
from typing import Optional, Callable

from PyQt6.QtCore import (
    Qt, QObject, pyqtSlot, pyqtSignal, QUrl, QPoint, QTimer, QPropertyAnimation, QEasingCurve
)
from PyQt6.QtGui import QColor, QScreen, QGuiApplication, QCursor, QAction, QFont, QIcon
from PyQt6.QtWidgets import QMainWindow, QApplication, QMenu
from PyQt6.QtWebEngineWidgets import QWebEngineView
from PyQt6.QtWebEngineCore import QWebEngineSettings, QWebEnginePage
from PyQt6.QtWebChannel import QWebChannel

from core.proprioception import ProprioceptionEngine, KinematicActionStep, PostureState, ActivityState
from core.locomotion_controller import DesktopLocomotionController
from core.behaviour_system import SolBehaviourSystem


class SolWebPage(QWebEnginePage):
    """Custom page capturing JavaScript console logs for Python terminal."""
    def javaScriptConsoleMessage(self, level, message, lineNumber, sourceID):
        print(f"[3D Stage JS] {message}", flush=True)


class AvatarBridge(QObject):
    """Bridge exposed to JavaScript inside QWebEngineView."""
    clip_finished = pyqtSignal(str)
    file_dropped = pyqtSignal(str, int)
    avatar_clicked = pyqtSignal()
    telemetry_received = pyqtSignal(dict)
    context_menu_requested = pyqtSignal(int, int)
    drag_started = pyqtSignal(int, int)
    drag_moved = pyqtSignal(int, int)
    drag_ended = pyqtSignal(int, int)

    @pyqtSlot(int, int)
    def onDragStart(self, screen_x: int, screen_y: int):
        self.drag_started.emit(screen_x, screen_y)

    @pyqtSlot(int, int)
    def onDragMove(self, screen_x: int, screen_y: int):
        self.drag_moved.emit(screen_x, screen_y)

    @pyqtSlot(int, int)
    def onDragEnd(self, screen_x: int, screen_y: int):
        self.drag_ended.emit(screen_x, screen_y)

    @pyqtSlot(str)
    def onClipFinished(self, clip_name: str):
        self.clip_finished.emit(clip_name)

    @pyqtSlot(str, int)
    def onFileDropped(self, file_name: str, file_size: int):
        self.file_dropped.emit(file_name, file_size)

    @pyqtSlot()
    def onAvatarClicked(self):
        self.avatar_clicked.emit()

    @pyqtSlot(int, int)
    def onContextMenu(self, screen_x: int, screen_y: int):
        self.context_menu_requested.emit(screen_x, screen_y)

    @pyqtSlot(str)
    def onTelemetry(self, raw_json: str):
        import json
        try:
            data = json.loads(raw_json)
            self.telemetry_received.emit(data)
        except Exception:
            pass


class BrahmaSolAvatarWindow(QMainWindow):
    """The physical desktop body of Brahma Sol."""

    toggle_dashboard = pyqtSignal()
    file_received = pyqtSignal(str)

    # Thread-safe signals for cross-thread calls
    _sig_play_clip = pyqtSignal(str, float, bool)
    _sig_say = pyqtSignal(str, float)
    _sig_hide_speech = pyqtSignal()
    _sig_look_at = pyqtSignal(float, float)
    _sig_move_to = pyqtSignal(int, int, float)
    _sig_execute_steps = pyqtSignal(object)
    _sig_set_heading = pyqtSignal(float)
    _sig_speech_start = pyqtSignal(str, str)
    _sig_speech_end = pyqtSignal()
    _sig_listening_start = pyqtSignal()
    _sig_listening_end = pyqtSignal()
    _sig_thinking_start = pyqtSignal()
    _sig_celebrate = pyqtSignal(str)
    _sig_confusion = pyqtSignal(str)
    _sig_task_action = pyqtSignal(str, str)

    def __init__(self, proprioception: Optional[ProprioceptionEngine] = None):
        super().__init__()
        self.proprioception = proprioception or ProprioceptionEngine()

        # Window properties: Frameless, Always on Top, Translucent Tool Window
        self.setWindowFlags(
            Qt.WindowType.FramelessWindowHint |
            Qt.WindowType.WindowStaysOnTopHint |
            Qt.WindowType.Tool
        )
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground, True)
        self.setAttribute(Qt.WidgetAttribute.WA_NoSystemBackground, True)

        # Dimensions: 440w x 540h (character + speech bubble headroom)
        self.avatar_width = 440
        self.avatar_height = 540
        self.resize(self.avatar_width, self.avatar_height)

        # Initial desktop placement (Bottom-right corner above taskbar)
        screen = QGuiApplication.primaryScreen()
        if screen:
            screen_geo = screen.availableGeometry()
            init_x = screen_geo.left() + screen_geo.width() - self.avatar_width - 30
            init_y = screen_geo.top() + screen_geo.height() - self.avatar_height - 10
            self.move(init_x, init_y)
            self.proprioception.world_x = float(init_x)
            self.proprioception.world_y = float(init_y)

        # Setup WebEngineView with transparent background
        self.web_view = QWebEngineView(self)
        self.web_page = SolWebPage(self.web_view)
        self.web_view.setPage(self.web_page)
        self.setCentralWidget(self.web_view)

        # Configure settings
        settings = self.web_view.settings()
        settings.setAttribute(QWebEngineSettings.WebAttribute.LocalContentCanAccessRemoteUrls, True)
        settings.setAttribute(QWebEngineSettings.WebAttribute.LocalContentCanAccessFileUrls, True)
        settings.setAttribute(QWebEngineSettings.WebAttribute.JavascriptEnabled, True)
        settings.setAttribute(QWebEngineSettings.WebAttribute.Accelerated2dCanvasEnabled, True)
        settings.setAttribute(QWebEngineSettings.WebAttribute.WebGLEnabled, True)

        self.web_page.setBackgroundColor(QColor(0, 0, 0, 0))
        self.web_view.setStyleSheet("background: transparent;")
        self.setStyleSheet("background: transparent;")

        # Setup QWebChannel bridge
        self.channel = QWebChannel(self.web_page)
        self.bridge = AvatarBridge()
        self.channel.registerObject("pyBridge", self.bridge)
        self.web_page.setWebChannel(self.channel)

        # Connect bridge signals
        self.bridge.avatar_clicked.connect(self._handle_avatar_click)
        self.bridge.file_dropped.connect(self._handle_file_drop)
        self.bridge.clip_finished.connect(self._handle_clip_finished)
        self.bridge.context_menu_requested.connect(self._show_context_menu)
        self.bridge.drag_started.connect(self._handle_drag_start)
        self.bridge.drag_moved.connect(self._handle_drag_move)
        self.bridge.drag_ended.connect(self._handle_drag_end)

        self._drag_offset_x = 0
        self._drag_offset_y = 0

        # Dragging window support
        self._is_dragging = False
        self._drag_start_pos = QPoint()
        self._press_global_pos = QPoint()
        self._drag_offset_x = 0
        self._drag_offset_y = 0
        # Ultra-fast 60 FPS hardware cursor drag tracker (smooth DWM sync, strict work area clamping)
        self._drag_timer = QTimer(self)
        self._drag_timer.setInterval(16)  # 60 Hz DWM sync
        self._drag_timer.timeout.connect(self._track_hardware_drag)

        # Autonomous movement animation with constant linear stride (eliminates foot-sliding)
        self._move_anim = QPropertyAnimation(self, b"pos")
        self._move_anim.setEasingCurve(QEasingCurve.Type.Linear)
        self._move_anim.finished.connect(self._handle_move_finished)

        # Subsystems: Locomotion Controller & Intelligent Behavior System
        self.locomotion = DesktopLocomotionController(self, self.proprioception, parent=self)
        self.behaviour = SolBehaviourSystem(self, self.locomotion, self.proprioception, parent=self)

        # Connect thread-safe dispatchers (queued to Qt main thread)
        self._sig_play_clip.connect(self._do_play_clip, Qt.ConnectionType.QueuedConnection)
        self._sig_say.connect(self._do_say, Qt.ConnectionType.QueuedConnection)
        self._sig_hide_speech.connect(self._do_hide_speech, Qt.ConnectionType.QueuedConnection)
        self._sig_look_at.connect(self._do_look_at, Qt.ConnectionType.QueuedConnection)
        self._sig_move_to.connect(self._do_move_to, Qt.ConnectionType.QueuedConnection)
        self._sig_execute_steps.connect(self._do_execute_kinematic_steps, Qt.ConnectionType.QueuedConnection)
        self._sig_set_heading.connect(self._do_set_heading, Qt.ConnectionType.QueuedConnection)
        self._sig_speech_start.connect(self._do_speech_start, Qt.ConnectionType.QueuedConnection)
        self._sig_speech_end.connect(self._do_speech_end, Qt.ConnectionType.QueuedConnection)
        self._sig_listening_start.connect(self._do_listening_start, Qt.ConnectionType.QueuedConnection)
        self._sig_listening_end.connect(self._do_listening_end, Qt.ConnectionType.QueuedConnection)
        self._sig_thinking_start.connect(self._do_thinking_start, Qt.ConnectionType.QueuedConnection)
        self._sig_celebrate.connect(self._do_celebrate, Qt.ConnectionType.QueuedConnection)
        self._sig_confusion.connect(self._do_confusion, Qt.ConnectionType.QueuedConnection)
        self._sig_task_action.connect(self._do_task_action, Qt.ConnectionType.QueuedConnection)

        # Load local HTML stage
        html_path = Path(__file__).resolve().parent / "avatar_stage.html"
        self.web_view.load(QUrl.fromLocalFile(str(html_path)))

        # Telemetry timer (2 Hz)
        self._sync_timer = QTimer(self)
        self._sync_timer.timeout.connect(self._sync_telemetry)
        self._sync_timer.start(500)

        # Vocalize initial welcome when stage is ready
        QTimer.singleShot(2200, lambda: self.say("Brahma Sol online and operational. Ready when you are.", 4.0, vocalize=True))

    def _handle_move_finished(self) -> None:
        """Called immediately when QPropertyAnimation reaches destination."""
        if hasattr(self, "locomotion") and self.locomotion and hasattr(self.locomotion, "on_movement_finished"):
            self.locomotion.on_movement_finished()

    # =========================================================================
    # HIGH-LEVEL SPEECH & EMOTIONAL REACTION INTERFACES (THREAD-SAFE)
    # =========================================================================

    def start_speaking(self, text: str, emotion: str = "neutral") -> None:
        """Starts synchronized speech animation & bubble (thread-safe)."""
        self._sig_speech_start.emit(str(text or ""), str(emotion or "neutral"))

    def _do_speech_start(self, text: str, emotion: str) -> None:
        if hasattr(self, "behaviour") and self.behaviour:
            self.behaviour.on_speech_start(text, emotion)

    def stop_speaking(self) -> None:
        """Stops speech animation and returns to posture idle (thread-safe)."""
        self._sig_speech_end.emit()

    def _do_speech_end(self) -> None:
        if hasattr(self, "behaviour") and self.behaviour:
            self.behaviour.on_speech_end()

    def start_listening(self) -> None:
        """Enters attentive listening posture (thread-safe)."""
        self._sig_listening_start.emit()

    def _do_listening_start(self) -> None:
        if hasattr(self, "behaviour") and self.behaviour:
            self.behaviour.on_listening_start()

    def stop_listening(self) -> None:
        """Returns to normal idle after listening (thread-safe)."""
        self._sig_listening_end.emit()

    def _do_listening_end(self) -> None:
        if hasattr(self, "behaviour") and self.behaviour:
            self.behaviour.on_listening_end()

    def start_thinking(self) -> None:
        """Enters contemplative thinking posture (thread-safe)."""
        self._sig_thinking_start.emit()

    def _do_thinking_start(self) -> None:
        if hasattr(self, "behaviour") and self.behaviour:
            self.behaviour.on_thinking_start()

    def celebrate(self, success_type: str = "general") -> None:
        """Plays victory celebration animation (thread-safe)."""
        self._sig_celebrate.emit(str(success_type or "general"))

    def _do_celebrate(self, success_type: str) -> None:
        if hasattr(self, "behaviour") and self.behaviour:
            self.behaviour.celebrate_task(success_type)

    def show_confusion(self, error_str: str = "") -> None:
        """Shows confused reaction on unexpected error (thread-safe)."""
        self._sig_confusion.emit(str(error_str or ""))

    def _do_confusion(self, error_str: str) -> None:
        if hasattr(self, "behaviour") and self.behaviour:
            self.behaviour.show_confusion(error_str)

    def trigger_task_animation(self, category: str, detail: str = "") -> None:
        """Dispatches proactive task/tool contextual animation across the 62 suite."""
        self._sig_task_action.emit(str(category or ""), str(detail or ""))

    def _do_task_action(self, category: str, detail: str) -> None:
        if hasattr(self, "behaviour") and self.behaviour:
            self.behaviour.trigger_task_animation(category, detail)

    def summon(self, target_x: int, target_y: int, speech: str = "I'm right here!") -> None:
        """Summons Brahma Sol to approach target location."""
        self.locomotion.summon_to(target_x, target_y, speech)

    def reset_to_default_position(self) -> None:
        """Resets desktop position to bottom-right corner."""
        screen = self.locomotion.get_current_screen() or QGuiApplication.primaryScreen()
        if screen:
            geo = screen.availableGeometry()
            init_x = geo.left() + geo.width() - self.avatar_width - 30
            init_y = geo.top() + geo.height() - self.avatar_height - 10
            self.move(init_x, init_y)
            self.proprioception.world_x = float(init_x)
            self.proprioception.world_y = float(init_y)
            self.locomotion.stop_current_movement()
            self.play_clip("Greeting", blend_time=0.2, loop=False)

    # =========================================================================
    # JAVASCRIPT THREE.JS BRIDGE METHODS
    # =========================================================================

    def play_clip(self, clip_name: str, blend_time: float = 0.15, loop: bool = True) -> None:
        self._sig_play_clip.emit(clip_name, float(blend_time), bool(loop))

    def _do_play_clip(self, clip_name: str, blend_time: float, loop: bool) -> None:
        try:
            safe_name = clip_name.replace('"', '\\"')
            js = f'window.brahmaSolAPI && window.brahmaSolAPI.playClip("{safe_name}", {blend_time}, {"true" if loop else "false"});'
            self.web_view.page().runJavaScript(js)
            self.proprioception.current_clip = clip_name
        except Exception as e:
            print(f"[AvatarWindow] play_clip error: {e}", flush=True)

    def say(self, text: str, duration: float = 3.5, vocalize: bool = True) -> None:
        self._sig_say.emit(text, float(duration))
        if vocalize and text and text.strip():
            self._vocalize_thought(text.strip())

    def _vocalize_thought(self, text: str) -> None:
        """Vocalizes companion thoughts aloud with Kokoro TTS and synchronized gestures."""
        try:
            from core.kokoro_tts_engine import KokoroTTSEngine
            engine = KokoroTTSEngine.get_instance()
            if getattr(engine, "_is_speaking", False):
                return

            is_sitting = (self.proprioception.posture == PostureState.SITTING)
            talk_clip = "Sitting Talking" if is_sitting else "Idle Talking"
            idle_clip = "Sitting Idle" if is_sitting else "Idle Subtle"

            def _on_speech_start():
                try:
                    self.start_speaking(text)
                except Exception:
                    pass

            def _on_speech_finish():
                try:
                    self.stop_speaking()
                except Exception:
                    pass

            if engine.is_available:
                engine.speak(
                    text,
                    on_start=_on_speech_start,
                    on_finish=_on_speech_finish,
                    block=False,
                    interrupt=False
                )
            else:
                def _sapi_worker():
                    _on_speech_start()
                    try:
                        from actions.attention_monitor import _speak_sapi_male
                        _speak_sapi_male(text)
                    except Exception:
                        pass
                    finally:
                        _on_speech_finish()
                import threading
                threading.Thread(target=_sapi_worker, daemon=True, name="sapi-companion-voice").start()
        except Exception as e:
            print(f"[AvatarWindow] Vocalize notice: {e}", flush=True)

    def _do_say(self, text: str, duration: float) -> None:
        try:
            clean = (text or "").strip()
            if not clean:
                self._do_hide_speech()
                return
            import json
            safe_json = json.dumps(clean)
            js = f"window.brahmaSolAPI && window.brahmaSolAPI.say({safe_json}, {duration});"
            self.web_view.page().runJavaScript(js)
        except Exception as e:
            print(f"[AvatarWindow] say error: {e}", flush=True)

    def hide_speech(self) -> None:
        self._sig_hide_speech.emit()

    def _do_hide_speech(self) -> None:
        try:
            self.web_view.page().runJavaScript("window.brahmaSolAPI && window.brahmaSolAPI.hideSpeech();")
        except Exception as e:
            print(f"[AvatarWindow] hide_speech error: {e}", flush=True)

    def look_at(self, normalized_x: float, normalized_y: float) -> None:
        self._sig_look_at.emit(float(normalized_x), float(normalized_y))

    def _do_look_at(self, normalized_x: float, normalized_y: float) -> None:
        try:
            js = f"window.brahmaSolAPI && window.brahmaSolAPI.lookAt({normalized_x:.4f}, {normalized_y:.4f});"
            self.web_view.page().runJavaScript(js)
        except Exception as e:
            print(f"[AvatarWindow] look_at error: {e}", flush=True)

    def set_heading(self, yaw: float) -> None:
        self._sig_set_heading.emit(float(yaw))

    def _do_set_heading(self, yaw: float) -> None:
        try:
            self.web_view.page().runJavaScript(f"window.brahmaSolAPI && window.brahmaSolAPI.setHeading({yaw:.4f});")
        except Exception:
            pass

    # =========================================================================
    # AUTONOMOUS DESKTOP LOCOMOTION
    # =========================================================================

    def move_to(self, dest_x: int, dest_y: int, duration_sec: float = 2.0) -> None:
        self._sig_move_to.emit(int(dest_x), int(dest_y), float(duration_sec))

    def _do_move_to(self, dest_x: int, dest_y: int, duration_sec: float) -> None:
        try:
            self._move_anim.stop()
            self._move_anim.setDuration(int(duration_sec * 1000))
            self._move_anim.setStartValue(self.pos())
            self._move_anim.setEndValue(QPoint(int(dest_x), int(dest_y)))
            self._move_anim.start()
        except Exception as e:
            print(f"[AvatarWindow] move_to error: {e}", flush=True)

    def execute_kinematic_steps(self, steps: list[KinematicActionStep]) -> None:
        self._sig_execute_steps.emit(steps)

    def _do_execute_kinematic_steps(self, steps: list[KinematicActionStep]) -> None:
        if not steps:
            return

        def _run_sequence(idx: int):
            if idx >= len(steps):
                return

            step = steps[idx]
            step_dur = max(0.1, step.duration)

            if step.action_type == "ANIMATION" and step.clip_name:
                self._do_play_clip(step.clip_name, step.blend_time, step.loop)
            elif step.action_type == "ROTATE_YAW" and step.target_yaw is not None:
                try:
                    self.web_view.page().runJavaScript(
                        f"window.brahmaSolAPI && window.brahmaSolAPI.setHeading({step.target_yaw:.4f});"
                    )
                except Exception:
                    pass
            elif step.action_type == "MOVE_DELTA" and step.target_x is not None and step.target_y is not None:
                if step.target_yaw is not None:
                    try:
                        self.web_view.page().runJavaScript(
                            f"window.brahmaSolAPI && window.brahmaSolAPI.setHeading({step.target_yaw:.4f});"
                        )
                    except Exception:
                        pass
                if step.clip_name:
                    self._do_play_clip(step.clip_name, step.blend_time, True)
                self._do_move_to(int(step.target_x), int(step.target_y), step_dur)
            elif step.action_type == "SPEECH_BUBBLE" and step.speech_text:
                if step.clip_name:
                    self._do_play_clip(step.clip_name, step.blend_time, step.loop)
                self._do_say(step.speech_text, step_dur)

            self.proprioception.apply_step_completion(step)
            QTimer.singleShot(int(step_dur * 1000), lambda: _run_sequence(idx + 1))

        _run_sequence(0)

    # =========================================================================
    # EVENTS & INTERACTION
    # =========================================================================

    def _handle_drag_start(self, screen_x: int, screen_y: int) -> None:
        if self._is_dragging:
            return
        self._is_dragging = True
        self.locomotion.stop_current_movement()
        cursor_pos = QCursor.pos()
        self._drag_offset_x = cursor_pos.x() - self.x()
        self._drag_offset_y = cursor_pos.y() - self.y()
        self.locomotion.on_drag_started()
        self._drag_timer.start()

    def _track_hardware_drag(self) -> None:
        if not self._is_dragging:
            self._drag_timer.stop()
            return

        # Check if left mouse button is still held down anywhere on desktop
        is_down = False
        try:
            import ctypes
            # VK_LBUTTON = 0x01. Bit 15 indicates currently held down
            is_down = bool(ctypes.windll.user32.GetAsyncKeyState(0x01) & 0x8000)
        except Exception:
            is_down = bool(QApplication.mouseButtons() & Qt.MouseButton.LeftButton)

        if not is_down:
            self._handle_drag_end(self.x(), self.y())
            return

        cursor_pos = QCursor.pos()
        target_x = cursor_pos.x() - self._drag_offset_x
        target_y = cursor_pos.y() - self._drag_offset_y

        # Strict multi-monitor work area clamping (never goes off-screen or into taskbar)
        app = QGuiApplication.instance()
        screen = app.screenAt(cursor_pos) if app else None
        if not screen and app:
            for s in app.screens():
                if s.geometry().contains(cursor_pos):
                    screen = s
                    break
        if not screen:
            screen = self.locomotion.get_current_screen() or QGuiApplication.primaryScreen()

        if screen:
            geo = screen.availableGeometry()
            w = self.avatar_width
            h = self.avatar_height
            min_x = geo.left() + 10
            max_x = geo.left() + geo.width() - w - 10
            min_y = geo.top() + 10
            max_y = geo.top() + geo.height() - h - 10

            target_x = max(min_x, min(max_x, target_x))
            target_y = max(min_y, min(max_y, target_y))

        if abs(self.x() - target_x) >= 2 or abs(self.y() - target_y) >= 2:
            self.move(target_x, target_y)
            self.proprioception.world_x = float(target_x)
            self.proprioception.world_y = float(target_y)

    def _handle_drag_move(self, screen_x: int, screen_y: int) -> None:
        # Hardware timer (_track_hardware_drag) handles ultra-smooth 125 FPS dragging
        pass

    def _handle_drag_end(self, screen_x: int, screen_y: int) -> None:
        if self._is_dragging:
            self._is_dragging = False
            self._drag_timer.stop()
            try:
                self.web_view.page().runJavaScript(
                    "window.brahmaSolAPI && window.brahmaSolAPI.onDragFinished && window.brahmaSolAPI.onDragFinished();"
                )
            except Exception:
                pass
            self.locomotion.on_drag_finished(self.x(), self.y())

    def _handle_avatar_click(self) -> None:
        """Clicking on avatar wakes it up or toggles dashboard."""
        self.behaviour.register_interaction()
        print("[AvatarWindow] Avatar clicked -> emitting toggle_dashboard", flush=True)
        self.toggle_dashboard.emit()

    def _handle_file_drop(self, file_name: str, file_size: int) -> None:
        self.behaviour.register_interaction()
        print(f"[AvatarWindow] File dropped: {file_name} ({file_size} bytes)", flush=True)
        self.file_received.emit(file_name)

    def _handle_clip_finished(self, clip_name: str) -> None:
        pass

    def _sync_telemetry(self) -> None:
        p = self.pos()
        self.proprioception.world_x = float(p.x())
        self.proprioception.world_y = float(p.y())

    # =========================================================================
    # RIGHT-CLICK CONTEXT MENU
    # =========================================================================

    def _show_context_menu(self, global_x: int, global_y: int) -> None:
        """Displays sleek desktop companion quick controls."""
        menu = QMenu(self)
        menu.setStyleSheet("""
            QMenu {
                background: #FFFFFF;
                border: 1.5px solid #E2E8F0;
                border-radius: 14px;
                padding: 6px;
            }
            QMenu::item {
                color: #0F172A;
                padding: 6px 20px 6px 14px;
                border-radius: 8px;
                font-family: 'Segoe UI';
                font-size: 9.5pt;
                font-weight: 600;
            }
            QMenu::item:selected {
                background: #F0F9FF;
                color: #0284C7;
            }
            QMenu::item:disabled {
                color: #94A3B8;
            }
            QMenu::separator {
                height: 1px;
                background: #E2E8F0;
                margin: 4px 6px;
            }
        """)

        title_act = menu.addAction("✦ Brahma Sol Companion")
        title_act.setEnabled(False)

        menu.addSeparator()

        dash_act = menu.addAction("💬  Open / Hide Dashboard")
        dash_act.triggered.connect(self._handle_avatar_click)

        roam_now_act = menu.addAction("🚶  Roam Somewhere Now")
        roam_now_act.triggered.connect(lambda: self.locomotion._eval_autonomous_roam())

        menu.addSeparator()

        pin_act = menu.addAction("📍  Pin to This Position")
        pin_act.setCheckable(True)
        pin_act.setChecked(self.locomotion.pinned)
        pin_act.triggered.connect(lambda c: self.locomotion.set_pinned(c))

        roam_toggle_act = menu.addAction("🏃  Autonomous Roaming")
        roam_toggle_act.setCheckable(True)
        roam_toggle_act.setChecked(self.locomotion.roaming_enabled)
        roam_toggle_act.triggered.connect(lambda c: self.locomotion.set_roaming_enabled(c))

        track_act = menu.addAction("👁  Track Cursor")
        track_act.setCheckable(True)
        track_act.setChecked(self.locomotion.cursor_tracking_enabled)
        track_act.triggered.connect(lambda c: self.locomotion.set_cursor_tracking(c))

        menu.addSeparator()

        # Posture toggles
        sit_text = "Stand Up" if self.proprioception.posture == PostureState.SITTING else "Sit Down"
        sit_act = menu.addAction(f"🧘  {sit_text}")
        sit_act.triggered.connect(self.behaviour.toggle_sitting)

        sleep_text = "Wake Up" if self.proprioception.posture == PostureState.SLEEPING else "Rest & Sleep"
        sleep_act = menu.addAction(f"💤  {sleep_text}")
        sleep_act.triggered.connect(self.behaviour.toggle_sleep)

        menu.addSeparator()

        # Expressive 62-Suite Quick Actions Submenu
        actions_menu = menu.addMenu("✨  Companion Expressive Actions")
        actions_menu.setStyleSheet(menu.styleSheet())
        
        act_dance = actions_menu.addAction("💃  Dance for Me")
        act_dance.triggered.connect(lambda: self.trigger_task_animation("dance"))

        act_stretch = actions_menu.addAction("🏋️  Take a Stretch Break")
        act_stretch.triggered.connect(lambda: self.trigger_task_animation("stretch_break"))

        act_salute = actions_menu.addAction("🫡  Respectful Salute")
        act_salute.triggered.connect(lambda: self.trigger_task_animation("terminal"))

        act_bow = actions_menu.addAction("🙇  Polite Bow")
        act_bow.triggered.connect(lambda: self.trigger_task_animation("bow"))

        act_power = actions_menu.addAction("⚡  Power Up Surge")
        act_power.triggered.connect(lambda: self.trigger_task_animation("code_synthesis"))

        act_roll = actions_menu.addAction("🌀  Evasive Combat Roll")
        act_roll.triggered.connect(lambda: self.trigger_task_animation("roll"))

        act_cheer = actions_menu.addAction("🎉  Celebrate Victory")
        act_cheer.triggered.connect(lambda: self.celebrate("code"))

        menu.addSeparator()

        reset_act = menu.addAction("🔄  Reset Desktop Position")
        reset_act.triggered.connect(self.reset_to_default_position)

        pt = QPoint(global_x, global_y) if global_x > 0 else QCursor.pos()
        menu.exec(pt)

    def contextMenuEvent(self, event):
        self._show_context_menu(event.globalPos().x(), event.globalPos().y())

    # =========================================================================
    # MOUSE DRAG WINDOW REPOSITIONING WITH AIRBORNE REACTIONS
    # =========================================================================

    def moveEvent(self, event):
        super().moveEvent(event)
        p = self.pos()
        self.proprioception.world_x = float(p.x())
        self.proprioception.world_y = float(p.y())

    def mousePressEvent(self, event):
        if event.button() == Qt.MouseButton.LeftButton:
            self._press_global_pos = event.globalPosition().toPoint()
            self._drag_start_pos = event.globalPosition().toPoint() - self.frameGeometry().topLeft()
            self._is_dragging = False
            super().mousePressEvent(event)
        elif event.button() == Qt.MouseButton.RightButton:
            self._show_context_menu(event.globalPosition().toPoint().x(), event.globalPosition().toPoint().y())
            event.accept()
        elif event.button() == Qt.MouseButton.MiddleButton:
            self._is_dragging = True
            self._drag_start_pos = event.globalPosition().toPoint() - self.frameGeometry().topLeft()
            self.locomotion.on_drag_started()
            event.accept()
        else:
            super().mousePressEvent(event)

    def mouseMoveEvent(self, event):
        if event.buttons() & Qt.MouseButton.LeftButton:
            dist = (event.globalPosition().toPoint() - self._press_global_pos).manhattanLength()
            if dist > 8 and not self._is_dragging:
                self._is_dragging = True
                self.locomotion.on_drag_started()

            if self._is_dragging:
                new_pos = event.globalPosition().toPoint() - self._drag_start_pos
                self.move(new_pos)
                event.accept()
                return

        super().mouseMoveEvent(event)

    def mouseReleaseEvent(self, event):
        if self._is_dragging:
            self._is_dragging = False
            self.locomotion.on_drag_finished(self.x(), self.y())
            event.accept()
            return

        self._is_dragging = False
        super().mouseReleaseEvent(event)
