#!/usr/bin/env python3
"""NotebookLM tool implementations using notebooklm-py v0.3.4.

Uses the NotebookLMClient async API directly — no subprocess calls.
All functions are async and return JSON-serializable dicts.
"""

import os
from contextlib import asynccontextmanager
from typing import Any

from notebooklm import NotebookLMClient

# ---------------------------------------------------------------------------
# Shared client helper
# ---------------------------------------------------------------------------


@asynccontextmanager
async def _get_client():
    """Create a NotebookLMClient from stored credentials.

    Uses ``NotebookLMClient.from_storage()`` which reads cookies/tokens
    from the default storage location (~/.notebooklm/).
    """
    async with await NotebookLMClient.from_storage() as client:
        yield client


# ---------------------------------------------------------------------------
# Notebook resolution helper
# ---------------------------------------------------------------------------


async def _resolve_notebook(client: NotebookLMClient, name_or_id: str) -> str:
    """Resolve a notebook name or ID to a notebook ID.

    If *name_or_id* looks like a raw ID (no spaces, hex-ish), return it
    directly. Otherwise, list all notebooks and find a fuzzy match by title.

    Returns:
        The notebook ID string.

    Raises:
        ValueError: If no matching notebook is found.
    """
    # Fast path: if it looks like an ID (contains only hex-safe chars or dashes)
    # try to use it directly
    clean = name_or_id.strip()

    # If it contains spaces or is clearly a title, do a lookup
    if " " in clean or len(clean) > 60:
        return await _lookup_by_title(client, clean)

    # Try as ID first — if the API accepts it, great
    try:
        nb = await client.notebooks.get(notebook_id=clean)
        return nb.id
    except Exception:
        pass

    # Fall back to title lookup
    return await _lookup_by_title(client, clean)


async def _lookup_by_title(client: NotebookLMClient, title: str) -> str:
    """Find a notebook by fuzzy title match."""
    notebooks = await client.notebooks.list()
    title_lower = title.lower()

    # Exact match first
    for nb in notebooks:
        if nb.title.lower() == title_lower:
            return nb.id

    # Substring / contains match
    for nb in notebooks:
        if title_lower in nb.title.lower() or nb.title.lower() in title_lower:
            return nb.id

    available = ", ".join(f'"{nb.title}" ({nb.id})' for nb in notebooks[:10])
    raise ValueError(
        f'No notebook matching "{title}". '
        f"Available: {available or '(none)'}"
    )


# ---------------------------------------------------------------------------
# Serialization helpers
# ---------------------------------------------------------------------------


def _serialize_notebook(nb) -> dict[str, Any]:
    """Convert a Notebook object to a JSON-serializable dict."""
    return {
        "id": nb.id,
        "title": getattr(nb, "title", ""),
    }


def _serialize_source(src) -> dict[str, Any]:
    """Convert a Source object to a JSON-serializable dict."""
    result = {"id": getattr(src, "id", None)}
    for attr in ("title", "url", "type", "status"):
        val = getattr(src, attr, None)
        if val is not None:
            result[attr] = str(val)
    return result


def _serialize_ask_result(result) -> dict[str, Any]:
    """Convert an AskResult to a JSON-serializable dict."""
    data: dict[str, Any] = {"answer": result.answer}
    if hasattr(result, "references") and result.references:
        data["references"] = [
            {k: v for k, v in vars(c).items() if v is not None}
            if hasattr(c, "__dict__")
            else str(c)
            for c in result.references
        ]
    if hasattr(result, "conversation_id"):
        data["conversation_id"] = result.conversation_id
    return data


# ---------------------------------------------------------------------------
# Core tools
# ---------------------------------------------------------------------------


async def create_notebook(
    title: str,
    sources: list[str] | None = None,
    text_sources: list[str] | None = None,
) -> dict[str, Any]:
    """Create a NotebookLM notebook, optionally adding URL and text sources."""
    async with _get_client() as client:
        nb = await client.notebooks.create(title=title)
        added_sources = []

        # Add URL sources
        for url in (sources or []):
            try:
                src = await client.sources.add_url(nb.id, url, wait=True)
                added_sources.append(_serialize_source(src))
            except Exception as exc:
                added_sources.append({"url": url, "error": str(exc)})

        # Add text sources
        for i, text in enumerate(text_sources or []):
            text_title = f"Text Source {i + 1}"
            try:
                src = await client.sources.add_text(nb.id, text_title, text, wait=True)
                added_sources.append(_serialize_source(src))
            except Exception as exc:
                added_sources.append({"text_title": text_title, "error": str(exc)})

        return {
            "status": "ok",
            "notebook": _serialize_notebook(nb),
            "sources_added": added_sources,
            "source_count": len(added_sources),
        }


