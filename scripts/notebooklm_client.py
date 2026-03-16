#!/usr/bin/env python3
"""
NotebookLM Client - CLI wrapper around notebooklm-py v0.3.4.

Subcommands:
    create      - Create a notebook with URL, text, and/or file sources
    list        - List all notebooks
    delete      - Delete a notebook
    add-source  - Add a source (URL, text, or file) to an existing notebook
    ask         - Ask a question against a notebook
    summarize   - Get the notebook summary
    generate    - Generate an artifact (audio/video/slides/report/quiz/etc.)
    download    - Download a generated artifact
    research    - Run deep web research on a topic
    podcast     - Alias for generate --type audio (also downloads the file)
    qa          - Alias for generate --type quiz

Output:
    JSON to stdout for machine parsing.
    Progress/status messages to stderr.

Dependencies:
    pip install notebooklm-py python-dotenv
"""

import argparse
import asyncio
import json
import sys
from pathlib import Path

# Load .env from project root if present
try:
    from dotenv import load_dotenv

    _project_root = Path(__file__).resolve().parent.parent
    _env_file = _project_root / ".env"
    if _env_file.exists():
        load_dotenv(_env_file)
except ImportError:
    pass


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _json_out(data: dict) -> None:
    """Print JSON to stdout."""
    print(json.dumps(data, ensure_ascii=False, indent=2))


def _err(msg: str) -> None:
    """Print progress / status to stderr."""
    print(f"[nlm] {msg}", file=sys.stderr)


def _json_error(message: str, code: str = "CLIENT_ERROR") -> None:
    """Print JSON error to stdout and exit 1."""
    _json_out({"error": message, "code": code})
    sys.exit(1)


# Common language code aliases → notebooklm-py format
_LANG_MAP = {
    "zh-tw": "zh_Hant", "zh-hant": "zh_Hant", "zh_tw": "zh_Hant", "zh-TW": "zh_Hant",
    "zh-cn": "zh_Hans", "zh-hans": "zh_Hans", "zh_cn": "zh_Hans", "zh-CN": "zh_Hans",
    "pt-br": "pt_BR", "pt-pt": "pt_PT", "es-mx": "es_MX", "fr-ca": "fr_CA",
}


def _normalize_lang(lang: str) -> str:
    """Map common language codes to notebooklm-py format."""
    return _LANG_MAP.get(lang, _LANG_MAP.get(lang.lower(), lang))


def _serialize(obj) -> object:
    """Best-effort serialize an object to JSON-compatible types."""
    if obj is None:
        return None
    if isinstance(obj, (str, int, float, bool)):
        return obj
    if isinstance(obj, (list, tuple)):
        return [_serialize(x) for x in obj]
    if isinstance(obj, dict):
        return {k: _serialize(v) for k, v in obj.items()}
    if hasattr(obj, "isoformat"):
        return obj.isoformat()
    if hasattr(obj, "__dict__"):
        return {k: _serialize(v) for k, v in vars(obj).items() if not k.startswith("_")}
    return str(obj)


def _notebook_to_dict(nb) -> dict:
    """Convert a Notebook object to a serializable dict."""
    return {
        "id": nb.id,
        "title": nb.title,
    }


def _source_to_dict(src) -> dict:
    """Convert a Source object to a serializable dict."""
    d = {"id": src.id}
    for attr in ("title", "type", "status", "url"):
        val = getattr(src, attr, None)
        if val is not None:
            d[attr] = _serialize(val)
    return d


