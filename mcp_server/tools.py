"""NotebookLM operations exposed by the MCP server."""

from __future__ import annotations

import asyncio
from pathlib import Path
from typing import Any

from scripts.common import (
    ARTIFACT_SPECS,
    UsageError,
    fetch_trends,
    get_client,
    ingest_sources,
    resolve_notebook,
    run_research,
    serialize,
    serialize_notebook,
    serialize_source,
    source_result_summary,
    validate_url,
)
from scripts.common import (
    download_artifact as core_download_artifact,
)
from scripts.common import (
    generate_artifact as core_generate_artifact,
)
from scripts.common import (
    list_artifacts as core_list_artifacts,
)


async def create_notebook(
    title: str,
    sources: list[str] | None = None,
    text_sources: list[str] | None = None,
    file_sources: list[str] | None = None,
) -> dict[str, Any]:
    """Create a notebook and ingest mixed sources with truthful status counts."""
    if not title.strip():
        raise UsageError("Notebook title cannot be empty.")
    async with get_client() as client:
        notebook = await client.notebooks.create(title=title.strip())
        results = await ingest_sources(
            client,
            notebook.id,
            urls=sources or (),
            texts=text_sources or (),
            files=file_sources or (),
        )
        summary = source_result_summary(results)
        notebook.sources_count = summary["succeeded"]
        status = "ok"
        if summary["failed"]:
            status = "failed" if summary["succeeded"] == 0 else "partial"
        return {
            "status": status,
            "notebook": serialize_notebook(notebook),
            "source_summary": summary,
            "sources": results,
        }


async def list_notebooks() -> dict[str, Any]:
    """List all notebooks."""
    async with get_client() as client:
        notebooks = list(await client.notebooks.list() or [])
        return {
            "status": "ok",
            "notebooks": [serialize_notebook(item) for item in notebooks],
            "count": len(notebooks),
        }


async def delete_notebook(name_or_id: str) -> dict[str, Any]:
    """Delete a notebook; current notebooklm-py returns ``None`` on success."""
    async with get_client() as client:
        notebook = await resolve_notebook(client, name_or_id)
        await client.notebooks.delete(notebook_id=notebook.id)
        return {
            "status": "ok",
            "deleted": True,
            "notebook": serialize_notebook(notebook),
        }


async def add_source(
    name_or_id: str,
    url: str | None = None,
    text: str | None = None,
    text_title: str | None = None,
    file_path: str | None = None,
) -> dict[str, Any]:
    """Add exactly one URL, text, or local file source."""
    provided = [value is not None for value in (url, text, file_path)]
    if sum(provided) != 1:
        raise UsageError("Provide exactly one of url, text, or file_path.")

    async with get_client() as client:
        notebook = await resolve_notebook(client, name_or_id)
        if url is not None:
            source = await client.sources.add_url(notebook.id, validate_url(url), wait=True, wait_timeout=180)
        elif text is not None:
            if not text.strip():
                raise UsageError("Text source cannot be empty.")
            source = await client.sources.add_text(
                notebook.id,
                title=(text_title or "Text Source").strip() or "Text Source",
                content=text,
                wait=True,
                wait_timeout=180,
            )
        else:
            path = Path(file_path or "").expanduser()
            if not path.is_file():
                raise UsageError(f"Source file not found: {path}")
            source = await client.sources.add_file(notebook.id, file_path=path, wait=True, wait_timeout=180)
        return {
            "status": "ok",
            "notebook_id": notebook.id,
            "source": serialize_source(source),
        }


async def ask(name_or_id: str, query: str) -> dict[str, Any]:
    """Ask a question and preserve typed citation metadata."""
    if not query.strip():
        raise UsageError("Query cannot be empty.")
    async with get_client() as client:
        notebook = await resolve_notebook(client, name_or_id)
        result = await client.chat.ask(notebook.id, question=query.strip())
        return {
            "status": "ok",
            "notebook_id": notebook.id,
            "answer": result.answer,
            "references": serialize(getattr(result, "references", ()) or ()),
            "conversation_id": getattr(result, "conversation_id", None),
        }


