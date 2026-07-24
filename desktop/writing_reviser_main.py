from __future__ import annotations

import argparse
import ctypes
import logging
import signal
import sys
import threading
from datetime import datetime, timezone
from pathlib import Path

from desktop.offline_writing_controller import (
    diagnose_ollama_local_http_provider,
    start_offline_writing_runtime,
)
from desktop.paths import ensure_desktop_directories, resolve_desktop_paths
from desktop.settings import load_desktop_settings, save_desktop_settings
from desktop.single_instance import WindowsSingleInstance
from desktop.windows_startup import (
    default_packaged_reviser_path,
    disable_writing_reviser_startup,
    enable_writing_reviser_startup,
    get_writing_reviser_startup_state,
)


APP_NAME = "Personal AI Writing Reviser"
MUTEX_NAME = r"Local\PersonalAIWritingReviserV1"


class WritingReviserBackgroundApp:
    def __init__(
        self,
        stop_event: threading.Event | None = None,
        instance: WindowsSingleInstance | None = None,
    ):
        self.stop_event = stop_event or threading.Event()
        self.instance = instance or WindowsSingleInstance(MUTEX_NAME)
        self.runtime = None

    def run(self) -> int:
        if not self.instance.acquire():
            return 0

        paths = resolve_desktop_paths()
        ensure_desktop_directories(paths)
        log_file = paths.logs_dir / "writing-reviser.log"
        _setup_logging(log_file)
        _append_log(log_file, f"Writing reviser starting data_dir={paths.data_dir}")

        try:
            settings = load_desktop_settings(paths)
            save_desktop_settings(paths, settings)
            self.runtime = start_offline_writing_runtime(settings, logger=logging.getLogger())
            if not self.runtime.has_registered_hotkeys:
                logging.error("Offline writing background startup failed stage=hotkey_unavailable")
                return 1
            _install_shutdown_handlers(self.stop_event)
            logging.info("Offline writing background process ready")
            while not self.stop_event.wait(timeout=60):
                pass
            return 0
        except Exception as exc:
            logging.exception("Offline writing background process failed")
            _append_log(log_file, f"Writing reviser failed error={exc}")
            return 1
        finally:
            if self.runtime is not None:
                self.runtime.stop()
                logging.info("Offline writing background runtime stopped")
            self.instance.release()


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=APP_NAME)
    parser.add_argument("--enable-startup", action="store_true")
    parser.add_argument("--disable-startup", action="store_true")
    parser.add_argument("--startup-status", action="store_true")
    parser.add_argument("--diagnose-ollama-provider", action="store_true")
    parser.add_argument("--exe", help="Packaged PersonalAIWritingReviser.exe path")
    args = parser.parse_args(argv)

    if args.enable_startup:
        enable_writing_reviser_startup(args.exe or default_packaged_reviser_path())
        return 0
    if args.disable_startup:
        disable_writing_reviser_startup()
        return 0
    if args.startup_status:
        state = get_writing_reviser_startup_state()
        print(f"enabled={state.enabled} command={state.command or ''}")
        return 0
    if args.diagnose_ollama_provider:
        paths = resolve_desktop_paths()
        ensure_desktop_directories(paths)
        _setup_logging(paths.logs_dir / "writing-reviser.log")
        settings = load_desktop_settings(paths)
        return 0 if diagnose_ollama_local_http_provider(settings, logger=logging.getLogger()) else 1

    return WritingReviserBackgroundApp().run()


def _setup_logging(log_file: Path) -> None:
    logging.basicConfig(
        filename=str(log_file),
        level=logging.INFO,
        format="%(asctime)s | %(levelname)s | %(name)s | %(message)s",
        force=True,
    )


def _append_log(log_file: Path, message: str) -> None:
    try:
        timestamp = datetime.now(timezone.utc).isoformat()
        with open(log_file, "a", encoding="utf-8") as handle:
            handle.write(f"{timestamp} | {message}\n")
    except OSError:
        return


def _install_shutdown_handlers(stop_event: threading.Event) -> None:
    def request_stop(*_args) -> None:
        stop_event.set()

    signal.signal(signal.SIGTERM, request_stop)
    signal.signal(signal.SIGINT, request_stop)
    if sys.platform == "win32":
        try:
            handler_type = ctypes.WINFUNCTYPE(ctypes.c_bool, ctypes.c_ulong)

            @handler_type
            def console_handler(_event) -> bool:
                stop_event.set()
                return True

            _install_shutdown_handlers._console_handler = console_handler
            ctypes.windll.kernel32.SetConsoleCtrlHandler(console_handler, True)
        except Exception:
            return


if __name__ == "__main__":
    raise SystemExit(main())
