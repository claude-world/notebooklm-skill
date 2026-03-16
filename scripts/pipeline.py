#!/usr/bin/env python3
"""
NotebookLM Pipeline Orchestrator

High-level workflow orchestrator that uses the notebooklm-py (v0.3.4) API
directly to chain NotebookLM operations with external tools (trend-pulse, RSS)
and produce structured content.

Workflows:
    research-to-article  - Sources -> notebook -> research -> article draft
    research-to-social   - Sources -> notebook -> summarize -> social post draft
    trend-to-content     - Trending topics -> notebooks -> research -> content drafts
    batch-digest         - RSS feed -> notebook -> digest summary
    generate-all         - Sources -> notebook -> generate all artifact types -> download

Usage:
    python pipeline.py research-to-article --sources url1 url2 --title "Topic"
    python pipeline.py research-to-social --sources url1 url2 --platform threads
    python pipeline.py trend-to-content --geo TW --count 3 --platform threads
    python pipeline.py batch-digest --rss https://example.com/feed.xml --title "Weekly Digest"
    python pipeline.py generate-all --sources url1 url2 --title "Research" --output-dir ./output

Output:
    JSON to stdout with research findings + content drafts.
    Progress messages to stderr.

Dependencies:
    pip install notebooklm-py python-dotenv feedparser
"""

import argparse
import asyncio
import json
import os
import subprocess
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
# Constants
# ---------------------------------------------------------------------------

# Research questions for article generation
ARTICLE_QUESTIONS = [
    "What are the main topics and key themes covered in these sources?",
    "What are the most important findings, data points, or arguments presented?",
    "What are the different perspectives or viewpoints expressed?",
    "What practical implications or actionable takeaways can be drawn?",
    "Are there any controversies, limitations, or gaps in the information?",
]

# Platform-specific constraints for social posts
PLATFORM_SPECS = {
    "threads": {"max_chars": 500, "style": "conversational, use line breaks, no hashtags in body"},
    "twitter": {"max_chars": 280, "style": "concise, use hashtags sparingly"},
    "linkedin": {"max_chars": 3000, "style": "professional, use bullet points"},
    "instagram": {"max_chars": 2200, "style": "engaging, use emojis and hashtags"},
    "generic": {"max_chars": 1000, "style": "clear and informative"},
}

# All artifact types supported by NotebookLM
ARTIFACT_TYPES = [
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
]


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _json_out(data: dict) -> None:
    """Print JSON to stdout."""
    print(json.dumps(data, ensure_ascii=False, indent=2))


def _err(msg: str) -> None:
    """Print progress / status to stderr."""
    print(f"[pipeline] {msg}", file=sys.stderr)


def _json_error(message: str, code: str = "PIPELINE_ERROR") -> None:
    """Print JSON error to stdout and exit 1."""
    _json_out({"error": message, "code": code})
    sys.exit(1)


def _ensure_notebooklm():
    """Ensure notebooklm-py is importable."""
    try:
        from notebooklm import NotebookLMClient  # noqa: F401
    except ImportError:
        _json_error(
            "notebooklm-py not installed. Run: pip install notebooklm-py",
            "IMPORT_ERROR",
        )


