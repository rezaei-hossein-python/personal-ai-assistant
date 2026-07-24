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
    offline_writing_enabled: bool = True
    offline_writing_provider: str = "ollama_cli"
    offline_writing_model: str = "llama3.2:3b"
    offline_writing_ollama_base_url: str = "http://127.0.0.1:11434"
    offline_writing_hotkey: str = "Ctrl+Alt+W"
    offline_writing_timeout_seconds: float = 45.0
    offline_writing_max_characters: int = 4000


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
