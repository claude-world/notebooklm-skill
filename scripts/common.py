"""Shared NotebookLM operations for the CLI, pipelines, and MCP server.

This module is the compatibility boundary for ``notebooklm-py``.  Keeping API
adaptation here prevents the three public interfaces from drifting apart.
"""

from __future__ import annotations

import asyncio
import json
import os
import shlex
from collections.abc import Mapping, Sequence
from contextlib import asynccontextmanager
from dataclasses import dataclass, fields, is_dataclass
from datetime import date, datetime
from enum import Enum
from pathlib import Path
from typing import Any
from urllib.parse import urlparse

from dotenv import load_dotenv

load_dotenv()


class UsageError(ValueError):
    """Raised when a caller supplies an invalid or ambiguous argument."""


class AuthenticationRequired(RuntimeError):
    """Raised when no usable NotebookLM browser session is available."""


def storage_path(profile: str | None = None) -> Path:
    """Return the active notebooklm-py storage path, including profiles."""
    try:
        from notebooklm.paths import get_storage_path

        return get_storage_path(profile)
    except (ImportError, RuntimeError):
        return Path.home() / ".notebooklm" / "storage_state.json"


def authentication_message() -> str:
    """Return actionable authentication guidance without exposing cookies."""
    return (
        "[AUTH_REQUIRED] NotebookLM authentication is missing or expired. "
        "Run `uvx --from notebooklm-py notebooklm login` (or "
        "`python3 -m notebooklm login` after installation), then retry. "
        f"Active session path: {storage_path()}"
    )


@asynccontextmanager
async def get_client():
    """Yield an authenticated client and normalize authentication failures."""
    from notebooklm import AuthError, AuthExtractionError, NotebookLMClient

    try:
        async with NotebookLMClient.from_storage() as client:
            try:
                yield client
            except (AuthError, AuthExtractionError) as exc:
                raise AuthenticationRequired(authentication_message()) from exc
    except (AuthError, AuthExtractionError) as exc:
        raise AuthenticationRequired(authentication_message()) from exc
    except FileNotFoundError as exc:
        # Do not turn a missing upload file into an authentication error.
        if not storage_path().exists() and not os.getenv("NOTEBOOKLM_AUTH_JSON"):
            raise AuthenticationRequired(authentication_message()) from exc
        raise


def normalize_language(language: str | None) -> str:
    """Normalize common BCP-47 aliases to NotebookLM language identifiers."""
    if not language:
        return "en"
    aliases = {
        "zh-tw": "zh_Hant",
        "zh-hant": "zh_Hant",
        "zh_tw": "zh_Hant",
        "zh-cn": "zh_Hans",
        "zh-hans": "zh_Hans",
        "zh_cn": "zh_Hans",
        "pt-br": "pt_BR",
        "pt-pt": "pt_PT",
        "es-mx": "es_MX",
        "fr-ca": "fr_CA",
    }
    return aliases.get(language.casefold(), language)


def serialize(value: Any) -> Any:
    """Convert typed notebooklm-py results to JSON-compatible values."""
    if value is None or isinstance(value, (str, int, float, bool)):
        return value
    if isinstance(value, Enum):
        return serialize(value.value)
    if isinstance(value, (Path, date, datetime)):
        return value.isoformat() if hasattr(value, "isoformat") else str(value)
    if isinstance(value, Mapping):
        return {str(key): serialize(item) for key, item in value.items()}
    if isinstance(value, (list, tuple, set, frozenset)):
        return [serialize(item) for item in value]
    if is_dataclass(value) and not isinstance(value, type):
        return {
            field.name: serialize(getattr(value, field.name))
            for field in fields(value)
            if not field.name.startswith("_")
        }
    if hasattr(value, "__dict__"):
        return {key: serialize(item) for key, item in vars(value).items() if not key.startswith("_")}
    return str(value)


def serialize_notebook(notebook: Any) -> dict[str, Any]:
    """Serialize stable, useful notebook metadata."""
    result = {"id": notebook.id, "title": getattr(notebook, "title", "")}
    for attribute in ("created_at", "sources_count", "is_owner"):
        value = getattr(notebook, attribute, None)
        if value is not None:
            result[attribute] = serialize(value)
    return result


