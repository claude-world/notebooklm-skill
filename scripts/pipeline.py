#!/usr/bin/env python3
"""High-level, JSON-first NotebookLM workflow orchestration."""

from __future__ import annotations

import argparse
import asyncio
import json
import os
import re
import sys
from importlib.metadata import PackageNotFoundError, version
from pathlib import Path
from typing import Any

from scripts.common import (
    ARTIFACT_SPECS,
    AuthenticationRequired,
    UsageError,
    download_artifact,
    fetch_rss_entries,
    fetch_trends,
    generate_artifact,
    get_client,
    ingest_sources,
    run_research,
    serialize,
    serialize_generation_status,
    serialize_notebook,
    source_result_summary,
    validate_url,
)

ARTICLE_QUESTIONS = (
    "What are the main topics and key themes covered by these sources?",
    "What are the most important findings, evidence, and data points?",
    "Which perspectives disagree, and what supports each perspective?",
    "What practical implications and actionable takeaways follow?",
    "What limitations, uncertainties, or information gaps remain?",
)

PLATFORM_SPECS = {
    "threads": {"max_chars": 500, "style": "conversational with useful line breaks"},
    "twitter": {"max_chars": 280, "style": "concise; use hashtags sparingly"},
    "linkedin": {"max_chars": 3000, "style": "professional and skimmable"},
    "instagram": {"max_chars": 2200, "style": "engaging; use emojis sparingly"},
    "generic": {"max_chars": 1000, "style": "clear and informative"},
}

DEFAULT_GENERATE_TYPES = (
    "audio",
    "video",
    "slides",
    "report",
    "quiz",
    "flashcards",
    "mind-map",
    "infographic",
    "data-table",
    "study-guide",
)


def _json_out(data: dict[str, Any]) -> None:
    print(json.dumps(data, ensure_ascii=False, indent=2))


def _err(message: str) -> None:
    print(f"[pipeline] {message}", file=sys.stderr)


def _package_version() -> str:
    try:
        return version("notebooklm-skill")
    except PackageNotFoundError:
        return "development"


def _has_source_inputs(args: argparse.Namespace) -> bool:
    return bool(args.sources or args.text_sources or args.files)


async def _create_with_sources(
    client: Any, args: argparse.Namespace, title: str
) -> tuple[Any, list[dict[str, Any]], dict[str, int]]:
    clean_title = title.strip()
    if not clean_title:
        raise UsageError("Notebook title cannot be empty.")
    notebook = await client.notebooks.create(title=clean_title)
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
    return notebook, results, summary


async def _ask(client: Any, notebook_id: str, question: str) -> dict[str, Any]:
    try:
        result = await client.chat.ask(notebook_id, question=question)
        return {
            "status": "ok",
            "question": question,
            "answer": result.answer,
            "references": serialize(getattr(result, "references", ()) or ()),
        }
    except Exception as exc:
        return {"status": "failed", "question": question, "error": str(exc)}


async def _ask_many(
    client: Any, notebook_id: str, questions: list[str] | tuple[str, ...], concurrency: int = 4
) -> list[dict[str, Any]]:
    semaphore = asyncio.Semaphore(concurrency)

    async def limited(question: str) -> dict[str, Any]:
        async with semaphore:
            return await _ask(client, notebook_id, question)

    return await asyncio.gather(*(limited(question) for question in questions))


def _source_failure_response(
    workflow: str,
    notebook: Any,
    source_results: list[dict[str, Any]],
    source_summary: dict[str, int],
) -> dict[str, Any]:
    return {
        "status": "failed",
        "workflow": workflow,
        "notebook": serialize_notebook(notebook),
        "source_summary": source_summary,
        "sources": source_results,
        "error": "No source was ingested; generation steps were skipped.",
    }


