import math
import pytest
from PyQt6.QtCore import QPoint, QRect
from PyQt6.QtWidgets import QApplication

from core.proprioception import ProprioceptionEngine, PostureState, ActivityState
from core.locomotion_controller import DesktopLocomotionController


@pytest.fixture(scope="session")
def qapp():
    app = QApplication.instance()
    if app is None:
        app = QApplication([])
    return app


class MockAvatar:
    def __init__(self):
        self._pos = QPoint(200, 300)
        self.avatar_width = 440
        self.avatar_height = 540
        self.played_clips = []
        self.look_at_calls = []

    def x(self):
        return self._pos.x()

    def y(self):
        return self._pos.y()

    def pos(self):
        return self._pos

    def move(self, x, y):
        self._pos = QPoint(x, y)

    def move_to(self, x, y, duration):
        self._pos = QPoint(x, y)

    def play_clip(self, clip, blend_time=0.2, loop=True):
        self.played_clips.append(clip)

    def look_at(self, nx, ny):
        self.look_at_calls.append((nx, ny))


def test_locomotion_intervals(qapp):
    avatar = MockAvatar()
    proprio = ProprioceptionEngine()
    loco = DesktopLocomotionController(avatar, proprio)

    # Active mode should schedule intervals around 14-30s
    loco.set_frequency("active")
    assert 14.0 <= loco._next_roam_interval_sec <= 35.0

    # Normal mode should be active and responsive (18-40s)
    loco.set_frequency("normal")
    assert 18.0 <= loco._next_roam_interval_sec <= 42.0


def test_roaming_bounds_clamping(qapp):
    avatar = MockAvatar()
    proprio = ProprioceptionEngine()
    loco = DesktopLocomotionController(avatar, proprio)

    min_x, min_y, max_x, max_y = loco.get_safe_roaming_bounds()
    assert min_x < max_x
    assert min_y < max_y


def test_drag_finished_never_exceeds_interface(qapp):
    avatar = MockAvatar()
    proprio = ProprioceptionEngine()
    loco = DesktopLocomotionController(avatar, proprio)

    min_x, min_y, max_x, max_y = loco.get_safe_roaming_bounds()

    # Attempt to drop far outside screen boundaries (negative coordinates)
    loco.on_drag_finished(-9999, -9999)
    assert avatar.x() >= min_x
    assert avatar.y() >= min_y

    # Attempt to drop far beyond screen boundaries (huge positive coordinates)
    loco.on_drag_finished(99999, 99999)
    assert avatar.x() <= max_x
    assert avatar.y() <= max_y


def test_cursor_tracking_cache(qapp):
    avatar = MockAvatar()
    proprio = ProprioceptionEngine()
    loco = DesktopLocomotionController(avatar, proprio)

    # Trigger first look at
    loco._eval_cursor_awareness()
    avatar.look_at_calls.clear()

    # Second immediate evaluation without mouse movement should be completely skipped
    loco._eval_cursor_awareness()
    assert len(avatar.look_at_calls) == 0
