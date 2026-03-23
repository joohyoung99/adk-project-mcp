from __future__ import annotations

from google.adk.agents.llm_agent import LlmAgent

from app.config.settings import settings
from app.mcp.toolsets import filesystem_toolset, notion_toolset
from app.prompt.instructions import (
    filesystem_search_instruction,
    merge_instruction,
    notion_search_instruction,
    save_to_file_instruction,
    summary_only_instruction,
)
from app.tool.callbacks import tool_callbacks


def make_notion_search_agent() -> LlmAgent:
    return LlmAgent(
        name="NotionSearchAgent",
        model=settings.model,
        instruction=notion_search_instruction,
        tools=[notion_toolset] if notion_toolset else [],
        output_key="notion_result",
        **tool_callbacks(),
    )


def make_filesystem_search_agent() -> LlmAgent:
    return LlmAgent(
        name="FilesystemSearchAgent",
        model=settings.model,
        instruction=filesystem_search_instruction,
        tools=[filesystem_toolset],
        output_key="filesystem_result",
        **tool_callbacks(),
    )


def make_merge_agent() -> LlmAgent:
    return LlmAgent(
        name="MergeAgent",
        model=settings.model,
        instruction=merge_instruction,
        output_key="merged_result",
        **tool_callbacks(),
    )


def make_save_to_file_agent() -> LlmAgent:
    return LlmAgent(
        name="SaveToFileAgent",
        model=settings.model,
        instruction=save_to_file_instruction,
        tools=[filesystem_toolset],
        output_key="save_result",
        **tool_callbacks(),
    )


def make_summary_only_agent() -> LlmAgent:
    return LlmAgent(
        name="SummaryOnlyAgent",
        model=settings.model,
        instruction=summary_only_instruction,
        **tool_callbacks(),
    )
