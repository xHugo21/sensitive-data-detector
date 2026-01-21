from typing import TYPE_CHECKING, Any
from .types import GuardState

if TYPE_CHECKING:
    from .types import GuardState


async def debug_ainvoke(app: Any, inputs: "GuardState") -> "GuardState":
    """Prints modified state fields on each node hop (async)"""
    final_state: dict[str, Any] = {}
    previous_state: dict[str, Any] = dict(inputs)
    print("\n--- Starting Execution (Async) ---\n")

    print(f"Initial state: {inputs}\n")

    async for chunk in app.astream(inputs, stream_mode="updates"):
        for node, update in chunk.items():
            print(f"Node '{node}' finished.")

            modified_fields = {}
            for key, value in update.items():
                if key not in previous_state or previous_state[key] != value:
                    modified_fields[key] = value

            if modified_fields:
                print(f"   Modified fields: {modified_fields}\n")
            else:
                print(f"   No fields modified\n")

            # Update previous state for next comparison
            previous_state.update(update)
            final_state = update

    return final_state  # type: ignore[return-value]


def append_error(state: GuardState, message: str) -> None:
    """Add error to state."""
    if "errors" not in state:
        state["errors"] = []
    state["errors"].append(message)


def append_warning(state: GuardState, message: str) -> None:
    """Add warning to state."""
    if "warnings" not in state:
        state["warnings"] = []
    state["warnings"].append(message)