async def _find_notebook(client, identifier: str):
    """Find a notebook by name or ID.

    Tries exact ID match first, then exact name, then partial name match.
    Returns the Notebook object or calls _json_error if not found.
    """
    try:
        notebooks = await client.notebooks.list()
    except Exception as exc:
        _json_error(f"Cannot list notebooks: {exc}", "API_ERROR")

    if not notebooks:
        _json_error("No notebooks found.", "NOT_FOUND")

    # Try exact ID match
    for nb in notebooks:
        if nb.id == identifier:
            return nb

    # Try exact name match (case-insensitive)
    identifier_lower = identifier.lower()
    for nb in notebooks:
        if nb.title.lower() == identifier_lower:
            return nb

    # Try partial name match (fuzzy)
    matches = [nb for nb in notebooks if identifier_lower in nb.title.lower()]

    if len(matches) == 1:
        return matches[0]
    elif len(matches) > 1:
        names = [m.title for m in matches]
        _json_error(
            f"Ambiguous notebook name '{identifier}'. Matches: {names}",
            "AMBIGUOUS",
        )

    _json_error(
        f"Notebook '{identifier}' not found. Use 'list' to see available notebooks.",
        "NOT_FOUND",
    )


# ---------------------------------------------------------------------------
# Artifact type mapping
# ---------------------------------------------------------------------------

# Maps --type value to (generate_method_name, download_method_name, default_extension)
ARTIFACT_TYPES = {
    "audio":       ("generate_audio",            "download_audio",       "m4a"),
    "video":       ("generate_video",            "download_video",       "mp4"),
    "cinematic":   ("generate_cinematic_video",  "download_video",       "mp4"),
    "slides":      ("generate_slide_deck",       "download_slide_deck",  "pdf"),
    "report":      ("generate_report",           "download_report",      "md"),
    "quiz":        ("generate_quiz",             "download_quiz",        "json"),
    "flashcards":  ("generate_flashcards",       "download_flashcards",  "json"),
    "mind-map":    ("generate_mind_map",         "download_mind_map",    "json"),
    "infographic": ("generate_infographic",      "download_infographic", "png"),
    "data-table":  ("generate_data_table",       "download_data_table",  "csv"),
    "study-guide": ("generate_study_guide",      "download_report",      "md"),
}


# ---------------------------------------------------------------------------
# Subcommands
# ---------------------------------------------------------------------------

async def cmd_create(args) -> None:
    """Create a new notebook, optionally adding URL/text/file sources."""
    from notebooklm import NotebookLMClient

    sources = args.sources or []
    text_sources = args.text_sources or []
    title = args.title or "Untitled Research"

    async with await NotebookLMClient.from_storage() as client:
        _err(f"Creating notebook '{title}'...")
        try:
            nb = await client.notebooks.create(title=title)
        except Exception as exc:
            _json_error(f"Failed to create notebook: {exc}", "CREATE_ERROR")

        nb_id = nb.id
        added_sources = []

        # Add URL sources
        for url in sources:
            _err(f"Adding URL source: {url}")
            try:
                src = await client.sources.add_url(nb_id, url, wait=True, wait_timeout=120)
                added_sources.append(_source_to_dict(src))
            except Exception as exc:
                _err(f"Warning: Failed to add URL '{url}': {exc}")
                added_sources.append({"url": url, "error": str(exc)})

        # Add text sources
        for i, text in enumerate(text_sources):
            text_title = f"Text Source {i + 1}"
            _err(f"Adding text source: {text_title}")
            try:
                src = await client.sources.add_text(nb_id, title=text_title, content=text, wait=True)
                added_sources.append(_source_to_dict(src))
            except Exception as exc:
                _err(f"Warning: Failed to add text source: {exc}")
                added_sources.append({"title": text_title, "error": str(exc)})

        _err(f"Notebook created: {nb_id}")
        _json_out({
            "status": "ok",
            "action": "create",
            "notebook": _notebook_to_dict(nb),
            "sources_added": added_sources,
        })


async def cmd_list(_args) -> None:
    """List all notebooks."""
    from notebooklm import NotebookLMClient

    async with await NotebookLMClient.from_storage() as client:
        _err("Listing notebooks...")
        try:
            notebooks = await client.notebooks.list()
        except Exception as exc:
            _json_error(f"Failed to list notebooks: {exc}", "LIST_ERROR")

        nb_list = [_notebook_to_dict(nb) for nb in (notebooks or [])]
        _err(f"Found {len(nb_list)} notebook(s).")
        _json_out({
            "status": "ok",
            "action": "list",
            "count": len(nb_list),
            "notebooks": nb_list,
        })


