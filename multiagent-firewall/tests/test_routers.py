from __future__ import annotations

from multiagent_firewall import routers


def test_use_anonymizer_false_for_ollama():
    state = {"llm_provider": "ollama", "anonymize_for_remote_llm": True}
    assert routers._use_anonymizer(state) is False


def test_use_anonymizer_true_for_remote():
    state = {"llm_provider": "openai", "anonymize_for_remote_llm": True}
    assert routers._use_anonymizer(state) is True