async def list_notebooks() -> dict[str, Any]:
    """List all notebooks in the account."""
    async with _get_client() as client:
        notebooks = await client.notebooks.list()
        return {
            "status": "ok",
            "notebooks": [_serialize_notebook(nb) for nb in notebooks],
            "count": len(notebooks),
        }


async def delete_notebook(name_or_id: str) -> dict[str, Any]:
    """Delete a notebook by name or ID."""
    async with _get_client() as client:
        notebook_id = await _resolve_notebook(client, name_or_id)
        ok = await client.notebooks.delete(notebook_id=notebook_id)
        return {
            "status": "ok" if ok else "failed",
            "deleted": notebook_id,
        }


async def add_source(
    name_or_id: str,
    url: str | None = None,
    text: str | None = None,
    text_title: str | None = None,
    file_path: str | None = None,
) -> dict[str, Any]:
    """Add a source (URL, text, or file) to an existing notebook."""
    async with _get_client() as client:
        notebook_id = await _resolve_notebook(client, name_or_id)

        if url:
            src = await client.sources.add_url(notebook_id, url, wait=True)
        elif text:
            title = text_title or "Text Source"
            src = await client.sources.add_text(notebook_id, title, text, wait=True)
        elif file_path:
            src = await client.sources.add_file(notebook_id, file_path, wait=True)
        else:
            return {"status": "failed", "error": "Provide url, text, or file_path"}

        return {
            "status": "ok",
            "notebook_id": notebook_id,
            "source": _serialize_source(src),
        }


async def ask(name_or_id: str, query: str) -> dict[str, Any]:
    """Ask a question against a notebook's sources."""
    async with _get_client() as client:
        notebook_id = await _resolve_notebook(client, name_or_id)
        result = await client.chat.ask(notebook_id, question=query)
        return {
            "status": "ok",
            "notebook_id": notebook_id,
            **_serialize_ask_result(result),
        }


async def summarize(name_or_id: str) -> dict[str, Any]:
    """Generate a summary of a notebook's content."""
    async with _get_client() as client:
        notebook_id = await _resolve_notebook(client, name_or_id)
        summary = await client.notebooks.get_summary(notebook_id=notebook_id)
        return {
            "status": "ok",
            "notebook_id": notebook_id,
            "summary": summary,
        }


# ---------------------------------------------------------------------------
# Artifact tools
# ---------------------------------------------------------------------------

# Maps user-facing type names to generate method names
_ARTIFACT_GENERATORS = {
    "audio": "generate_audio",
    "video": "generate_video",
    "slides": "generate_slide_deck",
    "report": "generate_report",
    "quiz": "generate_quiz",
    "flashcards": "generate_flashcards",
    "mind-map": "generate_mind_map",
    "infographic": "generate_infographic",
    "data-table": "generate_data_table",
    "study-guide": "generate_study_guide",
}

# Maps types to (download_method, supports_output_format)
_ARTIFACT_DOWNLOADERS = {
    "audio":       ("download_audio",       False),
    "video":       ("download_video",       False),
    "slides":      ("download_slide_deck",  True),
    "report":      ("download_report",      False),
    "study-guide": ("download_report",      False),   # study-guide is a report subtype
    "quiz":        ("download_quiz",        True),
    "flashcards":  ("download_flashcards",  True),
    "mind-map":    ("download_mind_map",    False),
    "infographic": ("download_infographic", False),
    "data-table":  ("download_data_table",  False),
}


