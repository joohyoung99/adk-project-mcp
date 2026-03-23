from __future__ import annotations

from google.adk.agents.parallel_agent import ParallelAgent
from google.adk.agents.sequential_agent import SequentialAgent

from app.agent.sub_agents import (
    make_filesystem_search_agent,
    make_merge_agent,
    make_notion_search_agent,
    make_save_to_file_agent,
    make_summary_only_agent,
)


parallel_collect_agent = ParallelAgent(
    name="ParallelCollectAgent",
    sub_agents=[make_notion_search_agent(), make_filesystem_search_agent()],
    description="Notion과 Filesystem을 병렬로 검색한다.",
)

run_parallel_pipeline = SequentialAgent(
    name="run_parallel_pipeline",
    sub_agents=[
        parallel_collect_agent,
        make_merge_agent(),
        make_summary_only_agent(),
    ],
    description="병렬 수집 후 머지해서 사용자에게 요약 응답한다.",
)

run_sequential_pipeline = SequentialAgent(
    name="run_sequential_pipeline",
    sub_agents=[
        make_notion_search_agent(),
        make_merge_agent(),
        make_save_to_file_agent(),
    ],
    description="Notion 내용을 읽고 정리해서 파일로 저장한다.",
)