async def cmd_delete(args) -> None:
    """Delete a notebook."""
    from notebooklm import NotebookLMClient

    async with await NotebookLMClient.from_storage() as client:
        _err(f"Finding notebook '{args.notebook}'...")
        nb = await _find_notebook(client, args.notebook)
        nb_id = nb.id
        nb_title = nb.title

        _err(f"Deleting notebook '{nb_title}' ({nb_id})...")
        try:
            ok = await client.notebooks.delete(notebook_id=nb_id)
        except Exception as exc:
            _json_error(f"Failed to delete notebook: {exc}", "DELETE_ERROR")

        _err(f"Notebook deleted: {nb_title}")
        _json_out({
            "status": "ok",
            "action": "delete",
            "notebook_id": nb_id,
            "title": nb_title,
            "deleted": bool(ok),
        })


async def cmd_add_source(args) -> None:
    """Add a source (URL, text, or file) to an existing notebook."""
    from notebooklm import NotebookLMClient

    async with await NotebookLMClient.from_storage() as client:
        _err(f"Finding notebook '{args.notebook}'...")
        nb = await _find_notebook(client, args.notebook)
        nb_id = nb.id

        try:
            if args.url:
                _err(f"Adding URL source: {args.url}")
                src = await client.sources.add_url(nb_id, args.url, wait=True, wait_timeout=120)
            elif args.file:
                _err(f"Adding file source: {args.file}")
                src = await client.sources.add_file(nb_id, file_path=args.file, wait=True)
            elif args.text:
                text_title = args.text_title or "Text Source"
                _err(f"Adding text source: {text_title}")
                src = await client.sources.add_text(nb_id, title=text_title, content=args.text, wait=True)
            else:
                _json_error("Provide one of --url, --file, or --text.", "NO_SOURCE")
        except Exception as exc:
            _json_error(f"Failed to add source: {exc}", "ADD_SOURCE_ERROR")

        _err("Source added.")
        _json_out({
            "status": "ok",
            "action": "add-source",
            "notebook_id": nb_id,
            "source": _source_to_dict(src),
        })


async def cmd_ask(args) -> None:
    """Ask a question against a notebook."""
    from notebooklm import NotebookLMClient

    if not args.query:
        _json_error("--query is required.", "MISSING_QUERY")

    async with await NotebookLMClient.from_storage() as client:
        _err(f"Finding notebook '{args.notebook}'...")
        nb = await _find_notebook(client, args.notebook)
        nb_id = nb.id

        _err(f"Asking: {args.query[:80]}...")
        try:
            result = await client.chat.ask(nb_id, question=args.query)
        except Exception as exc:
            _json_error(f"Failed to ask question: {exc}", "ASK_ERROR")

        references = _serialize(result.references) if result.references else []

        _json_out({
            "status": "ok",
            "action": "ask",
            "notebook_id": nb_id,
            "query": args.query,
            "answer": result.answer,
            "references": references,
            "conversation_id": result.conversation_id,
        })


async def cmd_summarize(args) -> None:
    """Get the notebook summary via the dedicated API."""
    from notebooklm import NotebookLMClient

    async with await NotebookLMClient.from_storage() as client:
        _err(f"Finding notebook '{args.notebook}'...")
        nb = await _find_notebook(client, args.notebook)
        nb_id = nb.id

        _err("Getting notebook summary...")
        try:
            summary = await client.notebooks.get_summary(notebook_id=nb_id)
        except Exception as exc:
            _json_error(f"Failed to get summary: {exc}", "SUMMARIZE_ERROR")

        _json_out({
            "status": "ok",
            "action": "summarize",
            "notebook_id": nb_id,
            "summary": summary,
        })