async def generate_artifact(
    name_or_id: str,
    artifact_type: str,
    lang: str = "en",
    instructions: str | None = None,
) -> dict[str, Any]:
    """Generate an artifact (audio, video, slides, report, quiz, etc.)."""
    if artifact_type not in _ARTIFACT_GENERATORS:
        return {
            "status": "failed",
            "error": f"Unknown artifact type '{artifact_type}'. "
            f"Supported: {', '.join(_ARTIFACT_GENERATORS.keys())}",
        }

    async with _get_client() as client:
        notebook_id = await _resolve_notebook(client, name_or_id)
        method = getattr(client.artifacts, _ARTIFACT_GENERATORS[artifact_type])

        # Build kwargs based on what each generator accepts.
        # See references/api_surface.md for full parameter lists.
        kwargs: dict[str, Any] = {}

        # language — accepted by most types except quiz, flashcards, mind-map
        if artifact_type in ("audio", "video", "slides", "report",
                             "infographic", "data-table", "study-guide"):
            kwargs["language"] = lang

        # instructions — parameter name varies by type
        if instructions:
            if artifact_type in ("audio", "video", "slides", "quiz",
                                 "flashcards", "infographic", "data-table"):
                kwargs["instructions"] = instructions
            elif artifact_type in ("report", "study-guide"):
                kwargs["extra_instructions"] = instructions

        # report_format — only for report type (default "briefing_doc")
        if artifact_type == "report":
            kwargs["report_format"] = "briefing_doc"

        status = await method(notebook_id, **kwargs)

        # mind-map returns a dict immediately, not a GenerationStatus
        if artifact_type == "mind-map":
            result: dict[str, Any] = {
                "status": "ok",
                "notebook_id": notebook_id,
                "artifact_type": artifact_type,
            }
            if isinstance(status, dict):
                for k, v in status.items():
                    result[k] = v
            return result

        # Wait for completion
        final = await client.artifacts.wait_for_completion(
            notebook_id, status.task_id, timeout=3600
        )

        result = {
            "status": "ok",
            "notebook_id": notebook_id,
            "artifact_type": artifact_type,
            "task_id": status.task_id,
        }
        # Serialize final status
        if hasattr(final, "__dict__"):
            for k, v in vars(final).items():
                if v is not None and k != "task_id":
                    result[k] = str(v) if not isinstance(v, (str, int, float, bool)) else v
        return result


async def download_artifact(
    name_or_id: str,
    artifact_type: str,
    output_path: str,
    output_format: str | None = None,
) -> dict[str, Any]:
    """Download a generated artifact to a local file."""
    if artifact_type not in _ARTIFACT_DOWNLOADERS:
        return {
            "status": "failed",
            "error": f"Download not supported for '{artifact_type}'. "
            f"Supported: {', '.join(_ARTIFACT_DOWNLOADERS.keys())}",
        }

    async with _get_client() as client:
        notebook_id = await _resolve_notebook(client, name_or_id)
        method_name, supports_format = _ARTIFACT_DOWNLOADERS[artifact_type]
        method = getattr(client.artifacts, method_name)

        kwargs: dict[str, Any] = {"output_path": output_path}
        if supports_format and output_format is not None:
            kwargs["output_format"] = output_format

        path = await method(notebook_id, **kwargs)
        return {
            "status": "ok",
            "notebook_id": notebook_id,
            "artifact_type": artifact_type,
            "output_path": str(path),
        }


async def list_sources(name_or_id: str) -> dict[str, Any]:
    """List all sources in a notebook (used as proxy for listing artifacts)."""
    async with _get_client() as client:
        notebook_id = await _resolve_notebook(client, name_or_id)
        sources = await client.sources.list(notebook_id)
        return {
            "status": "ok",
            "notebook_id": notebook_id,
            "sources": [_serialize_source(s) for s in sources],
            "count": len(sources),
        }


# ---------------------------------------------------------------------------
# Research tool
# ---------------------------------------------------------------------------


async def research(
    name_or_id: str,
    query: str,
    mode: str = "fast",
) -> dict[str, Any]:
    """Start a research query against a notebook and poll until done."""
    async with _get_client() as client:
        notebook_id = await _resolve_notebook(client, name_or_id)
        result = await client.research.start(
            notebook_id, query=query, source="web", mode=mode
        )

        # Poll until complete
        status = await client.research.poll(notebook_id)

        output: dict[str, Any] = {
            "status": "ok",
            "notebook_id": notebook_id,
            "query": query,
            "mode": mode,
        }
        # Serialize result and status
        for obj in (result, status):
            if hasattr(obj, "__dict__"):
                for k, v in vars(obj).items():
                    if v is not None:
                        output[k] = str(v) if not isinstance(v, (str, int, float, bool, list, dict)) else v
        return output


# ---------------------------------------------------------------------------
# Pipeline tools
# ---------------------------------------------------------------------------