async def summarize(name_or_id: str) -> dict[str, Any]:
    """Return the notebook summary."""
    async with get_client() as client:
        notebook = await resolve_notebook(client, name_or_id)
        summary = await client.notebooks.get_summary(notebook_id=notebook.id)
        return {"status": "ok", "notebook_id": notebook.id, "summary": summary}


async def list_sources(name_or_id: str) -> dict[str, Any]:
    """List notebook sources."""
    async with get_client() as client:
        notebook = await resolve_notebook(client, name_or_id)
        sources = list(await client.sources.list(notebook.id) or [])
        return {
            "status": "ok",
            "notebook_id": notebook.id,
            "sources": [serialize_source(item) for item in sources],
            "count": len(sources),
        }


async def list_artifacts(name_or_id: str, artifact_type: str | None = None) -> dict[str, Any]:
    """List actual generated artifacts, optionally filtered by type."""
    async with get_client() as client:
        notebook = await resolve_notebook(client, name_or_id)
        artifacts = await core_list_artifacts(client, notebook.id, artifact_type)
        return {
            "status": "ok",
            "notebook_id": notebook.id,
            "artifact_type": artifact_type,
            "artifacts": artifacts,
            "count": len(artifacts),
        }


async def generate_artifact(
    name_or_id: str,
    artifact_type: str,
    lang: str = "en",
    instructions: str | None = None,
    source_ids: list[str] | None = None,
    options: dict[str, str] | None = None,
    wait: bool = True,
    timeout: float | None = None,
) -> dict[str, Any]:
    """Generate any canonical artifact type with validated options."""
    async with get_client() as client:
        notebook = await resolve_notebook(client, name_or_id)
        result = await core_generate_artifact(
            client,
            notebook.id,
            artifact_type,
            language=lang,
            instructions=instructions,
            source_ids=source_ids,
            options=options,
            wait=wait,
            timeout=timeout,
        )
        result["notebook_id"] = notebook.id
        return result


async def download_artifact(
    name_or_id: str,
    artifact_type: str,
    output_path: str,
    output_format: str | None = None,
    artifact_id: str | None = None,
    force: bool = False,
) -> dict[str, Any]:
    """Download an exact or latest artifact without silent overwrites."""
    async with get_client() as client:
        notebook = await resolve_notebook(client, name_or_id)
        path = await core_download_artifact(
            client,
            notebook.id,
            artifact_type,
            output_path,
            artifact_id=artifact_id,
            output_format=output_format,
            force=force,
        )
        return {
            "status": "ok",
            "notebook_id": notebook.id,
            "artifact_type": artifact_type,
            "artifact_id": artifact_id,
            "output_path": path,
        }


async def research(
    name_or_id: str,
    query: str,
    mode: str = "fast",
    wait: bool = True,
    import_results: bool = True,
    max_sources: int = 10,
    timeout: float = 1800,
) -> dict[str, Any]:
    """Run a complete research lifecycle and optionally import findings."""
    async with get_client() as client:
        notebook = await resolve_notebook(client, name_or_id)
        result = await run_research(
            client,
            notebook.id,
            query,
            mode=mode,
            wait=wait,
            import_results=import_results,
            max_sources=max_sources,
            timeout=timeout,
        )
        result["notebook_id"] = notebook.id
        return result