async def cmd_generate(args) -> None:
    """Generate an artifact from a notebook.

    Supports: audio, video, cinematic, slides, report, quiz, flashcards,
    mind-map, infographic, data-table, study-guide.
    """
    from notebooklm import NotebookLMClient

    artifact_type = args.type
    if artifact_type not in ARTIFACT_TYPES:
        _json_error(
            f"Unknown artifact type '{artifact_type}'. "
            f"Supported: {', '.join(ARTIFACT_TYPES.keys())}",
            "INVALID_TYPE",
        )

    gen_method_name, dl_method_name, default_ext = ARTIFACT_TYPES[artifact_type]

    async with await NotebookLMClient.from_storage() as client:
        _err(f"Finding notebook '{args.notebook}'...")
        nb = await _find_notebook(client, args.notebook)
        nb_id = nb.id

        # Build generation kwargs
        gen_kwargs = {"notebook_id": nb_id}

        # Language parameter (most generate methods accept it)
        lang = _normalize_lang(getattr(args, "lang", None) or "en")
        if artifact_type in ("audio", "video", "cinematic", "slides", "report",
                             "infographic", "data-table", "study-guide"):
            gen_kwargs["language"] = lang

        # Instructions parameter
        instructions = getattr(args, "instructions", None)
        if instructions and artifact_type in ("audio", "video", "cinematic", "slides",
                                               "quiz", "flashcards", "infographic",
                                               "data-table"):
            gen_kwargs["instructions"] = instructions

        # Report format (only for report type)
        if artifact_type == "report":
            gen_kwargs["report_format"] = getattr(args, "report_format", None) or "briefing_doc"

        _err(f"Generating {artifact_type}... (this may take a few minutes)")

        gen_method = getattr(client.artifacts, gen_method_name)

        try:
            status = await gen_method(**gen_kwargs)
        except Exception as exc:
            _json_error(f"Failed to generate {artifact_type}: {exc}", "GENERATE_ERROR")

        # mind-map returns immediately (dict), others return GenerationStatus
        if artifact_type == "mind-map":
            result_data = _serialize(status)
            _err("Mind map generated.")
        else:
            # Wait for completion
            task_id = status.task_id
            _err(f"Task started: {task_id}. Waiting for completion...")
            try:
                final = await client.artifacts.wait_for_completion(nb_id, task_id, timeout=3600)
                result_data = _serialize(final)
            except Exception as exc:
                _json_error(f"Artifact generation timed out or failed: {exc}", "TIMEOUT_ERROR")
            _err(f"{artifact_type.capitalize()} generation complete.")

        output = {
            "status": "ok",
            "action": "generate",
            "artifact_type": artifact_type,
            "notebook_id": nb_id,
            "result": result_data,
        }

        # Auto-download if --output is specified
        output_path = getattr(args, "output", None)
        if output_path and dl_method_name:
            _err(f"Downloading to {output_path}...")
            try:
                dl_method = getattr(client.artifacts, dl_method_name)
                dl_kwargs = {"notebook_id": nb_id, "output_path": output_path}
                fmt = getattr(args, "output_format", None)
                if fmt and artifact_type in ("slides", "quiz", "flashcards"):
                    dl_kwargs["output_format"] = fmt
                path = await dl_method(**dl_kwargs)
                output["downloaded_to"] = str(path)
                _err(f"Downloaded to {path}")
            except Exception as exc:
                _err(f"Warning: Download failed: {exc}")
                output["download_error"] = str(exc)

        _json_out(output)


async def cmd_download(args) -> None:
    """Download a previously generated artifact."""
    from notebooklm import NotebookLMClient

    artifact_type = args.type
    if artifact_type not in ARTIFACT_TYPES:
        _json_error(
            f"Unknown artifact type '{artifact_type}'. "
            f"Supported: {', '.join(ARTIFACT_TYPES.keys())}",
            "INVALID_TYPE",
        )

    _, dl_method_name, default_ext = ARTIFACT_TYPES[artifact_type]
    if not dl_method_name:
        _json_error(f"Download not supported for artifact type '{artifact_type}'.", "NOT_SUPPORTED")

    output_path = args.output
    if not output_path:
        _json_error("--output is required for download.", "MISSING_OUTPUT")

    async with await NotebookLMClient.from_storage() as client:
        _err(f"Finding notebook '{args.notebook}'...")
        nb = await _find_notebook(client, args.notebook)
        nb_id = nb.id

        _err(f"Downloading {artifact_type} to {output_path}...")
        try:
            dl_method = getattr(client.artifacts, dl_method_name)
            dl_kwargs = {"notebook_id": nb_id, "output_path": output_path}
            fmt = getattr(args, "output_format", None)
            if fmt and artifact_type in ("slides", "quiz", "flashcards"):
                dl_kwargs["output_format"] = fmt
            path = await dl_method(**dl_kwargs)
        except Exception as exc:
            _json_error(f"Failed to download {artifact_type}: {exc}", "DOWNLOAD_ERROR")

        _err(f"Downloaded to {path}")
        _json_out({
            "status": "ok",
            "action": "download",
            "artifact_type": artifact_type,
            "notebook_id": nb_id,
            "output_path": str(path),
        })


