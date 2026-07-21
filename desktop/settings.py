from __future__ import annotations

import json
from dataclasses import asdict, dataclass

from desktop.paths import DesktopPaths


@dataclass
class DesktopSettings:
    window_width: int = 1280
    window_height: int = 820
    window_min_width: int = 960
    window_min_height: int = 640
    database_backend: str = "sqlite"


def load_desktop_settings(paths: DesktopPaths) -> DesktopSettings:
    if not paths.settings_file.exists():
        return DesktopSettings()
    try:
        raw = json.loads(paths.settings_file.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return DesktopSettings()
    allowed = {field: raw[field] for field in asdict(DesktopSettings()) if field in raw}
    return DesktopSettings(**allowed)


def save_desktop_settings(paths: DesktopPaths, settings: DesktopSettings) -> None:
    paths.settings_file.write_text(
        json.dumps(asdict(settings), indent=2, sort_keys=True),
        encoding="utf-8",
    )
