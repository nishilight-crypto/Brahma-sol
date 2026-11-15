"""
core/behaviour_system.py
========================
High-Level Intelligent Behavior System, Emotion & State Machine for Brahma Sol.

Features:
1. Physical & Mental States:
   - Postures: STANDING, SITTING, SLEEPING, MEDITATING, LEVITATING
   - Activities: IDLE, ROAMING, SPEAKING, LISTENING, THINKING, DRAGGED, CELEBRATING, CONFUSED
2. Speech Synchronization:
   - Synchronizes 3D talking clips strictly with TTS playback start & stop.
   - Posture continuity: Speaks while sitting if seated ("Sitting Talking").
   - Emotional accents (celebrations, thinking gestures, salute).
3. Inactivity & Fatigue Cycles:
   - 3-5 mins: Relaxed posture shift / arms folded.
   - 6-12 mins: Sits down on taskbar ledge.
   - >15 mins: Enters gentle sleep state.
   - Any user interaction (click, speech, drag) wakes up Brahma instantly.
"""

from __future__ import annotations

import time
import random
from typing import Optional, Callable

from PyQt6.QtCore import QObject, QTimer, pyqtSignal

from core.proprioception import ProprioceptionEngine, PostureState, ActivityState
from core.animation_registry import ALL_ANIMATIONS