def serialize_source(source: Any) -> dict[str, Any]:
    """Serialize a source using the current ``kind`` API."""
    result = {"id": getattr(source, "id", None)}
    for attribute in ("title", "url", "kind", "status", "created_at"):
        value = getattr(source, attribute, None)
        if value is not None:
            result[attribute] = serialize(value)
    return result


def serialize_artifact(artifact: Any) -> dict[str, Any]:
    """Serialize artifact metadata without exposing signed download URLs."""
    result = {
        "id": getattr(artifact, "id", None),
        "title": getattr(artifact, "title", ""),
    }
    for attribute in ("kind", "status", "created_at"):
        value = getattr(artifact, attribute, None)
        if value is not None:
            result[attribute] = serialize(value)
    return result


async def resolve_notebook(client: Any, identifier: str) -> Any:
    """Resolve an ID or unique title/substring to a notebook object."""
    query = identifier.strip()
    if not query:
        raise UsageError("Notebook name or ID cannot be empty.")

    notebooks = list(await client.notebooks.list() or [])
    id_matches = [item for item in notebooks if item.id == query]
    if id_matches:
        return id_matches[0]

    folded = query.casefold()
    exact = [item for item in notebooks if item.title.casefold() == folded]
    if len(exact) == 1:
        return exact[0]
    if len(exact) > 1:
        raise UsageError(f"Notebook title '{query}' is ambiguous. Use an ID: " + ", ".join(item.id for item in exact))

    partial = [item for item in notebooks if folded in item.title.casefold()]
    if len(partial) == 1:
        return partial[0]
    if len(partial) > 1:
        choices = ", ".join(f"{item.title} ({item.id})" for item in partial[:10])
        raise UsageError(f"Notebook '{query}' is ambiguous. Matches: {choices}")
    raise UsageError(f"Notebook '{query}' was not found.")


def validate_url(url: str) -> str:
    """Validate a web/YouTube source URL."""
    candidate = url.strip()
    parsed = urlparse(candidate)
    if parsed.scheme not in {"http", "https"} or not parsed.netloc:
        raise UsageError(f"Invalid source URL: {url!r}")
    return candidate


async def fetch_trends(geo: str, count: int) -> list[dict[str, Any]]:
    """Fetch and normalize trend-pulse JSON without invoking a shell or npx."""
    if not 1 <= count <= 20:
        raise UsageError("Trend count must be between 1 and 20.")
    command = shlex.split(os.getenv("TREND_PULSE_CMD", "trend-pulse"))
    if not command:
        raise UsageError("TREND_PULSE_CMD cannot be empty.")
    try:
        process = await asyncio.create_subprocess_exec(
            *command,
            "trending",
            "--geo",
            geo,
            "--count",
            str(count),
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
        )
        stdout, stderr = await asyncio.wait_for(process.communicate(), timeout=60)
    except FileNotFoundError as exc:
        raise RuntimeError("trend-pulse is not installed. Install it or set TREND_PULSE_CMD.") from exc
    except TimeoutError as exc:
        raise RuntimeError("trend-pulse timed out after 60 seconds.") from exc
    if process.returncode != 0:
        detail = stderr.decode(errors="replace").strip()[:300]
        raise RuntimeError(f"trend-pulse failed: {detail or f'exit {process.returncode}'}")
    try:
        payload = json.loads(stdout)
    except json.JSONDecodeError as exc:
        raise RuntimeError("trend-pulse returned invalid JSON.") from exc
    if isinstance(payload, dict):
        payload = payload.get("merged") or payload.get("trends") or payload.get("items") or []
    if not isinstance(payload, list):
        raise RuntimeError("trend-pulse JSON must contain a list of trends.")

    trends: list[dict[str, Any]] = []
    for item in payload:
        if isinstance(item, str):
            normalized = {"title": item}
        elif isinstance(item, dict):
            normalized = dict(item)
            normalized["title"] = (
                item.get("title") or item.get("keyword") or item.get("name") or item.get("query") or ""
            )
        else:
            continue
        if str(normalized["title"]).strip():
            normalized["title"] = str(normalized["title"]).strip()
            trends.append(normalized)
    return trends[:count]


