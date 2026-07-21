from __future__ import annotations

import logging
import json
import os
import secrets
import socket
import threading
import time
from dataclasses import dataclass

import httpx
import uvicorn

from desktop.paths import DesktopPaths
from desktop.secrets import DesktopSecretService
from desktop.settings import DesktopSettings


@dataclass
class DesktopBackend:
    host: str
    port: int
    server: uvicorn.Server
    thread: threading.Thread

    @property
    def url(self) -> str:
        return f"http://{self.host}:{self.port}"


def configure_desktop_environment(
    paths: DesktopPaths,
    settings: DesktopSettings,
    secret_service: DesktopSecretService | None = None,
    port: int | None = None,
) -> int:
    selected_port = port or select_loopback_port()
    secret_service = secret_service or DesktopSecretService()
    openai_key = secret_service.get_secret("OPENAI_API_KEY") or ""
    jwt_secret = secret_service.get_secret("JWT_SECRET_KEY")
    if not jwt_secret:
        jwt_secret = secrets.token_urlsafe(48)
        secret_service.set_secret("JWT_SECRET_KEY", jwt_secret)

    os.environ.update(
        {
            "APP_ENV": "desktop",
            "DESKTOP_MODE": "true",
            "DATABASE_BACKEND": settings.database_backend,
            "DATABASE_URL": f"sqlite:///{paths.sqlite_database.as_posix()}",
            "API_HOST": "127.0.0.1",
            "API_PORT": str(selected_port),
            "ALLOWED_ORIGINS": json.dumps([f"http://127.0.0.1:{selected_port}"]),
            "TRUSTED_HOSTS": json.dumps(["127.0.0.1", "localhost"]),
            "API_DOCS_ENABLED": "false",
            "DEBUG": "false",
            "OPENAI_API_KEY": openai_key,
            "JWT_SECRET_KEY": jwt_secret,
            "SECRET_KEY": jwt_secret,
            "DESKTOP_DATA_DIR": str(paths.data_dir),
            "DESKTOP_LOG_DIR": str(paths.logs_dir),
            "DESKTOP_FRONTEND_DIR": str(paths.frontend_dir),
        }
    )
    return selected_port


def start_backend(host: str = "127.0.0.1", port: int | None = None) -> DesktopBackend:
    if host != "127.0.0.1":
        raise RuntimeError("Desktop backend must bind to 127.0.0.1")
    selected_port = port or int(os.environ["API_PORT"])

    from app.main import app

    config = uvicorn.Config(
        app,
        host=host,
        port=selected_port,
        log_level="info",
        access_log=False,
        log_config=None,
        loop="asyncio",
    )
    server = uvicorn.Server(config)
    thread = threading.Thread(target=server.run, name="desktop-backend", daemon=True)
    thread.start()
    return DesktopBackend(host=host, port=selected_port, server=server, thread=thread)


def wait_for_readiness(url: str, attempts: int = 40, delay_seconds: float = 0.25) -> None:
    last_error: Exception | None = None
    for _ in range(attempts):
        try:
            response = httpx.get(f"{url}/ready", timeout=1.0)
            if response.status_code == 200:
                return
        except Exception as exc:
            last_error = exc
        time.sleep(delay_seconds)
    raise RuntimeError("Desktop backend did not become ready") from last_error


def stop_backend(backend: DesktopBackend, timeout_seconds: float = 8.0) -> None:
    backend.server.should_exit = True
    backend.thread.join(timeout=timeout_seconds)
    if backend.thread.is_alive():
        logging.getLogger("personal-ai-assistant").warning(
            "Backend thread did not stop before timeout"
        )


def select_loopback_port() -> int:
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
        sock.bind(("127.0.0.1", 0))
        return int(sock.getsockname()[1])
