from __future__ import annotations

from unittest.mock import MagicMock

from multiagent_firewall.orchestrator import GuardOrchestrator


def test_stream_updates_passes_stream_mode(guard_config):
    orchestrator = GuardOrchestrator(guard_config)
    fake_graph = MagicMock()
    fake_graph.stream.return_value = iter(())
    orchestrator._graph = fake_graph

    initial_state, updates = orchestrator.stream_updates(
        text="hello",
        stream_mode=["tasks", "updates"],
    )

    fake_graph.stream.assert_called_once_with(
        initial_state,
        stream_mode=["tasks", "updates"],
    )
    assert initial_state["raw_text"] == "hello"
    assert updates is not None