def _run_trend_pulse(geo: str = "TW", count: int = 5) -> list[dict]:
    """Run trend-pulse CLI to get trending topics.

    Tries the trend-pulse CLI tool first, then falls back to npx.
    Returns a list of trend dicts with at minimum a 'title' key.
    """
    _err(f"Fetching trending topics (geo={geo}, count={count})...")

    # Try CLI first
    try:
        result = subprocess.run(
            ["trend-pulse", "trending", "--geo", geo, "--count", str(count), "--json"],
            capture_output=True,
            text=True,
            timeout=60,
        )
        if result.returncode == 0 and result.stdout.strip():
            data = json.loads(result.stdout)
            if isinstance(data, list):
                return data[:count]
            elif isinstance(data, dict) and "trends" in data:
                return data["trends"][:count]
            elif isinstance(data, dict) and "items" in data:
                return data["items"][:count]
            return [data] if data else []
    except (FileNotFoundError, subprocess.TimeoutExpired):
        _err("trend-pulse CLI not found or timed out.")
    except json.JSONDecodeError:
        _err("trend-pulse returned non-JSON output.")

    # Try npx fallback
    try:
        result = subprocess.run(
            ["npx", "trend-pulse", "trending", "--geo", geo, "--count", str(count), "--json"],
            capture_output=True,
            text=True,
            timeout=90,
        )
        if result.returncode == 0 and result.stdout.strip():
            data = json.loads(result.stdout)
            if isinstance(data, list):
                return data[:count]
            elif isinstance(data, dict):
                items = data.get("trends") or data.get("items") or []
                return items[:count]
    except (FileNotFoundError, subprocess.TimeoutExpired, json.JSONDecodeError):
        _err("npx trend-pulse fallback also failed.")

    _err("Warning: Could not fetch trends. Returning empty list.")
    return []


def _fetch_rss(url: str, max_entries: int = 20) -> list[dict]:
    """Fetch and parse an RSS/Atom feed.

    Returns list of dicts with: title, link, summary, published.
    """
    _err(f"Fetching RSS feed: {url}")

    try:
        import feedparser
    except ImportError:
        _json_error(
            "feedparser not installed. Run: pip install feedparser",
            "IMPORT_ERROR",
        )

    try:
        feed = feedparser.parse(url)
    except Exception as exc:
        _json_error(f"Failed to parse RSS feed: {exc}", "RSS_ERROR")

    if feed.bozo and not feed.entries:
        _json_error(
            f"RSS feed error: {getattr(feed, 'bozo_exception', 'Unknown error')}",
            "RSS_PARSE_ERROR",
        )

    entries = []
    for entry in feed.entries[:max_entries]:
        entries.append({
            "title": getattr(entry, "title", "Untitled"),
            "link": getattr(entry, "link", ""),
            "summary": getattr(entry, "summary", "")[:500],
            "published": getattr(entry, "published", ""),
        })

    _err(f"Fetched {len(entries)} entries from RSS feed.")
    return entries


# ---------------------------------------------------------------------------
# Workflows
# ---------------------------------------------------------------------------

def workflow_research_to_article(args) -> None:
    """Sources -> notebook -> research questions -> article draft JSON.

    Process:
    1. Create a NotebookLM notebook with the provided sources
    2. Ask a series of research questions to extract key information
    3. Ask for a structured article draft
    4. Output JSON with research findings and article draft
    """
    _ensure_notebooklm()
    from notebooklm import NotebookLMClient

    sources = args.sources or []
    text_sources = args.text_sources or []
    title = args.title or "Research"

    if not sources and not text_sources:
        _json_error("Provide at least one --sources URL or --text-sources.", "NO_SOURCES")

    async def _run():
        async with await NotebookLMClient.from_storage() as client:
            # Step 1: Create notebook + add sources
            _err("Step 1/3: Creating notebook and adding sources...")
            nb = await client.notebooks.create(title=title)
            notebook_id = nb.id
            _err(f"  Notebook created: {notebook_id}")

            sources_added = 0
            for url in sources:
                _err(f"  Adding URL source: {url[:80]}...")
                try:
                    await client.sources.add_url(nb.id, url, wait=True)
                    sources_added += 1
                except Exception as exc:
                    _err(f"  Warning: Failed to add {url}: {exc}")

            for text in text_sources:
                _err(f"  Adding text source ({len(text)} chars)...")
                try:
                    await client.sources.add_text(nb.id, text, wait=True)
                    sources_added += 1
                except Exception as exc:
                    _err(f"  Warning: Failed to add text source: {exc}")

            _err(f"  {sources_added} sources added.")

            # Step 2: Ask research questions
            _err("Step 2/3: Researching with key questions...")
            research_findings = []
            for i, question in enumerate(ARTICLE_QUESTIONS, 1):
                _err(f"  Question {i}/{len(ARTICLE_QUESTIONS)}: {question[:60]}...")
                try:
                    result = await client.chat.ask(nb.id, question)
                    research_findings.append({
                        "question": question,
                        "answer": result.answer,
                        "citations": [c.__dict__ if hasattr(c, '__dict__') else str(c) for c in (result.references or [])],
                    })
                except Exception as exc:
                    _err(f"  Warning: Question {i} failed: {exc}")
                    research_findings.append({
                        "question": question,
                        "answer": f"[Error: {exc}]",
                        "citations": [],
                    })

            # Step 3: Generate article draft
            _err("Step 3/3: Generating article draft...")
            article_prompt = (
                "Based on all the content in this notebook, write a well-structured article draft. "
                "Include: a compelling title, an introduction, 3-5 main sections with headers, "
                "key data points and evidence, and a conclusion with actionable takeaways. "
                "Write in a clear, authoritative style suitable for a technical audience."
            )

            try:
                draft_result = await client.chat.ask(nb.id, article_prompt)
                article_draft = draft_result.answer
            except Exception as exc:
                article_draft = f"[Error: failed to generate article draft: {exc}]"

            _err("Pipeline complete.")
            return {
                "status": "ok",
                "workflow": "research-to-article",
                "title": title,
                "notebook_id": notebook_id,
                "sources": sources,
                "text_sources_count": len(text_sources),
                "sources_added": sources_added,
                "research_findings": research_findings,
                "article_draft": article_draft,
            }

    try:
        result = asyncio.run(_run())
        _json_out(result)
    except KeyboardInterrupt:
        _json_error("Pipeline cancelled by user.", "CANCELLED")
    except Exception as exc:
        _json_error(f"Pipeline error: {exc}", "PIPELINE_ERROR")


