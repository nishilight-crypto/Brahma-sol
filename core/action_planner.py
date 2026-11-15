"""
core/action_planner.py
======================
Layer 2 Action Planner & Behavior Coordinator for Brahma Sol.

Translates high-level AI intents, voice states, and environmental events into
physically grounded, kinematically valid action sequences for the 3D Body Controller.
"""

from __future__ import annotations

import time
import threading
from typing import Optional, Dict, Any, Callable, List

from core.proprioception import (
    ProprioceptionEngine, KinematicActionStep, PostureState, ActivityState
)
from core.animation_registry import ALL_ANIMATIONS


class SolActionPlanner:
    """Coordinates high-level AI intents with the physical body and speech."""

    def __init__(self, proprioception: ProprioceptionEngine, avatar_window=None, speak_fn=None):
        self.proprioception = proprioception
        self.avatar_window = avatar_window
        self.speak_fn = speak_fn

    def set_avatar_window(self, win):
        self.avatar_window = win

    def set_speak_fn(self, fn: Callable[[str], None]):
        self.speak_fn = fn

    # =========================================================================
    # INTENT DISPATCHER TO PHYSICAL ACTION
    # =========================================================================

    def plan_speech_reaction(self, text: str) -> List[KinematicActionStep]:
        """Returns kinematic action steps for speech reaction."""
        return self.proprioception.plan_speech(text)

    def execute_speech(self, text: str, emotion: str = "neutral") -> None:
        """
        Coordinates holographic speech bubble, talking animation, and TTS audio.
        """
        clean_text = (text or "").strip()
        if not clean_text:
            return

        if self.avatar_window and hasattr(self.avatar_window, "start_speaking"):
            self.avatar_window.start_speaking(clean_text, emotion=emotion)
        elif self.avatar_window:
            steps = self.proprioception.plan_speech(clean_text, emotion=emotion)
            self.avatar_window.execute_kinematic_steps(steps)

        # Synchronize voice speech
        if self.speak_fn:
            def _speak_worker():
                try:
                    self.speak_fn(clean_text)
                except Exception as e:
                    print(f"[ActionPlanner] Speech error: {e}", flush=True)
            threading.Thread(target=_speak_worker, daemon=True, name="sol-voice-worker").start()

    def execute_locomotion(self, target_x: float, target_y: float) -> None:
        """Plans and executes autonomous locomotion to destination."""
        if self.avatar_window and hasattr(self.avatar_window, "locomotion"):
            self.avatar_window.locomotion.execute_roam(int(target_x), int(target_y))
        elif self.avatar_window:
            steps = self.proprioception.plan_locomotion(target_x, target_y)
            if steps:
                self.avatar_window.execute_kinematic_steps(steps)

    def execute_posture_change(self, target_posture: PostureState) -> None:
        """Transitions posture with full kinematic validation."""
        if self.avatar_window and hasattr(self.avatar_window, "behaviour"):
            if target_posture == PostureState.SITTING:
                self.avatar_window.behaviour.sit_down()
            elif target_posture == PostureState.STANDING:
                self.avatar_window.behaviour.stand_up()
            elif target_posture == PostureState.SLEEPING:
                self.avatar_window.behaviour.sleep()
        elif self.avatar_window:
            steps = self.proprioception.plan_posture_transition(target_posture)
            if steps:
                self.avatar_window.execute_kinematic_steps(steps)

    def execute_celebration(self, success_type: str = "general") -> None:
        """Triggered upon successful task completion or self-healing fix."""
        if self.avatar_window and hasattr(self.avatar_window, "celebrate"):
            self.avatar_window.celebrate(success_type)
        elif self.avatar_window:
            clip = "Victory Fist Pump" if success_type == "code" else "Victory"
            self.avatar_window.play_clip(clip, blend_time=0.2, loop=False)

    def execute_error_reaction(self, error_str: str) -> None:
        """Triggered when an exception occurs before or during self-healing."""
        if self.avatar_window and hasattr(self.avatar_window, "show_confusion"):
            self.avatar_window.show_confusion(error_str)
        elif self.avatar_window:
            self.avatar_window.play_clip("Confused", blend_time=0.2, loop=False)

    def summon(self, target_x: int, target_y: int, speech: str = "I'm right here!") -> None:
        """Summons Brahma Sol to approach target location."""
        if self.avatar_window and hasattr(self.avatar_window, "summon"):
            self.avatar_window.summon(target_x, target_y, speech)
        else:
            self.execute_locomotion(float(target_x), float(target_y))

    def stop(self) -> None:
        pass
