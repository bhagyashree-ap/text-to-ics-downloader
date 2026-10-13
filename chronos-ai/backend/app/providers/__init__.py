"""Provider factory (spec section 6)."""
from __future__ import annotations

from ..core.config import settings
from .base import ProviderResult, QwenProvider
from .mock_provider import MockQwenProvider


def get_provider() -> QwenProvider:
    if settings.mock_mode:
        return MockQwenProvider()
    if settings.QWEN_PROVIDER == "openai_compatible":
        from .qwen_openai import QwenOpenAIProvider

        return QwenOpenAIProvider()
    # Unknown provider -> safe default to mock, clearly logged by caller.
    return MockQwenProvider()


__all__ = ["get_provider", "QwenProvider", "ProviderResult", "MockQwenProvider"]
