from __future__ import annotations

import json
import os

from google.adk.runners import Runner
from google.adk.sessions import DatabaseSessionService
from google.genai import types

from agent import root_agent
from app.config.settings import settings
from app.services.notion_oauth import NotionOAuthService


def ensure_model_api_key() -> None:
    if not (settings.model):
        raise ValueError("GOOGLE_API_KEY 또는 GEMINI_API_KEY를 설정해야 합니다.")


async def ensure_session(
    session_service: DatabaseSessionService,
    user_id: str,
    session_id: str,
):
    session = await session_service.get_session(
        app_name=settings.app_name,
        user_id=user_id,
        session_id=session_id,
    )
    if session:
        return session

    return await session_service.create_session(
        app_name=settings.app_name,
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
    for function_call in event.get_function_calls():
        print(f"\n[FUNCTION CALL] {function_call.name}")
        print(_compact(function_call.args))

    for function_response in event.get_function_responses():
        print(f"\n[FUNCTION RESPONSE] {function_response.name}")
        print(_compact(function_response.response))


def print_banner(*, notion_connected: bool) -> None:
    print("ADK MCP CLI")
    print(f"Filesystem allowed dirs: {', '.join(settings.filesystem_allowed_dirs)}")
    print(f"Notion MCP URL: {settings.notion_mcp_url}")
    print(f"Notion OAuth connected: {notion_connected}")
    if not notion_connected:
        print("Notion을 쓰려면 먼저 `python3 main.py login-notion` 을 실행하세요.")
    print("종료: exit")


async def run_chat_cli() -> None:
    ensure_model_api_key()
    oauth_service = NotionOAuthService()
    notion_tokens = oauth_service.get_valid_access_token()

    session_service = DatabaseSessionService(db_url=settings.postgres_url)
    runner = Runner(
        app_name=settings.app_name,
        agent=root_agent,
        session_service=session_service,
    )
    session = await ensure_session(
        session_service=session_service,
        user_id=settings.default_user_id,
        session_id=settings.default_session_id,
    )

    print_banner(notion_connected=bool(notion_tokens))

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