async def workflow_research_to_article(args: argparse.Namespace) -> dict[str, Any]:
    """Sources -> evidence questions -> grounded article draft."""
    if not _has_source_inputs(args):
        raise UsageError("Provide at least one --sources, --text-sources, or --files value.")
    async with get_client() as client:
        _err("Creating notebook and ingesting sources...")
        notebook, source_results, summary = await _create_with_sources(client, args, args.title)
        if summary["succeeded"] == 0:
            return _source_failure_response("research-to-article", notebook, source_results, summary)

        _err("Extracting evidence with five research questions...")
        findings = await _ask_many(client, notebook.id, ARTICLE_QUESTIONS)
        article_prompt = (
            f"Write a source-grounded article in {args.language} for {args.audience}. "
            f"Tone: {args.tone}. Include a specific title, introduction, 3-5 descriptive "
            "section headings, evidence with inline NotebookLM citations, limitations, and a "
            "conclusion with actionable takeaways. Do not invent facts absent from the sources."
        )
        article = await _ask(client, notebook.id, article_prompt)
        failed_findings = sum(item["status"] == "failed" for item in findings)
        status = "ok"
        if article["status"] == "failed":
            status = "failed"
        elif summary["failed"] or failed_findings:
            status = "partial"
        return {
            "status": status,
            "workflow": "research-to-article",
            "title": args.title,
            "notebook": serialize_notebook(notebook),
            "source_summary": summary,
            "sources": source_results,
            "research_findings": findings,
            "article": article,
        }


async def workflow_research_to_social(args: argparse.Namespace) -> dict[str, Any]:
    """Sources -> summary -> platform-specific drafts."""
    if not _has_source_inputs(args):
        raise UsageError("Provide at least one --sources, --text-sources, or --files value.")
    specs = PLATFORM_SPECS[args.platform]
    async with get_client() as client:
        notebook, source_results, summary = await _create_with_sources(client, args, args.title)
        if summary["succeeded"] == 0:
            return _source_failure_response("research-to-social", notebook, source_results, summary)
        summary_prompt = (
            "Summarize the notebook's key claims, supporting evidence, uncertainties, and the "
            "three most useful takeaways. Preserve NotebookLM citations."
        )
        social_prompt = (
            f"Write a primary {args.platform} draft in {args.language}, no more than "
            f"{specs['max_chars']} characters. Style: {specs['style']}. Ground claims in the "
            f"sources and add {args.variants} clearly separated alternative drafts, each within "
            "the same character limit."
        )
        notebook_summary, social = await asyncio.gather(
            _ask(client, notebook.id, summary_prompt),
            _ask(client, notebook.id, social_prompt),
        )
        status = "ok"
        if social["status"] == "failed":
            status = "failed"
        elif summary["failed"] or notebook_summary["status"] == "failed":
            status = "partial"
        return {
            "status": status,
            "workflow": "research-to-social",
            "title": args.title,
            "notebook": serialize_notebook(notebook),
            "platform": args.platform,
            "platform_specs": specs,
            "source_summary": summary,
            "sources": source_results,
            "summary": notebook_summary,
            "social": social,
        }


def _trend_urls(trend: dict[str, Any]) -> list[str]:
    candidates: list[Any] = []
    for key in ("url", "link", "newsUrl", "news_url"):
        if trend.get(key):
            candidates.append(trend[key])
    for article in trend.get("articles") or trend.get("news") or trend.get("relatedArticles") or []:
        if isinstance(article, str):
            candidates.append(article)
        elif isinstance(article, dict):
            candidates.append(article.get("url") or article.get("link"))
    urls: list[str] = []
    for candidate in candidates:
        if not candidate:
            continue
        try:
            url = validate_url(str(candidate))
        except UsageError:
            continue
        if url not in urls:
            urls.append(url)
    return urls[:10]