async def cmd_research(args) -> None:
    """Run deep web research on a topic within a notebook."""
    from notebooklm import NotebookLMClient

    async with await NotebookLMClient.from_storage() as client:
        _err(f"Finding notebook '{args.notebook}'...")
        nb = await _find_notebook(client, args.notebook)
        nb_id = nb.id

        mode = getattr(args, "mode", None) or "fast"
        _err(f"Starting research on '{args.query}' (mode={mode})...")

        try:
            result = await client.research.start(nb_id, query=args.query, source="web", mode=mode)
        except Exception as exc:
            _json_error(f"Failed to start research: {exc}", "RESEARCH_ERROR")

        # Poll until complete
        _err("Polling for research results...")
        try:
            for _ in range(120):  # up to ~10 minutes at 5s intervals
                status = await client.research.poll(nb_id)
                state = status.get("state") or status.get("status") if isinstance(status, dict) else str(status)
                if isinstance(status, dict) and status.get("state") in ("completed", "done", "COMPLETED"):
                    break
                _err(f"Research status: {state}...")
                await asyncio.sleep(5)
        except Exception as exc:
            _err(f"Warning: Polling failed: {exc}")

        _json_out({
            "status": "ok",
            "action": "research",
            "notebook_id": nb_id,
            "query": args.query,
            "mode": mode,
            "result": _serialize(result),
            "final_status": _serialize(status) if "status" in dir() else None,
        })


async def cmd_podcast(args) -> None:
    """Alias: generate audio overview and download it."""
    from notebooklm import NotebookLMClient

    async with await NotebookLMClient.from_storage() as client:
        _err(f"Finding notebook '{args.notebook}'...")
        nb = await _find_notebook(client, args.notebook)
        nb_id = nb.id

        lang = _normalize_lang(getattr(args, "lang", None) or "en")
        instructions = getattr(args, "instructions", None)

        gen_kwargs = {"notebook_id": nb_id, "language": lang}
        if instructions:
            gen_kwargs["instructions"] = instructions

        _err("Generating audio overview... (this may take a few minutes)")
        try:
            status = await client.artifacts.generate_audio(**gen_kwargs)
        except Exception as exc:
            _json_error(f"Failed to generate podcast: {exc}", "PODCAST_ERROR")

        task_id = status.task_id
        _err(f"Task started: {task_id}. Waiting for completion...")
        try:
            final = await client.artifacts.wait_for_completion(nb_id, task_id, timeout=3600)
        except Exception as exc:
            _json_error(f"Podcast generation timed out or failed: {exc}", "TIMEOUT_ERROR")

        _err("Audio generation complete.")

        output = {
            "status": "ok",
            "action": "podcast",
            "notebook_id": nb_id,
            "language": lang,
            "result": _serialize(final),
        }

        # Auto-download if --output specified
        output_path = getattr(args, "output", None)
        if output_path:
            _err(f"Downloading podcast to {output_path}...")
            try:
                path = await client.artifacts.download_audio(nb_id, output_path=output_path)
                output["downloaded_to"] = str(path)
                _err(f"Downloaded to {path}")
            except Exception as exc:
                _err(f"Warning: Download failed: {exc}")
                output["download_error"] = str(exc)

        _json_out(output)


