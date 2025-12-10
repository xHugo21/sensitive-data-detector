from __future__ import annotations

import importlib

import os


def test_use_anonymizer_false_for_ollama(monkeypatch):
    monkeypatch.setenv("ANONYMIZE_FOR_REMOTE_LLM", "true")
    monkeypatch.setenv("LLM_PROVIDER", "ollama")
    routers = importlib.reload(
        importlib.import_module("multiagent_firewall.routers")
    )
    assert routers._use_anonymizer() is False


def test_use_anonymizer_true_for_remote(monkeypatch):
    monkeypatch.setenv("ANONYMIZE_FOR_REMOTE_LLM", "true")
    monkeypatch.setenv("LLM_PROVIDER", "openai")
    routers = importlib.reload(
        importlib.import_module("multiagent_firewall.routers")
    )
    assert routers._use_anonymizer() is True
