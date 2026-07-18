from __future__ import annotations

import json
from types import SimpleNamespace
from unittest.mock import AsyncMock

import pytest

from scripts import pipeline
from scripts.common import AuthenticationRequired, UsageError
from tests.conftest import client_context, record


def use_client(monkeypatch, client):
    monkeypatch.setattr(pipeline, "get_client", lambda: client_context(client))


def test_parser_has_five_workflows_and_source_options():
    parser = pipeline.build_parser()
    choices = next(action for action in parser._actions if action.dest == "workflow").choices
    assert set(choices) == {
        "research-to-article",
        "research-to-social",
        "trend-to-content",
        "batch-digest",
        "generate-all",
    }
    args = parser.parse_args(
        [
            "--profile",
            "work",
            "research-to-article",
            "--text-sources",
            "notes",
            "--audience",
            "engineers",
        ]
    )
    assert args.profile == "work" and pipeline._has_source_inputs(args)


@pytest.mark.asyncio
async def test_ask_and_ask_many_partial(client):
    good = await pipeline._ask(client, "nb", "question")
    assert good["status"] == "ok" and good["references"]
    client.chat.ask.side_effect = [record(answer="A", references=[]), RuntimeError("bad")]
    answers = await pipeline._ask_many(client, "nb", ["one", "two"], concurrency=1)
    assert [item["status"] for item in answers] == ["ok", "failed"]


@pytest.mark.asyncio
async def test_research_to_article_success_partial_and_no_sources(monkeypatch, client):
    use_client(monkeypatch, client)
    args = pipeline.build_parser().parse_args(["research-to-article", "--text-sources", "notes", "--title", "Article"])
    result = await pipeline.workflow_research_to_article(args)
    assert result["status"] == "ok"
    assert result["notebook"]["sources_count"] == 1
    assert len(result["research_findings"]) == 5
    assert result["article"]["answer"].startswith("Grounded")

    client.sources.add_text.side_effect = RuntimeError("rejected")
    failed = await pipeline.workflow_research_to_article(args)
    assert failed["status"] == "failed" and "skipped" in failed["error"]

    empty = pipeline.build_parser().parse_args(["research-to-article"])
    with pytest.raises(UsageError, match="Provide"):
        await pipeline.workflow_research_to_article(empty)


@pytest.mark.asyncio
async def test_research_to_social_statuses(monkeypatch, client):
    use_client(monkeypatch, client)
    args = pipeline.build_parser().parse_args(
        [
            "research-to-social",
            "--text-sources",
            "notes",
            "--platform",
            "threads",
            "--variants",
            "2",
        ]
    )
    result = await pipeline.workflow_research_to_social(args)
    assert result["status"] == "ok"
    assert result["platform_specs"]["max_chars"] == 500
    client.chat.ask.side_effect = [RuntimeError("summary"), record(answer="draft", references=[])]
    partial = await pipeline.workflow_research_to_social(args)
    assert partial["status"] == "partial"


def test_trend_url_extraction_deduplicates_and_validates():
    urls = pipeline._trend_urls(
        {
            "url": "https://example.com/a",
            "news": [
                "https://example.com/a",
                {"link": "https://example.com/b"},
                {"url": "file:///bad"},
            ],
        }
    )
    assert urls == ["https://example.com/a", "https://example.com/b"]


@pytest.mark.asyncio
async def test_trend_to_content_ok_partial_failed(monkeypatch, client):
    use_client(monkeypatch, client)
    monkeypatch.setattr(
        pipeline,
        "fetch_trends",
        AsyncMock(
            return_value=[
                {"title": "One", "url": "https://example.com/one"},
                {"title": "Two", "description": "context"},
            ]
        ),
    )
    args = pipeline.build_parser().parse_args(["trend-to-content", "--count", "2", "--platform", "threads"])
    result = await pipeline.workflow_trend_to_content(args)
    assert result["status"] == "ok" and result["trends_processed"] == 2

    monkeypatch.setattr(pipeline, "run_research", AsyncMock(side_effect=RuntimeError("research")))
    client.sources.add_url.side_effect = RuntimeError("source")
    client.sources.add_text.side_effect = RuntimeError("source")
    failed = await pipeline.workflow_trend_to_content(args)
    assert failed["status"] == "failed"
    monkeypatch.setattr(pipeline, "fetch_trends", AsyncMock(return_value=[]))
    with pytest.raises(RuntimeError, match="no usable"):
        await pipeline.workflow_trend_to_content(args)


def test_parse_qa():
    assert pipeline._parse_qa("Q1: Why?\nA1: Because.\nQ2: How?\nA2: Carefully.") == [
        {"question": "Why?", "answer": "Because."},
        {"question": "How?", "answer": "Carefully."},
    ]
    assert pipeline._parse_qa("not formatted") == []


