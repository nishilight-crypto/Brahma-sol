import os
import sys
from pathlib import Path


def get_user_data_dir() -> Path:
    override = os.getenv("BRAHMA_DATA_DIR")
    if override:
        d = Path(override)
    elif sys.platform == "darwin":
        d = Path.home() / "Library" / "Application Support" / "BrahmaSol"
    else:
        app_data = os.getenv('LOCALAPPDATA', os.path.expanduser('~'))
        d = Path(app_data) / 'BrahmaAI'
    try:
        d.mkdir(parents=True, exist_ok=True)
    except OSError:
        pass
    return d
