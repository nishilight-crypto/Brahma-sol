import os
import tempfile
from pathlib import Path
import pytest

from core.verifier import verify_tool_result
from core.sensorium import PassiveSensorium


def test_verifier_syntax_error_detection():
    # Create temporary invalid python file
    with tempfile.NamedTemporaryFile(suffix=".py", delete=False, mode="w", encoding="utf-8") as tf:
        tf.write("def broken_code(:\n    print('invalid syntax')\n")
        temp_path = tf.name

    try:
        report = verify_tool_result("file_controller", {"file_path": temp_path, "action": "write"}, "ok")
        assert report["verified"] is False
        assert "Syntax error detected" in report["details"]
        assert "Autonomous Self-Healing Directive" in report["details"]
    finally:
        if os.path.exists(temp_path):
            os.remove(temp_path)


def test_verifier_valid_python_success():
    # Create temporary valid python file
    with tempfile.NamedTemporaryFile(suffix=".py", delete=False, mode="w", encoding="utf-8") as tf:
        tf.write("def valid_function():\n    return 42\n")
        temp_path = tf.name

    try:
        report = verify_tool_result("file_controller", {"file_path": temp_path, "action": "write"}, "ok")
        assert report["verified"] is True
        assert report["warning"] is None
    finally:
        if os.path.exists(temp_path):
            os.remove(temp_path)


def test_verifier_empty_file_warning():
    # Create temporary 0-byte file
    with tempfile.NamedTemporaryFile(suffix=".py", delete=False, mode="w", encoding="utf-8") as tf:
        temp_path = tf.name

    try:
        report = verify_tool_result("file_controller", {"file_path": temp_path, "action": "write"}, "ok")
        assert report["verified"] is False
        assert "0 bytes (empty)" in report["details"]
    finally:
        if os.path.exists(temp_path):
            os.remove(temp_path)


def test_sensorium_terminal_error_detection():
    sensorium = PassiveSensorium(poll_interval=100.0)
    alerts = []
    sensorium.register_interjection_handler(lambda at, meta: alerts.append((at, meta)))

    # Simulate active PowerShell terminal with an error title
    sensorium.current_process_name = "powershell.exe"
    sensorium.current_window = {
        "title": "Administrator: Windows PowerShell - Error: Process crashed with exit code 1",
        "class_name": "ConsoleWindowClass",
        "hwnd": 1234
    }

    sensorium._evaluate_heuristics()
    assert any(a[0] == "terminal_error" for a in alerts)
    term_alert = next(a[1] for a in alerts if a[0] == "terminal_error")
    assert "noticed an error in your terminal" in term_alert["speech"]


def test_workspace_sentinel_persistence():
    with tempfile.NamedTemporaryFile(suffix=".db", delete=False) as tf:
        db_path = tf.name

    try:
        from core.memory_cortex import MemoryCortex
        cortex1 = MemoryCortex(db_path=Path(db_path))
        cortex1.record_project_activity("brahma-evo-local", r"D:\titech\brahma-evo-local", "Working on memory")
        cortex1.set_workspace_state("user_preference_editor", "vscode")

        # Simulate fresh session after restart by reading with a new cortex instance
        cortex2 = MemoryCortex(db_path=Path(db_path))
        snap = cortex2.get_workspace_snapshot()

        assert snap["active_project"]["name"] == "brahma-evo-local"
        assert snap["active_project"]["path"] == r"D:\titech\brahma-evo-local"
        assert cortex2.get_workspace_state("user_preference_editor") == "vscode"
    finally:
        if os.path.exists(db_path):
            try: os.remove(db_path)
            except Exception: pass


def test_workspace_sentinel_command_and_error_tracking():
    with tempfile.NamedTemporaryFile(suffix=".db", delete=False) as tf:
        db_path = tf.name

    try:
        from core.memory_cortex import MemoryCortex
        cortex = MemoryCortex(db_path=Path(db_path))

        cortex.record_command_execution("pytest tests/test_commercial_upgrades.py", exit_code=0)
        cortex.record_command_execution("npm run dev", exit_code=1)
        cortex.record_observed_error("SyntaxError in app.py", source="terminal")

        snap = cortex.get_workspace_snapshot()
        assert len(snap["recent_commands"]) == 2
        assert snap["recent_commands"][0]["command"] == "npm run dev"
        assert len(snap["recent_errors"]) == 1
        assert snap["recent_errors"][0]["resolved"] is False

        # Mark resolved
        cortex.resolve_last_error()
        snap_after = cortex.get_workspace_snapshot()
        assert snap_after["recent_errors"][0]["resolved"] is True
    finally:
        if os.path.exists(db_path):
            try: os.remove(db_path)
            except Exception: pass


