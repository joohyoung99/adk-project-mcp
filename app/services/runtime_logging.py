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


def _looks_like_write_tool(tool_name: str) -> bool:
    normalized = tool_name.lower()
    keywords = ("create", "update", "append", "insert", "write")
    return any(keyword in normalized for keyword in keywords)


def _has_resource_identity(response: Any) -> bool:
    if isinstance(response, dict):
        if response.get("id") or response.get("url"):
            return True
        return any(_has_resource_identity(value) for value in response.values())
    if isinstance(response, list):
        return any(_has_resource_identity(item) for item in response)
    return False


def before_tool_callback(tool: BaseTool, args: dict[str, Any], tool_context: ToolContext) -> None:
    print(f"[TOOL CALL] agent={tool_context.agent_name} tool={tool.name}")
    print(f"[TOOL ARGS] {_compact(args)}")
    return None


def after_tool_callback(
    tool: BaseTool,
    args: dict[str, Any],
    tool_context: ToolContext,
    tool_response: dict[str, Any],
) -> None:
    print(f"[TOOL RESPONSE] agent={tool_context.agent_name} tool={tool.name}")
    print(_compact(tool_response))
    if _looks_like_write_tool(tool.name) and not _has_resource_identity(tool_response):
        print(
            "[TOOL VERIFY] 쓰기 계열 응답이지만 생성/수정된 리소스의 id 또는 url이 없어 "
            "성공으로 단정하지 않습니다."
        )
    return None


def on_tool_error_callback(
    tool: BaseTool,
    args: dict[str, Any],
    tool_context: ToolContext,
    error: Exception,
) -> None:
    print(
        f"[TOOL ERROR] agent={tool_context.agent_name} tool={tool.name} "
        f"error={type(error).__name__}: {error}"
    )
    return None
