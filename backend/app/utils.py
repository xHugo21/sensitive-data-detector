from __future__ import annotations

from typing import Any

from .config import DEBUG_MODE


def debug_log(*args: Any, **kwargs: Any) -> None:
    """Prints debug message based on DEBUG_MODE environment variable."""
    if not DEBUG_MODE:
        return

    kwargs.setdefault("flush", True)
    print(*args, **kwargs)
