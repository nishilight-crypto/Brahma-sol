"""
Autonomous Tool Verification Engine (Verify-Before-Reporting) for Brahma AI.
Performs deterministic static analysis, process checks, and output validation
before any tool result is reported to the user or finalized by the planner.
Prevents hallucinations and enables autonomous self-healing.
"""

import os
import sys
import ast
import json
import py_compile
from pathlib import Path
from typing import Dict, Any, Optional
import psutil


def verify_tool_result(name: str, args: Dict[str, Any], result: Any) -> Dict[str, Any]:
    """
    Deterministically verifies tool execution outcomes.
    Returns:
        {
            "verified": bool,
            "details": str,
            "warning": Optional[str]
        }
    """
    res_str = str(result) if result is not None else ""
    low_res = res_str.lower()

    # 1. Verification of File Operations & Code Generation
    file_path = args.get("file_path") or args.get("path") or args.get("target_path")
    if file_path and isinstance(file_path, (str, Path)):
        p = Path(file_path).resolve()
        # If this was an operation supposed to write or create a file
        action = str(args.get("action", "")).lower()
        is_write_op = any(w in action for w in ("create", "write", "save", "edit", "append", "generate")) or name in (
            "file_controller", "dev_agent", "write_file", "save_file"
        )

        if is_write_op and p.exists():
            try:
                size = p.stat().st_size
                if size == 0 and "empty" not in action:
                    return {
                        "verified": False,
                        "details": f"File '{p.name}' was created but has 0 bytes (empty). Please ensure content is written properly.",
                        "warning": "Empty file created."
                    }

                # Python syntax verification
                if p.suffix.lower() == ".py":
                    try:
                        content = p.read_text(encoding="utf-8", errors="replace")
                        ast.parse(content, filename=str(p))
                    except SyntaxError as syn_err:
                        return {
                            "verified": False,
                            "details": (
                                f"Syntax error detected in generated file '{p.name}' at line {syn_err.lineno}: {syn_err.msg}.\n"
                                f"Line: {syn_err.text}\n"
                                f"Autonomous Self-Healing Directive: Fix this syntax error before reporting completion."
                            ),
                            "warning": f"Python SyntaxError at line {syn_err.lineno}."
                        }

                # JSON verification
                elif p.suffix.lower() == ".json":
                    try:
                        content = p.read_text(encoding="utf-8", errors="replace")
                        json.loads(content)
                    except json.JSONDecodeError as j_err:
                        return {
                            "verified": False,
                            "details": (
                                f"Invalid JSON generated in '{p.name}' (line {j_err.lineno}, col {j_err.colno}): {j_err.msg}.\n"
                                f"Autonomous Self-Healing Directive: Reformat the JSON to be strictly valid."
                            ),
                            "warning": f"Invalid JSON format."
                        }

            except Exception as e_verify:
                print(f"[VERIFIER] Notice verifying file: {e_verify}")

    # 2. Verification of Application Launch (open_app)
    if name == "open_app":
        app_target = str(args.get("app_name") or args.get("target") or args.get("name") or "").lower().strip()
        if app_target in ("globe", "3d globe", "holo globe", "hologlobe", "interactive globe", "map globe", "earth"):
            return {"verified": True, "details": "Brahma 3D Interactive HoloGlobe overlay active."}
        if app_target:
            running_procs = []
            try:
                for proc in psutil.process_iter(["name"]):
                    p_name = (proc.info.get("name") or "").lower()
                    if p_name:
                        running_procs.append(p_name)
            except Exception:
                pass

            target_base = Path(app_target).stem.lower()
            matched = any(target_base in p for p in running_procs)
            if not matched:
                return {
                    "verified": False,
                    "details": (
                        f"Application '{app_target}' was invoked but does not appear to be actively running in the process table.\n"
                        f"Autonomous Self-Healing Directive: Verify the executable name or path and attempt launch via system shell."
                    ),
                    "warning": f"Process '{app_target}' not found in active processes."
                }

    # 3. Verification of General Execution Failures
    failure_indicators = ("traceback", "failed:", "error: [winerror", "syntaxerror", "modulenotfounderror")
    if any(fi in low_res for fi in failure_indicators):
        return {
            "verified": False,
            "details": f"Tool execution output indicated an unhandled failure: {res_str[:300]}",
            "warning": "Execution failure detected."
        }

    return {
        "verified": True,
        "details": "Execution outcome verified successfully.",
        "warning": None
    }