def workflow_research_to_social(args) -> None:
    """Sources -> notebook -> summarize -> social post draft JSON.

    Process:
    1. Create a NotebookLM notebook with the provided sources
    2. Get a summary of all content
    3. Generate a social media post draft tailored to the platform
    4. Output JSON with summary and post draft
    """
    _ensure_notebooklm()
    from notebooklm import NotebookLMClient

    sources = args.sources or []
    text_sources = args.text_sources or []
    platform = args.platform or "threads"
    title = args.title or "Social Research"

    if not sources and not text_sources:
        _json_error("Provide at least one --sources URL or --text-sources.", "NO_SOURCES")

    specs = PLATFORM_SPECS.get(platform, PLATFORM_SPECS["generic"])

    async def _run():
        async with await NotebookLMClient.from_storage() as client:
            # Step 1: Create notebook + add sources
            _err("Step 1/3: Creating notebook and adding sources...")
            nb = await client.notebooks.create(title=title)
            notebook_id = nb.id

            for url in sources:
                _err(f"  Adding URL source: {url[:80]}...")
                try:
                    await client.sources.add_url(nb.id, url, wait=True)
                except Exception as exc:
                    _err(f"  Warning: Failed to add {url}: {exc}")

            for text in text_sources:
                try:
                    await client.sources.add_text(nb.id, text, wait=True)
                except Exception as exc:
                    _err(f"  Warning: Failed to add text source: {exc}")

            # Step 2: Get summary
            _err("Step 2/3: Summarizing content...")
            summary_prompt = (
                "Provide a comprehensive summary of all the content in this notebook. "
                "Cover the key points, main arguments, and notable data."
            )
            try:
                summary_result = await client.chat.ask(nb.id, summary_prompt)
                summary = summary_result.answer
            except Exception as exc:
                summary = f"[Error: failed to summarize: {exc}]"

            # Step 3: Generate social post
            _err(f"Step 3/3: Generating {platform} post draft...")
            social_prompt = (
                f"Based on this notebook's content, write a social media post for {platform}. "
                f"Constraints: maximum {specs['max_chars']} characters. "
                f"Style: {specs['style']}. "
                "The post should be engaging, share a key insight or surprising fact, "
                "and make the reader want to learn more. "
                "Also suggest 3 alternative post variations with different angles."
            )

            try:
                social_result = await client.chat.ask(nb.id, social_prompt)
                social_draft = social_result.answer
            except Exception as exc:
                social_draft = f"[Error: failed to generate social post: {exc}]"

            _err("Pipeline complete.")
            return {
                "status": "ok",
                "workflow": "research-to-social",
                "title": title,
                "notebook_id": notebook_id,
                "platform": platform,
                "platform_specs": specs,
                "sources": sources,
                "text_sources_count": len(text_sources),
                "summary": summary,
                "social_draft": social_draft,
            }

    try:
        result = asyncio.run(_run())
        _json_out(result)
    except KeyboardInterrupt:
        _json_error("Pipeline cancelled by user.", "CANCELLED")
    except Exception as exc:
        _json_error(f"Pipeline error: {exc}", "PIPELINE_ERROR")


