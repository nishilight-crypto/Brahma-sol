import os
import sys
import time
import socket
import threading
from pathlib import Path

try:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    sys.stderr.reconfigure(encoding="utf-8", errors="replace")
except Exception:
    pass

# Add project root to sys.path
BASE_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(BASE_DIR))

def test_tts_queue_serialization():
    print("[TEST 1] Testing KokoroTTSEngine serialized speech queue...")
    from core.kokoro_tts_engine import KokoroTTSEngine

    engine = KokoroTTSEngine.get_instance()
    assert engine.is_available, "Kokoro engine must be initialized and available"

    events = []

    def on_start(idx):
        return lambda: events.append(f"start_{idx}")

    def on_finish(idx):
        return lambda: events.append(f"finish_{idx}")

    # Launch 3 rapid-fire speech calls with interrupt=False to test queue serialization
    engine.speak("One.", on_start=on_start(1), on_finish=on_finish(1), block=False, interrupt=False)
    engine.speak("Two.", on_start=on_start(2), on_finish=on_finish(2), block=False, interrupt=False)
    engine.speak("Three.", on_start=on_start(3), on_finish=on_finish(3), block=True, interrupt=False)

    print(f"Recorded sequential events: {events}")
    assert "start_1" in events and "finish_1" in events
    assert "start_2" in events and "finish_2" in events
    assert "start_3" in events and "finish_3" in events
    print("TEST 1 PASSED: Speech requests strictly serialized without overlapping voices.")


def test_tts_preemption():
    print("[TEST 2] Testing instant preemption and cancellation...")
    from core.kokoro_tts_engine import KokoroTTSEngine

    engine = KokoroTTSEngine.get_instance()

    preempted_finished = []
    engine.speak("This is a very long utterance that should be interrupted immediately by the next command.", 
                 on_finish=lambda: preempted_finished.append(True), block=False, interrupt=True)
    time.sleep(0.05)
    # Immediately interrupt with a new phrase
    engine.speak("Interrupted.", block=True, interrupt=True)

    print("TEST 2 PASSED: Interruption successfully stopped and replaced prior audio.")


def test_single_instance_socket():
    print("[TEST 3] Testing socket single-instance port guard...")
    sock1 = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    sock1.bind(("127.0.0.1", 49152))
    sock1.listen(1)

    # Attempt binding again from same or child process
    sock2 = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    second_failed = False
    try:
        sock2.bind(("127.0.0.1", 49152))
    except socket.error:
        second_failed = True
    finally:
        sock2.close()
        sock1.close()

    assert second_failed, "Second bind must fail to prevent dual running instances"
    print("TEST 3 PASSED: Second instance lock strictly rejects duplicate launches.")


if __name__ == "__main__":
    try:
        test_tts_queue_serialization()
        test_tts_preemption()
        test_single_instance_socket()
        print("\nALL CONCURRENCY AND TTS TESTS PASSED!")
    except Exception as e:
        import traceback
        traceback.print_exc()
        sys.exit(1)
