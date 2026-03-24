from __future__ import annotations

from mcp import StdioServerParameters

from google.adk.tools.mcp_tool import MCPToolset
from google.adk.tools.mcp_tool.mcp_session_manager import (
    StdioConnectionParams,
    StreamableHTTPConnectionParams,
)

from app.config.settings import settings
from app.services.notion_oauth import NotionOAuthService


class NotionMCPToolset(MCPToolset):
    async def get_tools(self, readonly_context=None):  # type: ignore[override]
        tokens = NotionOAuthService().get_valid_access_token()
        if not tokens:
            return []

        self._mcp_session_manager._connection_params.headers = {
            "Authorization": f"Bearer {tokens.access_token}",
        }
        return await super().get_tools(readonly_context)


filesystem_toolset = MCPToolset(
    connection_params=StdioConnectionParams(
        server_params=StdioServerParameters(
            command="npx",
            args=[
                "-y",
                "@modelcontextprotocol/server-filesystem",
                settings.filesystem_allowed_dir,
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
        "write_file",
        "edit_file",
        "create_directory",
        "list_allowed_directories",
    ],
)

notion_toolset = NotionMCPToolset(
    connection_params=StreamableHTTPConnectionParams(
        url=settings.notion_mcp_url,
        headers={},
        timeout=10.0,
    ),
)
