import json
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

from app.providers.model_provider import ProviderAvailabilityError


def post_json(
    url: str,
    headers: dict[str, str],
    payload: dict,
    timeout_seconds: int = 60,
) -> dict:
    request = Request(
        url=url,
        data=json.dumps(payload).encode("utf-8"),
        headers={
            "Content-Type": "application/json",
            **headers,
        },
        method="POST",
    )

    try:
        with urlopen(request, timeout=timeout_seconds) as response:
            return json.loads(response.read().decode("utf-8"))
    except HTTPError as exc:
        details = exc.read().decode("utf-8", errors="replace")
        raise ProviderAvailabilityError(
            f"Provider HTTP error {exc.code}: {details[:500]}"
        ) from exc
    except URLError as exc:
        raise ProviderAvailabilityError(
            f"Provider request failed: {exc.reason}"
        ) from exc
