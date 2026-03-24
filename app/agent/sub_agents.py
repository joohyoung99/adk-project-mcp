from __future__ import annotations

from google import genai
from google.adk.agents.llm_agent import LlmAgent
from google.adk.tools import FunctionTool
from google.genai import types

from app.config.settings import settings
from app.mcp.toolsets import filesystem_toolset, notion_toolset
from app.prompt.instructions import (
    filesystem_search_instruction,
    merge_instruction,
    notion_search_instruction,
    notion_only_merge_instruction,
    save_to_file_instruction,
    summary_only_instruction,
    ragengine_search_instruction,
)
from app.tool.callbacks import tool_callbacks




def search_vertex_rag(query: str) -> str:

    project = settings.google_cloud_project
    location = settings.google_cloud_location
    rag_corpus = settings.vertex_rag_corpus
    
    if not project:
        return "Vertex RAG 검색 실패: GOOGLE_CLOUD_PROJECT 환경 변수가 필요합니다."
    if not rag_corpus:
        return "Vertex RAG 검색 실패: VERTEX_RAG_CORPUS 환경 변수가 필요합니다."

    client = genai.Client(
        vertexai=True,
        project=project,
        location=location,
    )

    response = client.models.generate_content(
        model=settings.model,
        contents=[
            types.Content(
                role="user",
                parts=[types.Part.from_text(text=query)],
            ),
        ],
        config=types.GenerateContentConfig(
            temperature=1,
            tools=[
                types.Tool(
                    retrieval=types.Retrieval(
                        vertex_rag_store=types.VertexRagStore(
                            rag_resources=[
                                types.VertexRagStoreRagResource(
                                    rag_corpus=rag_corpus,
                                )
                            ],
                            rag_retrieval_config=types.RagRetrievalConfig(
                                filter=types.RagRetrievalConfigFilter(
                                    vector_distance_threshold=0.3,
                                ),
                                ranking=types.RagRetrievalConfigRanking(
                                    rank_service=types.RagRetrievalConfigRankingRankService(
                                        model_name="semantic-ranker-512",
                                    )
                                ),
                                top_k=5,
                            ),
                        )
                    )
                )
            ],
        ),
    )
    return response.text or "Vertex RAG 검색 결과가 비어 있습니다."



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


def make_notion_only_merge_agent() -> LlmAgent:
    return LlmAgent(
        name="NotionOnlyMergeAgent",
        model=settings.model,
        instruction=notion_only_merge_instruction,
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


def make_ragengine_search_agent() -> LlmAgent:
    return LlmAgent(
        name="RAGEngineSearchAgent",
        model=settings.model,
        instruction=ragengine_search_instruction,
        tools=[FunctionTool(search_vertex_rag)],
        output_key="ragengine_result",
        **tool_callbacks(),
    )