async def workflow_trend_to_content(args: argparse.Namespace) -> dict[str, Any]:
    """trend-pulse -> NotebookLM web research/import -> grounded platform draft."""
    trends = await fetch_trends(args.geo, args.count)
    if not trends:
        raise RuntimeError("trend-pulse returned no usable topics.")
    specs = PLATFORM_SPECS[args.platform]
    results: list[dict[str, Any]] = []
    async with get_client() as client:
        for index, trend in enumerate(trends, 1):
            topic = trend["title"]
            _err(f"Researching trend {index}/{len(trends)}: {topic}")
            item: dict[str, Any] = {"topic": topic, "trend": trend}
            try:
                notebook = await client.notebooks.create(title=f"Trend: {topic}")
                item["notebook"] = serialize_notebook(notebook)
                urls = _trend_urls(trend)
                description = str(trend.get("description") or trend.get("summary") or topic)
                initial_sources = await ingest_sources(
                    client,
                    notebook.id,
                    urls=urls,
                    texts=() if urls else (description,),
                    wait_timeout=args.source_timeout,
                    concurrency=args.source_concurrency,
                )
                item["initial_sources"] = initial_sources
                item["initial_source_summary"] = source_result_summary(initial_sources)
                research_error = None
                try:
                    item["research"] = await run_research(
                        client,
                        notebook.id,
                        topic,
                        mode=args.research_mode,
                        wait=True,
                        timeout=args.research_timeout,
                        import_results=True,
                        max_sources=args.max_research_sources,
                    )
                except Exception as exc:
                    research_error = str(exc)
                    item["research_error"] = research_error

                usable = item["initial_source_summary"]["succeeded"] > 0 or not research_error
                if not usable:
                    item.update(
                        {
                            "status": "failed",
                            "error": "Neither initial sources nor web research produced content.",
                        }
                    )
                    results.append(item)
                    continue
                prompt = (
                    f"Write a {args.platform} draft in {args.language} explaining why '{topic}' "
                    f"matters. Maximum {specs['max_chars']} characters; style: {specs['style']}. "
                    "Use only notebook evidence, preserve citations, and acknowledge uncertainty."
                )
                content = await _ask(client, notebook.id, prompt)
                item["content"] = content
                item["status"] = (
                    "failed"
                    if content["status"] == "failed"
                    else ("partial" if research_error or item["initial_source_summary"]["failed"] else "ok")
                )
            except Exception as exc:
                item.update({"status": "failed", "error": str(exc)})
            results.append(item)
    failures = sum(item["status"] == "failed" for item in results)
    partials = sum(item["status"] == "partial" for item in results)
    status = "ok"
    if failures == len(results):
        status = "failed"
    elif failures or partials:
        status = "partial"
    return {
        "status": status,
        "workflow": "trend-to-content",
        "geo": args.geo,
        "platform": args.platform,
        "trends_requested": args.count,
        "trends_processed": len(results),
        "results": results,
    }


def _parse_qa(text: str) -> list[dict[str, str]]:
    parts = re.split(r"(?im)^\s*Q(?:uestion)?\s*\d*\s*[:.)-]\s*", text)
    pairs: list[dict[str, str]] = []
    for part in parts[1:]:
        match = re.split(r"(?im)^\s*A(?:nswer)?\s*\d*\s*[:.)-]\s*", part, maxsplit=1)
        if len(match) == 2 and match[0].strip() and match[1].strip():
            pairs.append({"question": match[0].strip(), "answer": match[1].strip()})
    return pairs


async def workflow_batch_digest(args: argparse.Namespace) -> dict[str, Any]:
    """Bounded RSS fetch -> source ingestion -> digest and Q&A."""
    entries = await fetch_rss_entries(
        args.rss,
        max_entries=args.max_entries,
        timeout=args.rss_timeout,
        max_bytes=args.max_feed_bytes,
    )
    if not entries:
        raise RuntimeError("The RSS feed contains no entries.")
    urls = [entry["link"] for entry in entries if entry["link"]]
    texts = [
        f"Title: {entry['title']}\nPublished: {entry['published']}\n\n{entry['summary']}"
        for entry in entries
        if not entry["link"]
    ]
    async with get_client() as client:
        notebook = await client.notebooks.create(title=args.title)
        source_results = await ingest_sources(
            client,
            notebook.id,
            urls=urls,
            texts=texts,
            wait_timeout=args.source_timeout,
            concurrency=args.source_concurrency,
        )
        summary = source_result_summary(source_results)
        if summary["succeeded"] == 0:
            return _source_failure_response("batch-digest", notebook, source_results, summary)
        digest_prompt = (
            f"Create a {args.language} newsletter digest with an executive summary, source-by-source "
            "highlights, cross-source themes, material disagreements, and three takeaways. Preserve citations."
        )
        qa_prompt = (
            f"Generate {args.qa_count} important Q&A pairs in {args.language}. Format each exactly as "
            "Q: question on one line, then A: grounded answer with citations."
        )
        digest, qa = await asyncio.gather(
            _ask(client, notebook.id, digest_prompt), _ask(client, notebook.id, qa_prompt)
        )
        qa_pairs = _parse_qa(qa.get("answer", "")) if qa["status"] == "ok" else []
        status = "ok"
        if digest["status"] == "failed":
            status = "failed"
        elif summary["failed"] or qa["status"] == "failed" or not qa_pairs:
            status = "partial"
        return {
            "status": status,
            "workflow": "batch-digest",
            "title": args.title,
            "notebook": serialize_notebook(notebook),
            "rss_url": args.rss,
            "entries_fetched": len(entries),
            "entries": entries,
            "source_summary": summary,
            "sources": source_results,
            "digest": digest,
            "qa": qa,
            "qa_pairs": qa_pairs,
        }


