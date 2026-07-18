#!/usr/bin/env python3
"""JSON-first command-line interface for NotebookLM automation."""

from __future__ import annotations

import argparse
import asyncio
import json
import os
import sys
from importlib.metadata import PackageNotFoundError, version
from pathlib import Path
from typing import Any

from scripts.common import (
    ARTIFACT_SPECS,
    AuthenticationRequired,
    UsageError,
    download_artifact,
    generate_artifact,
    get_client,
    ingest_sources,
    list_artifacts,
    resolve_notebook,
    run_research,
    serialize,
    serialize_notebook,
    serialize_source,
    source_result_summary,
    validate_url,
)


def _json_out(data: dict[str, Any]) -> None:
    """Write one machine-readable response to stdout."""
    print(json.dumps(data, ensure_ascii=False, indent=2))


def _err(message: str) -> None:
    """Write progress only to stderr."""
    print(f"[nlm] {message}", file=sys.stderr)


def _package_version() -> str:
    try:
        return version("notebooklm-skill")
    except PackageNotFoundError:
        return "development"


async def cmd_create(args: argparse.Namespace) -> dict[str, Any]:
    """Create a notebook and ingest URL, text, and file sources."""
    title = args.title.strip()
    if not title:
        raise UsageError("Notebook title cannot be empty.")
    async with get_client() as client:
        _err(f"Creating notebook '{title}'...")
        notebook = await client.notebooks.create(title=title)
        results = await ingest_sources(
            client,
            notebook.id,
            urls=args.sources,
            texts=args.text_sources,
            files=args.files,
            wait_timeout=args.source_timeout,
            concurrency=args.source_concurrency,
        )
        summary = source_result_summary(results)
        notebook.sources_count = summary["succeeded"]
        status = "ok"
        if summary["failed"]:
            status = "failed" if summary["succeeded"] == 0 else "partial"
        if args.strict and summary["failed"]:
            status = "failed"
        return {
            "status": status,
            "action": "create",
            "notebook": serialize_notebook(notebook),
            "source_summary": summary,
            "sources": results,
        }


async def cmd_list(_args: argparse.Namespace) -> dict[str, Any]:
    """List notebooks."""
    async with get_client() as client:
        notebooks = list(await client.notebooks.list() or [])
        return {
            "status": "ok",
            "action": "list",
            "count": len(notebooks),
            "notebooks": [serialize_notebook(item) for item in notebooks],
        }


async def cmd_delete(args: argparse.Namespace) -> dict[str, Any]:
    """Delete a notebook after explicit confirmation."""
    if not args.yes:
        raise UsageError("Deletion is irreversible. Re-run with --yes to confirm.")
    async with get_client() as client:
        notebook = await resolve_notebook(client, args.notebook)
        await client.notebooks.delete(notebook_id=notebook.id)
        return {
            "status": "ok",
            "action": "delete",
            "deleted": True,
            "notebook": serialize_notebook(notebook),
        }


async def cmd_add_source(args: argparse.Namespace) -> dict[str, Any]:
    """Add exactly one source to a notebook."""
    async with get_client() as client:
        notebook = await resolve_notebook(client, args.notebook)
        if args.url:
            source = await client.sources.add_url(
                notebook.id,
                validate_url(args.url),
                wait=True,
                wait_timeout=args.source_timeout,
            )
        elif args.text:
            if not args.text.strip():
                raise UsageError("Text source cannot be empty.")
            source = await client.sources.add_text(
                notebook.id,
                title=args.text_title,
                content=args.text,
                wait=True,
                wait_timeout=args.source_timeout,
            )
        else:
            file_path = Path(args.file).expanduser()
            if not file_path.is_file():
                raise UsageError(f"Source file not found: {file_path}")
            source = await client.sources.add_file(
                notebook.id,
                file_path=file_path,
                wait=True,
                wait_timeout=args.source_timeout,
            )
        return {
            "status": "ok",
            "action": "add-source",
            "notebook_id": notebook.id,
            "source": serialize_source(source),
        }


async def cmd_ask(args: argparse.Namespace) -> dict[str, Any]:
    """Ask a source-grounded question."""
    if not args.query.strip():
        raise UsageError("Query cannot be empty.")
    async with get_client() as client:
        notebook = await resolve_notebook(client, args.notebook)
        result = await client.chat.ask(notebook.id, question=args.query.strip())
        return {
            "status": "ok",
            "action": "ask",
            "notebook_id": notebook.id,
            "query": args.query.strip(),
            "answer": result.answer,
            "references": serialize(getattr(result, "references", ()) or ()),
            "conversation_id": getattr(result, "conversation_id", None),
        }


