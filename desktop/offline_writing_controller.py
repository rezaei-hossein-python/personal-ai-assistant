from __future__ import annotations

import logging
import sys
import threading
import time
import traceback

from app.offline_writing import OfflineWritingConfig, OfflineWritingService
from app.offline_writing.provider import (
    OfflineWritingProviderError,
    OfflineWritingProviderUnavailable,
)
from app.offline_writing.providers.ollama_cli import OllamaCliOfflineWritingProvider
from desktop.hotkeys import HotkeyBinding, WindowsHotkeyManager
from desktop.settings import DesktopSettings
from desktop.text_selection import WindowsSelectedTextAdapter


class OfflineWritingController:
    def __init__(
        self,
        service: OfflineWritingService,
        text_adapter: WindowsSelectedTextAdapter,
        logger: logging.Logger | None = None,
    ):
        self.service = service
        self.text_adapter = text_adapter
        self.logger = logger or logging.getLogger("personal-ai-assistant")
        self._lock = threading.Lock()

    def trigger(self) -> None:
        thread = threading.Thread(
            target=self._run_revision,
            name="offline-writing-revision",
            daemon=True,
        )
        thread.start()

    def _run_revision(self) -> None:
        started = time.perf_counter()
        if not self._lock.acquire(blocking=False):
            self.logger.info("Offline writing skipped category=busy")
            return
        try:
            try:
                capture = self.text_adapter.capture()
            except Exception as exc:
                self.logger.warning(
                    "Offline writing capture failed category=%s",
                    exc.__class__.__name__,
                )
                return
            if capture is None:
                self.logger.info("Offline writing skipped category=empty_selection")
                return
            try:
                result = self.service.revise(capture.text)
            except OfflineWritingProviderError as exc:
                self.logger.warning(
                    "Offline writing local provider failure category=%s",
                    exc.__class__.__name__,
                )
                return
            except ImportError as exc:
                self.logger.error(
                    "Offline writing import failure stage=revision "
                    "exception_type=%s message=%s traceback=%s",
                    exc.__class__.__name__,
                    exc,
                    "".join(traceback.format_exception(exc.__class__, exc, exc.__traceback__)).rstrip(),
                )
                return
            except Exception as exc:
                self.logger.warning(
                    "Offline writing failed category=%s",
                    exc.__class__.__name__,
                )
                return
            if not self.text_adapter.replace(capture, result.revised_text):
                self.logger.warning(
                    "Offline writing replacement skipped category=focus_changed"
                )
            duration_ms = (time.perf_counter() - started) * 1000
            self.logger.info("Offline writing operation completed duration_ms=%.2f", duration_ms)
        finally:
            duration_ms = (time.perf_counter() - started) * 1000
            self.logger.info("Offline writing total duration_ms=%.2f", duration_ms)
            self._lock.release()


class DesktopOfflineWritingRuntime:
    def __init__(self, hotkey_manager: WindowsHotkeyManager | None):
        self.hotkey_manager = hotkey_manager

    @property
    def has_registered_hotkeys(self) -> bool:
        return bool(self.hotkey_manager and self.hotkey_manager.registered_count)

    def stop(self) -> None:
        if self.hotkey_manager:
            self.hotkey_manager.stop()


def start_offline_writing_runtime(
    settings: DesktopSettings,
    logger: logging.Logger | None = None,
) -> DesktopOfflineWritingRuntime:
    logger = logger or logging.getLogger("personal-ai-assistant")
    if sys.platform != "win32":
        logger.info("Offline writing hotkey skipped platform=%s", sys.platform)
        return DesktopOfflineWritingRuntime(None)
    config = OfflineWritingConfig(
        enabled=settings.offline_writing_enabled,
        provider=settings.offline_writing_provider,
        model=settings.offline_writing_model,
        hotkey=settings.offline_writing_hotkey,
        timeout_seconds=settings.offline_writing_timeout_seconds,
        max_characters=settings.offline_writing_max_characters,
        ollama_base_url=settings.offline_writing_ollama_base_url,
    )
    if not config.enabled:
        logger.info("Offline writing hotkey disabled")
        return DesktopOfflineWritingRuntime(None)
    if config.provider != "ollama_cli":
        logger.error("Unsupported offline writing provider=%s", config.provider)
        return DesktopOfflineWritingRuntime(None)

    try:
        provider = OllamaCliOfflineWritingProvider(
            model=config.model,
            base_url=config.ollama_base_url,
        )
    except OfflineWritingProviderUnavailable:
        logger.error("Offline writing provider unavailable category=invalid_local_endpoint")
        return DesktopOfflineWritingRuntime(None)
    service = OfflineWritingService(provider=provider, config=config, logger=logger)
    controller = OfflineWritingController(
        service=service,
        text_adapter=WindowsSelectedTextAdapter(logger=logger),
        logger=logger,
    )
    hotkey_manager = WindowsHotkeyManager(
        bindings=[
            HotkeyBinding(
                identifier=15001,
                shortcut=config.hotkey,
                callback=controller.trigger,
            )
        ],
        logger=logger,
    )
    hotkey_manager.start()
    return DesktopOfflineWritingRuntime(hotkey_manager)


def diagnose_ollama_local_http_provider(
    settings: DesktopSettings,
    logger: logging.Logger | None = None,
) -> bool:
    logger = logger or logging.getLogger("personal-ai-assistant")
    config = OfflineWritingConfig(
        enabled=settings.offline_writing_enabled,
        provider=settings.offline_writing_provider,
        model=settings.offline_writing_model,
        hotkey=settings.offline_writing_hotkey,
        timeout_seconds=settings.offline_writing_timeout_seconds,
        max_characters=settings.offline_writing_max_characters,
        ollama_base_url=settings.offline_writing_ollama_base_url,
    )
    try:
        logger.info("Offline writing provider diagnostic stage=provider_construct")
        provider = OllamaCliOfflineWritingProvider(
            model=config.model,
            base_url=config.ollama_base_url,
        )
        logger.info(
            "Offline writing provider diagnostic stage=http_client_import provider=%s model=%s",
            provider.provider_name,
            provider.model_identifier,
        )
        provider.validate_http_runtime()
        logger.info("Offline writing provider diagnostic stage=ollama_tags_request")
        provider.ensure_model_available_for_diagnostic(timeout_seconds=5.0)
        logger.info(
            "Offline writing provider diagnostic succeeded provider=%s model=%s",
            provider.provider_name,
            provider.model_identifier,
        )
        return True
    except ImportError as exc:
        logger.error(
            "Offline writing import failure stage=diagnostic "
            "exception_type=%s message=%s traceback=%s",
            exc.__class__.__name__,
            exc,
            "".join(traceback.format_exception(exc.__class__, exc, exc.__traceback__)).rstrip(),
        )
        return False
    except OfflineWritingProviderError as exc:
        logger.warning(
            "Offline writing provider diagnostic failed category=%s message=%s",
            exc.__class__.__name__,
            exc,
        )
        return False
