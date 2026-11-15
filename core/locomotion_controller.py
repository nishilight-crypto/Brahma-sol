"""
core/locomotion_controller.py
=============================
Physical Desktop Locomotion, Navigation & Intelligent Behavior Controller for Brahma Sol.

Optimized & Responsive:
1. High-Performance Autonomous Desktop Roaming:
   - Dynamic, natural movement across the entire screen without stubborn freezes.
   - Snappy agile turns with smooth heading interpolation into walking strides.
   - Dynamic stride velocity matching (Walk_2, Jog, Sprint, Levitate).
   - Rich post-arrival idle behaviors without persistent sitting locks.
   - Multi-monitor awareness and clean screen boundary clamping.
2. Ultra-Smooth Interaction:
   - Cached desktop cursor tracking (eliminates redundant IPC spikes).
   - Fast pick-up / drag airborne reactions and landing impact physics.
   - Instant response on summon or roam commands.
3. User Controls & Customization:
   - Roaming toggle, frequency (slow/normal/active), speed scale, pin position.
"""

from __future__ import annotations

import math
import random
import time
from typing import Optional, Tuple, Callable

from PyQt6.QtCore import QObject, QTimer, QPoint, QRect, QPropertyAnimation, QEasingCurve, pyqtSignal
from PyQt6.QtGui import QCursor, QGuiApplication, QScreen

from core.proprioception import ProprioceptionEngine, PostureState, ActivityState, KinematicActionStep
from core.animation_registry import ALL_ANIMATIONS


