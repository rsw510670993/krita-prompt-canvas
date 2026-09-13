from __future__ import annotations

import shutil
from importlib.resources import files
from pathlib import Path

from .paths import krita_plugin_dir


PLUGIN_NAME = "krita_prompt_canvas_bridge"


def install_plugin(destination: Path | None = None) -> tuple[Path, Path]:
    target_root = destination or krita_plugin_dir()
    target_root.mkdir(parents=True, exist_ok=True)
    assets = files("krita_prompt_canvas") / "plugin_assets"
    source_package = assets / PLUGIN_NAME
    source_desktop = assets / f"{PLUGIN_NAME}.desktop"
    target_package = target_root / PLUGIN_NAME
    target_desktop = target_root / f"{PLUGIN_NAME}.desktop"
    if target_package.exists():
        shutil.rmtree(target_package)
    shutil.copytree(str(source_package), target_package)
    shutil.copy2(str(source_desktop), target_desktop)
    return target_package, target_desktop

