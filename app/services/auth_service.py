import base64
import hashlib
import hmac
import json
import secrets
from datetime import datetime, timedelta, timezone

from app.config import settings


def hash_password(password: str) -> str:
    salt = secrets.token_bytes(16)
    password_hash = hashlib.pbkdf2_hmac(
        "sha256",
        password.encode("utf-8"),
        salt,
        600_000,
    )
    return (
        f"pbkdf2_sha256$600000$"
        f"{base64.urlsafe_b64encode(salt).decode('utf-8')}$"
        f"{base64.urlsafe_b64encode(password_hash).decode('utf-8')}"
    )


def verify_password(password: str, hashed_password: str) -> bool:
    try:
        algorithm, iterations, salt, expected_hash = hashed_password.split("$")
        if algorithm != "pbkdf2_sha256":
            return False

        password_hash = hashlib.pbkdf2_hmac(
            "sha256",
            password.encode("utf-8"),
            base64.urlsafe_b64decode(salt.encode("utf-8")),
            int(iterations),
        )
        return hmac.compare_digest(
            base64.urlsafe_b64encode(password_hash).decode("utf-8"),
            expected_hash,
        )
    except Exception:
        return False


def _base64url_encode(data: bytes) -> str:
    return base64.urlsafe_b64encode(data).rstrip(b"=").decode("utf-8")


def _base64url_decode(data: str) -> bytes:
    padding = "=" * (-len(data) % 4)
    return base64.urlsafe_b64decode((data + padding).encode("utf-8"))


def create_access_token(user_id: int) -> str:
    now = datetime.now(timezone.utc)
    expires_at = now + timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
    if settings.JWT_ALGORITHM != "HS256":
        raise RuntimeError("Only HS256 JWT tokens are supported")

    header = {"alg": settings.JWT_ALGORITHM, "typ": "JWT"}
    payload = {
        "sub": str(user_id),
        "iat": int(now.timestamp()),
        "exp": int(expires_at.timestamp()),
    }

    encoded_header = _base64url_encode(
        json.dumps(header, separators=(",", ":")).encode("utf-8")
    )
    encoded_payload = _base64url_encode(
        json.dumps(payload, separators=(",", ":")).encode("utf-8")
    )
    signing_input = f"{encoded_header}.{encoded_payload}".encode("utf-8")
    signature = hmac.new(
        settings.SECRET_KEY.encode("utf-8"),
        signing_input,
        hashlib.sha256,
    ).digest()

    return f"{encoded_header}.{encoded_payload}.{_base64url_encode(signature)}"


def decode_access_token(token: str) -> int:
    try:
        encoded_header, encoded_payload, encoded_signature = token.split(".")
        signing_input = f"{encoded_header}.{encoded_payload}".encode("utf-8")
        expected_signature = hmac.new(
            settings.SECRET_KEY.encode("utf-8"),
            signing_input,
            hashlib.sha256,
        ).digest()

        if not hmac.compare_digest(
            _base64url_encode(expected_signature),
            encoded_signature,
        ):
            raise ValueError("Invalid token signature")

        payload = json.loads(_base64url_decode(encoded_payload))
        header = json.loads(_base64url_decode(encoded_header))
        if header.get("alg") != settings.JWT_ALGORITHM:
            raise ValueError("Invalid token algorithm")
        expires_at = int(payload["exp"])
        if expires_at < int(datetime.now(timezone.utc).timestamp()):
            raise ValueError("Token expired")

        return int(payload["sub"])
    except Exception as exc:
        raise ValueError("Invalid access token") from exc
