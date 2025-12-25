import os

import pytest

from multiagent_firewall.config import GuardConfig
from multiagent_firewall.orchestrator import GuardOrchestrator


def pytest_configure(config):
    config._integration_metrics = []


def _format_rate(numerator: int, denominator: int) -> str:
    if denominator == 0:
        return "n/a"
    return f"{(numerator / denominator) * 100:.2f}%"


def pytest_terminal_summary(terminalreporter, exitstatus, config):
    metrics = getattr(config, "_integration_metrics", None)
    if not metrics:
        return

    total_cases = len(metrics)
    case_passes = sum(1 for entry in metrics if entry["case_pass"])
    tp = sum(entry["tp"] for entry in metrics)
    fp = sum(entry["fp"] for entry in metrics)
    fn = sum(entry["fn"] for entry in metrics)

    precision = _format_rate(tp, tp + fp)
    recall = _format_rate(tp, tp + fn)
    f1 = _format_rate(2 * tp, (2 * tp) + fp + fn)
    case_pass_rate = _format_rate(case_passes, total_cases)

    terminalreporter.section("Integration metrics", sep="-")
    terminalreporter.write_line(f"Cases: {total_cases}  Pass: {case_passes}")
    terminalreporter.write_line(f"TP: {tp}  FP: {fp}  FN: {fn}")
    terminalreporter.write_line(
        f"Precision: {precision}  Recall: {recall}  F1: {f1}"
    )
    terminalreporter.write_line(f"Case pass rate: {case_pass_rate}")


@pytest.fixture(scope="module")
def orchestrator():
    if not os.getenv("LLM_API_KEY"):
        pytest.skip("LLM_API_KEY not set. Skipping integration tests.")

    config = GuardConfig.from_env()
    return GuardOrchestrator(config)