def workflow_trend_to_content(args) -> None:
    """Trending topics -> notebooks -> research -> content drafts.

    Process:
    1. Fetch trending topics via trend-pulse
    2. For each topic, search for related content (URLs from trend data)
    3. Create a NotebookLM notebook per topic
    4. Research and generate content drafts
    5. Output JSON with all research + drafts
    """
    _ensure_notebooklm()
    from notebooklm import NotebookLMClient

    geo = args.geo or "TW"
    count = args.count or 3
    platform = args.platform or "threads"

    # Step 1: Fetch trends
    _err("Step 1/4: Fetching trending topics...")
    trends = _run_trend_pulse(geo=geo, count=count)

    if not trends:
        _json_error("No trending topics found.", "NO_TRENDS")

    _err(f"Found {len(trends)} trending topics.")

    async def _run():
        async with await NotebookLMClient.from_storage() as client:
            results = []

            for i, trend in enumerate(trends, 1):
                trend_title = trend.get("title") or trend.get("name") or trend.get("query") or f"Trend #{i}"
                trend_urls = []

                # Extract URLs from trend data
                for key in ("url", "link", "newsUrl", "news_url"):
                    if trend.get(key):
                        trend_urls.append(trend[key])

                # Extract related article URLs
                articles = trend.get("articles") or trend.get("news") or trend.get("relatedArticles") or []
                for article in articles:
                    if isinstance(article, dict):
                        for key in ("url", "link"):
                            if article.get(key):
                                trend_urls.append(article[key])
                    elif isinstance(article, str) and article.startswith("http"):
                        trend_urls.append(article)

                _err(f"\nProcessing trend {i}/{len(trends)}: {trend_title} ({len(trend_urls)} URLs)")

                trend_result = {
                    "trend": trend_title,
                    "trend_data": trend,
                    "urls_found": trend_urls,
                    "notebook_id": None,
                    "summary": None,
                    "content_draft": None,
                }

                # Create notebook
                try:
                    nb = await client.notebooks.create(title=f"Trend: {trend_title}")
                    trend_result["notebook_id"] = nb.id
                except Exception as exc:
                    _err(f"  Warning: Failed to create notebook for '{trend_title}': {exc}")
                    results.append(trend_result)
                    continue

                # Add sources
                if trend_urls:
                    for url in trend_urls[:5]:
                        try:
                            await client.sources.add_url(nb.id, url, wait=True)
                        except Exception as exc:
                            _err(f"  Warning: Failed to add URL {url}: {exc}")
                else:
                    # Use trend description as text source
                    desc = trend.get("description") or trend.get("summary") or trend_title
                    try:
                        await client.sources.add_text(nb.id, desc, wait=True)
                    except Exception as exc:
                        _err(f"  Warning: Failed to add text source: {exc}")

                # Summarize
                try:
                    summary_result = await client.chat.ask(nb.id, "Summarize the key points from all sources.")
                    trend_result["summary"] = summary_result.answer
                except Exception as exc:
                    _err(f"  Warning: Failed to summarize '{trend_title}': {exc}")

                # Generate content draft
                specs = PLATFORM_SPECS.get(platform, PLATFORM_SPECS["generic"])
                content_prompt = (
                    f"Based on this trending topic and notebook content, create a {platform} post. "
                    f"Maximum {specs['max_chars']} characters. Style: {specs['style']}. "
                    "Focus on: why this is trending, what people should know, and a unique angle or insight. "
                    "Make it engaging and shareable."
                )

                try:
                    content_result = await client.chat.ask(nb.id, content_prompt)
                    trend_result["content_draft"] = content_result.answer
                except Exception as exc:
                    _err(f"  Warning: Failed to generate content for '{trend_title}': {exc}")

                results.append(trend_result)

            return results

    try:
        results = asyncio.run(_run())
        _err(f"\nPipeline complete. Processed {len(results)} trends.")
        _json_out({
            "status": "ok",
            "workflow": "trend-to-content",
            "geo": geo,
            "platform": platform,
            "trends_requested": count,
            "trends_processed": len(results),
            "results": results,
        })
    except KeyboardInterrupt:
        _json_error("Pipeline cancelled by user.", "CANCELLED")
    except Exception as exc:
        _json_error(f"Pipeline error: {exc}", "PIPELINE_ERROR")