async def workflow_generate_all(args: argparse.Namespace) -> dict[str, Any]:
    """Ingest sources, start selected artifact jobs, then wait/download exactly."""
    if not _has_source_inputs(args):
        raise UsageError("Provide at least one --sources, --text-sources, or --files value.")
    if args.download and not args.wait:
        raise UsageError("--download requires --wait; use --no-download with --no-wait.")
    types = list(dict.fromkeys(args.types))
    output_dir = Path(args.output_dir).expanduser()
    if output_dir.is_symlink():
        raise UsageError(f"Refusing to use a symlink output directory: {output_dir}")
    if args.download:
        output_dir.mkdir(parents=True, exist_ok=True)

    async with get_client() as client:
        notebook, source_results, summary = await _create_with_sources(client, args, args.title)
        if summary["succeeded"] == 0:
            return _source_failure_response("generate-all", notebook, source_results, summary)

        started: list[dict[str, Any]] = []
        for artifact_type in types:
            _err(f"Starting {artifact_type} generation...")
            try:
                result = await generate_artifact(
                    client,
                    notebook.id,
                    artifact_type,
                    language=args.language,
                    instructions=args.instructions,
                    wait=False,
                    timeout=args.timeout,
                )
                started.append({"type": artifact_type, "generation": result})
            except Exception as exc:
                started.append({"type": artifact_type, "status": "failed", "error": str(exc)})

        if not args.wait:
            failures = sum(item.get("status") == "failed" for item in started)
            return {
                "status": "failed" if failures == len(started) else ("partial" if failures else "started"),
                "workflow": "generate-all",
                "notebook": serialize_notebook(notebook),
                "source_summary": summary,
                "sources": source_results,
                "artifacts_requested": len(types),
                "artifacts": started,
            }

        semaphore = asyncio.Semaphore(args.artifact_concurrency)

        async def finish(item: dict[str, Any]) -> dict[str, Any]:
            if item.get("status") == "failed":
                return item
            artifact_type = item["type"]
            generation = item["generation"]
            spec = ARTIFACT_SPECS[artifact_type]
            async with semaphore:
                try:
                    if spec.immediate:
                        artifact_id = generation.get("result", {}).get("note_id")
                        final_data = generation.get("result")
                    else:
                        artifact_id = generation["task_id"]
                        final = await client.artifacts.wait_for_completion(
                            notebook.id,
                            artifact_id,
                            timeout=args.timeout or spec.timeout,
                        )
                        state = str(getattr(final, "status", "")).casefold()
                        if state != "completed":
                            raise RuntimeError(
                                getattr(final, "error", None) or f"generation ended in state '{state or 'unknown'}'"
                            )
                        final_data = serialize_generation_status(final)
                    result: dict[str, Any] = {
                        "type": artifact_type,
                        "status": "ok",
                        "artifact_id": artifact_id,
                        "result": final_data,
                    }
                    if args.download:
                        path = output_dir / f"{artifact_type}.{spec.extension}"
                        downloaded = await download_artifact(
                            client,
                            notebook.id,
                            artifact_type,
                            path,
                            artifact_id=artifact_id,
                            force=args.force,
                        )
                        result["path"] = downloaded
                        result["size_bytes"] = Path(downloaded).stat().st_size if Path(downloaded).exists() else 0
                    return result
                except Exception as exc:
                    return {"type": artifact_type, "status": "failed", "error": str(exc)}

        artifacts = await asyncio.gather(*(finish(item) for item in started))
        succeeded = sum(item["status"] == "ok" for item in artifacts)
        status = "ok" if succeeded == len(artifacts) else ("failed" if succeeded == 0 else "partial")
        return {
            "status": status,
            "workflow": "generate-all",
            "title": args.title,
            "notebook": serialize_notebook(notebook),
            "source_summary": summary,
            "sources": source_results,
            "output_dir": str(output_dir) if args.download else None,
            "language": args.language,
            "artifacts_requested": len(types),
            "artifacts_succeeded": succeeded,
            "artifacts_failed": len(artifacts) - succeeded,
            "artifacts": artifacts,
        }


def _add_source_arguments(parser: argparse.ArgumentParser) -> None:
    parser.add_argument("--sources", nargs="*", default=[], metavar="URL")
    parser.add_argument("--text-sources", nargs="*", default=[], metavar="TEXT")
    parser.add_argument("--files", nargs="*", default=[], metavar="PATH")
    parser.add_argument("--source-timeout", type=float, default=180)
    parser.add_argument("--source-concurrency", type=int, default=4)


