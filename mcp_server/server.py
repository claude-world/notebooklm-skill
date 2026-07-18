#!/usr/bin/env python3
"""FastMCP server for the notebooklm-skill operations."""

from __future__ import annotations

import argparse
import os
from collections.abc import Awaitable
from importlib.metadata import PackageNotFoundError, version
from typing import Any, Literal

from fastmcp import FastMCP
from fastmcp.exceptions import ToolError

from mcp_server.tools import (
    SUPPORTED_ARTIFACT_TYPES,
    add_source,
    ask,
    create_notebook,
    delete_notebook,
    download_artifact,
    generate_artifact,
    list_artifacts,
    list_notebooks,
    list_sources,
    research,
    research_pipeline,
    summarize,
    trend_research,
)

mcp = FastMCP(
    "notebooklm",
    instructions=(
        "NotebookLM research automation with profile-aware authentication, mixed-source "
        "ingestion, source-grounded chat, complete research lifecycle management, and "
        f"artifact generation/download ({', '.join(SUPPORTED_ARTIFACT_TYPES)}). "
        "If authentication is required, tell the user to run "
        "`uvx --from notebooklm-py notebooklm login`, then retry. "
        "Notebook deletion requires confirm=true. Downloads refuse to overwrite existing "
        "files unless force=true."
    ),
)


def _package_version() -> str:
    try:
        return version("notebooklm-skill")
    except PackageNotFoundError:
        return "development"


async def registered_tools() -> list[Any]:
    """Return registered tools across the supported FastMCP 2.x/3.x APIs."""
    list_tools = getattr(mcp, "list_tools", None)
    if list_tools is not None:
        return list(await list_tools())
    legacy_server: Any = mcp
    return list((await legacy_server.get_tools()).values())


async def _invoke(operation: Awaitable[dict[str, Any]]) -> dict[str, Any]:
    """Turn implementation exceptions into real MCP tool errors."""
    try:
        return await operation
    except ToolError:
        raise
    except Exception as exc:
        raise ToolError(str(exc)) from exc


@mcp.tool()
async def nlm_create_notebook(
    title: str,
    sources: list[str] | None = None,
    text_sources: list[str] | None = None,
    file_sources: list[str] | None = None,
) -> dict[str, Any]:
    """Create a notebook with optional URL, raw-text, and local-file sources.

    Returns per-source outcomes and truthful requested/succeeded/failed counts.
    """
    return await _invoke(create_notebook(title, sources, text_sources, file_sources))


@mcp.tool()
async def nlm_list() -> dict[str, Any]:
    """List NotebookLM notebooks with IDs, titles, and source counts."""
    return await _invoke(list_notebooks())


@mcp.tool()
async def nlm_delete(notebook: str, confirm: bool = False) -> dict[str, Any]:
    """Permanently delete a notebook only when ``confirm`` is true."""
    if not confirm:
        return {
            "status": "requires_confirmation",
            "message": "Notebook deletion is irreversible. Call again with confirm=true.",
            "notebook": notebook,
        }
    return await _invoke(delete_notebook(notebook))


@mcp.tool()
async def nlm_add_source(
    notebook: str,
    url: str | None = None,
    text: str | None = None,
    text_title: str | None = None,
    file_path: str | None = None,
) -> dict[str, Any]:
    """Add exactly one URL, text, or local file source to a notebook."""
    return await _invoke(add_source(notebook, url=url, text=text, text_title=text_title, file_path=file_path))


@mcp.tool()
async def nlm_ask(notebook: str, query: str) -> dict[str, Any]:
    """Ask a source-grounded question and return answer citations."""
    return await _invoke(ask(notebook, query))


@mcp.tool()
async def nlm_summarize(notebook: str) -> dict[str, Any]:
    """Return the NotebookLM-generated summary for a notebook."""
    return await _invoke(summarize(notebook))


@mcp.tool()
async def nlm_list_sources(notebook: str) -> dict[str, Any]:
    """List ingested sources with current kind and processing status."""
    return await _invoke(list_sources(notebook))