def workflow_batch_digest(args) -> None:
    """RSS feed -> fetch entries -> notebook -> digest summary.

    Process:
    1. Fetch RSS feed entries
    2. Create a NotebookLM notebook with entry URLs
    3. Generate a digest summary
    4. Generate Q&A pairs for key topics
    5. Output JSON with digest + Q&A
    """
    _ensure_notebooklm()
    from notebooklm import NotebookLMClient

    rss_url = args.rss
    title = args.title or "Batch Digest"
    max_entries = args.max_entries or 10
    qa_count = args.qa_count or 5

    if not rss_url:
        _json_error("--rss URL is required.", "MISSING_RSS")

    # Step 1: Fetch RSS
    _err("Step 1/4: Fetching RSS feed...")
    entries = _fetch_rss(rss_url, max_entries=max_entries)

    if not entries:
        _json_error("No entries found in RSS feed.", "EMPTY_FEED")

    # Separate URLs and text-only entries
    urls = [e["link"] for e in entries if e.get("link")]
    text_entries = [e for e in entries if not e.get("link")]

    if not urls and not text_entries:
        _json_error("No usable content from RSS feed entries.", "NO_CONTENT")

    async def _run():
        async with await NotebookLMClient.from_storage() as client:
            # Step 2: Create notebook with entry URLs
            _err("Step 2/4: Creating notebook with feed entries...")
            nb = await client.notebooks.create(title=title)
            notebook_id = nb.id

            for url in urls[:10]:  # NotebookLM has source limits
                try:
                    await client.sources.add_url(nb.id, url, wait=True)
                except Exception as exc:
                    _err(f"  Warning: Failed to add {url}: {exc}")

            for e in text_entries[:5]:
                text = f"Title: {e['title']}\n\n{e.get('summary', '')}"
                try:
                    await client.sources.add_text(nb.id, text, wait=True)
                except Exception as exc:
                    _err(f"  Warning: Failed to add text source: {exc}")

            # Step 3: Generate digest summary
            _err("Step 3/4: Generating digest summary...")
            digest_prompt = (
                "Create a comprehensive digest of all the articles/content in this notebook. "
                "Format as a newsletter-style digest with:\n"
                "1. A brief executive summary (2-3 sentences)\n"
                "2. Key highlights from each article/source\n"
                "3. Common themes across all content\n"
                "4. Top 3 takeaways for the reader"
            )

            try:
                digest_result = await client.chat.ask(nb.id, digest_prompt)
                digest_text = digest_result.answer
            except Exception as exc:
                digest_text = f"[Error: failed to generate digest: {exc}]"

            # Step 4: Generate Q&A
            _err("Step 4/4: Generating key Q&A pairs...")
            qa_pairs = []
            qa_prompt = (
                f"Based on all the content in this notebook, generate {qa_count} "
                "important questions and their detailed answers. Format each as:\n"
                "Q: [question]\nA: [answer]\n\n"
                "Focus on the most insightful and actionable information."
            )

            try:
                qa_result = await client.chat.ask(nb.id, qa_prompt)
                # Parse Q&A from response text
                qa_text = qa_result.answer
                # Simple parsing: split by Q: markers
                parts = qa_text.split("Q:")
                for part in parts[1:]:  # skip first empty split
                    if "A:" in part:
                        q, a = part.split("A:", 1)
                        qa_pairs.append({
                            "question": q.strip(),
                            "answer": a.strip(),
                        })
            except Exception as exc:
                _err(f"  Warning: Failed to generate Q&A: {exc}")

            _err("Pipeline complete.")
            return {
                "status": "ok",
                "workflow": "batch-digest",
                "title": title,
                "notebook_id": notebook_id,
                "rss_url": rss_url,
                "entries_fetched": len(entries),
                "entries": entries,
                "urls_added": len(urls),
                "digest": digest_text,
                "qa_pairs": qa_pairs,
            }

    try:
        result = asyncio.run(_run())
        _json_out(result)
    except KeyboardInterrupt:
        _json_error("Pipeline cancelled by user.", "CANCELLED")
    except Exception as exc:
        _json_error(f"Pipeline error: {exc}", "PIPELINE_ERROR")