async def research_pipeline(
    sources: list[str],
    questions: list[str],
    output_format: str = "article",
    title: str | None = None,
) -> dict[str, Any]:
    """Create a notebook, ingest sources, ask questions, and assemble content."""
    if not sources:
        raise UsageError("At least one source URL is required.")
    if not questions or any(not question.strip() for question in questions):
        raise UsageError("At least one non-empty research question is required.")
    if output_format not in {"article", "thread", "report"}:
        raise UsageError("output_format must be article, thread, or report.")
    if len(sources) > 50 or len(questions) > 25:
        raise UsageError("A pipeline supports at most 50 sources and 25 questions.")

    async with get_client() as client:
        notebook = await client.notebooks.create(title=(title or f"Research: {output_format}").strip())
        added = await ingest_sources(client, notebook.id, urls=sources)
        source_summary = source_result_summary(added)
        if source_summary["succeeded"] == 0:
            return {
                "status": "failed",
                "notebook": serialize_notebook(notebook),
                "source_summary": source_summary,
                "sources": added,
                "error": "No sources were ingested; questions were not sent.",
            }

        semaphore = asyncio.Semaphore(4)

        async def ask_one(question: str) -> dict[str, Any]:
            async with semaphore:
                try:
                    result = await client.chat.ask(notebook.id, question=question.strip())
                    return {
                        "status": "ok",
                        "question": question.strip(),
                        "answer": result.answer,
                        "references": serialize(getattr(result, "references", ()) or ()),
                    }
                except Exception as exc:
                    return {
                        "status": "failed",
                        "question": question.strip(),
                        "error": str(exc),
                    }

        answers = await asyncio.gather(*(ask_one(question) for question in questions))
        successful = [item for item in answers if item["status"] == "ok"]
        if output_format == "thread":
            content = "\n\n".join(f"{index}/ {item['answer']}" for index, item in enumerate(successful, 1))
        elif output_format == "report":
            content = "\n\n---\n\n".join(f"## {item['question']}\n\n{item['answer']}" for item in successful)
        else:
            content = "\n\n".join(item["answer"] for item in successful)
        status = "ok" if len(successful) == len(answers) else "partial"
        if not successful:
            status = "failed"
        return {
            "status": status,
            "notebook": serialize_notebook(notebook),
            "source_summary": source_summary,
            "sources": added,
            "answers": answers,
            "content": content,
            "output_format": output_format,
        }


async def trend_research(
    geo: str = "TW",
    count: int = 5,
    platform: str = "threads",
) -> dict[str, Any]:
    """Research current trend topics, import findings, then draft content."""
    limits = {"threads": 500, "twitter": 280, "instagram": 2200, "article": 5000}
    if platform not in limits:
        raise UsageError(f"Unsupported platform '{platform}'. Choose: {', '.join(limits)}")
    trend_items = await fetch_trends(geo, count)
    trends = [item["title"] for item in trend_items]
    if not trends:
        raise RuntimeError("trend-pulse returned no usable topics.")

    results: list[dict[str, Any]] = []
    async with get_client() as client:
        for topic in trends:
            item: dict[str, Any] = {"topic": topic, "platform": platform}
            try:
                notebook = await client.notebooks.create(title=f"Trend: {topic}")
                item["notebook_id"] = notebook.id
                item["research"] = await run_research(
                    client,
                    notebook.id,
                    topic,
                    mode="fast",
                    wait=True,
                    import_results=True,
                    max_sources=10,
                    timeout=900,
                )
                prompt = (
                    f"Create a {platform} draft about '{topic}' grounded only in this notebook. "
                    f"Keep the primary draft within {limits[platform]} characters and clearly "
                    "separate any optional alternatives."
                )
                answer = await client.chat.ask(notebook.id, question=prompt)
                content = answer.answer
                item.update(
                    {
                        "status": "ok",
                        "content": content,
                        "character_count": len(content),
                        "within_limit": len(content) <= limits[platform],
                        "references": serialize(getattr(answer, "references", ()) or ()),
                    }
                )
            except Exception as exc:
                item.update({"status": "failed", "error": str(exc)})
            results.append(item)
    failures = sum(item["status"] == "failed" for item in results)
    return {
        "status": "ok" if not failures else ("failed" if failures == len(results) else "partial"),
        "geo": geo,
        "platform": platform,
        "trends_processed": len(results),
        "results": results,
    }


SUPPORTED_ARTIFACT_TYPES = tuple(ARTIFACT_SPECS)
