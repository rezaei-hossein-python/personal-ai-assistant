from __future__ import annotations

import sys
from dataclasses import dataclass
from pathlib import Path

try:
    import winreg
except ImportError:  # pragma: no cover - exercised only off Windows
    winreg = None


RUN_KEY = r"Software\Microsoft\Windows\CurrentVersion\Run"
WRITING_REVISER_VALUE_NAME = "PersonalAIWritingReviser"


@dataclass(frozen=True)
class StartupState:
    enabled: bool
    command: str | None


def enable_writing_reviser_startup(executable: str | Path) -> None:
    _require_winreg()
    exe_path = Path(executable).expanduser().resolve()
    if exe_path.suffix.lower() != ".exe":
        raise ValueError("Startup must point to the packaged reviser .exe")
    if not exe_path.exists():
        raise FileNotFoundError(f"Packaged reviser executable not found: {exe_path}")
    command = f'"{exe_path}"'
    with winreg.OpenKey(
        winreg.HKEY_CURRENT_USER,
        RUN_KEY,
        0,
        winreg.KEY_SET_VALUE,
    ) as key:
        winreg.SetValueEx(key, WRITING_REVISER_VALUE_NAME, 0, winreg.REG_SZ, command)


def disable_writing_reviser_startup() -> None:
    _require_winreg()
    with winreg.OpenKey(
        winreg.HKEY_CURRENT_USER,
        RUN_KEY,
        0,
        winreg.KEY_SET_VALUE,
    ) as key:
        try:
            winreg.DeleteValue(key, WRITING_REVISER_VALUE_NAME)
        except FileNotFoundError:
            return


def get_writing_reviser_startup_state() -> StartupState:
    _require_winreg()
    with winreg.OpenKey(winreg.HKEY_CURRENT_USER, RUN_KEY, 0, winreg.KEY_READ) as key:
        try:
            value, _ = winreg.QueryValueEx(key, WRITING_REVISER_VALUE_NAME)
        except FileNotFoundError:
            return StartupState(enabled=False, command=None)
    return StartupState(enabled=True, command=str(value))


def default_packaged_reviser_path() -> Path:
    if getattr(sys, "frozen", False):
        return Path(sys.executable).resolve()
    return (
        Path(__file__).resolve().parents[1]
        / "dist"
        / "PersonalAIWritingReviser"
        / "PersonalAIWritingReviser.exe"
    ).resolve()


def _require_winreg() -> None:
    if winreg is None:
        raise RuntimeError("Windows startup integration is only available on Windows")