class SolBehaviourSystem(QObject):
    """High-level behavior coordinator and state machine."""

    state_changed = pyqtSignal(str, str)  # (posture, activity)

    def __init__(self, avatar_window, locomotion_controller, proprioception: ProprioceptionEngine, parent=None):
        super().__init__(parent)
        self.avatar = avatar_window
        self.locomotion = locomotion_controller
        self.proprioception = proprioception

        self._is_speaking = False
        self._speech_safety_timer = None
        self._previous_posture = PostureState.STANDING
        self._last_interaction_time = time.time()

        # Inactivity & Fatigue Watchdog (checks every 5 seconds)
        self._fatigue_timer = QTimer(self)
        self._fatigue_timer.timeout.connect(self._eval_fatigue_cycle)
        self._fatigue_timer.start(5000)

    @property
    def current_activity(self) -> ActivityState:
        return self.proprioception.activity

    @property
    def current_posture(self) -> PostureState:
        return self.proprioception.posture

    def register_interaction(self) -> None:
        """Resets inactivity counter whenever the user interacts."""
        self._last_interaction_time = time.time()
        self.proprioception.last_user_interaction = self._last_interaction_time

        # If Brahma is sleeping or sitting due to fatigue, wake up!
        if self.proprioception.posture == PostureState.SLEEPING:
            self.wake_up()

    # =========================================================================
    # SPEECH & VOICE SYNCHRONIZATION
    # =========================================================================

    def on_speech_start(self, text: str, emotion: str = "neutral") -> None:
        """Invoked when TTS speech playback begins."""
        self.register_interaction()
        self._is_speaking = True
        self.proprioception.activity = ActivityState.SPEAKING

        # Cancel any previous speech failsafe timer
        if self._speech_safety_timer:
            self._speech_safety_timer.stop()
            self._speech_safety_timer = None

        # Pause autonomous roaming during speech
        if self.locomotion:
            self.locomotion.stop_current_movement()

        talk_clip = "Idle Talking"

        # Check for emotional gesture accent (e.g. celebration or greeting)
        low = (text or "").lower()
        if "welcome" in low or "hello" in low or "hi there" in low or "hey" in low:
            self.avatar.play_clip("Greeting", blend_time=0.25, loop=False)
            QTimer.singleShot(3800, lambda: self._play_talking_if_speaking(talk_clip))
        elif "success" in low or "completed" in low or "congratulations" in low:
            self.celebrate_task("general")
            QTimer.singleShot(2800, lambda: self._play_talking_if_speaking(talk_clip))
        else:
            self.avatar.play_clip(talk_clip, blend_time=0.25, loop=True)

        self.avatar.say(text, max(3.5, len(text) / 14.0), vocalize=False)
        self.state_changed.emit(self.proprioception.posture.value, self.proprioception.activity.value)

        # Failsafe timer: ensures avatar ALWAYS concludes speech animation even if TTS aborts
        dur_sec = max(3.5, len(text) / 13.0) + 1.2
        self._speech_safety_timer = QTimer(self)
        self._speech_safety_timer.setSingleShot(True)
        self._speech_safety_timer.timeout.connect(self._on_speech_safety_timeout)
        self._speech_safety_timer.start(int(dur_sec * 1000))

    def _on_speech_safety_timeout(self) -> None:
        if self._is_speaking:
            self.on_speech_end()

    def _play_talking_if_speaking(self, clip_name: str) -> None:
        if self._is_speaking and self.avatar:
            self.avatar.play_clip(clip_name, blend_time=0.3, loop=True)

    def on_speech_end(self) -> None:
        """Invoked when TTS speech finishes playing."""
        if self._speech_safety_timer:
            self._speech_safety_timer.stop()
            self._speech_safety_timer = None

        if not self._is_speaking:
            return

        self._is_speaking = False
        self.proprioception.activity = ActivityState.IDLE

        # Return smoothly to serene standing idle posture
        if self.avatar:
            self.avatar.play_clip("Idle Subtle", blend_time=0.35, loop=True)

        self.state_changed.emit(self.proprioception.posture.value, self.proprioception.activity.value)

    def on_listening_start(self) -> None:
        """Invoked when mic opens and Brahma is actively listening."""
        if self.proprioception.activity == ActivityState.SPEAKING or self._is_speaking:
            return

        self.register_interaction()
        self.proprioception.activity = ActivityState.LISTENING

        if self.locomotion:
            self.locomotion.stop_current_movement()

        if self.proprioception.posture == PostureState.STANDING:
            self.avatar.play_clip("Idle Listening", blend_time=0.25, loop=True)
        elif self.proprioception.posture == PostureState.SITTING:
            # Subtle nod while seated
            self.avatar.play_clip("Head Nod", blend_time=0.2, loop=False)

        self.state_changed.emit(self.proprioception.posture.value, self.proprioception.activity.value)

    def on_listening_end(self) -> None:
        if self.proprioception.activity == ActivityState.LISTENING:
            self.proprioception.activity = ActivityState.IDLE
            if self.proprioception.posture == PostureState.STANDING:
                self.avatar.play_clip("Idle Subtle", blend_time=0.3, loop=True)

    def on_thinking_start(self) -> None:
        """Invoked when local AI model is generating responses or reasoning."""
        self.proprioception.activity = ActivityState.THINKING
        if self.locomotion:
            self.locomotion.stop_current_movement()
        if self.proprioception.posture in (PostureState.STANDING, PostureState.LEVITATING):
            self.avatar.play_clip("Idle_FoldArms", blend_time=0.35, loop=True)
        self.state_changed.emit(self.proprioception.posture.value, self.proprioception.activity.value)

    def on_executing_start(self) -> None:
        """Invoked when executing tools, running automations, or doing agent work."""
        self.register_interaction()
        self.proprioception.activity = ActivityState.PERFORMING_TOOL
        if self.locomotion:
            self.locomotion.stop_current_movement()
        self.avatar.play_clip("Interact", blend_time=0.35, loop=True)
        self.state_changed.emit(self.proprioception.posture.value, self.proprioception.activity.value)

    # =========================================================================
    # EMOTIONAL REACTIONS & CELEBRATIONS
    # =========================================================================

    def celebrate_task(self, success_type: str = "general") -> None:
        """Celebrates when tasks or fixes complete successfully."""
        self.register_interaction()
        clip = "Victory Fist Pump" if success_type == "code" else "Victory"
        if self.proprioception.posture == PostureState.SITTING:
            clip = "Cheering Two Hands"

        self.avatar.play_clip(clip, blend_time=0.30, loop=False)

        # Return to idle after celebration
        dur = 2.25 if clip == "Victory Fist Pump" else (1.58 if clip == "Cheering Two Hands" else 2.5)
        fallback = "Sitting Idle" if self.proprioception.posture == PostureState.SITTING else "Idle Subtle"
        QTimer.singleShot(int(dur * 1000), lambda: self.avatar.play_clip(fallback, blend_time=0.35, loop=True))

    def show_confusion(self, error_text: str = "") -> None:
        """Triggered when an unexpected error occurs."""
        self.register_interaction()
        self.avatar.play_clip("Confused", blend_time=0.30, loop=False)
        QTimer.singleShot(2900, lambda: self.avatar.play_clip("Idle Subtle", blend_time=0.35, loop=True))

    # =========================================================================
    # POSTURE STATE TRANSITIONS
    # =========================================================================

    def sit_down(self) -> None:
        """Transitions into relaxed sitting posture."""
        if self.proprioception.posture == PostureState.SITTING:
            return
        if self.locomotion:
            self.locomotion.stop_current_movement()

        self.avatar.play_clip("Sitting Enter", blend_time=0.15, loop=False)
        self.proprioception.posture = PostureState.SITTING
        QTimer.singleShot(1250, lambda: self.avatar.play_clip("Sitting Idle", blend_time=0.15, loop=True))
        self.state_changed.emit(self.proprioception.posture.value, self.proprioception.activity.value)

    def stand_up(self) -> None:
        """Rises from sitting posture back to standing."""
        if self.proprioception.posture == PostureState.STANDING:
            return
        if self.proprioception.posture == PostureState.SITTING:
            self.avatar.play_clip("Sitting Exit", blend_time=0.15, loop=False)
            self.proprioception.posture = PostureState.STANDING
            QTimer.singleShot(900, lambda: self.avatar.play_clip("Idle Subtle", blend_time=0.15, loop=True))
        elif self.proprioception.posture == PostureState.SLEEPING:
            self.wake_up()
        self.state_changed.emit(self.proprioception.posture.value, self.proprioception.activity.value)

    def toggle_sitting(self) -> None:
        if self.proprioception.posture == PostureState.SITTING:
            self.stand_up()
        else:
            self.sit_down()

    def sleep(self) -> None:
        """Enters sleep state after prolonged absence."""
        if self.proprioception.posture == PostureState.SLEEPING:
            return
        if self.locomotion:
            self.locomotion.stop_current_movement()

        self.avatar.play_clip("Kneeling Tired", blend_time=0.15, loop=False)
        self.proprioception.posture = PostureState.SLEEPING
        QTimer.singleShot(700, lambda: self.avatar.play_clip("Sleeping", blend_time=0.15, loop=True))
        self.state_changed.emit(self.proprioception.posture.value, self.proprioception.activity.value)

    def wake_up(self) -> None:
        """Wakes up when user interacts."""
        if self.proprioception.posture != PostureState.SLEEPING:
            return

        self.avatar.play_clip("Land Three Point", blend_time=0.15, loop=False)
        self.proprioception.posture = PostureState.STANDING
        self.avatar.say("I'm awake and ready!", 3.0)
        QTimer.singleShot(950, lambda: self.avatar.play_clip("Idle Subtle", blend_time=0.15, loop=True))
        self.state_changed.emit(self.proprioception.posture.value, self.proprioception.activity.value)

    def toggle_sleep(self) -> None:
        if self.proprioception.posture == PostureState.SLEEPING:
            self.wake_up()
        else:
            self.sleep()

    # =========================================================================
    # FATIGUE & IDLE CYCLE WATCHDOG
    # =========================================================================

    def _eval_fatigue_cycle(self) -> None:
        """Evaluates inactivity time for organic, subtle companion presence."""
        if not getattr(self.locomotion, "idle_postures_enabled", True):
            return

        idle_seconds = time.time() - self._last_interaction_time

        # If currently speaking or navigating, skip
        if self.proprioception.activity in (ActivityState.SPEAKING, ActivityState.NAVIGATING, ActivityState.DRAGGED):
            return

        # Natural standing presence: calm breathing, occasional thoughtful arms cross
        if self.proprioception.posture == PostureState.STANDING:
            if 180 <= idle_seconds < 200 and self.proprioception.current_clip == "Idle Subtle":
                self.avatar.play_clip("Idle_FoldArms", blend_time=0.4, loop=True)
                QTimer.singleShot(15000, lambda: self.avatar.play_clip("Idle Subtle", blend_time=0.35, loop=True) if self.proprioception.activity == ActivityState.IDLE else None)