def workflow_generate_all(args) -> None:
    """Sources -> notebook -> generate all artifact types -> download all.

    Process:
    1. Create a NotebookLM notebook with the provided sources
    2. Generate all requested artifact types (audio, video, slides, report, etc.)
    3. Wait for generation to complete
    4. Download all artifacts to output directory
    5. Output JSON with artifact paths and metadata
    """
    _ensure_notebooklm()
    from notebooklm import NotebookLMClient

    sources = args.sources or []
    text_sources = args.text_sources or []
    title = args.title or "Research"
    output_dir = Path(args.output_dir or "./notebooklm-output")
    language = args.language or "en"
    types = args.types or ARTIFACT_TYPES

    if not sources and not text_sources:
        _json_error("Provide at least one --sources URL or --text-sources.", "NO_SOURCES")

    # Map artifact type names to API method names
    GENERATE_METHODS = {
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

    DOWNLOAD_METHODS = {
        "audio": "download_audio",
        "video": "download_video",
        "slides": "download_slide_deck",
        "report": "download_report",
        "quiz": "download_quiz",
        "flashcards": "download_flashcards",
        "mind-map": "download_mind_map",
        "infographic": "download_infographic",
        "data-table": "download_data_table",
        "study-guide": "download_report",
    }

    FILE_EXTENSIONS = {
        "audio": "m4a",
        "video": "mp4",
        "slides": "pdf",
        "report": "md",
        "quiz": "json",
        "flashcards": "json",
        "mind-map": "json",
        "infographic": "png",
        "data-table": "csv",
        "study-guide": "md",
    }

    async def _run():
        async with await NotebookLMClient.from_storage() as client:
            # Step 1: Create notebook + add sources
            _err("Step 1/4: Creating notebook and adding sources...")
            nb = await client.notebooks.create(title=title)
            notebook_id = nb.id
            _err(f"  Notebook created: {notebook_id}")

            sources_added = 0
            for url in sources:
                _err(f"  Adding URL source: {url[:80]}...")
                try:
                    await client.sources.add_url(nb.id, url, wait=True)
                    sources_added += 1
                except Exception as exc:
                    _err(f"  Warning: Failed to add {url}: {exc}")

            for text in text_sources:
                try:
                    await client.sources.add_text(nb.id, text, wait=True)
                    sources_added += 1
                except Exception as exc:
                    _err(f"  Warning: Failed to add text source: {exc}")

            _err(f"  {sources_added} sources added.")

            # Step 2: Create output directory
            output_dir.mkdir(parents=True, exist_ok=True)

            # Step 3: Generate all artifact types
            _err(f"Step 2/4: Generating {len(types)} artifact types...")
            generation_tasks = {}
            for artifact_type in types:
                generate_method_name = GENERATE_METHODS.get(artifact_type)
                if not generate_method_name:
                    _err(f"  Warning: Unknown artifact type '{artifact_type}', skipping.")
                    continue

                _err(f"  Generating {artifact_type}...")
                try:
                    generate_method = getattr(client.artifacts, generate_method_name)
                    kwargs = {}
                    if artifact_type in ("audio", "video", "slides", "report",
                                         "infographic", "data-table", "study-guide"):
                        kwargs["language"] = language
                    status = await generate_method(nb.id, **kwargs)
                    generation_tasks[artifact_type] = status.task_id
                    _err(f"  {artifact_type} generation started (task: {status.task_id})")
                except Exception as exc:
                    _err(f"  Warning: Failed to start {artifact_type} generation: {exc}")

            # Step 4: Wait for completion + download
            _err(f"Step 3/4: Waiting for {len(generation_tasks)} artifacts to complete...")
            artifacts = []
            for artifact_type, task_id in generation_tasks.items():
                _err(f"  Waiting for {artifact_type} (task: {task_id})...")
                try:
                    await client.artifacts.wait_for_completion(nb.id, task_id, timeout=3600)
                    _err(f"  {artifact_type} generation complete.")
                except Exception as exc:
                    _err(f"  Warning: {artifact_type} generation failed or timed out: {exc}")
                    artifacts.append({
                        "type": artifact_type,
                        "status": "failed",
                        "error": str(exc),
                    })
                    continue

                # Download
                ext = FILE_EXTENSIONS.get(artifact_type, "bin")
                output_path = output_dir / f"{artifact_type}.{ext}"
                download_method_name = DOWNLOAD_METHODS.get(artifact_type)

                try:
                    download_method = getattr(client.artifacts, download_method_name)
                    await download_method(nb.id, output_path=str(output_path))
                    _err(f"  Downloaded {artifact_type} -> {output_path}")
                    artifacts.append({
                        "type": artifact_type,
                        "status": "ok",
                        "path": str(output_path),
                        "size_bytes": output_path.stat().st_size if output_path.exists() else 0,
                    })
                except Exception as exc:
                    _err(f"  Warning: Failed to download {artifact_type}: {exc}")
                    artifacts.append({
                        "type": artifact_type,
                        "status": "download_failed",
                        "error": str(exc),
                    })

            _err("Step 4/4: Pipeline complete.")
            succeeded = [a for a in artifacts if a["status"] == "ok"]
            failed = [a for a in artifacts if a["status"] != "ok"]

            return {
                "status": "ok",
                "workflow": "generate-all",
                "title": title,
                "notebook_id": notebook_id,
                "sources": sources,
                "text_sources_count": len(text_sources),
                "sources_added": sources_added,
                "output_dir": str(output_dir),
                "language": language,
                "artifacts_requested": len(types),
                "artifacts_succeeded": len(succeeded),
                "artifacts_failed": len(failed),
                "artifacts": artifacts,
            }

    try:
        result = asyncio.run(_run())
        _json_out(result)
    except KeyboardInterrupt:
        _json_error("Pipeline cancelled by user.", "CANCELLED")
    except Exception as exc:
        _json_error(f"Pipeline error: {exc}", "PIPELINE_ERROR")


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------

def main() -> None:
    parser = argparse.ArgumentParser(
        description="NotebookLM Pipeline Orchestrator - High-level content workflows (notebooklm-py v0.3.4)",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Workflows:

  research-to-article
    Takes URLs/text sources, creates a notebook, researches with key questions,
    and outputs a structured article draft.

    python pipeline.py research-to-article \\
        --sources https://example.com/article1 https://example.com/article2 \\
        --title "AI Trends 2026"

  research-to-social
    Takes URLs/text sources, summarizes content, and generates platform-specific
    social media post drafts.

    python pipeline.py research-to-social \\
        --sources https://example.com/article \\
        --platform threads --title "AI News"

  trend-to-content
    Fetches trending topics via trend-pulse, creates notebooks for each,
    researches them, and generates content drafts.

    python pipeline.py trend-to-content --geo TW --count 3 --platform threads

  batch-digest
    Fetches an RSS feed, creates a notebook with the entries, and generates
    a newsletter-style digest with Q&A pairs.

    python pipeline.py batch-digest \\
        --rss https://example.com/feed.xml \\
        --title "Weekly AI Digest" --max-entries 15

  generate-all
    Creates a notebook, generates all artifact types (audio, video, slides,
    report, quiz, flashcards, mind-map, infographic, data-table, study-guide),
    waits for completion, and downloads everything.

    python pipeline.py generate-all \\
        --sources https://example.com/article \\
        --title "Research" --output-dir ./output --language zh-TW
        """,
    )

    subparsers = parser.add_subparsers(dest="workflow", help="Workflow to run")

    # research-to-article
    p_article = subparsers.add_parser(
        "research-to-article",
        help="Sources -> research -> article draft",
    )
    p_article.add_argument("--sources", nargs="*", default=[], help="URL sources")
    p_article.add_argument("--text-sources", nargs="*", default=[], help="Raw text sources")
    p_article.add_argument("--title", default="Research", help="Research title")

    # research-to-social
    p_social = subparsers.add_parser(
        "research-to-social",
        help="Sources -> summarize -> social post draft",
    )
    p_social.add_argument("--sources", nargs="*", default=[], help="URL sources")
    p_social.add_argument("--text-sources", nargs="*", default=[], help="Raw text sources")
    p_social.add_argument("--platform", default="threads",
                          choices=list(PLATFORM_SPECS.keys()),
                          help="Target platform (default: threads)")
    p_social.add_argument("--title", default="Social Research", help="Research title")

    # trend-to-content
    p_trend = subparsers.add_parser(
        "trend-to-content",
        help="Trending topics -> research -> content drafts",
    )
    p_trend.add_argument("--geo", default="TW", help="Geo for trends (default: TW)")
    p_trend.add_argument("--count", type=int, default=3, help="Number of trends (default: 3)")
    p_trend.add_argument("--platform", default="threads",
                         choices=list(PLATFORM_SPECS.keys()),
                         help="Target platform (default: threads)")

    # batch-digest
    p_digest = subparsers.add_parser(
        "batch-digest",
        help="RSS feed -> notebook -> digest summary",
    )
    p_digest.add_argument("--rss", required=True, help="RSS/Atom feed URL")
    p_digest.add_argument("--title", default="Batch Digest", help="Digest title")
    p_digest.add_argument("--max-entries", type=int, default=10, help="Max RSS entries (default: 10)")
    p_digest.add_argument("--qa-count", type=int, default=5, help="Q&A pairs to generate (default: 5)")

    # generate-all
    p_generate = subparsers.add_parser(
        "generate-all",
        help="Sources -> notebook -> generate all artifact types -> download",
    )
    p_generate.add_argument("--sources", nargs="*", default=[], help="URL sources")
    p_generate.add_argument("--text-sources", nargs="*", default=[], help="Raw text sources")
    p_generate.add_argument("--title", default="Research", help="Notebook title")
    p_generate.add_argument("--output-dir", default="./notebooklm-output", help="Download directory (default: ./notebooklm-output)")
    p_generate.add_argument("--language", default="en", help="Language for audio/video (default: en)")
    p_generate.add_argument("--types", nargs="*", default=ARTIFACT_TYPES,
                            choices=ARTIFACT_TYPES,
                            help=f"Artifact types to generate (default: all). Options: {', '.join(ARTIFACT_TYPES)}")

    args = parser.parse_args()

    if not args.workflow:
        parser.print_help()
        sys.exit(1)

    workflow_map = {
        "research-to-article": workflow_research_to_article,
        "research-to-social": workflow_research_to_social,
        "trend-to-content": workflow_trend_to_content,
        "batch-digest": workflow_batch_digest,
        "generate-all": workflow_generate_all,
    }

    try:
        workflow_map[args.workflow](args)
    except KeyboardInterrupt:
        _json_error("Pipeline cancelled by user.", "CANCELLED")
    except SystemExit:
        raise  # Let sys.exit() propagate
    except Exception as exc:
        _json_error(f"Pipeline error: {exc}", "PIPELINE_ERROR")


if __name__ == "__main__":
    main()