async def fetch_rss_entries(
    url: str, *, max_entries: int = 20, timeout: float = 30, max_bytes: int = 5_000_000
) -> list[dict[str, str]]:
    """Fetch an HTTP(S) RSS/Atom feed with time and size limits."""
    if not 1 <= max_entries <= 100:
        raise UsageError("RSS max entries must be between 1 and 100.")
    if timeout <= 0 or max_bytes <= 0:
        raise UsageError("RSS timeout and maximum bytes must be positive.")
    feed_url = validate_url(url)
    try:
        import feedparser
        import httpx
    except ImportError as exc:
        raise RuntimeError("RSS support requires feedparser and httpx.") from exc

    chunks: list[bytes] = []
    received = 0
    async with httpx.AsyncClient(follow_redirects=True, timeout=timeout) as http:
        async with http.stream("GET", feed_url) as response:
            response.raise_for_status()
            async for chunk in response.aiter_bytes():
                received += len(chunk)
                if received > max_bytes:
                    raise RuntimeError(f"RSS feed exceeds the {max_bytes}-byte safety limit.")
                chunks.append(chunk)
    parsed = feedparser.parse(b"".join(chunks))
    if getattr(parsed, "bozo", False) and not getattr(parsed, "entries", None):
        detail = getattr(parsed, "bozo_exception", "unknown parse error")
        raise RuntimeError(f"RSS feed could not be parsed: {detail}")
    entries: list[dict[str, str]] = []
    for entry in list(getattr(parsed, "entries", ()))[:max_entries]:
        entries.append(
            {
                "title": str(getattr(entry, "title", "Untitled")),
                "link": str(getattr(entry, "link", "")),
                "summary": str(getattr(entry, "summary", ""))[:2000],
                "published": str(getattr(entry, "published", "")),
            }
        )
    return entries


async def ingest_sources(
    client: Any,
    notebook_id: str,
    *,
    urls: Sequence[str] = (),
    texts: Sequence[str] = (),
    files: Sequence[str | Path] = (),
    wait_timeout: float = 180,
    concurrency: int = 4,
) -> list[dict[str, Any]]:
    """Add mixed sources concurrently while preserving result order."""
    if concurrency < 1:
        raise UsageError("Source concurrency must be at least 1.")
    if wait_timeout <= 0:
        raise UsageError("Source timeout must be positive.")

    jobs: list[tuple[str, str, Any]] = []
    for url in urls:
        jobs.append(("url", url, validate_url(url)))
    for index, text in enumerate(texts, 1):
        if not text.strip():
            raise UsageError(f"Text source {index} cannot be empty.")
        jobs.append(("text", f"Text Source {index}", text))
    for raw_path in files:
        path = Path(raw_path).expanduser()
        jobs.append(("file", str(path), path))

    semaphore = asyncio.Semaphore(concurrency)

    async def add_one(source_type: str, label: str, payload: Any) -> dict[str, Any]:
        async with semaphore:
            try:
                if source_type == "url":
                    source = await client.sources.add_url(notebook_id, payload, wait=True, wait_timeout=wait_timeout)
                elif source_type == "text":
                    source = await client.sources.add_text(
                        notebook_id,
                        title=label,
                        content=payload,
                        wait=True,
                        wait_timeout=wait_timeout,
                    )
                else:
                    if not payload.is_file():
                        raise FileNotFoundError(f"Source file not found: {payload}")
                    source = await client.sources.add_file(
                        notebook_id,
                        file_path=payload,
                        wait=True,
                        wait_timeout=wait_timeout,
                    )
                return {
                    "status": "ok",
                    "source_type": source_type,
                    "input": label,
                    "source": serialize_source(source),
                }
            except Exception as exc:
                return {
                    "status": "failed",
                    "source_type": source_type,
                    "input": label,
                    "error": str(exc),
                }

    return await asyncio.gather(*(add_one(*job) for job in jobs))


def source_result_summary(results: Sequence[Mapping[str, Any]]) -> dict[str, int]:
    """Count successful and failed source ingestion attempts."""
    succeeded = sum(item.get("status") == "ok" for item in results)
    return {
        "requested": len(results),
        "succeeded": succeeded,
        "failed": len(results) - succeeded,
    }


