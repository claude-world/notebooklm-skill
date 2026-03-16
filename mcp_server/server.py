#!/usr/bin/env python3
"""NotebookLM MCP Server.

A FastMCP server that exposes 13 NotebookLM tools, usable by Claude Code,
Cursor, Gemini CLI, and any other MCP-compatible client.

Uses notebooklm-py v0.3.4 async API directly — no subprocess calls.

Usage:
    # stdio mode (default — for Claude Code / Cursor)
    notebooklm-mcp                    # after pip install .
    python3 mcp_server/server.py      # direct invocation

    # HTTP mode (for remote / multi-client access)
    notebooklm-mcp --http
    notebooklm-mcp --http --port 8765

MCP client configuration examples:

    # Claude Code — add to .mcp.json
    {
      "mcpServers": {
        "notebooklm": {
          "command": "python3",
          "args": ["/path/to/mcp_server/server.py"]
        }
      }
    }

    # Cursor — add to .cursor/mcp.json
    {
      "mcpServers": {
        "notebooklm": {
          "command": "python3",
          "args": ["/path/to/mcp_server/server.py"]
        }
      }
    }

    # Gemini CLI — add to ~/.gemini/settings.json
    {
      "mcpServers": {
        "notebooklm": {
          "command": "python3",
          "args": ["/path/to/mcp_server/server.py"]
        }
      }
    }

    # HTTP mode (any client that supports SSE/streamable HTTP)
    {
      "mcpServers": {
        "notebooklm": {
          "url": "http://localhost:8765/mcp"
        }
      }
    }
"""

import argparse
import sys
from pathlib import Path

# Allow direct invocation: python3 mcp_server/server.py (without pip install).
# Has no effect when called via pip-installed `notebooklm-mcp` entry point.
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from fastmcp import FastMCP

from mcp_server.tools import (
    add_source,
    ask,
    create_notebook,
    delete_notebook,
    download_artifact,
    generate_artifact,
    list_notebooks,
    list_sources,
    research,
    research_pipeline,
    summarize,
    trend_research,
)

# ---------------------------------------------------------------------------
# Server instance
# ---------------------------------------------------------------------------

mcp = FastMCP(
    "notebooklm",
    instructions=(
        "NotebookLM research engine — create notebooks, ask questions, "
        "generate and download 10 artifact types (audio, video, slides, "
        "report, study-guide, quiz, flashcards, mind-map, infographic, "
        "data-table), and run full research-to-content pipelines."
    ),
)


# ---------------------------------------------------------------------------
# Core Tools (7)
# ---------------------------------------------------------------------------


@mcp.tool()
async def nlm_create_notebook(
    title: str,
    sources: list[str] | None = None,
    text_sources: list[str] | None = None,
) -> dict:
    """Create a NotebookLM notebook, optionally with URL and text sources.

    Args:
        title: Human-readable notebook title.
        sources: Optional list of URLs to ingest (web pages, PDFs, YouTube).
        text_sources: Optional list of raw text strings to add as sources.

    Returns:
        Notebook metadata including notebook id and sources added.

    Example:
        nlm_create_notebook(
            title="AI Safety Research",
            sources=["https://arxiv.org/abs/2401.00001"],
            text_sources=["Additional context about AI alignment..."]
        )
    """
    try:
        return await create_notebook(title, sources, text_sources)
    except Exception as exc:
        return {"error": str(exc), "status": "failed"}


@mcp.tool()
async def nlm_list() -> dict:
    """List all notebooks in the NotebookLM account.

    Returns:
        Dict with notebooks list, each containing id and title.

    Example:
        nlm_list()
    """
    try:
        return await list_notebooks()
    except Exception as exc:
        return {"error": str(exc), "status": "failed"}


@mcp.tool()
async def nlm_delete(notebook: str) -> dict:
    """Delete a notebook and all its sources. Irreversible.

    Args:
        notebook: Notebook ID or title to delete.

    Returns:
        Deletion status and deleted notebook ID.

    Example:
        nlm_delete(notebook="Old Research")
    """
    try:
        return await delete_notebook(notebook)
    except Exception as exc:
        return {"error": str(exc), "status": "failed"}


