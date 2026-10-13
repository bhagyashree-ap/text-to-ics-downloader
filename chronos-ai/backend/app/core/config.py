"""Environment-based configuration (spec sections 6 & 23)."""
from __future__ import annotations

import os

try:
    from dotenv import load_dotenv

    load_dotenv()
except Exception:
    pass


def _get(name: str, default: str = "") -> str:
    return os.getenv(name, default).strip()


def _get_int(name: str, default: int) -> int:
    try:
        return int(os.getenv(name, str(default)))
    except (TypeError, ValueError):
        return default


class Settings:
    APP_ENV: str = _get("APP_ENV", "development")
    APP_HOST: str = _get("APP_HOST", "0.0.0.0")
    APP_PORT: int = _get_int("APP_PORT", 8000)
    LOG_LEVEL: str = _get("LOG_LEVEL", "INFO")

    # Qwen provider adapter config.
    QWEN_PROVIDER: str = _get("QWEN_PROVIDER", "mock")  # "mock" | "openai_compatible"
    QWEN_MODEL: str = _get("QWEN_MODEL", "Qwen/Qwen2.5-14B-Instruct")
    QWEN_API_BASE_URL: str = _get("QWEN_API_BASE_URL", "")
    QWEN_API_KEY: str = _get("QWEN_API_KEY", "")
    QWEN_TIMEOUT_SECONDS: float = float(_get("QWEN_TIMEOUT_SECONDS", "30") or "30")
    QWEN_MAX_RETRIES: int = _get_int("QWEN_MAX_RETRIES", 2)
    QWEN_MAX_INPUT_CHARACTERS: int = _get_int("QWEN_MAX_INPUT_CHARACTERS", 20000)

    # Pipeline behavior
    DEFAULT_TIMEZONE: str = _get("DEFAULT_TIMEZONE", "UTC")
    DEFAULT_EVENT_DURATION_MINUTES: int = _get_int("DEFAULT_EVENT_DURATION_MINUTES", 60)

    # gRPC service targets (in-process by default for the MVP single container).
    GRPC_INPUT_PROCESSING_TARGET: str = _get("GRPC_INPUT_PROCESSING_TARGET", "localhost:50051")
    GRPC_AI_EXTRACTION_TARGET: str = _get("GRPC_AI_EXTRACTION_TARGET", "localhost:50052")
    GRPC_DATE_NORMALIZATION_TARGET: str = _get("GRPC_DATE_NORMALIZATION_TARGET", "localhost:50053")
    GRPC_EVENT_VALIDATION_TARGET: str = _get("GRPC_EVENT_VALIDATION_TARGET", "localhost:50054")
    GRPC_CLARIFICATION_TARGET: str = _get("GRPC_CLARIFICATION_TARGET", "localhost:50055")
    GRPC_REMINDER_TARGET: str = _get("GRPC_REMINDER_TARGET", "localhost:50056")
    GRPC_ICS_GENERATION_TARGET: str = _get("GRPC_ICS_GENERATION_TARGET", "localhost:50057")
    GRPC_ARTIFACT_TARGET: str = _get("GRPC_ARTIFACT_TARGET", "localhost:50058")
    GRPC_PORT: int = _get_int("GRPC_PORT", 50051)
    GRPC_DEADLINE_SECONDS: float = float(_get("GRPC_DEADLINE_SECONDS", "20") or "20")

    # Artifacts
    ARTIFACT_STORAGE_PATH: str = _get("ARTIFACT_STORAGE_PATH", "/tmp/chronos-artifacts")
    ARTIFACT_TTL_SECONDS: int = _get_int("ARTIFACT_TTL_SECONDS", 3600)

    # Limits
    MAX_TEXT_CHARACTERS: int = _get_int("MAX_TEXT_CHARACTERS", 50000)
    MAX_UPLOAD_BYTES: int = _get_int("MAX_UPLOAD_BYTES", 10 * 1024 * 1024)

    @property
    def mock_mode(self) -> bool:
        return self.QWEN_PROVIDER == "mock" or not self.QWEN_API_BASE_URL


settings = Settings()
