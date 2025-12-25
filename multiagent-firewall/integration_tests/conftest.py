import os

import pytest

from multiagent_firewall.config import GuardConfig
from multiagent_firewall.orchestrator import GuardOrchestrator


@pytest.fixture(scope="module")
def orchestrator():
    if not os.getenv("LLM_API_KEY"):
        pytest.skip("LLM_API_KEY not set. Skipping integration tests.")

    config = GuardConfig.from_env()
    return GuardOrchestrator(config)
