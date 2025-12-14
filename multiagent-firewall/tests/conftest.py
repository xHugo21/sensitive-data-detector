from __future__ import annotations

import pytest

from multiagent_firewall.config import (
    GuardConfig,
    LLMConfig,
    OCRConfig,
)


@pytest.fixture
def guard_config() -> GuardConfig:
    return GuardConfig(
        llm=LLMConfig(
            provider="openai",
            model="gpt-4o-mini",
            client_params={"api_key": "test-api-key"},
        ),
        llm_ocr=None,
        ocr=OCRConfig(),
        debug=False,
    )
