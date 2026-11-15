"""
core/proprioception.py
======================
Physical Body-State, Kinematics & Proprioception Engine for Brahma Sol.

Tracks the avatar's:
1. Physical Position (world_x, world_y screen coordinates)
2. Orientation (facing_yaw radians, 0 = user)
3. Posture (STANDING, SITTING, CROUCHING, SLEEPING, MEDITATING, LEVITATING)
4. Current Activity (IDLE, SPEAKING, NAVIGATING, GESTURING, THINKING, RESTING)
5. Active Animation Clip & blend status
6. Attention Focus Target (x, y) for procedural head/neck IK
7. Energy & Fatigue Cycles
8. Physical Boundaries & Obstacle Constraints

Enforces kinematic validity so Brahma Sol never attempts physically contradictory
actions (e.g., walking while sitting, or jumping while sleeping).
"""

from __future__ import annotations

import math
import time
from dataclasses import dataclass, field
from enum import Enum
from typing import List, Optional, Tuple, Dict, Any, Callable

from core.animation_registry import ALL_ANIMATIONS, AnimationClip, get_animation_by_name


class PostureState(str, Enum):
    STANDING = "STANDING"
    SITTING = "SITTING"
    CROUCHING = "CROUCHING"
    SLEEPING = "SLEEPING"
    MEDITATING = "MEDITATING"
    LEVITATING = "LEVITATING"


class ActivityState(str, Enum):
    IDLE = "IDLE"
    SPEAKING = "SPEAKING"
    LISTENING = "LISTENING"
    THINKING = "THINKING"
    NAVIGATING = "NAVIGATING"
    GESTURING = "GESTURING"
    DRAGGED = "DRAGGED"
    RESTING = "RESTING"
    PERFORMING_TOOL = "PERFORMING_TOOL"


@dataclass
class ScreenBounds:
    min_x: int = 50
    min_y: int = 50
    max_x: int = 1920
    max_y: int = 1040  # Accounts for Windows taskbar (typical 1080 - 40)
    taskbar_y: int = 980


@dataclass
class KinematicActionStep:
    action_type: str  # "ANIMATION", "MOVE_DELTA", "ROTATE_YAW", "WAIT", "SPEECH_BUBBLE"
    clip_name: Optional[str] = None
    duration: float = 0.0
    loop: bool = False
    blend_time: float = 0.3
    target_x: Optional[float] = None
    target_y: Optional[float] = None
    target_yaw: Optional[float] = None
    speech_text: Optional[str] = None
    description: str = ""


