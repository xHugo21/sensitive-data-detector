import os

import math
import statistics
from datetime import datetime
from pathlib import Path

import pytest

from multiagent_firewall.config import GuardConfig
from multiagent_firewall.orchestrator import GuardOrchestrator


def pytest_configure(config):
    config._integration_metrics = []


def _format_rate(numerator: int, denominator: int) -> str:
    if denominator == 0:
        return "n/a"
    return f"{(numerator / denominator) * 100:.2f}%"


def _format_ms(value: float | None) -> str:
    if value is None:
        return "n/a"
    return f"{value * 1000:.2f} ms"


def _percentile(values: list[float], percentile: float) -> float | None:
    if not values:
        return None
    sorted_values = sorted(values)
    index = math.ceil(len(sorted_values) * percentile) - 1
    index = max(0, min(index, len(sorted_values) - 1))
    return sorted_values[index]


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
    durations = [
        entry["duration_s"] for entry in metrics if entry.get("duration_s") is not None
    ]
    mean_time = statistics.mean(durations) if durations else None
    median_time = statistics.median(durations) if durations else None
    p95_time = _percentile(durations, 0.95)

    # Aggregate source counts
    total_source_counts = {}
    for entry in metrics:
        for source, count in entry.get("source_counts", {}).items():
            total_source_counts[source] = total_source_counts.get(source, 0) + count

    sources_str = ", ".join(f"{k}: {v}" for k, v in sorted(total_source_counts.items()))

    terminalreporter.section("Integration metrics", sep="-")
    terminalreporter.write_line(f"Cases: {total_cases}  Pass: {case_passes}")
    terminalreporter.write_line(f"Fields detected: TP: {tp}  FP: {fp}  FN: {fn}")
    terminalreporter.write_line(f"Precision: {precision}  Recall: {recall}  F1: {f1}")
    terminalreporter.write_line(f"Case pass rate: {case_pass_rate}")
    terminalreporter.write_line(f"Sources: {sources_str}")
    terminalreporter.write_line(
        "Latency (mean/median/p95): "
        f"{_format_ms(mean_time)} / {_format_ms(median_time)} / {_format_ms(p95_time)}"
    )

    # Keep in sync with integration_tests/test_end_to_end_detection.py constants.
    dataset_name = "nvidia/Nemotron-PII"
    dataset_split = "test"
    dataset_text_field = "text"
    dataset_locales = os.getenv("INTEGRATION_DATASET_LOCALES", "us")
    dataset_max_cases = os.getenv("INTEGRATION_DATASET_MAX_CASES", "200")
    dataset_seed = os.getenv("INTEGRATION_DATASET_SEED", "1337")
    llm_provider = os.getenv("LLM_PROVIDER", "unknown")
    llm_model = os.getenv("LLM_MODEL", "unknown")
    force_llm_detector = os.getenv("FORCE_LLM_DETECTOR", "false")
    ner_enabled = os.getenv("NER_ENABLED", "false")
    ner_min_score = os.getenv("NER_MIN_SCORE", "0.5")

    summary_lines = [
        "Integration metrics",
        f"Cases: {total_cases}  Pass: {case_passes}",
        f"Fields detected: TP: {tp}  FP: {fp}  FN: {fn}",
        f"Precision: {precision}  Recall: {recall}  F1: {f1}",
        f"Case pass rate: {case_pass_rate}",
        f"Sources: {sources_str}",
        "Latency (mean/median/p95): "
        f"{_format_ms(mean_time)} / {_format_ms(median_time)} / {_format_ms(p95_time)}",
        "",
        "Run parameters",
        f"LLM_PROVIDER: {llm_provider}",
        f"LLM_MODEL: {llm_model}",
        f"FORCE_LLM_DETECTOR: {force_llm_detector}",
        f"NER_ENABLED: {ner_enabled}",
        f"NER_MIN_SCORE: {ner_min_score}",
        f"DATASET: {dataset_name} ({dataset_split}/{dataset_text_field})",
        f"INTEGRATION_DATASET_LOCALES: {dataset_locales}",
        f"INTEGRATION_DATASET_MAX_CASES: {dataset_max_cases}",
        f"INTEGRATION_DATASET_SEED: {dataset_seed}",
        f"EXIT_STATUS: {exitstatus}",
    ]

    logs_dir = Path(__file__).parent / "run_logs"
    logs_dir.mkdir(exist_ok=True)
    timestamp = datetime.now().strftime("%d%m%Y-%H%M%S")
    log_path = logs_dir / f"integration-summary-{timestamp}.txt"
    log_path.write_text("\n".join(summary_lines) + "\n")


@pytest.fixture(scope="module")
def orchestrator():
    if not os.getenv("LLM_API_KEY"):
        pytest.skip("LLM_API_KEY not set. Skipping integration tests.")

    config = GuardConfig.from_env()
    return GuardOrchestrator(config)