@mcp.tool()
async def nlm_add_source(
    notebook: str,
    url: str | None = None,
    text: str | None = None,
    text_title: str | None = None,
    file_path: str | None = None,
) -> dict:
    """Add a source to an existing notebook.

    Provide exactly one of: url, text, or file_path.

    Args:
        notebook: Notebook ID or title.
        url: URL to add (web page, PDF, YouTube, etc.).
        text: Raw text content to add as a source.
        text_title: Title for the text source (default "Text Source").
        file_path: Local file path to upload (PDF, TXT, etc.).

    Returns:
        Source metadata including source id and type.

    Example:
        nlm_add_source(notebook="My Research", url="https://example.com/paper.pdf")
        nlm_add_source(notebook="My Research", text="Key finding: ...", text_title="Notes")
    """
    try:
        return await add_source(notebook, url=url, text=text, text_title=text_title, file_path=file_path)
    except Exception as exc:
        return {"error": str(exc), "status": "failed"}


@mcp.tool()
async def nlm_ask(notebook: str, query: str) -> dict:
    """Ask a question against a notebook's ingested sources.

    The answer is grounded in the notebook's content and includes citations.

    Args:
        notebook: Notebook ID or title to query.
        query: Natural-language question.

    Returns:
        Answer text with citations pointing to source passages.

    Example:
        nlm_ask(notebook="AI Safety Research", query="What are the main risks?")
    """
    try:
        return await ask(notebook, query)
    except Exception as exc:
        return {"error": str(exc), "status": "failed"}


@mcp.tool()
async def nlm_summarize(notebook: str) -> dict:
    """Generate a summary of a notebook's content.

    Args:
        notebook: Notebook ID or title.

    Returns:
        Summary text extracted from all ingested sources.

    Example:
        nlm_summarize(notebook="AI Safety Research")
    """
    try:
        return await summarize(notebook)
    except Exception as exc:
        return {"error": str(exc), "status": "failed"}


@mcp.tool()
async def nlm_list_sources(notebook: str) -> dict:
    """List all sources in a notebook.

    Args:
        notebook: Notebook ID or title.

    Returns:
        List of sources with id, title, type, and status.

    Example:
        nlm_list_sources(notebook="AI Safety Research")
    """
    try:
        return await list_sources(notebook)
    except Exception as exc:
        return {"error": str(exc), "status": "failed"}


# ---------------------------------------------------------------------------
# Artifact Tools (3)
# ---------------------------------------------------------------------------


@mcp.tool()
async def nlm_generate(
    notebook: str,
    type: str,
    lang: str = "en",
    instructions: str | None = None,
) -> dict:
    """Generate an artifact from a notebook.

    Supports 10 artifact types. Waits for generation to complete.

    Args:
        notebook: Notebook ID or title.
        type: Artifact type — one of: audio, video, slides, report, quiz,
              flashcards, mind-map, infographic, data-table, study-guide.
        lang: Language code (default "en"). Used for audio, video, slides,
              report, infographic, data-table, study-guide.
        instructions: Optional generation instructions. Passed as
                      "instructions" for audio/video/slides/quiz/flashcards/
                      infographic/data-table, or as "extra_instructions" for
                      report/study-guide. Not used for mind-map.

    Returns:
        Generation status with task_id and completion details.

    Example:
        nlm_generate(notebook="AI Safety", type="audio", lang="en")
        nlm_generate(notebook="AI Safety", type="report", instructions="Add executive summary")
        nlm_generate(notebook="AI Safety", type="quiz", instructions="Focus on chapter 3")
    """
    try:
        return await generate_artifact(notebook, type, lang=lang, instructions=instructions)
    except Exception as exc:
        return {"error": str(exc), "status": "failed"}


@mcp.tool()
async def nlm_download(
    notebook: str,
    type: str,
    output_path: str,
    output_format: str | None = None,
) -> dict:
    """Download a generated artifact to a local file.

    Supports all 10 artifact types:
      - audio → .m4a
      - video → .mp4
      - slides → PDF (default) or PPTX (output_format="pptx")
      - report → Markdown
      - study-guide → Markdown
      - quiz → JSON (default), Markdown ("markdown"), or HTML ("html")
      - flashcards → JSON (default), Markdown ("markdown"), or HTML ("html")
      - mind-map → JSON
      - infographic → PNG
      - data-table → CSV

    Args:
        notebook: Notebook ID or title.
        type: Artifact type — audio, video, slides, report, study-guide,
              quiz, flashcards, mind-map, infographic, or data-table.
        output_path: Local file path to save the artifact.
        output_format: Optional output format for types that support it.
                       slides: "pdf" (default) or "pptx".
                       quiz/flashcards: "json" (default), "markdown", or "html".

    Returns:
        Download status and output file path.

    Example:
        nlm_download(notebook="AI Safety", type="audio", output_path="podcast.m4a")
        nlm_download(notebook="AI Safety", type="slides", output_path="deck.pptx", output_format="pptx")
        nlm_download(notebook="AI Safety", type="quiz", output_path="quiz.md", output_format="markdown")
    """
    try:
        return await download_artifact(notebook, type, output_path, output_format=output_format)
    except Exception as exc:
        return {"error": str(exc), "status": "failed"}


