# ADK Notion MCP CLI

Google ADK로 만든 CLI 챗봇입니다.

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

예시 질문
  - 노션에 강화학습 세미나 페이지 내용 요약해서 로컬로 저장해줘
  - 노션에서 강화학습 세미나 관련 내용 찾아서 요약해줘
  - 노션 내용과 로컬 파일을 같이 비교해서 통합 정리해줘
  - 노션 강화학습 내용 정리해서 markdown 파일로 저장해줘

## 에이전트 구조

```text
root_agent = SupervisorAgent
|
+-- run_parallel_pipeline (SequentialAgent)
|   |
|   +-- ParallelCollectAgent (ParallelAgent)
|   |   |
|   |   +-- NotionSearchAgent
|   |   +-- FilesystemSearchAgent
|   |
|   +-- MergeAgent
|   +-- SummaryOnlyAgent
|
+-- run_sequential_pipeline (SequentialAgent)
    |
    +-- NotionSearchAgent
    +-- MergeAgent
    +-- SaveToFileAgent
```

라우팅 기준:

- `run_parallel_pipeline`: Notion과 로컬 파일을 함께 조사, 비교, 통합할 때
- `run_sequential_pipeline`: Notion 내용을 읽어 정리한 뒤 markdown 파일로 저장할 때



## 주요 파일

- [main.py](/home/pachu/works/adk-project-mcp/main.py): CLI 실행과 이벤트 출력
- [agent.py](/home/pachu/works/adk-project-mcp/agent.py): root/filesystem/notion agent 구성
- [app/config/settings.py](/home/pachu/works/adk-project-mcp/app/config/settings.py): 환경 변수 로딩
- [app/services/notion_oauth.py](/home/pachu/works/adk-project-mcp/app/services/notion_oauth.py): OAuth 로그인과 토큰 refresh
- [app/config/mcp_servers.example.json](/home/pachu/works/adk-project-mcp/app/config/mcp_servers.example.json): Notion MCP 설정 예시
