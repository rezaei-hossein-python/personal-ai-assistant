from __future__ import annotations

import logging
import re
import threading
import time
import unicodedata
from dataclasses import dataclass

from app.offline_writing.provider import (
    OfflineWritingProvider,
    OfflineWritingProviderError,
    OfflineWritingProviderTimeout,
    OfflineWritingProviderUnavailable,
)


REVISION_INSTRUCTION = """You are an offline writing revision engine.
Task: make the minimum changes required to turn the user's selected English text into polished, natural, grammatically correct English with the minimum necessary edits.

Rules:
- Make the smallest set of changes needed to correct grammar, spelling, punctuation, awkward phrasing, sentence structure, and naturalness.
- Preserve tense unless grammar or explicit context requires correcting it.
- Respect explicit time markers such as yesterday, today, tomorrow, since, for, already, and yet.
- Preserve pronouns exactly unless grammar makes the original pronoun impossible.
- Preserve names.
- Preserve meaning, facts, numbers, dates, email addresses, URLs, and tone.
- Avoid unnecessary synonyms.
- Do not make wording more formal unless required.
- Do not add information.
- Do not remove information.
- Preserve paragraph structure where reasonable.
- Return only the revised text.
- Do not include explanations, headings, commentary, quotation marks around the result, markdown, preambles, conclusions, scores, or correction lists.

Examples:
Input:
I have spoke with client yesterday and he said he don't received the documents yet.
Preferred:
I spoke with the client yesterday, and he said he hadn't received the documents yet."""


class OfflineWritingError(RuntimeError):
    pass


class OfflineWritingBusy(OfflineWritingError):
    pass


class OfflineWritingInputError(OfflineWritingError):
    pass


class OfflineWritingMalformedOutput(OfflineWritingError):
    pass


@dataclass(frozen=True)
class OfflineWritingConfig:
    enabled: bool = True
    provider: str = "ollama_cli"
    model: str = "llama3.2:3b"
    hotkey: str = "Ctrl+Alt+W"
    timeout_seconds: float = 45.0
    max_characters: int = 4000
    ollama_base_url: str = "http://127.0.0.1:11434"


@dataclass(frozen=True)
class WritingRevisionResult:
    original_character_count: int
    revised_text: str
    provider: str
    model: str
    duration_ms: float


class OfflineWritingService:
    def __init__(
        self,
        provider: OfflineWritingProvider,
        config: OfflineWritingConfig | None = None,
        logger: logging.Logger | None = None,
    ):
        self.provider = provider
        self.config = config or OfflineWritingConfig()
        self.logger = logger or logging.getLogger("personal-ai-assistant")
        self._lock = threading.Lock()

    def revise(self, selected_text: str) -> WritingRevisionResult:
        if not self.config.enabled:
            raise OfflineWritingInputError("Offline writing is disabled")
        if not selected_text or not selected_text.strip():
            raise OfflineWritingInputError("Selection is empty")
        if len(selected_text) > self.config.max_characters:
            raise OfflineWritingInputError("Selection exceeds maximum length")
        if not self._lock.acquire(blocking=False):
            raise OfflineWritingBusy("Offline writing revision already running")

        started = time.perf_counter()
        self.logger.info(
            "Offline writing local revision started chars=%s provider=%s model=%s",
            len(selected_text),
            self.provider.provider_name,
            self.provider.model_identifier,
        )
        try:
            if not self.provider.is_available():
                raise OfflineWritingProviderUnavailable("Local writing provider unavailable")
            self.logger.info(
                "Offline writing Ollama invocation started provider=%s model=%s",
                self.provider.provider_name,
                self.provider.model_identifier,
            )
            raw_output = self.provider.revise(
                selected_text,
                REVISION_INSTRUCTION,
                timeout_seconds=self.config.timeout_seconds,
            )
            self.logger.info(
                "Offline writing Ollama invocation completed raw_chars=%s provider=%s model=%s",
                len(raw_output),
                self.provider.provider_name,
                self.provider.model_identifier,
            )
            revised_text = sanitize_revision_output(raw_output, original_text=selected_text)
            duration_ms = (time.perf_counter() - started) * 1000
            self.logger.info(
                "Offline writing local revision succeeded original_chars=%s "
                "revised_chars=%s duration_ms=%.2f "
                "provider=%s model=%s",
                len(selected_text),
                len(revised_text),
                duration_ms,
                self.provider.provider_name,
                self.provider.model_identifier,
            )
            return WritingRevisionResult(
                original_character_count=len(selected_text),
                revised_text=revised_text,
                provider=self.provider.provider_name,
                model=self.provider.model_identifier,
                duration_ms=duration_ms,
            )
        except (
            OfflineWritingBusy,
            OfflineWritingInputError,
            OfflineWritingMalformedOutput,
            OfflineWritingProviderError,
            OfflineWritingProviderTimeout,
            OfflineWritingProviderUnavailable,
        ):
            duration_ms = (time.perf_counter() - started) * 1000
            self.logger.warning(
                "Offline writing revision failed category=%s chars=%s "
                "duration_ms=%.2f provider=%s model=%s",
                "local_failure",
                len(selected_text),
                duration_ms,
                self.provider.provider_name,
                self.provider.model_identifier,
            )
            raise
        finally:
            self._lock.release()


