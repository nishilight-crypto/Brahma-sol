import importlib
import io

from PIL import Image


def test_capture_screenshot_falls_back_to_primary_monitor(monkeypatch):
    screen_processor = importlib.import_module("actions.screen_processor")

    class FakeShot:
        rgb = Image.new("RGB", (10, 10), color="white").convert("RGB")
        size = (10, 10)

    class FakeMss:
        def __init__(self):
            self.monitors = [None]

        def grab(self, monitor):
            return FakeShot()

        def __enter__(self):
            return self

        def __exit__(self, exc_type, exc, tb):
            return False

    def fake_to_png(rgb, size):
        buf = io.BytesIO()
        rgb.save(buf, format="PNG")
        return buf.getvalue()

    monkeypatch.setattr(screen_processor.mss, "mss", lambda: FakeMss())
    monkeypatch.setattr(screen_processor.mss.tools, "to_png", fake_to_png)

    image_bytes = screen_processor._capture_screenshot()

    assert isinstance(image_bytes, bytes)
    assert image_bytes


def test_screen_process_uses_provided_image_bytes(monkeypatch):
    import base64
    screen_processor = importlib.import_module("actions.screen_processor")
    called = {"capture": False}

    def fake_capture_screenshot():
        called["capture"] = True
        return b"fallback"

    monkeypatch.setattr(screen_processor, "_capture_screenshot", fake_capture_screenshot)

    import llm_client
    class FakeLLM:
        def vision(self, prompt, image_b64):
            assert image_b64 == base64.b64encode(b"provided").decode("utf-8")
            return "I see the provided screen."

    monkeypatch.setattr(llm_client, "client", FakeLLM())

    result = screen_processor.screen_process(
        parameters={"text": "look at my screen", "angle": "screen"},
        player=None,
        image_bytes=b"provided",
    )

    assert result is True
    assert called["capture"] is False