async def cmd_summarize(args: argparse.Namespace) -> dict[str, Any]:
    """Return a notebook summary."""
    async with get_client() as client:
        notebook = await resolve_notebook(client, args.notebook)
        summary = await client.notebooks.get_summary(notebook_id=notebook.id)
        return {
            "status": "ok",
            "action": "summarize",
            "notebook_id": notebook.id,
            "summary": summary,
        }


async def cmd_list_sources(args: argparse.Namespace) -> dict[str, Any]:
    """List ingested sources."""
    async with get_client() as client:
        notebook = await resolve_notebook(client, args.notebook)
        sources = list(await client.sources.list(notebook.id) or [])
        return {
            "status": "ok",
            "action": "list-sources",
            "notebook_id": notebook.id,
            "count": len(sources),
            "sources": [serialize_source(item) for item in sources],
        }


async def cmd_list_artifacts(args: argparse.Namespace) -> dict[str, Any]:
    """List generated artifacts, not notebook sources."""
    async with get_client() as client:
        notebook = await resolve_notebook(client, args.notebook)
        artifacts = await list_artifacts(client, notebook.id, args.type)
        return {
            "status": "ok",
            "action": "list-artifacts",
            "notebook_id": notebook.id,
            "artifact_type": args.type,
            "count": len(artifacts),
            "artifacts": artifacts,
        }


def _generation_options(args: argparse.Namespace) -> dict[str, str | None]:
    names = (
        "audio_format",
        "audio_length",
        "video_format",
        "video_style",
        "style_prompt",
        "slide_format",
        "slide_length",
        "report_format",
        "custom_prompt",
        "quantity",
        "difficulty",
        "orientation",
        "detail_level",
        "style",
    )
    return {name: getattr(args, name, None) for name in names}


async def cmd_generate(args: argparse.Namespace) -> dict[str, Any]:
    """Generate an artifact, with optional precise auto-download."""
    if args.output and not args.wait:
        raise UsageError("--output requires waiting; remove --no-wait.")
    async with get_client() as client:
        notebook = await resolve_notebook(client, args.notebook)
        _err(f"Generating {args.type}...")
        result = await generate_artifact(
            client,
            notebook.id,
            args.type,
            language=args.lang,
            instructions=args.instructions,
            source_ids=args.source_ids,
            options=_generation_options(args),
            wait=args.wait,
            timeout=args.timeout,
        )
        result.update({"action": "generate", "notebook_id": notebook.id})
        if args.output:
            artifact_id = result.get("task_id") or result.get("result", {}).get("note_id")
            result["output_path"] = await download_artifact(
                client,
                notebook.id,
                args.type,
                args.output,
                artifact_id=artifact_id,
                output_format=args.output_format,
                force=args.force,
            )
        return result


async def cmd_download(args: argparse.Namespace) -> dict[str, Any]:
    """Download the selected or latest completed artifact."""
    async with get_client() as client:
        notebook = await resolve_notebook(client, args.notebook)
        path = await download_artifact(
            client,
            notebook.id,
            args.type,
            args.output,
            artifact_id=args.artifact_id,
            output_format=args.output_format,
            force=args.force,
        )
        return {
            "status": "ok",
            "action": "download",
            "notebook_id": notebook.id,
            "artifact_type": args.type,
            "artifact_id": args.artifact_id,
            "output_path": path,
        }


async def cmd_research(args: argparse.Namespace) -> dict[str, Any]:
    """Run a complete, pinned research lifecycle."""
    async with get_client() as client:
        notebook = await resolve_notebook(client, args.notebook)
        result = await run_research(
            client,
            notebook.id,
            args.query,
            mode=args.mode,
            wait=args.wait,
            timeout=args.timeout,
            import_results=args.import_results,
            max_sources=args.max_sources,
        )
        result.update({"action": "research", "notebook_id": notebook.id})
        return result


async def cmd_podcast(args: argparse.Namespace) -> dict[str, Any]:
    args.type = "audio"
    args.source_ids = []
    args.wait = True
    args.timeout = args.timeout or ARTIFACT_SPECS["audio"].timeout
    args.output_format = None
    result = await cmd_generate(args)
    result["action"] = "podcast"
    return result


async def cmd_qa(args: argparse.Namespace) -> dict[str, Any]:
    args.type = "quiz"
    args.lang = "en"
    args.source_ids = []
    args.wait = True
    args.timeout = args.timeout or ARTIFACT_SPECS["quiz"].timeout
    result = await cmd_generate(args)
    result["action"] = "qa"
    return result


