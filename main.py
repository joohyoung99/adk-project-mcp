from __future__ import annotations

import asyncio
import argparse
import json
import os

from google.adk.runners import Runner
from google.adk.sessions import DatabaseSessionService
from google.genai import types

from agent import create_root_agent
from app.config.settings import settings
from app.services.notion_oauth import NotionOAuthService


APP_NAME = "adk-project-mcp"


async def ensure_session(
    session_service: DatabaseSessionService,
    user_id: str,
    session_id: str,
):
    session = await session_service.get_session(
        app_name=APP_NAME,
        user_id=user_id,
        session_id=session_id,
    )
    if session:
        return session

    return await session_service.create_session(
        app_name=APP_NAME,
        user_id=user_id,
        session_id=session_id,
    )


def _compact(value: object, limit: int = 700) -> str:
    try:
        text = json.dumps(value, ensure_ascii=False, default=str)
    except TypeError:
        text = repr(value)
    if len(text) <= limit:
        return text
    return f"{text[:limit]}...<truncated>"


def print_event_debug(event: object) -> None:
    function_calls = event.get_function_calls()
    for function_call in function_calls:
        print(f"\n[FUNCTION CALL] {function_call.name}")
        print(_compact(function_call.args))

    function_responses = event.get_function_responses()
    for function_response in function_responses:
        print(f"\n[FUNCTION RESPONSE] {function_response.name}")
        print(_compact(function_response.response))


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


def ensure_model_api_key() -> None:
    if not (os.getenv("GOOGLE_API_KEY") or os.getenv("GEMINI_API_KEY")):
        raise ValueError("GOOGLE_API_KEY 또는 GEMINI_API_KEY를 설정해야 합니다.")


def login_notion() -> None:
    oauth_service = NotionOAuthService()
    tokens = oauth_service.login_via_browser()
    print("Notion OAuth 로그인 완료")
    print(f"토큰 저장 위치: {settings.notion_oauth_store_path}")
    print(f"Refresh token 저장됨: {bool(tokens.refresh_token)}")


async def chat() -> None:
    ensure_model_api_key()
    oauth_service = NotionOAuthService()
    notion_tokens = oauth_service.get_valid_access_token()

    session_service = DatabaseSessionService(db_url=settings.postgres_url)
    runner = Runner(
        app_name=APP_NAME,
        agent=create_root_agent(
            notion_headers=notion_tokens.authorization_headers if notion_tokens else None,
        ),
        session_service=session_service,
    )

    session = await ensure_session(
        session_service=session_service,
        user_id=settings.default_user_id,
        session_id=settings.default_session_id,
    )

    print("ADK MCP CLI")
    print(f"Filesystem allowed dirs: {', '.join(settings.filesystem_allowed_dirs)}")
    print(f"Notion MCP URL: {settings.notion_mcp_url}")
    print(f"Notion OAuth connected: {bool(notion_tokens)}")
    if not notion_tokens:
        print("Notion을 쓰려면 먼저 `python3 main.py login-notion` 을 실행하세요.")
    print("종료: exit")

    while True:
        user_input = input("\n> ").strip()
        if not user_input:
            continue
        if user_input.lower() in {"exit", "quit"}:
            break

        content = types.Content(
            role="user",
            parts=[types.Part(text=user_input)],
        )

        final_text = None
        async for event in runner.run_async(
            user_id=settings.default_user_id,
            session_id=session.id,
            new_message=content,
        ):
            print_event_debug(event)
            if event.is_final_response() and event.content and event.content.parts:
                texts = [part.text for part in event.content.parts if getattr(part, "text", None)]
                final_text = "".join(texts).strip()

        print("\n[Response]")
        print(final_text or "(응답 없음)")


if __name__ == "__main__":
    args = parse_args()
    try:
        if args.command == "login-notion":
            login_notion()
        else:
            asyncio.run(chat())
    except ValueError as exc:
        print(exc)