@pytest.mark.asyncio
async def test_batch_digest_url_and_text_entries(monkeypatch, client):
    use_client(monkeypatch, client)
    monkeypatch.setattr(
        pipeline,
        "fetch_rss_entries",
        AsyncMock(
            return_value=[
                {
                    "title": "Linked",
                    "link": "https://example.com/a",
                    "summary": "A",
                    "published": "Today",
                },
                {"title": "Text", "link": "", "summary": "B", "published": "Today"},
            ]
        ),
    )
    client.chat.ask.side_effect = [
        record(answer="Digest", references=[]),
        record(answer="Q: Why?\nA: Evidence [1]", references=[]),
    ]
    args = pipeline.build_parser().parse_args(["batch-digest", "--rss", "https://example.com/feed"])
    result = await pipeline.workflow_batch_digest(args)
    assert result["status"] == "ok" and result["entries_fetched"] == 2
    assert result["qa_pairs"][0]["question"] == "Why?"
    monkeypatch.setattr(pipeline, "fetch_rss_entries", AsyncMock(return_value=[]))
    with pytest.raises(RuntimeError, match="no entries"):
        await pipeline.workflow_batch_digest(args)


@pytest.mark.asyncio
async def test_generate_all_wait_download_detached_and_errors(monkeypatch, client, tmp_path):
    use_client(monkeypatch, client)
    args = pipeline.build_parser().parse_args(
        [
            "generate-all",
            "--text-sources",
            "notes",
            "--types",
            "slides",
            "mind-map",
            "--output-dir",
            str(tmp_path / "out"),
        ]
    )
    result = await pipeline.workflow_generate_all(args)
    assert result["status"] == "ok" and result["artifacts_succeeded"] == 2
    assert {item["type"] for item in result["artifacts"]} == {"slides", "mind-map"}

    detached_args = pipeline.build_parser().parse_args(
        [
            "generate-all",
            "--text-sources",
            "notes",
            "--types",
            "audio",
            "--no-wait",
            "--no-download",
        ]
    )
    detached = await pipeline.workflow_generate_all(detached_args)
    assert detached["status"] == "started"

    bad = pipeline.build_parser().parse_args(["generate-all", "--text-sources", "notes", "--no-wait"])
    with pytest.raises(UsageError, match="requires"):
        await pipeline.workflow_generate_all(bad)
    missing = pipeline.build_parser().parse_args(["generate-all"])
    with pytest.raises(UsageError, match="Provide"):
        await pipeline.workflow_generate_all(missing)

    symlink = tmp_path / "link"
    symlink.symlink_to(tmp_path / "elsewhere")
    symlink_args = pipeline.build_parser().parse_args(
        ["generate-all", "--text-sources", "notes", "--output-dir", str(symlink)]
    )
    with pytest.raises(UsageError, match="symlink"):
        await pipeline.workflow_generate_all(symlink_args)


@pytest.mark.asyncio
async def test_dispatch(monkeypatch):
    operation = AsyncMock(return_value={"status": "ok"})
    monkeypatch.setitem(pipeline.WORKFLOWS, "batch-digest", operation)
    args = SimpleNamespace(workflow="batch-digest")
    assert await pipeline.dispatch(args) == {"status": "ok"}


@pytest.mark.parametrize(
    ("exception", "exit_code", "code"),
    [
        (AuthenticationRequired("login"), 4, "AUTH_REQUIRED"),
        (UsageError("bad"), 2, "INVALID_ARGUMENT"),
        (TimeoutError("slow"), 1, "TIMEOUT"),
        (RuntimeError("boom"), 1, "PIPELINE_ERROR"),
        (KeyboardInterrupt(), 130, "CANCELLED"),
    ],
)
def test_run_errors(monkeypatch, capsys, exception, exit_code, code):
    async def fail(_args):
        raise exception

    monkeypatch.setattr(pipeline, "dispatch", fail)
    assert pipeline.run(["batch-digest", "--rss", "https://example.com/feed"]) == exit_code
    assert json.loads(capsys.readouterr().out)["code"] == code


def test_run_status_and_version(monkeypatch, capsys):
    async def okay(args):
        return {"status": "failed" if args.profile == "bad" else "partial"}

    monkeypatch.setattr(pipeline, "dispatch", okay)
    assert pipeline.run(["--profile", "work", "batch-digest", "--rss", "https://x.test"]) == 0
    assert json.loads(capsys.readouterr().out)["status"] == "partial"
    assert pipeline.run(["--profile", "bad", "batch-digest", "--rss", "https://x.test"]) == 1
    capsys.readouterr()
    monkeypatch.setattr(pipeline, "version", lambda _name: "2.0")
    assert pipeline._package_version() == "2.0"