async def cmd_qa(args) -> None:
    """Alias: generate a quiz from notebook content."""
    from notebooklm import NotebookLMClient

    async with await NotebookLMClient.from_storage() as client:
        _err(f"Finding notebook '{args.notebook}'...")
        nb = await _find_notebook(client, args.notebook)
        nb_id = nb.id

        instructions = getattr(args, "instructions", None)
        gen_kwargs = {"notebook_id": nb_id}
        if instructions:
            gen_kwargs["instructions"] = instructions

        _err("Generating quiz...")
        try:
            status = await client.artifacts.generate_quiz(**gen_kwargs)
        except Exception as exc:
            _json_error(f"Failed to generate quiz: {exc}", "QA_ERROR")

        task_id = status.task_id
        _err(f"Task started: {task_id}. Waiting for completion...")
        try:
            final = await client.artifacts.wait_for_completion(nb_id, task_id, timeout=3600)
        except Exception as exc:
            _json_error(f"Quiz generation timed out or failed: {exc}", "TIMEOUT_ERROR")

        _err("Quiz generation complete.")

        output = {
            "status": "ok",
            "action": "qa",
            "notebook_id": nb_id,
            "result": _serialize(final),
        }

        # Auto-download if --output specified
        output_path = getattr(args, "output", None)
        if output_path:
            _err(f"Downloading quiz to {output_path}...")
            try:
                fmt = getattr(args, "output_format", None) or "json"
                path = await client.artifacts.download_quiz(
                    nb_id, output_path=output_path, output_format=fmt
                )
                output["downloaded_to"] = str(path)
                _err(f"Downloaded to {path}")
            except Exception as exc:
                _err(f"Warning: Download failed: {exc}")
                output["download_error"] = str(exc)

        _json_out(output)


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------

