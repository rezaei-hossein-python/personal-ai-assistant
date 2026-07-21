from __future__ import annotations

SERVICE_NAME = "PersonalAIAssistant"


class SecretStorageError(RuntimeError):
    pass


class DesktopSecretService:
    def __init__(self, service_name: str = SERVICE_NAME):
        self.service_name = service_name

    def get_secret(self, name: str) -> str | None:
        try:
            import keyring

            return keyring.get_password(self.service_name, name)
        except Exception as exc:
            raise SecretStorageError("Secure secret storage is unavailable") from exc

    def set_secret(self, name: str, value: str) -> None:
        try:
            import keyring

            keyring.set_password(self.service_name, name, value)
        except Exception as exc:
            raise SecretStorageError("Secure secret storage is unavailable") from exc

    def delete_secret(self, name: str) -> None:
        try:
            import keyring

            try:
                keyring.delete_password(self.service_name, name)
            except keyring.errors.PasswordDeleteError:
                return
        except Exception as exc:
            raise SecretStorageError("Secure secret storage is unavailable") from exc

    def has_secret(self, name: str) -> bool:
        return bool(self.get_secret(name))
