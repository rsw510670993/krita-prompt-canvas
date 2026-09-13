from __future__ import annotations

import os
import sys
from pathlib import Path


def app_data_dir() -> Path:
    override = os.environ.get("KPC_DATA_DIR")
    if override:
        return Path(override).expanduser().resolve()
    if sys.platform == "win32":
        base = Path(os.environ.get("LOCALAPPDATA", Path.home() / "AppData" / "Local"))
    elif sys.platform == "darwin":
        base = Path.home() / "Library" / "Application Support"
    else:
        base = Path(os.environ.get("XDG_DATA_HOME", Path.home() / ".local" / "share"))
    return base / "krita-prompt-canvas"


def queue_dir() -> Path:
    override = os.environ.get("KPC_QUEUE_DIR")
    return Path(override).expanduser().resolve() if override else app_data_dir() / "queue"


def default_output_dir() -> Path:
    override = os.environ.get("KPC_OUTPUT_DIR")
    return Path(override).expanduser().resolve() if override else Path.cwd() / "outputs"


def krita_plugin_dir() -> Path:
    if sys.platform == "win32":
        base = Path(os.environ.get("APPDATA", Path.home() / "AppData" / "Roaming"))
        return base / "krita" / "pykrita"
    if sys.platform == "darwin":
        return Path.home() / "Library" / "Application Support" / "krita" / "pykrita"
    return Path.home() / ".local" / "share" / "krita" / "pykrita"