def _add_notebook_argument(parser: argparse.ArgumentParser) -> None:
    parser.add_argument("--notebook", required=True, help="Notebook title or ID")


def _add_download_arguments(parser: argparse.ArgumentParser) -> None:
    parser.add_argument("--output", help="Output file path")
    parser.add_argument("--output-format", help="pdf/pptx or json/markdown/html")
    parser.add_argument("--force", action="store_true", help="Overwrite an existing output file")


def _add_generation_options(parser: argparse.ArgumentParser) -> None:
    parser.add_argument("--audio-format", choices=("deep-dive", "brief", "critique", "debate"))
    parser.add_argument("--audio-length", choices=("short", "default", "long"))
    parser.add_argument("--video-format", choices=("explainer", "brief", "cinematic"))
    parser.add_argument(
        "--video-style",
        choices=(
            "auto-select",
            "custom",
            "classic",
            "whiteboard",
            "kawaii",
            "anime",
            "watercolor",
            "retro-print",
            "heritage",
            "paper-craft",
        ),
    )
    parser.add_argument("--style-prompt", help="Required when --video-style custom")
    parser.add_argument("--slide-format", choices=("detailed-deck", "presenter-slides"))
    parser.add_argument("--slide-length", choices=("default", "short"))
    parser.add_argument("--report-format", choices=("briefing-doc", "study-guide", "blog-post", "custom"))
    parser.add_argument("--custom-prompt", help="Required when --report-format custom")
    parser.add_argument("--quantity", choices=("fewer", "standard"))
    parser.add_argument("--difficulty", choices=("easy", "medium", "hard"))
    parser.add_argument("--orientation", choices=("landscape", "portrait", "square"))
    parser.add_argument("--detail-level", choices=("concise", "standard", "detailed"))
    parser.add_argument(
        "--style",
        choices=(
            "auto-select",
            "sketch-note",
            "professional",
            "bento-grid",
            "editorial",
            "instructional",
            "bricks",
            "clay",
            "anime",
            "kawaii",
            "scientific",
        ),
    )