ANSI_CSI_PATTERN = re.compile(r"\x1b\[[0-?]*[ -/]*[@-~]")
ANSI_OSC_PATTERN = re.compile(r"\x1b\][^\x07\x1b]*(?:\x07|\x1b\\)")
ANSI_ESCAPE_PATTERN = re.compile(r"\x1b[@-Z\\-_]")
CONTROL_CHARACTER_PATTERN = re.compile(r"[\x00-\x08\x0b\x0c\x0e-\x1f\x7f]")
MARKDOWN_FENCE_PATTERN = re.compile(
    r"^\s*```[^\r\n]*\r?\n(?P<body>.*?)(?:\r?\n)?```\s*$",
    re.DOTALL,
)


def sanitize_revision_output(output: str, original_text: str | None = None) -> str:
    if "\x00" in output:
        raise OfflineWritingMalformedOutput("Local model returned null bytes")
    revised = ANSI_OSC_PATTERN.sub("", output)
    revised = ANSI_CSI_PATTERN.sub("", revised)
    revised = ANSI_ESCAPE_PATTERN.sub("", revised)
    if "\x1b" in revised:
        raise OfflineWritingMalformedOutput("Local model returned escape characters")
    revised = revised.replace("\r\n", "\n").replace("\r", "\n")
    fenced = MARKDOWN_FENCE_PATTERN.match(revised)
    if fenced:
        revised = fenced.group("body")
    revised = CONTROL_CHARACTER_PATTERN.sub("", revised)
    revised = revised.strip()
    if not revised:
        raise OfflineWritingMalformedOutput("Local model returned empty output")
    if "```" in revised:
        raise OfflineWritingMalformedOutput("Local model returned markdown fences")
    lowered = revised.lower()
    prohibited_prefixes = (
        "here is",
        "here's",
        "revised text:",
        "revision:",
        "explanation:",
        "score:",
    )
    if lowered.startswith(prohibited_prefixes):
        raise OfflineWritingMalformedOutput("Local model returned commentary")
    if _is_single_wrapped_quote(revised):
        revised = revised[1:-1].strip()
    if not revised:
        raise OfflineWritingMalformedOutput("Local model returned empty output")
    _validate_revised_text(revised, original_text=original_text)
    return revised


def _is_single_wrapped_quote(value: str) -> bool:
    return bool(re.match(r"""^(['"]).*\1$""", value, flags=re.DOTALL))


def _validate_revised_text(revised: str, original_text: str | None = None) -> None:
    if not revised.strip():
        raise OfflineWritingMalformedOutput("Local model returned empty output")
    if "\x00" in revised or "\x1b" in revised or CONTROL_CHARACTER_PATTERN.search(revised):
        raise OfflineWritingMalformedOutput("Local model returned control characters")
    try:
        revised.encode("utf-8")
    except UnicodeError as exc:
        raise OfflineWritingMalformedOutput("Local model returned invalid Unicode") from exc
    for character in revised:
        if unicodedata.category(character) == "Cs":
            raise OfflineWritingMalformedOutput("Local model returned invalid Unicode")
    if original_text is not None:
        original_len = max(len(original_text.strip()), 1)
        max_len = max(original_len * 4, original_len + 500)
        if len(revised) > max_len:
            raise OfflineWritingMalformedOutput("Local model output was suspiciously long")