@dataclass(frozen=True)
class ArtifactSpec:
    """Canonical artifact behavior shared by every interface."""

    generator: str
    downloader: str
    extension: str
    language: bool = True
    instructions_parameter: str | None = "instructions"
    immediate: bool = False
    output_formats: tuple[str, ...] = ()
    timeout: float = 1800


ARTIFACT_SPECS: dict[str, ArtifactSpec] = {
    "audio": ArtifactSpec("generate_audio", "download_audio", "m4a", timeout=1800),
    "video": ArtifactSpec("generate_video", "download_video", "mp4", timeout=3600),
    "cinematic": ArtifactSpec("generate_cinematic_video", "download_video", "mp4", timeout=3600),
    "slides": ArtifactSpec(
        "generate_slide_deck",
        "download_slide_deck",
        "pdf",
        output_formats=("pdf", "pptx"),
    ),
    "report": ArtifactSpec("generate_report", "download_report", "md", instructions_parameter="extra_instructions"),
    "study-guide": ArtifactSpec(
        "generate_study_guide",
        "download_report",
        "md",
        instructions_parameter="extra_instructions",
    ),
    "quiz": ArtifactSpec(
        "generate_quiz",
        "download_quiz",
        "json",
        language=False,
        output_formats=("json", "markdown", "html"),
    ),
    "flashcards": ArtifactSpec(
        "generate_flashcards",
        "download_flashcards",
        "json",
        language=False,
        output_formats=("json", "markdown", "html"),
    ),
    "mind-map": ArtifactSpec("generate_mind_map", "download_mind_map", "json", immediate=True),
    "infographic": ArtifactSpec("generate_infographic", "download_infographic", "png", timeout=2400),
    "data-table": ArtifactSpec("generate_data_table", "download_data_table", "csv"),
}


_GENERATION_OPTIONS: dict[str, dict[str, tuple[str | None, str]]] = {
    "audio": {
        "audio_format": ("AudioFormat", "audio_format"),
        "audio_length": ("AudioLength", "audio_length"),
    },
    "video": {
        "video_format": ("VideoFormat", "video_format"),
        "video_style": ("VideoStyle", "video_style"),
        "style_prompt": (None, "style_prompt"),
    },
    "slides": {
        "slide_format": ("SlideDeckFormat", "slide_format"),
        "slide_length": ("SlideDeckLength", "slide_length"),
    },
    "report": {
        "report_format": ("ReportFormat", "report_format"),
        "custom_prompt": (None, "custom_prompt"),
    },
    "quiz": {
        "quantity": ("QuizQuantity", "quantity"),
        "difficulty": ("QuizDifficulty", "difficulty"),
    },
    "flashcards": {
        "quantity": ("QuizQuantity", "quantity"),
        "difficulty": ("QuizDifficulty", "difficulty"),
    },
    "infographic": {
        "orientation": ("InfographicOrientation", "orientation"),
        "detail_level": ("InfographicDetail", "detail_level"),
        "style": ("InfographicStyle", "style"),
    },
}


def _enum_option(enum_name: str, raw_value: str) -> Any:
    import notebooklm

    enum_type = getattr(notebooklm, enum_name)
    normalized = raw_value.strip().casefold().replace("-", "_")
    for member in enum_type:
        if member.name.casefold() == normalized:
            return member
        if isinstance(member.value, str) and member.value.casefold() == normalized:
            return member
    choices = ", ".join(member.name.casefold().replace("_", "-") for member in enum_type)
    raise UsageError(f"Invalid {enum_name} value '{raw_value}'. Choose: {choices}")