def main() -> None:
    parser = argparse.ArgumentParser(
        description="NotebookLM Client - CLI wrapper for notebooklm-py v0.3.4",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
    %(prog)s create --title "My Research" --sources https://example.com/article
    %(prog)s create --title "Notes" --text-sources "Raw text content here"
    %(prog)s list
    %(prog)s add-source --notebook "My Research" --url https://example.com/page2
    %(prog)s add-source --notebook "My Research" --file doc.pdf
    %(prog)s add-source --notebook "My Research" --text "Some notes" --text-title "My Notes"
    %(prog)s ask --notebook "My Research" --query "What are the key points?"
    %(prog)s summarize --notebook "My Research"
    %(prog)s generate --notebook "My Research" --type audio --lang en --output podcast.m4a
    %(prog)s generate --notebook "My Research" --type slides --output slides.pdf
    %(prog)s generate --notebook "My Research" --type report --output report.md
    %(prog)s generate --notebook "My Research" --type mind-map
    %(prog)s download --notebook "My Research" --type audio --output podcast.m4a
    %(prog)s podcast --notebook "My Research" --lang zh-TW --output podcast.m4a
    %(prog)s qa --notebook "My Research" --output quiz.json
    %(prog)s research --notebook "My Research" --query "latest trends" --mode fast
    %(prog)s delete --notebook "My Research"
        """,
    )

    subparsers = parser.add_subparsers(dest="command", help="Command to run")

    # create
    p_create = subparsers.add_parser("create", help="Create a notebook with optional sources")
    p_create.add_argument("--title", default="Untitled Research", help="Notebook title")
    p_create.add_argument("--sources", nargs="*", default=[], help="URL sources to add")
    p_create.add_argument("--text-sources", nargs="*", default=[], help="Raw text content to add as sources")

    # list
    subparsers.add_parser("list", help="List all notebooks")

    # delete
    p_delete = subparsers.add_parser("delete", help="Delete a notebook")
    p_delete.add_argument("--notebook", required=True, help="Notebook name or ID")

    # add-source
    p_add = subparsers.add_parser("add-source", help="Add a source to an existing notebook")
    p_add.add_argument("--notebook", required=True, help="Notebook name or ID")
    p_add_group = p_add.add_mutually_exclusive_group(required=True)
    p_add_group.add_argument("--url", help="URL to add as source")
    p_add_group.add_argument("--file", help="File path to add as source (e.g., doc.pdf)")
    p_add_group.add_argument("--text", help="Text content to add as source")
    p_add.add_argument("--text-title", default="Text Source", help="Title for text source (used with --text)")

    # ask
    p_ask = subparsers.add_parser("ask", help="Ask a question against a notebook")
    p_ask.add_argument("--notebook", required=True, help="Notebook name or ID")
    p_ask.add_argument("--query", required=True, help="Question to ask")

    # summarize
    p_summarize = subparsers.add_parser("summarize", help="Get the notebook summary")
    p_summarize.add_argument("--notebook", required=True, help="Notebook name or ID")

    # generate
    p_gen = subparsers.add_parser("generate", help="Generate an artifact from a notebook")
    p_gen.add_argument("--notebook", required=True, help="Notebook name or ID")
    p_gen.add_argument(
        "--type", required=True,
        choices=list(ARTIFACT_TYPES.keys()),
        help="Type of artifact to generate",
    )
    p_gen.add_argument("--lang", default="en", help="Language code (default: en)")
    p_gen.add_argument("--instructions", default=None, help="Custom instructions for generation")
    p_gen.add_argument("--output", default=None, help="Output file path (auto-download after generation)")
    p_gen.add_argument("--output-format", default=None, help="Output format: slides=pdf/pptx, quiz/flashcards=json/markdown/html")
    p_gen.add_argument("--report-format", default="briefing_doc", help="Report format (for --type report)")

    # download
    p_dl = subparsers.add_parser("download", help="Download a previously generated artifact")
    p_dl.add_argument("--notebook", required=True, help="Notebook name or ID")
    p_dl.add_argument(
        "--type", required=True,
        choices=list(ARTIFACT_TYPES.keys()),
        help="Type of artifact to download",
    )
    p_dl.add_argument("--output", required=True, help="Output file path")
    p_dl.add_argument("--output-format", default=None, help="Output format: slides=pdf/pptx, quiz/flashcards=json/markdown/html")

    # research
    p_research = subparsers.add_parser("research", help="Run deep web research on a topic")
    p_research.add_argument("--notebook", required=True, help="Notebook name or ID")
    p_research.add_argument("--query", required=True, help="Research query/topic")
    p_research.add_argument("--mode", choices=["fast", "deep"], default="fast", help="Research mode (default: fast)")

    # podcast (alias for generate --type audio + download)
    p_podcast = subparsers.add_parser("podcast", help="Generate and download audio overview (alias)")
    p_podcast.add_argument("--notebook", required=True, help="Notebook name or ID")
    p_podcast.add_argument("--lang", default="en", help="Language code (default: en)")
    p_podcast.add_argument("--instructions", default=None, help="Custom instructions")
    p_podcast.add_argument("--output", default=None, help="Output file path for downloaded audio")

    # qa (alias for generate --type quiz)
    p_qa = subparsers.add_parser("qa", help="Generate quiz from notebook content (alias)")
    p_qa.add_argument("--notebook", required=True, help="Notebook name or ID")
    p_qa.add_argument("--instructions", default=None, help="Custom instructions")
    p_qa.add_argument("--output", default=None, help="Output file path for downloaded quiz")
    p_qa.add_argument("--output-format", default=None, help="Output format: json (default), markdown, or html")

    args = parser.parse_args()

    if not args.command:
        parser.print_help()
        sys.exit(1)

    command_map = {
        "create": cmd_create,
        "list": cmd_list,
        "delete": cmd_delete,
        "add-source": cmd_add_source,
        "ask": cmd_ask,
        "summarize": cmd_summarize,
        "generate": cmd_generate,
        "download": cmd_download,
        "research": cmd_research,
        "podcast": cmd_podcast,
        "qa": cmd_qa,
    }

    handler = command_map[args.command]

    try:
        asyncio.run(handler(args))
    except KeyboardInterrupt:
        _json_error("Operation cancelled by user.", "CANCELLED")
    except Exception as exc:
        _json_error(f"Unexpected error: {exc}", "UNEXPECTED_ERROR")


if __name__ == "__main__":
    main()
