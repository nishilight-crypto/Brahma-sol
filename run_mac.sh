#!/bin/bash
# Brahma Sol — macOS launcher
cd "$(dirname "$0")"
if [ ! -d .venv ]; then
  echo "Creating Python 3.12 venv..."
  /opt/homebrew/bin/python3.12 -m venv .venv
  CFLAGS="-I/opt/homebrew/include" LDFLAGS="-L/opt/homebrew/lib" .venv/bin/pip install -r requirements-mac.txt
  .venv/bin/python -m playwright install chromium
fi
# Start Ollama if installed and not running
if command -v ollama >/dev/null && ! pgrep -x ollama >/dev/null; then
  (ollama serve >/dev/null 2>&1 &)
fi
exec .venv/bin/python main.py "$@"