@mcp.tool()
async def nlm_list_artifacts(
    notebook: str,
    type: str | None = None,
) -> dict:
    """List sources/artifacts in a notebook.

    Optionally filter by type.

    Args:
        notebook: Notebook ID or title.
        type: Optional filter — not yet supported by upstream API,
              returns all sources for now.

    Returns:
        List of sources in the notebook.

    Example:
        nlm_list_artifacts(notebook="AI Safety")
    """
    try:
        result = await list_sources(notebook)
        # Future: filter by type when upstream API supports it
        return result
    except Exception as exc:
        return {"error": str(exc), "status": "failed"}


# ---------------------------------------------------------------------------
# Research Tool (1)
# ---------------------------------------------------------------------------


@mcp.tool()
async def nlm_research(
    notebook: str,
    query: str,
    mode: str = "fast",
) -> dict:
    """Run a web research query within a notebook.

    Uses NotebookLM's built-in research capability to find and ingest
    web sources relevant to the query.

    Args:
        notebook: Notebook ID or title.
        query: Research topic or question.
        mode: Research mode — "fast" or "deep" (default "fast").

    Returns:
        Research results and status.

    Example:
        nlm_research(notebook="AI Safety", query="latest alignment techniques", mode="fast")
    """
    try:
        return await research(notebook, query, mode=mode)
    except Exception as exc:
        return {"error": str(exc), "status": "failed"}


# ---------------------------------------------------------------------------
# Pipeline Tools (2)
# ---------------------------------------------------------------------------


@mcp.tool()
async def nlm_research_pipeline(
    sources: list[str],
    questions: list[str],
    output_format: str = "article",
) -> dict:
    """Full research-to-content pipeline.

    End-to-end workflow: creates a notebook from source URLs, asks all
    research questions, and assembles answers into formatted content.

    Args:
        sources: URLs to ingest as research sources.
        questions: Research questions to investigate.
        output_format: Output format — "article", "thread", or "report"
                       (default "article").

    Returns:
        Notebook ID, individual answers, and assembled content.

    Example:
        nlm_research_pipeline(
            sources=["https://example.com/paper1", "https://example.com/paper2"],
            questions=["What is the main finding?", "What methodology was used?"],
            output_format="article"
        )
    """
    try:
        return await research_pipeline(sources, questions, output_format)
    except Exception as exc:
        return {"error": str(exc), "status": "failed"}


@mcp.tool()
async def nlm_trend_research(
    geo: str = "TW",
    count: int = 5,
    platform: str = "threads",
) -> dict:
    """Trending topics to researched content pipeline.

    Fetches current trending topics (via trend-pulse), then for each topic:
    creates a notebook, researches it, and generates platform-ready content.

    Args:
        geo: Geographic region code (default "TW"). Examples: "US", "JP".
        count: Number of trending topics to process (default 5).
        platform: Target content platform — "threads", "instagram", or
                  "article" (default "threads").

    Returns:
        Trends processed with generated content for each.

    Example:
        nlm_trend_research(geo="TW", count=3, platform="threads")
    """
    try:
        return await trend_research(geo, count, platform)
    except Exception as exc:
        return {"error": str(exc), "status": "failed"}


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------


def main() -> None:
    """Parse arguments and start the MCP server."""
    parser = argparse.ArgumentParser(
        description="NotebookLM MCP Server",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=(
            "Examples:\n"
            "  notebooklm-mcp                # stdio mode (Claude Code, Cursor)\n"
            "  notebooklm-mcp --http         # HTTP mode on port 8765\n"
            "  notebooklm-mcp --http --port 9000\n"
        ),
    )
    parser.add_argument(
        "--http",
        action="store_true",
        help="Run in HTTP mode instead of stdio (default port 8765)",
    )
    parser.add_argument(
        "--port",
        type=int,
        default=8765,
        help="Port for HTTP mode (default: 8765)",
    )
    args = parser.parse_args()

    if args.http:
        mcp.run(transport="streamable-http", host="0.0.0.0", port=args.port)
    else:
        mcp.run(transport="stdio")


if __name__ == "__main__":
    main()