def build_parser() -> argparse.ArgumentParser:
    """Build the public CLI contract (also used by tests)."""
    parser = argparse.ArgumentParser(
        description="NotebookLM automation CLI (JSON stdout, progress stderr)",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=(
            "Examples:\n"
            "  %(prog)s create --title Research --sources https://example.com\n"
            "  %(prog)s ask --notebook Research --query 'Key findings?'\n"
            "  %(prog)s generate --notebook Research --type slides --output deck.pdf\n"
            "  %(prog)s research --notebook Research --query 'Latest evidence' --mode deep\n"
            "  %(prog)s delete --notebook Research --yes"
        ),
    )
    parser.add_argument("--version", action="version", version=f"%(prog)s {_package_version()}")
    parser.add_argument("--profile", help="NotebookLM auth profile (or NOTEBOOKLM_PROFILE)")
    subparsers = parser.add_subparsers(dest="command", required=True)

    create = subparsers.add_parser("create", help="Create a notebook and add mixed sources")
    create.add_argument("--title", default="Untitled Research")
    create.add_argument("--sources", nargs="*", default=[], metavar="URL")
    create.add_argument("--text-sources", nargs="*", default=[], metavar="TEXT")
    create.add_argument("--files", nargs="*", default=[], metavar="PATH")
    create.add_argument("--source-timeout", type=float, default=180)
    create.add_argument("--source-concurrency", type=int, default=4)
    create.add_argument("--strict", action="store_true", help="Exit nonzero if any source fails")

    subparsers.add_parser("list", help="List notebooks")

    delete = subparsers.add_parser("delete", help="Delete a notebook")
    _add_notebook_argument(delete)
    delete.add_argument("--yes", action="store_true", help="Confirm irreversible deletion")

    add_source = subparsers.add_parser("add-source", help="Add one URL, text, or file source")
    _add_notebook_argument(add_source)
    source_group = add_source.add_mutually_exclusive_group(required=True)
    source_group.add_argument("--url")
    source_group.add_argument("--text")
    source_group.add_argument("--file")
    add_source.add_argument("--text-title", default="Text Source")
    add_source.add_argument("--source-timeout", type=float, default=180)

    ask = subparsers.add_parser("ask", help="Ask a source-grounded question")
    _add_notebook_argument(ask)
    ask.add_argument("--query", required=True)

    summarize = subparsers.add_parser("summarize", help="Get a notebook summary")
    _add_notebook_argument(summarize)

    sources = subparsers.add_parser("list-sources", help="List ingested sources")
    _add_notebook_argument(sources)

    artifacts = subparsers.add_parser("list-artifacts", help="List generated artifacts")
    _add_notebook_argument(artifacts)
    artifacts.add_argument("--type", choices=tuple(ARTIFACT_SPECS))

    generate = subparsers.add_parser("generate", help="Generate an artifact")
    _add_notebook_argument(generate)
    generate.add_argument("--type", required=True, choices=tuple(ARTIFACT_SPECS))
    generate.add_argument("--lang", default="en")
    generate.add_argument("--instructions")
    generate.add_argument("--source-ids", nargs="*", default=[])
    generate.add_argument("--wait", action=argparse.BooleanOptionalAction, default=True, help="Wait for completion")
    generate.add_argument("--timeout", type=float)
    _add_download_arguments(generate)
    _add_generation_options(generate)

    download = subparsers.add_parser("download", help="Download a generated artifact")
    _add_notebook_argument(download)
    download.add_argument("--type", required=True, choices=tuple(ARTIFACT_SPECS))
    download.add_argument("--artifact-id", help="Exact artifact ID (defaults to latest)")
    download.add_argument("--output", required=True)
    download.add_argument("--output-format")
    download.add_argument("--force", action="store_true")

    research = subparsers.add_parser("research", help="Run web research and import results")
    _add_notebook_argument(research)
    research.add_argument("--query", required=True)
    research.add_argument("--mode", choices=("fast", "deep"), default="fast")
    research.add_argument("--wait", action=argparse.BooleanOptionalAction, default=True)
    research.add_argument("--import-results", action=argparse.BooleanOptionalAction, default=True)
    research.add_argument("--max-sources", type=int, default=10)
    research.add_argument("--timeout", type=float, default=1800)

    podcast = subparsers.add_parser("podcast", help="Generate and optionally download audio")
    _add_notebook_argument(podcast)
    podcast.add_argument("--lang", default="en")
    podcast.add_argument("--instructions")
    podcast.add_argument("--output")
    podcast.add_argument("--timeout", type=float)
    podcast.add_argument("--force", action="store_true")
    podcast.add_argument("--audio-format", choices=("deep-dive", "brief", "critique", "debate"))
    podcast.add_argument("--audio-length", choices=("short", "default", "long"))

    qa = subparsers.add_parser("qa", help="Generate and optionally download a quiz")
    _add_notebook_argument(qa)
    qa.add_argument("--instructions")
    qa.add_argument("--output")
    qa.add_argument("--output-format", choices=("json", "markdown", "html"))
    qa.add_argument("--timeout", type=float)
    qa.add_argument("--force", action="store_true")
    qa.add_argument("--quantity", choices=("fewer", "standard"))
    qa.add_argument("--difficulty", choices=("easy", "medium", "hard"))
    return parser


COMMANDS = {
    "create": cmd_create,
    "list": cmd_list,
    "delete": cmd_delete,
    "add-source": cmd_add_source,
    "ask": cmd_ask,
    "summarize": cmd_summarize,
    "list-sources": cmd_list_sources,
    "list-artifacts": cmd_list_artifacts,
    "generate": cmd_generate,
    "download": cmd_download,
    "research": cmd_research,
    "podcast": cmd_podcast,
    "qa": cmd_qa,
}


async def dispatch(args: argparse.Namespace) -> dict[str, Any]:
    """Dispatch a parsed command."""
    return await COMMANDS[args.command](args)


def run(argv: list[str] | None = None) -> int:
    """Run the CLI and return a process exit code."""
    args = build_parser().parse_args(argv)
    if args.profile:
        os.environ["NOTEBOOKLM_PROFILE"] = args.profile
    try:
        result = asyncio.run(dispatch(args))
    except AuthenticationRequired as exc:
        _json_out({"status": "failed", "error": str(exc), "code": "AUTH_REQUIRED"})
        return 4
    except UsageError as exc:
        _json_out({"status": "failed", "error": str(exc), "code": "INVALID_ARGUMENT"})
        return 2
    except KeyboardInterrupt:
        _json_out({"status": "failed", "error": "Operation cancelled.", "code": "CANCELLED"})
        return 130
    except TimeoutError as exc:
        _json_out({"status": "failed", "error": str(exc), "code": "TIMEOUT"})
        return 1
    except Exception as exc:
        _json_out({"status": "failed", "error": str(exc), "code": "OPERATION_ERROR"})
        return 1

    _json_out(result)
    return 1 if result.get("status") == "failed" else 0


def main() -> None:
    raise SystemExit(run())


if __name__ == "__main__":
    main()
