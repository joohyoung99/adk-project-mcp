# ADK Notion MCP CLI

Google ADK로 만든 CLI 챗봇이다.

- `filesystem MCP`
- `Notion MCP (Streamable HTTP + OAuth)`
- `PostgreSQL session`

## 실행

루트 `.env`에 아래 값을 둔다.

```bash
DATABASE_URL=postgresql+asyncpg://user:password@host:5432/database
GOOGLE_API_KEY=...
FILESYSTEM_ALLOWED_DIRS=/absolute/path/one,/absolute/path/two
MODEL_GEMINI_2_5_FLASH=gemini-2.5-flash
NOTION_MCP_URL=https://mcp.notion.com/mcp
NOTION_CLIENT_NAME="ADK Project MCP CLI"
NOTION_REDIRECT_HOST=127.0.0.1
NOTION_REDIRECT_PORT=8787
```

Notion OAuth 로그인:

```bash
python3 main.py login-notion
```

채팅 실행:

```bash
python3 main.py
```

## 주요 파일

- [main.py](/home/pachu/works/adk-project-mcp/main.py): CLI 실행과 이벤트 출력
- [agent.py](/home/pachu/works/adk-project-mcp/agent.py): root/filesystem/notion agent 구성
- [app/config/settings.py](/home/pachu/works/adk-project-mcp/app/config/settings.py): 환경 변수 로딩
- [app/services/notion_oauth.py](/home/pachu/works/adk-project-mcp/app/services/notion_oauth.py): OAuth 로그인과 토큰 refresh
- [app/config/mcp_servers.example.json](/home/pachu/works/adk-project-mcp/app/config/mcp_servers.example.json): Notion MCP 설정 예시
