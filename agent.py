from __future__ import annotations

from google.adk.agents import Agent
from google.adk.tools import AgentTool
from google.adk.tools.mcp_tool import (
    MCPToolset,
    StdioConnectionParams,
    StreamableHTTPConnectionParams,
)
from mcp import StdioServerParameters

from app.config.settings import settings


def _filesystem_toolset() -> MCPToolset:
    return MCPToolset(
        connection_params=StdioConnectionParams(
            server_params=StdioServerParameters(
                command="npx",
                args=[
                    "-y",
                    "@modelcontextprotocol/server-filesystem",
                    *settings.filesystem_allowed_dirs,
                ],
            ),
            timeout=10.0,
        ),
        tool_filter=[
            "read_file",
            "read_multiple_files",
            "list_directory",
            "directory_tree",
            "search_files",
            "get_file_info",
            "list_allowed_directories",
        ],
    )


def _notion_toolset(headers: dict[str, str] | None) -> MCPToolset:
    return MCPToolset(
        connection_params=StreamableHTTPConnectionParams(
            url=settings.notion_mcp_url,
            headers=headers,
            timeout=10.0,
        )
    )


def create_root_agent(*, notion_headers: dict[str, str] | None = None) -> Agent:
    filesystem_agent = Agent(
        name="filesystem_agent",
        model=settings.model,
        description="Filesystem MCP 전용 에이전트",
        instruction=f"""
사용자의 로컬 파일과 폴더를 탐색하는 전용 에이전트다.
허용된 디렉터리만 접근한다: {", ".join(settings.filesystem_allowed_dirs)}

규칙:
- 필요한 파일만 읽는다.
- 읽은 결과는 짧고 구조적으로 요약한다.
- 파일 수정은 하지 않는다.
""".strip(),
        tools=[_filesystem_toolset()],
    )

    notion_available = bool(notion_headers)
    notion_instruction = """
사용자의 Notion 검색, 페이지 조회, 문서 정리 작업 전용 에이전트다.

규칙:
- 필요한 페이지와 데이터베이스만 조회한다.
- 결과는 짧고 구조적으로 요약한다.
- 사용자가 원하면 Notion용 초안 문서 구조로 정리한다.
""".strip()
    if not notion_available:
        notion_instruction += "\n- 현재 OAuth 로그인이 없어 Notion MCP를 호출할 수 없다."

    notion_agent = Agent(
        name="notion_agent",
        model=settings.model,
        description="Notion MCP 전용 에이전트",
        instruction=notion_instruction,
        tools=[_notion_toolset(notion_headers)] if notion_available else [],
    )

    return Agent(
        name="workspace_copilot",
        model=settings.model,
        description="Filesystem MCP와 Notion MCP를 함께 쓰는 루트 에이전트",
        instruction="""
당신은 업무 보조용 루트 에이전트다.

반드시 역할을 나눠서 처리한다.
- 파일/폴더 탐색, 로그/회의록 읽기: filesystem_agent 사용
- Notion 문서 검색, 페이지 조회, 정리: notion_agent 사용

작업 원칙:
- 파일 내용을 먼저 읽고 핵심 요약을 만든다.
- 이후 Notion 문서 조회 결과를 정리하거나 문서 초안을 작성한다.
- 사용자가 이미지/스크린샷을 언급하면 장애 공유 메시지 형식으로 정리한다.
- 사용자가 더 짧게 줄여달라고 하면 직전 맥락을 유지해서 축약한다.
""".strip(),
        tools=[
            AgentTool(agent=filesystem_agent),
            AgentTool(agent=notion_agent),
        ],
    )
