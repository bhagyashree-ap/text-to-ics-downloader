"""Runtime configuration, read from environment (.env supported)."""
from __future__ import annotations

import os

try:
    from dotenv import load_dotenv

    load_dotenv()
except Exception:  # python-dotenv optional; env vars still work without it
    pass


class Settings:
    # vLLM / OpenAI-compatible endpoint. Leave LLM_BASE_URL empty to force the
    # rules-based fallback (the app stays fully functional).
    LLM_BASE_URL: str = os.getenv("LLM_BASE_URL", "").strip()
    LLM_API_KEY: str = os.getenv("LLM_API_KEY", "EMPTY").strip()
    # For vLLM, set this to the served model name OR a registered LoRA adapter name.
    LLM_MODEL: str = os.getenv("LLM_MODEL", "Qwen/Qwen3-14B").strip()

    # How long to wait on the model before giving up and using the fallback.
    LLM_TIMEOUT_SECONDS: float = float(os.getenv("LLM_TIMEOUT_SECONDS", "30"))

    # Default event duration (minutes) when the text gives a start but no end.
    DEFAULT_DURATION_MINUTES: int = int(os.getenv("DEFAULT_DURATION_MINUTES", "60"))

    # CORS origin for the frontend.
    FRONTEND_ORIGIN: str = os.getenv("FRONTEND_ORIGIN", "http://localhost:3000").strip()

    @property
    def llm_enabled(self) -> bool:
        return bool(self.LLM_BASE_URL)


settings = Settings()
