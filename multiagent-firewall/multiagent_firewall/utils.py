from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from .types import GuardState


def debug_invoke(app: Any, inputs: "GuardState") -> "GuardState":
    """Prints the current state on each node hop"""
    final_state: dict[str, Any] = {}
    print("\n--- Starting Execution ---\n")

    for chunk in app.stream(inputs, stream_mode="updates"):
        for node, update in chunk.items():
            print(f"Node '{node}' finished.")
            print(f"   Update: {update}\n")
            final_state = update

    return final_state  # type: ignore[return-value]