async def research_pipeline(
    sources: list[str],
    questions: list[str],
    output_format: str = "article",
) -> dict[str, Any]:
    """Full research-to-content pipeline.

    Creates a notebook from sources, asks all questions, and assembles the
    answers into a structured output (article, thread, or report).
    """
    async with _get_client() as client:
        # 1. Create notebook
        nb = await client.notebooks.create(title=f"Research: {output_format}")
        notebook_id = nb.id

        # 2. Add sources
        added = []
        for url in sources:
            try:
                src = await client.sources.add_url(notebook_id, url, wait=True)
                added.append(_serialize_source(src))
            except Exception as exc:
                added.append({"url": url, "error": str(exc)})

        # 3. Ask each question
        answers = []
        for q in questions:
            try:
                result = await client.chat.ask(notebook_id, question=q)
                answers.append({
                    "question": q,
                    **_serialize_ask_result(result),
                })
            except Exception as exc:
                answers.append({"question": q, "error": str(exc)})

        # 4. Assemble content based on format
        if output_format == "thread":
            # Short-form: numbered points
            content_parts = []
            for i, a in enumerate(answers, 1):
                text = a.get("answer", a.get("error", ""))
                content_parts.append(f"{i}/ {text}")
            content = "\n\n".join(content_parts)
        elif output_format == "report":
            # Structured sections
            sections = []
            for a in answers:
                q = a.get("question", "")
                text = a.get("answer", a.get("error", ""))
                sections.append(f"## {q}\n\n{text}")
            content = "\n\n---\n\n".join(sections)
        else:
            # Article: flowing prose
            content_parts = []
            for a in answers:
                text = a.get("answer", a.get("error", ""))
                content_parts.append(text)
            content = "\n\n".join(content_parts)

        return {
            "status": "ok",
            "notebook_id": notebook_id,
            "sources_added": added,
            "answers": answers,
            "content": content,
            "output_format": output_format,
        }


async def trend_research(
    geo: str = "TW",
    count: int = 5,
    platform: str = "threads",
) -> dict[str, Any]:
    """Trending topics to researched content pipeline.

    Uses trend-pulse MCP (if available) or falls back to a web search,
    then for each topic creates a notebook, researches it, and generates
    platform-ready content.
    """
    # Try to get trends from trend-pulse
    trends: list[str] = []
    try:
        import json
        import subprocess

        trend_cmd = os.getenv("TREND_PULSE_CMD", "trend-pulse")
        result = subprocess.run(
            [trend_cmd, "trending", "--geo", geo, "--count", str(count), "--json"],
            capture_output=True,
            text=True,
            timeout=30,
        )
        if result.returncode == 0 and result.stdout.strip():
            data = json.loads(result.stdout.strip())
            if isinstance(data, list):
                trends = [t.get("title", t) if isinstance(t, dict) else str(t) for t in data[:count]]
            elif isinstance(data, dict) and "trends" in data:
                trends = [t.get("title", t) if isinstance(t, dict) else str(t) for t in data["trends"][:count]]
    except Exception:
        pass

    if not trends:
        return {
            "status": "failed",
            "error": "Could not fetch trending topics. Install trend-pulse or set TREND_PULSE_CMD.",
        }

    # Research each trend
    results = []
    async with _get_client() as client:
        for topic in trends:
            try:
                nb = await client.notebooks.create(title=f"Trend: {topic}")

                # Research the topic
                try:
                    await client.research.start(
                        nb.id, query=topic, source="web", mode="fast"
                    )
                    await client.research.poll(nb.id)
                except Exception:
                    pass  # Research may not be available

                # Generate a question and ask it
                question = f"What are the key points and latest developments about: {topic}?"
                try:
                    answer = await client.chat.ask(nb.id, question=question)
                    text = answer.answer
                except Exception as exc:
                    text = f"(research failed: {exc})"

                # Format for target platform
                if platform == "threads":
                    formatted = text[:450] if text else ""  # Thread-length
                elif platform == "instagram":
                    formatted = text[:2000] if text else ""
                else:
                    formatted = text

                results.append({
                    "topic": topic,
                    "notebook_id": nb.id,
                    "content": formatted,
                    "platform": platform,
                })
            except Exception as exc:
                results.append({"topic": topic, "error": str(exc)})

    return {
        "status": "ok",
        "geo": geo,
        "trends_processed": len(results),
        "results": results,
    }
