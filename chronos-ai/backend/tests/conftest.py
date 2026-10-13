"""Shared pytest fixtures. The suite runs in mock mode with NO Qwen credentials."""
from __future__ import annotations

import os

os.environ.setdefault("QWEN_PROVIDER", "mock")
os.environ.setdefault("DEFAULT_TIMEZONE", "America/New_York")

import pytest  # noqa: E402


@pytest.fixture
def default_tz() -> str:
    return "America/New_York"