@mcp.tool()
async def nlm_generate(
    notebook: str,
    type: str,
    lang: str = "en",
    instructions: str | None = None,
    source_ids: list[str] | None = None,
    options: dict[str, str] | None = None,
    wait: bool = True,
    timeout: float | None = None,
) -> dict[str, Any]:
    """Generate an artifact, optionally waiting for completion.

    ``type`` supports audio, video, cinematic, slides, report, study-guide,
    quiz, flashcards, mind-map, infographic, and data-table. ``options`` may
    contain type-specific keys such as audio_format, audio_length,
    video_format, video_style, slide_format, slide_length, report_format,
    custom_prompt, quantity, difficulty, orientation, detail_level, or style.
    Set wait=false to return the task ID immediately for long media jobs.
    """
    return await _invoke(
        generate_artifact(
            notebook,
            type,
            lang=lang,
            instructions=instructions,
            source_ids=source_ids,
            options=options,
            wait=wait,
            timeout=timeout,
        )
    )


@mcp.tool()
async def nlm_download(
    notebook: str,
    type: str,
    output_path: str,
    output_format: str | None = None,
    artifact_id: str | None = None,
    force: bool = False,
) -> dict[str, Any]:
    """Download an exact artifact ID (or latest) to a local path.

    Existing files and symlinks are rejected unless the safe overwrite rules
    permit the path. Formats: slides=pdf/pptx; quiz/flashcards=json/markdown/html.
    """
    return await _invoke(
        download_artifact(
            notebook,
            type,
            output_path,
            output_format=output_format,
            artifact_id=artifact_id,
            force=force,
        )
    )


@mcp.tool()
async def nlm_list_artifacts(
    notebook: str,
    type: str | None = None,
) -> dict[str, Any]:
    """List actual generated artifacts, optionally filtered by canonical type."""
    return await _invoke(list_artifacts(notebook, type))


@mcp.tool()
async def nlm_research(
    notebook: str,
    query: str,
    mode: Literal["fast", "deep"] = "fast",
    wait: bool = True,
    import_results: bool = True,
    max_sources: int = 10,
    timeout: float = 1800,
) -> dict[str, Any]:
    """Run pinned web research, wait for a terminal state, and import findings."""
    return await _invoke(
        research(
            notebook,
            query,
            mode=mode,
            wait=wait,
            import_results=import_results,
            max_sources=max_sources,
            timeout=timeout,
        )
    )


@mcp.tool()
async def nlm_research_pipeline(
    sources: list[str],
    questions: list[str],
    output_format: Literal["article", "thread", "report"] = "article",
    title: str | None = None,
) -> dict[str, Any]:
    """Create a notebook, ingest URLs, ask questions, and assemble content."""
    return await _invoke(research_pipeline(sources, questions, output_format, title))


@mcp.tool()
async def nlm_trend_research(
    geo: str = "TW",
    count: int = 5,
    platform: Literal["threads", "twitter", "instagram", "article"] = "threads",
) -> dict[str, Any]:
    """Fetch trend-pulse topics, research/import each, and create grounded drafts."""
    return await _invoke(trend_research(geo, count, platform))


def build_parser() -> argparse.ArgumentParser:
    """Build the MCP server CLI parser."""
    parser = argparse.ArgumentParser(description="NotebookLM MCP Server")
    parser.add_argument("--version", action="version", version=f"%(prog)s {_package_version()}")
    parser.add_argument("--http", action="store_true", help="Use Streamable HTTP")
    parser.add_argument(
        "--host",
        default="127.0.0.1",
        help="HTTP bind host (loopback only; default: 127.0.0.1)",
    )
    parser.add_argument("--port", type=int, default=8765, help="HTTP port (default: 8765)")
    parser.add_argument("--profile", help="NotebookLM auth profile (or NOTEBOOKLM_PROFILE)")
    return parser


def main() -> None:
    """Start stdio or loopback-only HTTP transport."""
    parser = build_parser()
    args = parser.parse_args()
    if args.profile:
        os.environ["NOTEBOOKLM_PROFILE"] = args.profile
    if not 1 <= args.port <= 65535:
        parser.error("--port must be between 1 and 65535")
    try:
        if args.http:
            if args.host not in {"127.0.0.1", "localhost", "::1"}:
                parser.error(
                    "Remote HTTP binding is disabled because this server exposes account and local "
                    "file operations. Use loopback behind an authenticated TLS reverse proxy."
                )
            mcp.run(transport="http", host=args.host, port=args.port)
        else:
            mcp.run(transport="stdio")
    except KeyboardInterrupt:
        return


if __name__ == "__main__":
    main()
