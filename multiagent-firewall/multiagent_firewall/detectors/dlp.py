from __future__ import annotations

from typing import Dict


def default_regex_patterns() -> Dict[str, str]:
    return {
        "EMAIL": r"\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}\b",
        "PHONE_NUMBER": r"\b\+?\d[\d\s\-\(\)]{7,}\d\b",
    }


__all__ = ["default_regex_patterns"]
