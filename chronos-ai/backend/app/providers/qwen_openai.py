"""Qwen via an OpenAI-compatible server (e.g. vLLM) — spec section 6.

Uses guided JSON when the server supports it (vLLM `guided_json`). Handles timeouts,
bounded retries, and malformed responses. Credentials stay on the backend.
"""
from __future__ import annotations

import json
import time

from ..core.config import settings
from ..core.logging import log
from .base import EXTRACTION_JSON_SCHEMA, SYSTEM_PROMPT, ProviderResult, QwenProvider


class QwenOpenAIProvider(QwenProvider):
    def __init__(self) -> None:
        if not settings.QWEN_API_BASE_URL:
            raise RuntimeError("QWEN_API_BASE_URL is required for the openai_compatible provider.")

    def extract(self, text: str, today_iso: str, default_tz: str) -> ProviderResult:
        from openai import OpenAI

        client = OpenAI(
            base_url=settings.QWEN_API_BASE_URL,
            api_key=settings.QWEN_API_KEY or "EMPTY",
            timeout=settings.QWEN_TIMEOUT_SECONDS,
        )
        user_prompt = (
            f"Today is {today_iso}. Default timezone: {default_tz}.\n\n"
            f"Extract every event from the following text:\n\n{text}\n\n/no_think"
        )

        last_err: Exception | None = None
        for attempt in range(settings.QWEN_MAX_RETRIES + 1):
            try:
                resp = client.chat.completions.create(
                    model=settings.QWEN_MODEL,
                    messages=[
                        {"role": "system", "content": SYSTEM_PROMPT},
                        {"role": "user", "content": user_prompt},
                    ],
                    temperature=0,
                    extra_body={
                        "guided_json": EXTRACTION_JSON_SCHEMA,
                        "chat_template_kwargs": {"enable_thinking": False},
                    },
                )
                content = resp.choices[0].message.content or "{}"
                data = json.loads(content)
                events = data.get("events", [])
                if not isinstance(events, list):
                    raise ValueError("Model returned non-list 'events'.")
                return ProviderResult(events=events, used_mock=False, model=settings.QWEN_MODEL)
            except Exception as exc:  # noqa: BLE001
                last_err = exc
                log.warning("Qwen attempt %d failed: %s", attempt + 1, type(exc).__name__)
                if attempt < settings.QWEN_MAX_RETRIES:
                    time.sleep(min(2 ** attempt, 4))

        # Never fabricate success on failure (spec section 6 & 20).
        raise RuntimeError(f"Qwen extraction failed after retries: {last_err}")