def test_workspace_sentinel_startup_restoration_brief():
    with tempfile.NamedTemporaryFile(suffix=".db", delete=False) as tf:
        db_path = tf.name

    try:
        from core.memory_cortex import MemoryCortex
        cortex = MemoryCortex(db_path=Path(db_path))
        cortex.record_project_activity("Autonomous OS", r"C:\Dev\Brahma")
        cortex.record_command_execution("python main.py", exit_code=0)

        brief = cortex.generate_startup_restoration_brief()
        assert "[CROSS-SESSION WORKSPACE SENTINEL CONTEXT (RESTORED)]" in brief
        assert "Autonomous OS" in brief
        assert "python main.py" in brief
        assert "Workspace Health: Clean" in brief
    finally:
        if os.path.exists(db_path):
            try: os.remove(db_path)
            except Exception: pass


def test_offline_fact_harvesting():
    with tempfile.NamedTemporaryFile(suffix=".db", delete=False) as tf:
        db_path = tf.name

    try:
        from core.memory_cortex import MemoryCortex
        cortex = MemoryCortex(db_path=Path(db_path))
        harvested = cortex.auto_harvest_facts("My favorite language is Python and I am working on Brahma Evo")
        assert len(harvested) >= 1

        recalled = cortex.recall("Python project", top_k=3)
        assert len(recalled) >= 1
    finally:
        if os.path.exists(db_path):
            try: os.remove(db_path)
            except Exception: pass


def test_globe_routing_intent_reflex():
    from core.intent_dispatcher import IntentDispatcher
    dispatcher = IntentDispatcher()

    # 1. Run globe / open globe
    res_run = dispatcher.match_instant_reflex("run globe")
    assert res_run is not None
    assert res_run.intent == "geospatial_globe"
    assert res_run.action == "open"

    res_open = dispatcher.match_instant_reflex("open globe")
    assert res_open is not None
    assert res_open.intent == "geospatial_globe"
    assert res_open.action == "open"

    # 2. Distance queries (including user's exact phrasing with typo 'betwen')
    res_dist = dispatcher.match_instant_reflex("show distance betwen mumbai to bangalore on a globe")
    assert res_dist is not None
    assert res_dist.intent == "geospatial_globe"
    assert res_dist.action == "route"
    assert res_dist.parameters.get("origin") == "mumbai"
    assert res_dist.parameters.get("destination") == "bangalore"

    res_dist2 = dispatcher.match_instant_reflex("distance between mumbai and bangalore")
    assert res_dist2 is not None
    assert res_dist2.intent == "geospatial_globe"
    assert res_dist2.action == "route"
    assert res_dist2.parameters.get("origin") == "mumbai"
    assert res_dist2.parameters.get("destination") == "bangalore"

    # 3. Flight routes
    res_flight = dispatcher.match_instant_reflex("flight route from tokyo to london")
    assert res_flight is not None
    assert res_flight.intent == "geospatial_globe"
    assert res_flight.action == "route"
    assert res_flight.parameters.get("origin") == "tokyo"
    assert res_flight.parameters.get("destination") == "london"

    # 4. ISS Tracker
    res_iss = dispatcher.match_instant_reflex("track iss")
    assert res_iss is not None
    assert res_iss.intent == "geospatial_globe"
    assert res_iss.action == "iss"


def test_open_app_globe_interception():
    from actions.open_app import open_app
    from core.verifier import verify_tool_result

    # open_app should cleanly intercept "globe"
    res = open_app({"app_name": "globe"})
    assert "Opened Brahma 3D Interactive Globe" in res

    # Verifier should verify globe launch as true
    v_report = verify_tool_result("open_app", {"app_name": "globe"}, res)
    assert v_report["verified"] is True
    assert "HoloGlobe" in v_report["details"]


def test_mumbai_bangalore_distance_calculation():
    from actions.geospatial_globe import geocode_location, calculate_great_circle_route
    lat1, lon1, lbl1 = geocode_location("mumbai")
    lat2, lon2, lbl2 = geocode_location("bangalore")

    assert "Mumbai" in lbl1
    assert "Bengaluru" in lbl2 or "Bangalore" in lbl2

    route = calculate_great_circle_route(lat1, lon1, lat2, lon2)
    assert 800 <= route["distance_km"] <= 900
    assert 490 <= route["distance_miles"] <= 560
    assert "1h" in route["flight_time_estimate"]

