import structlog
from langchain_tavily import TavilySearch

from app.features.agent.v1.retriever.vector_db import hybrid_retriever
from app.features.agent.v1.state import DocumentWithSource

tavily_web_search = TavilySearch(max_results=3, search_depth="basic")


logger = structlog.get_logger()


async def web_search_tool(user_question: str):
    try:
        web_results = await tavily_web_search.ainvoke({"query": user_question})

        formatted_context_blocks = []
        for index, result in enumerate(web_results, start=1):
            formatted_context_blocks.append(
                f"--- Web Context Block [{index}] ---\n"
                f"Source URL: {result.get('url', 'N/A')}\n"
                f"Extracted Content: {result.get('content', '')}\n"
            )

        combined_web_context = "\n".join(formatted_context_blocks)

    except (ConnectionError, TimeoutError, TypeError, ValueError, RuntimeError):
        logger.exception(
            "Tavily Search Failed: Falling back to default baseline processing."
        )
        combined_web_context = (
            "No real-time web search results could be retrieved due to system limits."
        )

    return combined_web_context


async def retriever_tool(user_question: str):
    formatted_context_list = []
    documents_with_sources = []

    documents = await hybrid_retriever.ainvoke(user_question)

    for index, d in enumerate(documents):
        file = d.metadata.get("source", f"Source  {index}")
        page = d.metadata.get("page", 0)
        content = d.page_content

        documents_with_sources.append(
            DocumentWithSource(
                file=file,
                page=page,
                content=content,
            )
        )
        formatted_context_list.append(
            f"--- Document Source [{index}]: {file} (Page {page}) ---\n{content}"
        )

    documents_with_sources_formatted_str = "\n\n".join(formatted_context_list)

    return {
        "documents_with_sources": documents_with_sources,
        "documents_with_sources_formatted_str": documents_with_sources_formatted_str,
    }