def build_parser() -> argparse.ArgumentParser:
    """Build the documented workflow CLI contract."""
    parser = argparse.ArgumentParser(description="NotebookLM high-level workflows (JSON stdout, progress stderr)")
    parser.add_argument("--version", action="version", version=f"%(prog)s {_package_version()}")
    parser.add_argument("--profile", help="NotebookLM auth profile (or NOTEBOOKLM_PROFILE)")
    subparsers = parser.add_subparsers(dest="workflow", required=True)

    article = subparsers.add_parser("research-to-article", help="Sources to grounded article")
    _add_source_arguments(article)
    article.add_argument("--title", default="Research")
    article.add_argument("--language", default="en")
    article.add_argument("--audience", default="a well-informed general audience")
    article.add_argument("--tone", default="clear, authoritative, and appropriately cautious")

    social = subparsers.add_parser("research-to-social", help="Sources to social drafts")
    _add_source_arguments(social)
    social.add_argument("--title", default="Social Research")
    social.add_argument("--platform", choices=tuple(PLATFORM_SPECS), default="threads")
    social.add_argument("--language", default="en")
    social.add_argument("--variants", type=int, choices=range(0, 6), default=3)

    trend = subparsers.add_parser("trend-to-content", help="Trends to researched drafts")
    trend.add_argument("--geo", default="TW")
    trend.add_argument("--count", type=int, choices=range(1, 21), default=3)
    trend.add_argument("--platform", choices=tuple(PLATFORM_SPECS), default="threads")
    trend.add_argument("--language", default="en")
    trend.add_argument("--research-mode", choices=("fast", "deep"), default="fast")
    trend.add_argument("--max-research-sources", type=int, default=10)
    trend.add_argument("--research-timeout", type=float, default=1800)
    trend.add_argument("--source-timeout", type=float, default=180)
    trend.add_argument("--source-concurrency", type=int, default=4)

    digest = subparsers.add_parser("batch-digest", help="RSS/Atom feed to digest and Q&A")
    digest.add_argument("--rss", required=True)
    digest.add_argument("--title", default="Batch Digest")
    digest.add_argument("--max-entries", type=int, choices=range(1, 101), default=10)
    digest.add_argument("--qa-count", type=int, choices=range(1, 21), default=5)
    digest.add_argument("--language", default="en")
    digest.add_argument("--rss-timeout", type=float, default=30)
    digest.add_argument("--max-feed-bytes", type=int, default=5_000_000)
    digest.add_argument("--source-timeout", type=float, default=180)
    digest.add_argument("--source-concurrency", type=int, default=4)

    generate = subparsers.add_parser("generate-all", help="Sources to selected artifacts")
    _add_source_arguments(generate)
    generate.add_argument("--title", default="Research")
    generate.add_argument("--output-dir", default="./notebooklm-output")
    generate.add_argument("--language", default="en")
    generate.add_argument("--instructions")
    generate.add_argument(
        "--types",
        nargs="+",
        choices=tuple(ARTIFACT_SPECS),
        default=list(DEFAULT_GENERATE_TYPES),
    )
    generate.add_argument("--wait", action=argparse.BooleanOptionalAction, default=True)
    generate.add_argument("--download", action=argparse.BooleanOptionalAction, default=True)
    generate.add_argument("--timeout", type=float)
    generate.add_argument("--artifact-concurrency", type=int, choices=range(1, 5), default=2)
    generate.add_argument("--force", action="store_true")
    return parser


WORKFLOWS = {
    "research-to-article": workflow_research_to_article,
    "research-to-social": workflow_research_to_social,
    "trend-to-content": workflow_trend_to_content,
    "batch-digest": workflow_batch_digest,
    "generate-all": workflow_generate_all,
}


async def dispatch(args: argparse.Namespace) -> dict[str, Any]:
    return await WORKFLOWS[args.workflow](args)


def run(argv: list[str] | None = None) -> int:
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
        _json_out({"status": "failed", "error": "Pipeline cancelled.", "code": "CANCELLED"})
        return 130
    except TimeoutError as exc:
        _json_out({"status": "failed", "error": str(exc), "code": "TIMEOUT"})
        return 1
    except Exception as exc:
        _json_out({"status": "failed", "error": str(exc), "code": "PIPELINE_ERROR"})
        return 1
    _json_out(result)
    return 1 if result.get("status") == "failed" else 0


def main() -> None:
    raise SystemExit(run())


if __name__ == "__main__":
    main()
