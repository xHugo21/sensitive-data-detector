from __future__ import annotations

from typing import Any

from core.config import DEBUG_MODE


def debug_log(*args: Any, **kwargs: Any) -> None:
    """Prints the message only when DEBUG_MODE is enabled."""
    if not DEBUG_MODE:
        return

    kwargs.setdefault("flush", True)
    print(*args, **kwargs)
