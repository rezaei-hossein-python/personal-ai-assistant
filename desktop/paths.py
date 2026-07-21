from __future__ import annotations

import os
import sys
from dataclasses import dataclass
from pathlib import Path


APP_DIR_NAME = "PersonalAIAssistant"


@dataclass(frozen=True)
class DesktopPaths:
    data_dir: Path
    database_dir: Path
    logs_dir: Path
    cache_dir: Path
    temp_dir: Path
    backups_dir: Path
    settings_file: Path
    sqlite_database: Path
    frontend_dir: Path


def get_runtime_root() -> Path:
    bundle_root = getattr(sys, "_MEIPASS", None)
    if bundle_root:
        return Path(bundle_root).resolve()
    return Path(__file__).resolve().parents[1]


def get_default_data_dir() -> Path:
    local_app_data = os.environ.get("LOCALAPPDATA")
    if local_app_data:
        return Path(local_app_data) / APP_DIR_NAME
    return Path.home() / "AppData" / "Local" / APP_DIR_NAME


def resolve_desktop_paths(data_dir: str | Path | None = None) -> DesktopPaths:
    root = Path(data_dir).expanduser() if data_dir else get_default_data_dir()
    root = root.resolve()
    frontend_dir = _resolve_frontend_dir()
    return DesktopPaths(
        data_dir=root,
        database_dir=root / "database",
        logs_dir=root / "logs",
        cache_dir=root / "cache",
        temp_dir=root / "temp",
        backups_dir=root / "backups",
        settings_file=root / "settings.json",
        sqlite_database=root / "database" / "assistant.sqlite3",
        frontend_dir=frontend_dir,
    )


def ensure_desktop_directories(paths: DesktopPaths) -> None:
    for directory in (
        paths.data_dir,
        paths.database_dir,
        paths.logs_dir,
        paths.cache_dir,
        paths.temp_dir,
        paths.backups_dir,
    ):
        directory.mkdir(parents=True, exist_ok=True)


def _resolve_frontend_dir() -> Path:
    runtime_root = get_runtime_root()
    bundled = runtime_root / "frontend_dist"
    if bundled.exists():
        return bundled.resolve()
    return (runtime_root / "frontend" / "dist").resolve()