class DesktopLocomotionController(QObject):
    """Governs autonomous navigation, spatial positioning and interaction reflexes."""

    roaming_state_changed = pyqtSignal(bool)
    arrived_at_destination = pyqtSignal(int, int)

    def __init__(self, avatar_window, proprioception: ProprioceptionEngine, parent=None):
        super().__init__(parent)
        self.avatar = avatar_window
        self.proprioception = proprioception

        # Configuration options
        self.roaming_enabled: bool = True
        self.frequency_mode: str = "normal"  # "slow", "normal", "active"
        self.speed_scale: float = 1.0
        self.pinned: bool = False
        self.cursor_tracking_enabled: bool = False
        self.idle_postures_enabled: bool = True

        # State tracking
        self._is_roaming_now: bool = False
        self._is_dragged: bool = False
        self._last_cursor_pos = QPoint(0, 0)
        self._cursor_still_time: float = 0.0
        self._next_roam_interval_sec: float = 18.0
        self._last_norm_x: float = 0.0
        self._last_norm_y: float = 0.0

        # Autonomous Roaming Timer
        self._roam_timer = QTimer(self)
        self._roam_timer.timeout.connect(self._eval_autonomous_roam)
        self._schedule_next_roam(initial=True)

        # Desktop Cursor Awareness Timer (~14 Hz - cached & smooth, prevents IPC flooding)
        self._cursor_timer = QTimer(self)
        self._cursor_timer.timeout.connect(self._eval_cursor_awareness)
        self._cursor_timer.start(70)

    # =========================================================================
    # CONFIGURATION & SETTINGS
    # =========================================================================

    def set_roaming_enabled(self, enabled: bool) -> None:
        self.roaming_enabled = bool(enabled)
        if not self.roaming_enabled and self._is_roaming_now:
            self.stop_current_movement()
        self.roaming_state_changed.emit(self.roaming_enabled)
        print(f"[Locomotion] Autonomous roaming set to: {self.roaming_enabled}", flush=True)

    def set_frequency(self, mode: str) -> None:
        if mode in ("slow", "normal", "active"):
            self.frequency_mode = mode
            self._schedule_next_roam()
            print(f"[Locomotion] Roaming frequency set to: {mode}", flush=True)

    def set_pinned(self, pinned: bool) -> None:
        self.pinned = bool(pinned)
        if self.pinned:
            self.stop_current_movement()
        print(f"[Locomotion] Pinned state: {self.pinned}", flush=True)

    def set_speed_scale(self, scale: float) -> None:
        self.speed_scale = max(0.5, min(2.5, float(scale)))

    def set_cursor_tracking(self, enabled: bool) -> None:
        self.cursor_tracking_enabled = bool(enabled)
        if self.avatar:
            if not self.cursor_tracking_enabled:
                self.avatar.look_at(0.0, 0.0)
                try:
                    self.avatar.web_view.page().runJavaScript(
                        "window.brahmaSolAPI && window.brahmaSolAPI.setHeadIKEnabled && window.brahmaSolAPI.setHeadIKEnabled(false);"
                    )
                except Exception:
                    pass
            else:
                try:
                    self.avatar.web_view.page().runJavaScript(
                        "window.brahmaSolAPI && window.brahmaSolAPI.setHeadIKEnabled && window.brahmaSolAPI.setHeadIKEnabled(true);"
                    )
                except Exception:
                    pass

    @property
    def is_moving(self) -> bool:
        return self._is_roaming_now

    # =========================================================================
    # SCREEN BOUNDARIES & SAFE ROAMING LANES
    # =========================================================================

    def get_current_screen(self) -> Optional[QScreen]:
        """Finds screen where Brahma currently resides with maximum geometric overlap."""
        app = QGuiApplication.instance()
        if not app:
            return None
        pos = self.avatar.pos() if self.avatar else QPoint(100, 100)
        w = getattr(self.avatar, "avatar_width", 440)
        h = getattr(self.avatar, "avatar_height", 540)
        center_pos = QPoint(pos.x() + (w // 2), pos.y() + (h // 2))

        # 1. Check center of avatar
        screen = app.screenAt(center_pos)
        if screen:
            return screen

        # 2. Check top-left
        screen = app.screenAt(pos)
        if screen:
            return screen

        # 3. Find screen with largest intersection rectangle
        best_screen = None
        max_overlap = -1
        avatar_rect = QRect(pos.x(), pos.y(), w, h)
        for s in app.screens():
            inter = s.geometry().intersected(avatar_rect)
            overlap = inter.width() * inter.height()
            if overlap > max_overlap:
                max_overlap = overlap
                best_screen = s

        return best_screen or app.primaryScreen()

    def get_safe_roaming_bounds(self) -> Tuple[int, int, int, int]:
        """
        Returns (min_x, min_y, max_x, max_y) safe window coordinates.
        Ensures Brahma never clips off-screen or gets hidden under taskbars.
        """
        screen = self.get_current_screen()
        if not screen:
            return (40, 40, 1400, 800)

        geo = screen.availableGeometry()
        w = getattr(self.avatar, "avatar_width", 440)
        h = getattr(self.avatar, "avatar_height", 540)

        min_x = geo.left() + 10
        max_x = geo.left() + geo.width() - w - 10

        # Full screen roaming: from top of screen to above taskbar
        min_y = geo.top() + 10
        max_y = geo.top() + geo.height() - h - 10

        return (min_x, min_y, max_x, max_y)

    def get_random_safe_point(self) -> QPoint:
        """Returns a safe random destination point within screen boundaries."""
        min_x, min_y, max_x, max_y = self.get_safe_roaming_bounds()
        return QPoint(random.randint(min_x, max_x), random.randint(min_y, max_y))

    # =========================================================================
    # AUTONOMOUS ROAMING PLANNER (RESPONSIVE & DYNAMIC)
    # =========================================================================

    def _schedule_next_roam(self, initial: bool = False) -> None:
        """Schedules next autonomous exploration with natural, lively pacing."""
        if self.frequency_mode == "slow":
            base = 65.0
            variance = 20.0
        elif self.frequency_mode == "active":
            base = 20.0
            variance = 6.0
        else:  # "normal"
            base = 28.0
            variance = 8.0

        if initial:
            delay = 5.0  # Responsive initial start
        else:
            delay = base + random.uniform(-variance, variance)

        self._next_roam_interval_sec = max(14.0, delay)
        self._roam_timer.stop()
        self._roam_timer.start(int(self._next_roam_interval_sec * 1000))

    def _eval_autonomous_roam(self) -> None:
        """Evaluator called on roam timer tick."""
        if not self.roaming_enabled or self.pinned or self._is_dragged:
            self._schedule_next_roam()
            return

        # Do not roam if speaking, listening, or executing a tool
        if self.proprioception.activity in (
            ActivityState.SPEAKING, ActivityState.NAVIGATING, ActivityState.PERFORMING_TOOL
        ):
            self._schedule_next_roam()
            return

        # Do not roam if deep in sleep
        if self.proprioception.posture == PostureState.SLEEPING:
            self._schedule_next_roam()
            return

        # Generate destination
        min_x, min_y, max_x, max_y = self.get_safe_roaming_bounds()
        current_x = self.avatar.x() if self.avatar else self.proprioception.world_x
        current_y = self.avatar.y() if self.avatar else self.proprioception.world_y

        screen_w = max_x - min_x
        screen_h = max_y - min_y
        ground_y = max_y
        mid_y = min_y + int(screen_h * 0.42)
        high_y = min_y + int(screen_h * 0.12)

        # 70% Ground candidates (for walking & running), 20% mid-screen (elevated), 10% high
        ground_candidates = [
            (min_x + int(screen_w * 0.08), ground_y),
            (min_x + int(screen_w * 0.28), ground_y),
            (min_x + int(screen_w * 0.50), ground_y),
            (min_x + int(screen_w * 0.72), ground_y),
            (min_x + int(screen_w * 0.92), ground_y),
        ]
        elevated_candidates = [
            (min_x + int(screen_w * 0.15), mid_y),
            (min_x + int(screen_w * 0.82), mid_y),
            (min_x + int(screen_w * 0.48), high_y),
        ]

        is_currently_airborne = (current_y < ground_y - 90)

        if is_currently_airborne:
            # If currently elevated, 80% chance return to ground to walk/run
            pool = ground_candidates if random.random() < 0.80 else elevated_candidates
        else:
            # If on ground, 70% chance stroll/run on ground, 30% take off into air
            pool = ground_candidates if random.random() < 0.70 else elevated_candidates

        valid = [c for c in pool if math.hypot(c[0] - current_x, c[1] - current_y) > 120]
        if not valid:
            valid = [c for c in (ground_candidates + elevated_candidates) if math.hypot(c[0] - current_x, c[1] - current_y) > 80]

        dest_x, dest_y = random.choice(valid) if valid else random.choice(ground_candidates)
        self.execute_roam(dest_x, dest_y)

    def execute_roam(self, dest_x: int, dest_y: int, on_complete: Optional[Callable] = None) -> None:
        """Executes full locomotion sequence across entire screen with natural physics & pacing."""
        if not self.avatar:
            return

        min_x, min_y, max_x, max_y = self.get_safe_roaming_bounds()
        dest_x = max(min_x, min(max_x, dest_x))
        dest_y = max(min_y, min(max_y, dest_y))

        current_x = self.avatar.x()
        current_y = self.avatar.y()
        dx = dest_x - current_x
        dy = dest_y - current_y
        dist = math.hypot(dx, dy)

        if dist < 40:
            if on_complete:
                on_complete()
            self._schedule_next_roam()
            return

        self._is_roaming_now = True
        self.proprioception.activity = ActivityState.NAVIGATING

        ground_y = max_y
        is_current_on_ground = (current_y >= ground_y - 90)
        is_dest_on_ground = (dest_y >= ground_y - 90)
        is_ascending = (dest_y < current_y - 90)
        is_descending = (dest_y > current_y + 90 and is_dest_on_ground)

        def _step_1_wake_or_stand():
            if self.proprioception.posture == PostureState.SITTING:
                self.avatar.play_clip("Sitting Exit", blend_time=0.3, loop=False)
                self.proprioception.posture = PostureState.STANDING
                QTimer.singleShot(800, _step_2_direction_prep)
            elif self.proprioception.posture == PostureState.SLEEPING:
                self.avatar.play_clip("Land Three Point", blend_time=0.3, loop=False)
                self.proprioception.posture = PostureState.STANDING
                QTimer.singleShot(700, _step_2_direction_prep)
            else:
                _step_2_direction_prep()

        def _step_2_direction_prep():
            if not self._is_roaming_now:
                return

            moving_right = (dx > 0)
            target_heading = 1.5708 if moving_right else -1.5708

            if is_ascending:
                # Spring takeoff into flight glide
                self.avatar.play_clip("Jump_Start", blend_time=0.2, loop=False)
                if hasattr(self.avatar, "set_heading"):
                    self.avatar.set_heading(target_heading)
                QTimer.singleShot(340, _step_3_travel)
            elif is_current_on_ground and is_dest_on_ground and abs(dx) > 70:
                # Turn along ground before walking/running
                turn_clip = "Turn Right 90" if moving_right else "Turn Left 90"
                self.avatar.play_clip(turn_clip, blend_time=0.2, loop=False)
                if hasattr(self.avatar, "set_heading"):
                    self.avatar.set_heading(target_heading)
                QTimer.singleShot(320, _step_3_travel)
            else:
                # Airborne glide or vertical descent
                if hasattr(self.avatar, "set_heading"):
                    self.avatar.set_heading(target_heading)
                _step_3_travel()

        def _step_3_travel():
            if not self._is_roaming_now:
                return

            # Determine movement gait and duration
            if is_current_on_ground and is_dest_on_ground:
                # Ground locomotion: Walk, Jog, or Sprint
                if dist > 720:
                    move_clip = "Sprint"
                    base_speed = 210.0
                elif dist > 380:
                    move_clip = "Jog"
                    base_speed = 155.0
                else:
                    move_clip = "Walk_2"
                    base_speed = 100.0
            elif is_ascending:
                move_clip = "Levitate Idle"
                base_speed = 135.0
            elif is_descending:
                move_clip = "Levitate Idle"
                base_speed = 145.0
            else:
                move_clip = "Levitate Idle"
                base_speed = 120.0

            speed = base_speed * self.speed_scale
            duration_sec = max(2.0, dist / speed)

            # Butter-smooth crossfade
            self.avatar.play_clip(move_clip, blend_time=0.3, loop=True)
            self.avatar.move_to(dest_x, dest_y, duration_sec)

            # Register arrival callback for QPropertyAnimation.finished
            self._arrival_callback = _step_4_arrival
            if hasattr(self, "_arrival_timer") and self._arrival_timer:
                self._arrival_timer.stop()
            self._arrival_timer = QTimer(self)
            self._arrival_timer.setSingleShot(True)
            self._arrival_timer.timeout.connect(self.on_movement_finished)
            self._arrival_timer.start(int(duration_sec * 1000) + 120)

        def _step_4_arrival():
            if not self._is_roaming_now:
                return
            self._is_roaming_now = False

            # Face user gracefully
            if hasattr(self.avatar, "set_heading"):
                self.avatar.set_heading(0.0)

            self.proprioception.world_x = float(dest_x)
            self.proprioception.world_y = float(dest_y)

            if is_descending:
                # Cushioned superhero landing on ground, then rise
                self.avatar.play_clip("Land Three Point", blend_time=0.2, loop=False)
                self.proprioception.activity = ActivityState.IDLE
                self.proprioception.posture = PostureState.STANDING
                QTimer.singleShot(800, lambda: self.avatar.play_clip("Idle Subtle", blend_time=0.35, loop=True) if not self._is_roaming_now else None)
            elif not is_dest_on_ground:
                # Hovering peacefully at mid/high vantage point
                self.avatar.play_clip("Levitate Idle", blend_time=0.35, loop=True)
                self.proprioception.activity = ActivityState.IDLE
                self.proprioception.posture = PostureState.LEVITATING
            else:
                # Standing ground idle
                self.avatar.play_clip("Idle Subtle", blend_time=0.35, loop=True)
                self.proprioception.activity = ActivityState.IDLE
                self.proprioception.posture = PostureState.STANDING

            self.arrived_at_destination.emit(dest_x, dest_y)
            if on_complete:
                on_complete()

            # Proactive voice commentary upon arrival (45% chance)
            if hasattr(self.avatar, "say") and random.random() < 0.45:
                if is_descending or is_dest_on_ground:
                    lines = [
                        "Standing by on the taskbar.",
                        "Patrolling the lower deck.",
                        "All sentinels reporting nominal.",
                        "Checking in from over here.",
                        "Lower perimeter secure."
                    ]
                else:
                    lines = [
                        "Keeping watch right beside your workspace.",
                        "Clear vantage point from up here.",
                        "Observing the desktop from above.",
                        "Eye on the active windows."
                    ]
                line = random.choice(lines)
                QTimer.singleShot(700, lambda l=line: self.avatar.say(l, 3.2, vocalize=True) if hasattr(self.avatar, "say") else None)

            _step_5_post_arrival_behavior()

        def _step_5_post_arrival_behavior():
            # Trigger lively post-arrival idle animations after 6-9 seconds
            if not is_dest_on_ground:
                # Airborne
                def _do_air_idle():
                    if self.proprioception.activity == ActivityState.IDLE and not self._is_roaming_now:
                        r = random.random()
                        if r < 0.50:
                            self.avatar.play_clip("Meditate", blend_time=0.35, loop=True)
                            self.proprioception.posture = PostureState.MEDITATING
                            QTimer.singleShot(9000, lambda: self.avatar.play_clip("Levitate Idle", blend_time=0.35, loop=True) if not self._is_roaming_now and self.proprioception.activity == ActivityState.IDLE else None)
                        elif r < 0.80:
                            self.avatar.play_clip("Interact", blend_time=0.35, loop=False)
                            QTimer.singleShot(2500, lambda: self.avatar.play_clip("Levitate Idle", blend_time=0.35, loop=True) if not self._is_roaming_now and self.proprioception.activity == ActivityState.IDLE else None)
                QTimer.singleShot(7000, _do_air_idle)
            else:
                # Ground
                def _do_ground_idle():
                    if self.proprioception.activity == ActivityState.IDLE and not self._is_roaming_now:
                        r = random.random()
                        if r < 0.35:
                            self.avatar.play_clip("Idle_FoldArms", blend_time=0.35, loop=True)
                            QTimer.singleShot(8000, lambda: self.avatar.play_clip("Idle Subtle", blend_time=0.35, loop=True) if not self._is_roaming_now and self.proprioception.activity == ActivityState.IDLE else None)
                        elif r < 0.65:
                            self.avatar.play_clip("Interact", blend_time=0.35, loop=False)
                            QTimer.singleShot(2500, lambda: self.avatar.play_clip("Idle Subtle", blend_time=0.35, loop=True) if not self._is_roaming_now and self.proprioception.activity == ActivityState.IDLE else None)
                        elif r < 0.85:
                            self.avatar.play_clip("Salute", blend_time=0.3, loop=False)
                            QTimer.singleShot(2600, lambda: self.avatar.play_clip("Idle Subtle", blend_time=0.35, loop=True) if not self._is_roaming_now and self.proprioception.activity == ActivityState.IDLE else None)
                QTimer.singleShot(6500, _do_ground_idle)

            self._schedule_next_roam()

        _step_1_wake_or_stand()

    def on_movement_finished(self) -> None:
        """Called immediately when QPropertyAnimation reaches destination."""
        if not self._is_roaming_now:
            return
        if getattr(self, "_arrival_callback", None):
            cb = self._arrival_callback
            self._arrival_callback = None
            cb()

    def stop_current_movement(self) -> None:
        """Cancels active movement immediately and settles into idle."""
        if not self._is_roaming_now:
            return
        self._is_roaming_now = False
        if hasattr(self.avatar, "_move_anim"):
            self.avatar._move_anim.stop()
        if self.avatar and hasattr(self.avatar, "set_heading"):
            self.avatar.set_heading(0.0)
            if self.proprioception.posture == PostureState.SITTING:
                self.avatar.play_clip("Sitting Idle", blend_time=0.25, loop=True)
            else:
                self.avatar.play_clip("Idle Subtle", blend_time=0.25, loop=True)
        self.proprioception.activity = ActivityState.IDLE

    # =========================================================================
    # SUMMON & USER INTERACTION
    # =========================================================================

    def summon_to(self, target_x: int, target_y: int, speech: str = "I'm right here! Ready to help.") -> None:
        """User summons Brahma to come to a specific desktop position."""
        self.stop_current_movement()
        print(f"[Locomotion] Brahma summoned to ({target_x}, {target_y})", flush=True)

        def _on_summon_arrived():
            self.avatar.play_clip("Greeting", blend_time=0.2, loop=False)
            if speech:
                self.avatar.say(speech, 3.5)

        self.execute_roam(target_x, target_y, on_complete=_on_summon_arrived)

    def on_drag_started(self) -> None:
        """Called when user picks up Brahma Sol via mouse drag."""
        self.stop_current_movement()
        self._is_dragged = True
        self.proprioception.activity = ActivityState.DRAGGED
        # Play airborne dangling reaction
        self.avatar.play_clip("Jump air", blend_time=0.12, loop=True)

    def on_drag_finished(self, drop_x: int, drop_y: int) -> None:
        """Called when user releases dragged Brahma Sol."""
        self._is_dragged = False
        min_x, min_y, max_x, max_y = self.get_safe_roaming_bounds()
        clamped_x = max(min_x, min(max_x, drop_x))
        clamped_y = max(min_y, min(max_y, drop_y))

        self.avatar.move(clamped_x, clamped_y)
        self.proprioception.world_x = float(clamped_x)
        self.proprioception.world_y = float(clamped_y)

        # Impact landing sequence
        self.avatar.play_clip("Jump Land", blend_time=0.12, loop=False)
        self.proprioception.activity = ActivityState.IDLE
        self.proprioception.posture = PostureState.STANDING

        # Settle to Idle Subtle after landing
        QTimer.singleShot(650, lambda: self.avatar.play_clip("Idle Subtle", blend_time=0.15, loop=True))
        self._schedule_next_roam()

    # =========================================================================
    # GLOBAL DESKTOP CURSOR TRACKING (OPTIMIZED & CACHED)
    # =========================================================================

    def _eval_cursor_awareness(self) -> None:
        """Tracks user cursor across entire screen subtly without IPC flooding."""
        if not self.cursor_tracking_enabled or not self.avatar:
            return

        # Do not track cursor while moving, roaming, dragged, sleeping, or meditating
        if self._is_roaming_now or self.proprioception.activity in (
            ActivityState.NAVIGATING, ActivityState.DRAGGED
        ):
            if self._last_norm_x != 0.0 or self._last_norm_y != 0.0:
                self._last_norm_x = 0.0
                self._last_norm_y = 0.0
                self.avatar.look_at(0.0, 0.0)
            return

        if self.proprioception.posture in (PostureState.SLEEPING, PostureState.MEDITATING):
            if self._last_norm_x != 0.0 or self._last_norm_y != 0.0:
                self._last_norm_x = 0.0
                self._last_norm_y = 0.0
                self.avatar.look_at(0.0, 0.0)
            return

        cursor_pos = QCursor.pos()
        avatar_pos = self.avatar.pos()
        w = getattr(self.avatar, "avatar_width", 440)
        h = getattr(self.avatar, "avatar_height", 540)

        # Center of avatar's head/chest
        avatar_center_x = avatar_pos.x() + (w // 2)
        avatar_center_y = avatar_pos.y() + int(h * 0.35)

        dx = cursor_pos.x() - avatar_center_x
        dy = cursor_pos.y() - avatar_center_y
        dist = math.hypot(dx, dy)

        # Check if cursor is active or still
        if cursor_pos == self._last_cursor_pos:
            self._cursor_still_time += 0.07
        else:
            self._cursor_still_time = 0.0
            self._last_cursor_pos = cursor_pos

        # If cursor is far away (> 1600px) or still for > 20s, drift gaze gently forward
        if dist > 1600 or self._cursor_still_time > 20.0:
            if self._last_norm_x != 0.0 or self._last_norm_y != 0.0:
                self._last_norm_x = 0.0
                self._last_norm_y = 0.0
                self.avatar.look_at(0.0, 0.0)
            return

        # Normalize relative to avatar viewport with soft, wide falloff (screen_w * 0.65)
        screen = self.get_current_screen()
        screen_w = screen.size().width() if screen else 1920
        screen_h = screen.size().height() if screen else 1080

        norm_x = max(-1.0, min(1.0, dx / (screen_w * 0.65)))
        norm_y = max(-1.0, min(1.0, -dy / (screen_h * 0.65)))

        # Cache check: only dispatch IPC across WebEngine boundary when changed >= 3%
        if abs(norm_x - self._last_norm_x) >= 0.03 or abs(norm_y - self._last_norm_y) >= 0.03:
            self._last_norm_x = norm_x
            self._last_norm_y = norm_y
            self.avatar.look_at(norm_x, norm_y)
