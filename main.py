from __future__ import annotations

import argparse
import asyncio

from app.config.settings import settings
from app.services.chat_cli import run_chat_cli
from app.services.notion_oauth import NotionOAuthService


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="ADK MCP CLI")
    parser.add_argument(
        "command",
        nargs="?",
        default="chat",
        choices=["chat", "login-notion"],
        help="실행할 명령",
    )
    return parser.parse_args()


def login_notion() -> None:
    oauth_service = NotionOAuthService()
    tokens = oauth_service.login_via_browser()
    print("Notion OAuth 로그인 완료")
    print(f"토큰 저장 위치: {settings.notion_oauth_store_path}")
    print(f"Refresh token 저장됨: {bool(tokens.refresh_token)}")


def main() -> None:
    args = parse_args()
    if args.command == "login-notion":
        login_notion()
        return
    asyncio.run(run_chat_cli())


if __name__ == "__main__":
    try:
        main()
    except ValueError as exc:
        print(exc)