class ProprioceptionEngine:
    """The central nervous system and physical state model of Brahma Sol."""

    def __init__(self, bounds: Optional[ScreenBounds] = None):
        self.bounds = bounds or ScreenBounds()
        
        # Physical coordinates
        self.world_x: float = float(self.bounds.max_x - 350)
        self.world_y: float = float(self.bounds.taskbar_y - 200)
        self.facing_yaw: float = 0.0  # 0.0 = Facing forward/user, pi/2 = right, -pi/2 = left
        
        # Bodily states
        self.posture: PostureState = PostureState.STANDING
        self.activity: ActivityState = ActivityState.IDLE
        self.current_clip: str = "Idle Subtle"
        self.clip_start_time: float = time.time()
        
        # Attention target (where head and eyes look in screen space)
        self.attention_target: Tuple[float, float] = (self.world_x, self.world_y - 50)
        
        # Physiological / Energy state
        self.energy: float = 1.0  # 1.0 = fully energized, 0.1 = exhausted
        self.last_user_interaction: float = time.time()
        
        # Listeners for state change
        self._on_state_change: List[Callable[[Dict[str, Any]], None]] = []

    def register_listener(self, callback: Callable[[Dict[str, Any]], None]) -> None:
        self._on_state_change.append(callback)

    def _notify(self) -> None:
        state = self.get_telemetry()
        for cb in self._on_state_change:
            try:
                cb(state)
            except Exception:
                pass

    def get_telemetry(self) -> Dict[str, Any]:
        return {
            "x": round(self.world_x, 1),
            "y": round(self.world_y, 1),
            "facing_yaw": round(self.facing_yaw, 3),
            "posture": self.posture.value,
            "activity": self.activity.value,
            "current_clip": self.current_clip,
            "attention_target": (round(self.attention_target[0], 1), round(self.attention_target[1], 1)),
            "energy": round(self.energy, 2),
            "idle_seconds": round(time.time() - self.last_user_interaction, 1),
        }

    # =========================================================================
    # KINEMATIC TRANSITION VALIDATOR & PLANNER
    # =========================================================================

    def plan_posture_transition(self, target_posture: PostureState) -> List[KinematicActionStep]:
        """Validates and sequences posture transitions cleanly."""
        if self.posture == target_posture:
            return []

        steps: List[KinematicActionStep] = []

        # Case 1: Currently SITTING
        if self.posture == PostureState.SITTING:
            # Must stand up before any other posture!
            steps.append(KinematicActionStep(
                action_type="ANIMATION",
                clip_name="Sitting Exit",
                duration=1.29,
                loop=False,
                blend_time=0.25,
                description="Stand up from seated posture",
            ))
            # After Sitting Exit, posture becomes STANDING
            if target_posture == PostureState.STANDING:
                steps.append(KinematicActionStep(
                    action_type="ANIMATION",
                    clip_name="Idle Subtle",
                    duration=2.57,
                    loop=True,
                    blend_time=0.3,
                    description="Return to standing idle",
                ))
                return steps

        # Case 2: Currently SLEEPING
        elif self.posture == PostureState.SLEEPING:
            steps.append(KinematicActionStep(
                action_type="ANIMATION",
                clip_name="Land Three Point",
                duration=1.37,
                loop=False,
                blend_time=0.3,
                description="Wake up and rise from sleeping posture",
            ))

        # Case 3: Transition to SITTING
        if target_posture == PostureState.SITTING:
            steps.append(KinematicActionStep(
                action_type="ANIMATION",
                clip_name="Sitting Enter",
                duration=1.62,
                loop=False,
                blend_time=0.3,
                description="Sit down smoothly",
            ))
            steps.append(KinematicActionStep(
                action_type="ANIMATION",
                clip_name="Sitting Idle",
                duration=2.07,
                loop=True,
                blend_time=0.2,
                description="Loop seated idle",
            ))

        # Case 4: Transition to SLEEPING
        elif target_posture == PostureState.SLEEPING:
            steps.append(KinematicActionStep(
                action_type="ANIMATION",
                clip_name="Kneeling Tired",
                duration=0.83,
                loop=False,
                blend_time=0.3,
                description="Kneel down tiredly",
            ))
            steps.append(KinematicActionStep(
                action_type="ANIMATION",
                clip_name="Sleeping",
                duration=1.67,
                loop=True,
                blend_time=0.3,
                description="Enter continuous sleep cycle",
            ))

        # Case 5: Transition to MEDITATING
        elif target_posture == PostureState.MEDITATING:
            steps.append(KinematicActionStep(
                action_type="ANIMATION",
                clip_name="Meditate",
                duration=1.50,
                loop=True,
                blend_time=0.3,
                description="Enter zen meditation posture",
            ))

        # Case 6: Transition to LEVITATING
        elif target_posture == PostureState.LEVITATING:
            steps.append(KinematicActionStep(
                action_type="ANIMATION",
                clip_name="Levitate Entrance",
                duration=2.00,
                loop=False,
                blend_time=0.3,
                description="Rise into levitation",
            ))
            steps.append(KinematicActionStep(
                action_type="ANIMATION",
                clip_name="Levitate Idle",
                duration=2.00,
                loop=True,
                blend_time=0.2,
                description="Hover in levitation",
            ))

        # Case 7: Return to STANDING
        elif target_posture == PostureState.STANDING:
            steps.append(KinematicActionStep(
                action_type="ANIMATION",
                clip_name="Idle Subtle",
                duration=2.57,
                loop=True,
                blend_time=0.3,
                description="Return to standing ground state",
            ))

        return steps

    def plan_locomotion(self, target_x: float, target_y: float) -> List[KinematicActionStep]:
        """
        Plans physical movement to target coordinates.
        Enforces physical limitations:
        - Clamps within screen boundaries.
        - Automatically stands up if sitting.
        - Smoothly aligns yaw before walking.
        """
        # 1. Clamp target within physical screen boundaries
        clamped_x = max(self.bounds.min_x, min(self.bounds.max_x, target_x))
        clamped_y = max(self.bounds.min_y, min(self.bounds.max_y, target_y))

        dx = clamped_x - self.world_x
        dy = clamped_y - self.world_y
        dist = math.hypot(dx, dy)

        if dist < 20:
            # Already at target
            return []

        steps: List[KinematicActionStep] = []

        # 2. Kinematic Precondition: Must be STANDING to walk!
        if self.posture != PostureState.STANDING:
            steps.extend(self.plan_posture_transition(PostureState.STANDING))

        # 3. Heading & Turning Calculation
        # Screen coords: positive X is right, positive Y is down
        target_heading = math.atan2(dx, -dy)  # Relative to looking straight up/forward
        yaw_diff = target_heading - self.facing_yaw
        yaw_diff = (yaw_diff + math.pi) % (2 * math.pi) - math.pi  # Normalize to [-pi, pi]

        # Select turn animation if substantial rotation is required
        if abs(yaw_diff) > 1.2:  # > ~70 degrees
            if yaw_diff > 2.2 or yaw_diff < -2.2:
                turn_clip = "Turn Right 180" if yaw_diff > 0 else "Turn Left 180"
                dur = 1.48 if "Right" in turn_clip else 2.10
            else:
                turn_clip = "Turn Right 90" if yaw_diff > 0 else "Turn Left 90"
                dur = 2.0
            steps.append(KinematicActionStep(
                action_type="ANIMATION",
                clip_name=turn_clip,
                duration=dur,
                loop=False,
                blend_time=0.2,
                target_yaw=target_heading,
                description=f"Turn towards destination: {turn_clip}",
            ))
        else:
            steps.append(KinematicActionStep(
                action_type="ROTATE_YAW",
                target_yaw=target_heading,
                duration=0.3,
                description="Smooth yaw alignment",
            ))

        # 4. Locomotion Clip Selection based on distance
        walk_clip = "Sprint" if dist > 600 else ("Jog" if dist > 350 else "Walk_2")
        speed = 280.0 if walk_clip == "Sprint" else (180.0 if walk_clip == "Jog" else 110.0)  # px/sec
        move_duration = dist / speed

        steps.append(KinematicActionStep(
            action_type="MOVE_DELTA",
            clip_name=walk_clip,
            target_x=clamped_x,
            target_y=clamped_y,
            duration=move_duration,
            loop=True,
            blend_time=0.25,
            description=f"Navigate to ({clamped_x:.0f}, {clamped_y:.0f}) with {walk_clip}",
        ))

        # 5. Arrival: Face the user (yaw = 0.0) and return to Idle Subtle
        steps.append(KinematicActionStep(
            action_type="ROTATE_YAW",
            target_yaw=0.0,
            duration=0.3,
            description="Turn to face user",
        ))
        steps.append(KinematicActionStep(
            action_type="ANIMATION",
            clip_name="Idle Subtle",
            duration=2.57,
            loop=True,
            blend_time=0.3,
            description="Arrived: Settle into standing idle",
        ))

        return steps

    def plan_speech(self, text: str, emotion: str = "neutral") -> List[KinematicActionStep]:
        """
        Plans physical speech execution based on current posture and emotional tone.
        Maintains posture continuity (e.g. uses Sitting Talking if seated).
        """
        steps: List[KinematicActionStep] = []

        # If sleeping, wake up first
        if self.posture == PostureState.SLEEPING:
            steps.extend(self.plan_posture_transition(PostureState.STANDING))

        # Select speech clip based on posture
        if self.posture == PostureState.SITTING:
            talk_clip = "Sitting Talking"
            fallback_idle = "Sitting Idle"
        else:
            talk_clip = "Idle Talking"
            fallback_idle = "Idle Subtle"

        # Emotional accent gesture
        accent_gesture: Optional[str] = None
        accent_dur = 0.0

        if emotion == "celebration" or emotion == "triumph":
            accent_gesture = "Victory Fist Pump"
            accent_dur = 2.25
        elif emotion == "curious" or emotion == "perceptive":
            accent_gesture = "Interact"
            accent_dur = 2.50
        elif emotion == "confused" or emotion == "error":
            accent_gesture = "Confused"
            accent_dur = 2.92
        elif emotion == "playful" or emotion == "sarcastic":
            accent_gesture = "Insult"
            accent_dur = 2.77
        elif emotion == "respectful":
            accent_gesture = "Salute"
            accent_dur = 4.37

        # 1. Speech Bubble + Talking Animation
        # Rough estimation: 15 characters per second of speech
        speech_duration = max(2.0, min(12.0, len(text) / 14.0))

        if accent_gesture and self.posture == PostureState.STANDING:
            # Play accent gesture first, then talk
            steps.append(KinematicActionStep(
                action_type="ANIMATION",
                clip_name=accent_gesture,
                duration=accent_dur,
                loop=False,
                blend_time=0.2,
                description=f"Emotional accent: {accent_gesture}",
            ))

        steps.append(KinematicActionStep(
            action_type="SPEECH_BUBBLE",
            clip_name=talk_clip,
            speech_text=text,
            duration=speech_duration,
            loop=True,
            blend_time=0.25,
            description=f"Display speech bubble and play {talk_clip}",
        ))

        # Settle back to appropriate posture idle
        steps.append(KinematicActionStep(
            action_type="ANIMATION",
            clip_name=fallback_idle,
            duration=2.0,
            loop=True,
            blend_time=0.3,
            description=f"Speech complete: settle to {fallback_idle}",
        ))

        return steps

    def apply_step_completion(self, step: KinematicActionStep) -> None:
        """Updates internal physical state when an action step completes."""
        if step.target_x is not None:
            self.world_x = step.target_x
        if step.target_y is not None:
            self.world_y = step.target_y
        if step.target_yaw is not None:
            self.facing_yaw = step.target_yaw

        if step.clip_name:
            self.current_clip = step.clip_name
            self.clip_start_time = time.time()

            # Update posture state based on key clips
            if step.clip_name in ("Sitting Enter", "Sitting Idle", "Sitting Talking"):
                self.posture = PostureState.SITTING
            elif step.clip_name in ("Sitting Exit", "Idle Subtle", "Walk_2", "Jog", "Sprint", "Greeting", "Salute"):
                self.posture = PostureState.STANDING
            elif step.clip_name in ("Sleeping", "Kneeling Tired"):
                self.posture = PostureState.SLEEPING
            elif step.clip_name == "Meditate":
                self.posture = PostureState.MEDITATING
            elif step.clip_name in ("Levitate Entrance", "Levitate Idle"):
                self.posture = PostureState.LEVITATING

        self.last_user_interaction = time.time()
        self._notify()
