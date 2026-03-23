from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path

from dotenv import load_dotenv


BASE_DIR = Path(__file__).resolve().parents[2]
load_dotenv(BASE_DIR / ".env")


def _postgres_url() -> str:
    direct_url = (os.getenv("DATABASE_URL") or os.getenv("POSTGRES_URL") or "").strip()
    if direct_url:
        return direct_url

    raise ValueError("DATABASE_URL 또는 POSTGRES_URL을 설정해야 합니다.")


def _filesystem_allowed_dirs() -> list[str]:
    raw = (os.getenv("FILESYSTEM_ALLOWED_DIRS") or os.getenv("FILESYSTEM_ALLOWED_DIR") or "").strip()
    if raw:
        return [item.strip() for item in raw.split(",") if item.strip()]
    return [str(BASE_DIR / "samples")]


@dataclass(frozen=True, slots=True)
class Settings:
    app_name: str = "adk-project-mcp과제1"
    default_session_id: str = "session-4"
    default_user_id: str = "jhpark"
    samples_dir: Path = BASE_DIR / "samples"
    notion_oauth_store_path: Path = BASE_DIR / ".notion-oauth.json"
    model: str = os.getenv("MODEL_GEMINI_2_5_FLASH", "gemini-2.5-flash")
    filesystem_allowed_dirs: list[str] = None  # type: ignore[assignment]
    notion_mcp_url: str = os.getenv("NOTION_MCP_URL", "https://mcp.notion.com/mcp")
    notion_client_name: str = os.getenv("NOTION_CLIENT_NAME", "ADK Project MCP CLI")
    notion_redirect_host: str = os.getenv("NOTION_REDIRECT_HOST", "127.0.0.1")
    notion_redirect_port: int = int(os.getenv("NOTION_REDIRECT_PORT", "8787"))

    def __post_init__(self) -> None:
        object.__setattr__(self, "filesystem_allowed_dirs", _filesystem_allowed_dirs())

    @property
    def postgres_url(self) -> str:
        return _postgres_url()

    @property
    def filesystem_allowed_dir(self) -> str:
        return self.filesystem_allowed_dirs[0]

    @property
    def notion_redirect_uri(self) -> str:
        return f"http://{self.notion_redirect_host}:{self.notion_redirect_port}/callback"


settings = Settings()
