from __future__ import annotations

from unittest.mock import AsyncMock

import pytest

from mcp_server import tools
from scripts.common import UsageError
from tests.conftest import client_context, record


def use_client(monkeypatch, client):
    monkeypatch.setattr(tools, "get_client", lambda: client_context(client))


@pytest.mark.asyncio
async def test_notebook_crud_and_mixed_sources(monkeypatch, client):
    use_client(monkeypatch, client)
    created = await tools.create_notebook(" Research ", ["https://example.com"], ["text"], [])
    assert created["status"] == "ok" and created["source_summary"]["succeeded"] == 2
    assert created["notebook"]["sources_count"] == 2
    listed = await tools.list_notebooks()
    assert listed["count"] == 1
    deleted = await tools.delete_notebook("nb-1")
    assert deleted["deleted"] is True
    with pytest.raises(UsageError, match="empty"):
        await tools.create_notebook(" ")


@pytest.mark.asyncio
@pytest.mark.parametrize(
    ("kwargs", "method"),
    [
        ({"url": "https://example.com"}, "add_url"),
        ({"text": "notes", "text_title": "Notes"}, "add_text"),
    ],
)
async def test_add_source_kinds(monkeypatch, client, kwargs, method):
    use_client(monkeypatch, client)
    result = await tools.add_source("nb-1", **kwargs)
    assert result["source"]["id"] == "src-1"
    getattr(client.sources, method).assert_awaited_once()


@pytest.mark.asyncio
async def test_add_file_and_validation(monkeypatch, client, tmp_path):
    use_client(monkeypatch, client)
    path = tmp_path / "file.pdf"
    path.write_bytes(b"pdf")
    assert (await tools.add_source("nb-1", file_path=str(path)))["status"] == "ok"
    with pytest.raises(UsageError, match="exactly one"):
        await tools.add_source("nb-1")
    with pytest.raises(UsageError, match="exactly one"):
        await tools.add_source("nb-1", url="https://example.com", text="x")
    with pytest.raises(UsageError, match="empty"):
        await tools.add_source("nb-1", text=" ")
    with pytest.raises(UsageError, match="not found"):
        await tools.add_source("nb-1", file_path=str(tmp_path / "missing"))


@pytest.mark.asyncio
async def test_chat_summary_sources_and_artifacts(monkeypatch, client):
    use_client(monkeypatch, client)
    assert (await tools.ask("nb-1", "Evidence?"))["references"]
    with pytest.raises(UsageError):
        await tools.ask("nb-1", " ")
    assert (await tools.summarize("nb-1"))["summary"] == "Notebook summary"
    assert (await tools.list_sources("nb-1"))["count"] == 1
    listed = await tools.list_artifacts("nb-1", "slides")
    assert listed["count"] == 1 and listed["artifact_type"] == "slides"


@pytest.mark.asyncio
async def test_generate_download_and_research(monkeypatch, client, tmp_path):
    use_client(monkeypatch, client)
    generated = await tools.generate_artifact(
        "nb-1",
        "audio",
        lang="zh-TW",
        instructions="Focus",
        options={"audio_length": "short"},
        wait=False,
    )
    assert generated["status"] == "started" and generated["notebook_id"] == "nb-1"
    downloaded = await tools.download_artifact("nb-1", "report", str(tmp_path / "report.md"), artifact_id="report-1")
    assert downloaded["artifact_id"] == "report-1"
    researched = await tools.research("nb-1", "evidence", mode="deep", max_sources=1)
    assert researched["state"] == "completed"


@pytest.mark.asyncio
@pytest.mark.parametrize("output_format", ["article", "thread", "report"])
async def test_research_pipeline_formats(monkeypatch, client, output_format):
    use_client(monkeypatch, client)
    result = await tools.research_pipeline(["https://example.com"], ["What?", "Why?"], output_format, "Research")
    assert result["status"] == "ok"
    assert result["content"]
    if output_format == "thread":
        assert result["content"].startswith("1/")
    if output_format == "report":
        assert result["content"].startswith("## What?")


@pytest.mark.asyncio
async def test_research_pipeline_validation_and_failures(monkeypatch, client):
    use_client(monkeypatch, client)
    for sources, questions, output in [
        ([], ["q"], "article"),
        (["https://x"], [], "article"),
        (["https://x"], ["q"], "bad"),
    ]:
        with pytest.raises(UsageError):
            await tools.research_pipeline(sources, questions, output)
    with pytest.raises(UsageError, match="at most"):
        await tools.research_pipeline(["https://x"] * 51, ["q"])

    client.sources.add_url.side_effect = RuntimeError("source")
    failed = await tools.research_pipeline(["https://example.com"], ["q"])
    assert failed["status"] == "failed"

    client.sources.add_url.side_effect = None
    client.sources.add_url.return_value = record(id="s", title="S")
    client.chat.ask.side_effect = RuntimeError("chat")
    failed_questions = await tools.research_pipeline(["https://example.com"], ["q"])
    assert failed_questions["status"] == "failed"


@pytest.mark.asyncio
async def test_trend_research_status_and_validation(monkeypatch, client):
    use_client(monkeypatch, client)
    monkeypatch.setattr(tools, "fetch_trends", AsyncMock(return_value=[{"title": "One"}, {"title": "Two"}]))
    result = await tools.trend_research("TW", 2, "threads")
    assert result["status"] == "ok" and result["trends_processed"] == 2
    with pytest.raises(UsageError, match="Unsupported"):
        await tools.trend_research(platform="fax")
    monkeypatch.setattr(tools, "fetch_trends", AsyncMock(return_value=[]))
    with pytest.raises(RuntimeError, match="no usable"):
        await tools.trend_research()

    monkeypatch.setattr(tools, "fetch_trends", AsyncMock(return_value=[{"title": "Bad"}]))
    client.notebooks.create.side_effect = RuntimeError("create")
    failed = await tools.trend_research()
    assert failed["status"] == "failed"


def test_supported_types_match_common():
    assert "infographic" in tools.SUPPORTED_ARTIFACT_TYPES
    assert len(tools.SUPPORTED_ARTIFACT_TYPES) == 11