def build_generation_kwargs(
    artifact_type: str,
    *,
    language: str = "en",
    instructions: str | None = None,
    source_ids: Sequence[str] | None = None,
    options: Mapping[str, str | None] | None = None,
) -> dict[str, Any]:
    """Build validated notebooklm-py generation keyword arguments."""
    spec = ARTIFACT_SPECS.get(artifact_type)
    if spec is None:
        raise UsageError(f"Unknown artifact type '{artifact_type}'. Supported: " + ", ".join(ARTIFACT_SPECS))

    kwargs: dict[str, Any] = {}
    if source_ids:
        kwargs["source_ids"] = list(source_ids)
    if spec.language:
        kwargs["language"] = normalize_language(language)
    if instructions and spec.instructions_parameter:
        kwargs[spec.instructions_parameter] = instructions

    supplied = {key: value for key, value in (options or {}).items() if value is not None}
    rules = _GENERATION_OPTIONS.get(artifact_type, {})
    unsupported = sorted(set(supplied) - set(rules))
    if unsupported:
        raise UsageError(f"Options not supported for {artifact_type}: {', '.join(unsupported)}")
    for option_name, raw_value in supplied.items():
        enum_name, api_name = rules[option_name]
        assert raw_value is not None
        kwargs[api_name] = _enum_option(enum_name, raw_value) if enum_name else raw_value

    report_format = kwargs.get("report_format")
    if report_format is not None and getattr(report_format, "name", "") == "CUSTOM":
        if not kwargs.get("custom_prompt"):
            raise UsageError("--custom-prompt is required for a custom report.")
    video_style = kwargs.get("video_style")
    style_prompt = kwargs.get("style_prompt")
    if video_style is not None and getattr(video_style, "name", "") == "CUSTOM":
        if not style_prompt or not str(style_prompt).strip():
            raise UsageError("--style-prompt is required for a custom video style.")
    elif style_prompt:
        raise UsageError("--style-prompt requires --video-style custom.")
    video_format = kwargs.get("video_format")
    if video_format is not None and getattr(video_format, "name", "") == "CINEMATIC" and style_prompt:
        raise UsageError("A cinematic video does not support --style-prompt.")
    return kwargs


def serialize_generation_status(status: Any) -> dict[str, Any]:
    """Serialize a generation status without its signed URL."""
    return {
        key: serialize(getattr(status, key))
        for key in ("task_id", "status", "error", "error_code", "metadata")
        if getattr(status, key, None) is not None
    }


async def generate_artifact(
    client: Any,
    notebook_id: str,
    artifact_type: str,
    *,
    language: str = "en",
    instructions: str | None = None,
    source_ids: Sequence[str] | None = None,
    options: Mapping[str, str | None] | None = None,
    wait: bool = True,
    timeout: float | None = None,
) -> dict[str, Any]:
    """Generate an artifact and optionally wait for terminal completion."""
    spec = ARTIFACT_SPECS.get(artifact_type)
    if spec is None:
        raise UsageError(f"Unknown artifact type '{artifact_type}'.")
    if timeout is not None and timeout <= 0:
        raise UsageError("Artifact timeout must be positive.")

    method = getattr(client.artifacts, spec.generator)
    kwargs = build_generation_kwargs(
        artifact_type,
        language=language,
        instructions=instructions,
        source_ids=source_ids,
        options=options,
    )
    started = await method(notebook_id, **kwargs)
    if spec.immediate:
        return {
            "status": "ok",
            "state": "completed",
            "artifact_type": artifact_type,
            "result": serialize(started),
        }

    task_id = getattr(started, "task_id", None)
    if not task_id:
        message = getattr(started, "error", None) or "NotebookLM did not create a task."
        raise RuntimeError(f"Failed to generate {artifact_type}: {message}")
    result = {
        "status": "started" if not wait else "ok",
        "state": serialize(getattr(started, "status", "in_progress")),
        "artifact_type": artifact_type,
        "task_id": task_id,
    }
    if not wait:
        return result

    final = await client.artifacts.wait_for_completion(notebook_id, task_id, timeout=timeout or spec.timeout)
    final_state = str(getattr(final, "status", "")).casefold()
    if final_state != "completed":
        message = getattr(final, "error", None) or f"terminal state: {final_state or 'unknown'}"
        raise RuntimeError(f"{artifact_type} generation failed: {message}")
    result["state"] = "completed"
    result["result"] = serialize_generation_status(final)
    return result


