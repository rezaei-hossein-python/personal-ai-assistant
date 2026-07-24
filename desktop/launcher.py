from __future__ import annotations

import ctypes
import logging
import sys
from datetime import datetime, timezone

from desktop.paths import ensure_desktop_directories, resolve_desktop_paths
from desktop.settings import load_desktop_settings, save_desktop_settings


APP_TITLE = "Personal AI Assistant"
_MUTEX_HANDLE = None


def run_desktop() -> int:
    if not _acquire_single_instance_mutex():
        _show_error("Personal AI Assistant is already running.")
        return 1

    paths = resolve_desktop_paths()
    ensure_desktop_directories(paths)
    launcher_log = paths.logs_dir / "desktop-launcher.log"
    settings = load_desktop_settings(paths)
    save_desktop_settings(paths, settings)
    _setup_launcher_logging(launcher_log)
    _append_launcher_log(launcher_log, f"Launcher starting data_dir={paths.data_dir}")

    backend = None
    try:
        from desktop.lifecycle import (
            configure_desktop_environment,
            start_backend,
            wait_for_readiness,
        )

        port = configure_desktop_environment(paths, settings)
        logging.info("Starting desktop backend data_dir=%s port=%s", paths.data_dir, port)
        _append_launcher_log(launcher_log, f"Starting backend port={port}")
        backend = start_backend(port=port)
        wait_for_readiness(backend.url)
        _append_launcher_log(launcher_log, f"Backend ready url={backend.url}")
        _open_window(
            url=backend.url,
            width=settings.window_width,
            height=settings.window_height,
            min_width=settings.window_min_width,
            min_height=settings.window_min_height,
        )
        return 0
    except Exception as exc:
        logging.exception("Desktop startup failed")
        _append_launcher_log(launcher_log, f"Startup failed error={exc}")
        _show_error(f"Personal AI Assistant could not start.\n\n{exc}")
        return 1
    finally:
        if backend is not None:
            from desktop.lifecycle import stop_backend

            stop_backend(backend)
            logging.info("Desktop backend stopped")
            _append_launcher_log(launcher_log, "Backend stopped")


def _open_window(url: str, width: int, height: int, min_width: int, min_height: int) -> None:
    import webview

    window = webview.create_window(
        APP_TITLE,
        url,
        width=width,
        height=height,
        min_size=(min_width, min_height),
        resizable=True,
    )
    webview.start(debug=False)


def _show_error(message: str) -> None:
    try:
        ctypes.windll.user32.MessageBoxW(None, message, APP_TITLE, 0x10)
    except Exception:
        print(message, file=sys.stderr)


def _setup_launcher_logging(log_file) -> None:
    logging.basicConfig(
        filename=str(log_file),
        level=logging.INFO,
        format="%(asctime)s | %(levelname)s | %(name)s | %(message)s",
        force=True,
    )


def _append_launcher_log(log_file, message: str) -> None:
    try:
        timestamp = datetime.now(timezone.utc).isoformat()
        with open(log_file, "a", encoding="utf-8") as handle:
            handle.write(f"{timestamp} | {message}\n")
    except OSError:
        return


def _acquire_single_instance_mutex() -> bool:
    global _MUTEX_HANDLE
    try:
        kernel32 = ctypes.windll.kernel32
        _MUTEX_HANDLE = kernel32.CreateMutexW(
            None,
            False,
            "PersonalAIAssistantDesktopV1",
        )
        return kernel32.GetLastError() != 183
    except Exception:
        return True
