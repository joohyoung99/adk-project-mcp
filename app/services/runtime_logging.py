from __future__ import annotations

import json
from typing import Any

from google.adk.tools.base_tool import BaseTool
from google.adk.tools.tool_context import ToolContext


def _compact(value: Any, limit: int = 700) -> str:
    try:
        text = json.dumps(value, ensure_ascii=False, default=str)
    except TypeError:
        text = repr(value)
    if len(text) <= limit:
        return text
    return f"{text[:limit]}...<truncated>"

def before_tool_callback(tool: BaseTool, args: dict[str, Any], tool_context: ToolContext) -> None:
    print(f"[TOOL CALL] agent={tool_context.agent_name} tool={tool.name}")
    print(f"[TOOL ARGS] {_compact(args)}")
    return None
