"""
Brahma Local Brain Engine (v2)
Provides full offline local LLM execution using an OpenAI-compatible local runtime
(Ollama, LM Studio, vLLM, or LocalAI) with automatic tool-calling and hardware acceleration.
"""

import json
import os
import shutil
import subprocess
import sys
import time
import urllib.request
import urllib.error
import threading
from typing import Dict, Any, List, Optional, Generator

DEFAULT_ENDPOINT = "http://127.0.0.1:11434/v1"
OLLAMA_BASE = "http://127.0.0.1:11434"

CORE_LOCAL_TOOL_NAMES = {
    "open_app", "computer_control", "computer_settings", "system_diagnostics", "spotify_controller",
    "youtube_video", "web_search", "weather_report", "file_controller",
    "smart_organizer", "desktop_control", "execute_protocol", "reminder",
    "word_document", "pdf_document", "dev_agent", "recall_memory",
    "save_memory", "shutdown_brahma", "undo"
}



def convert_schema_to_lowercase(schema: Any) -> Any:
    """Recursively converts uppercase Gemini schema types (e.g. STRING, OBJECT) to lowercase (string, object)."""
    if not isinstance(schema, dict):
        return schema
    res = {}
    for k, v in schema.items():
        if k == "type" and isinstance(v, str):
            res[k] = v.lower()
        elif isinstance(v, dict):
            res[k] = convert_schema_to_lowercase(v)
        elif isinstance(v, list):
            res[k] = [convert_schema_to_lowercase(item) if isinstance(item, dict) else item for item in v]
        else:
            res[k] = v
    return res