def prepare_output_path(output_path: str | Path, *, force: bool = False) -> Path:
    """Validate a download path and create its parent directory."""
    path = Path(output_path).expanduser()
    if path.is_symlink():
        raise UsageError(f"Refusing to write through a symlink: {path}")
    if path.is_dir():
        raise UsageError(f"Output path is a directory: {path}")
    if path.exists() and not force:
        raise UsageError(f"Output already exists: {path}. Pass --force to overwrite it.")
    path.parent.mkdir(parents=True, exist_ok=True)
    return path


async def download_artifact(
    client: Any,
    notebook_id: str,
    artifact_type: str,
    output_path: str | Path,
    *,
    artifact_id: str | None = None,
    output_format: str | None = None,
    force: bool = False,
) -> str:
    """Download one artifact with type/format/path validation."""
    spec = ARTIFACT_SPECS.get(artifact_type)
    if spec is None:
        raise UsageError(f"Unknown artifact type '{artifact_type}'.")
    if output_format and output_format not in spec.output_formats:
        choices = ", ".join(spec.output_formats) or "none"
        raise UsageError(f"Output format '{output_format}' is not valid for {artifact_type}. Choices: {choices}")
    path = prepare_output_path(output_path, force=force)
    method = getattr(client.artifacts, spec.downloader)
    kwargs: dict[str, Any] = {}
    if artifact_id:
        kwargs["artifact_id"] = artifact_id
    if output_format:
        kwargs["output_format"] = output_format
    downloaded = await method(notebook_id, str(path), **kwargs)
    return str(downloaded)


_ARTIFACT_FILTERS = {
    "audio": "AUDIO",
    "video": "VIDEO",
    "cinematic": "VIDEO",
    "slides": "SLIDE_DECK",
    "report": "REPORT",
    "study-guide": "REPORT",
    "quiz": "QUIZ",
    "flashcards": "FLASHCARDS",
    "mind-map": "MIND_MAP",
    "infographic": "INFOGRAPHIC",
    "data-table": "DATA_TABLE",
}


async def list_artifacts(client: Any, notebook_id: str, artifact_type: str | None = None) -> list[dict[str, Any]]:
    """List actual generated artifacts, optionally filtered by type."""
    filter_value = None
    if artifact_type:
        enum_name = _ARTIFACT_FILTERS.get(artifact_type)
        if not enum_name:
            raise UsageError(f"Unknown artifact type '{artifact_type}'.")
        from notebooklm import ArtifactType

        filter_value = getattr(ArtifactType, enum_name)
    artifacts = await client.artifacts.list(notebook_id, filter_value)
    return [serialize_artifact(item) for item in artifacts]


async def run_research(
    client: Any,
    notebook_id: str,
    query: str,
    *,
    mode: str = "fast",
    wait: bool = True,
    timeout: float = 1800,
    import_results: bool = True,
    max_sources: int = 10,
) -> dict[str, Any]:
    """Start, wait for, and optionally import a NotebookLM research task."""
    if not query.strip():
        raise UsageError("Research query cannot be empty.")
    if mode not in {"fast", "deep"}:
        raise UsageError("Research mode must be 'fast' or 'deep'.")
    if timeout <= 0:
        raise UsageError("Research timeout must be positive.")
    if max_sources < 0:
        raise UsageError("Maximum imported sources cannot be negative.")

    started = await client.research.start(notebook_id, query=query.strip(), source="web", mode=mode)
    task_id = getattr(started, "task_id", None)
    if started is None or not task_id:
        raise RuntimeError("NotebookLM did not create a research task.")
    output: dict[str, Any] = {
        "status": "started" if not wait else "ok",
        "task_id": task_id,
        "mode": mode,
        "query": query.strip(),
    }
    if not wait:
        return output

    final = await client.research.wait_for_completion(notebook_id, task_id=task_id, timeout=timeout)
    state = str(getattr(final, "status", "")).casefold()
    if state != "completed":
        raise RuntimeError(f"Research task ended in state '{state or 'unknown'}'.")

    sources = list(getattr(final, "sources", ()) or ())
    imported: list[Any] = []
    if import_results and max_sources and sources:
        imported = await client.research.import_sources(notebook_id, task_id, sources[:max_sources])
    output.update(
        {
            "state": "completed",
            "result": serialize(final),
            "sources_found": len(sources),
            "sources_imported": len(imported),
            "imported": serialize(imported),
        }
    )
    return output
