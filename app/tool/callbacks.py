from __future__ import annotations

from app.services.runtime_logging import before_tool_callback


def tool_callbacks() -> dict[str, object]:
    return {
        "before_tool_callback": before_tool_callback,
    }