class LocalBrain:
    def __init__(self, endpoint: str = DEFAULT_ENDPOINT, default_model: str = "qwen2.5:7b"):
        self.endpoint = endpoint.rstrip("/")
        self.default_model = default_model
        self.enabled = False
        self._cached_models: List[str] = []

    def ensure_running(self, timeout_seconds: float = 10.0) -> bool:
        """Checks if Ollama is running. If not, automatically launches ollama.exe in background."""
        if self.is_available():
            return True

        print("[BRAHMA SOL] Ollama engine not detected. Searching for executable...")
        candidates = [
            shutil.which("ollama"),
            os.path.expandvars(r"%LOCALAPPDATA%\Programs\Ollama\ollama.exe"),
            os.path.expandvars(r"%PROGRAMFILES%\Ollama\ollama.exe"),
            r"C:\Users\Suryaansh\AppData\Local\Programs\Ollama\ollama.exe",
            # macOS
            "/usr/local/bin/ollama",
            "/opt/homebrew/bin/ollama",
            "/Applications/Ollama.app/Contents/MacOS/Ollama",
        ]
        ollama_bin = next((p for p in candidates if p and os.path.exists(p)), None)
        if ollama_bin:
            try:
                print(f"[BRAHMA SOL] 🚀 Launching background Ollama daemon: {ollama_bin} serve")
                flags = subprocess.CREATE_NO_WINDOW if os.name == "nt" else 0
                subprocess.Popen([ollama_bin, "serve"], creationflags=flags)
            except Exception as exc:
                print(f"[BRAHMA SOL] ⚠️ Error launching Ollama daemon: {exc}")

        # Wait for Ollama to become responsive
        start_t = time.time()
        while time.time() - start_t < timeout_seconds:
            if self.is_available():
                print("[BRAHMA SOL] ✅ Ollama daemon is active and responding.")
                return True
            time.sleep(0.5)

        return self.is_available()

    def is_available(self) -> bool:
        """Checks if the local LLM server is up and responding."""
        try:
            req = urllib.request.Request(f"{OLLAMA_BASE}/api/tags", method="GET")
            with urllib.request.urlopen(req, timeout=2.5) as resp:
                if resp.status == 200:
                    data = json.loads(resp.read().decode("utf-8"))
                    self._cached_models = [m.get("name") for m in data.get("models", [])]
                    # Select best local model: prefer 7b, fallback to 3b
                    if self._cached_models:
                        if "qwen2.5:7b" in self._cached_models:
                            self.default_model = "qwen2.5:7b"
                        elif "qwen2.5:3b" in self._cached_models:
                            self.default_model = "qwen2.5:3b"
                    return True
        except Exception:
            pass
        return False

    def list_installed_models(self) -> List[str]:
        """Returns all downloaded models on the local runtime."""
        self.is_available()
        return self._cached_models

    def pull_model_async(self, model_name: str, progress_callback=None):
        """Pulls a model from the local runtime library in the background."""
        def _pull():
            try:
                url = f"{OLLAMA_BASE}/api/pull"
                payload = json.dumps({"name": model_name}).encode("utf-8")
                req = urllib.request.Request(url, data=payload, headers={"Content-Type": "application/json"})
                with urllib.request.urlopen(req, timeout=1200) as resp:
                    for line in resp:
                        if line:
                            try:
                                chunk = json.loads(line.decode("utf-8"))
                                if progress_callback:
                                    progress_callback(chunk)
                            except Exception:
                                pass
            except Exception as e:
                if progress_callback:
                    progress_callback({"error": str(e)})

        threading.Thread(target=_pull, daemon=True).start()

    def format_tools_for_local(
        self,
        tool_declarations: List[Dict[str, Any]],
        focus_core: bool = True
    ) -> List[Dict[str, Any]]:
        """
        Formats and converts Gemini or OpenAI-style tool declarations into
        strictly compliant OpenAI tools with lowercased JSON schema types.
        If focus_core is True, filters to core desktop operating tools for high precision on 3B/7B models.
        """
        formatted = []
        for t in tool_declarations:
            name = t.get("name") or (t.get("function", {}).get("name") if isinstance(t.get("function"), dict) else None)
            if not name:
                continue
            if focus_core and name not in CORE_LOCAL_TOOL_NAMES:
                continue
            
            # Already formatted OpenAI tool
            if "type" in t and t.get("type") == "function" and "function" in t:
                fn = dict(t["function"])
                if "parameters" in fn:
                    fn["parameters"] = convert_schema_to_lowercase(fn["parameters"])
                formatted.append({"type": "function", "function": fn})
            else:
                desc = t.get("description", "")
                raw_params = t.get("parameters", {"type": "object", "properties": {}})
                params = convert_schema_to_lowercase(raw_params)
                formatted.append({
                    "type": "function",
                    "function": {
                        "name": name,
                        "description": desc,
                        "parameters": params,
                    }
                })
        return formatted

    def generate_chat_stream(
        self,
        messages: List[Dict[str, Any]],
        model: Optional[str] = None,
        tools: Optional[List[Dict[str, Any]]] = None,
        temperature: float = 0.2,
    ) -> Generator[Dict[str, Any], None, None]:
        """
        Streams completions from the local runtime.
        Yields parsed stream delta chunks or tool calls.
        """
        active_model = model or self.default_model
        payload: Dict[str, Any] = {
            "model": active_model,
            "messages": messages,
            "temperature": temperature,
            "stream": True,
        }

        if tools:
            payload["tools"] = self.format_tools_for_local(tools, focus_core=False)

        data = json.dumps(payload).encode("utf-8")
        req = urllib.request.Request(
            f"{self.endpoint}/chat/completions",
            data=data,
            headers={"Content-Type": "application/json"},
        )

        with urllib.request.urlopen(req, timeout=60.0) as resp:
            for line in resp:
                line_str = line.decode("utf-8").strip()
                if line_str.startswith("data: "):
                    content = line_str[6:].strip()
                    if content == "[DONE]":
                        break
                    try:
                        chunk = json.loads(content)
                        yield chunk
                    except Exception:
                        pass

    def chat_complete(
        self,
        messages: List[Dict[str, Any]],
        model: Optional[str] = None,
        tools: Optional[List[Dict[str, Any]]] = None,
        temperature: float = 0.1,
        focus_core: bool = True,
    ) -> Dict[str, Any]:
        """Non-streaming completion for fast single-turn tool calls and structured responses."""
        active_model = model or self.default_model

        # Guard: Vision-only or non-tool models cannot handle tools in Ollama
        if tools and any(m in active_model.lower() for m in ("moondream", "llava", "bakllava")):
            print(f"[BRAHMA SOL] ⚠️ Model '{active_model}' does not support tools. Switching to tool-capable model...")
            if self.is_available() and "qwen2.5:7b" in self._cached_models:
                active_model = "qwen2.5:7b"
            elif self.is_available() and "qwen2.5:3b" in self._cached_models:
                active_model = "qwen2.5:3b"
            else:
                tools = None

        payload: Dict[str, Any] = {
            "model": active_model,
            "messages": messages,
            "temperature": temperature,
            "stream": False,
        }
        if tools:
            payload["tools"] = self.format_tools_for_local(tools, focus_core=focus_core)

        def _send(p_data: Dict[str, Any]) -> Dict[str, Any]:
            body = json.dumps(p_data).encode("utf-8")
            r = urllib.request.Request(
                f"{self.endpoint}/chat/completions",
                data=body,
                headers={"Content-Type": "application/json"},
            )
            with urllib.request.urlopen(r, timeout=90.0) as resp:
                return json.loads(resp.read().decode("utf-8"))

        try:
            return _send(payload)
        except urllib.error.HTTPError as h_err:
            err_body = ""
            try:
                err_body = h_err.read().decode("utf-8", errors="ignore")
            except Exception:
                pass
            print(f"[BRAHMA SOL] ⚠️ Ollama HTTP {h_err.code}: {err_body}")
            # If model does not support tools, fallback to qwen2.5 or strip tools
            if "does not support tools" in err_body.lower() and tools:
                print("[BRAHMA SOL] 🛡️ Auto-healing: retrying with qwen2.5:7b tool execution...")
                payload["model"] = "qwen2.5:7b"
                try:
                    return _send(payload)
                except Exception:
                    print("[BRAHMA SOL] 🛡️ Fallback: retrying without tools...")
                    payload.pop("tools", None)
                    return _send(payload)
            raise
        except (urllib.error.URLError, ConnectionError, OSError):
            # Attempt to auto-launch Ollama daemon and retry once
            print("[BRAHMA SOL] Connection refused. Booting local Ollama engine daemon...")
            if self.ensure_running(timeout_seconds=8.0):
                try:
                    return _send(payload)
                except Exception as retry_exc:
                    print(f"[BRAHMA SOL] Retry failed after daemon boot: {retry_exc}")
                    raise
            raise


# Global singleton instance
local_brain = LocalBrain()
