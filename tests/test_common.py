from __future__ import annotations

import asyncio
import json
import sys
from dataclasses import dataclass
from datetime import date
from enum import Enum
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import AsyncMock

import httpx
import pytest

from scripts import common
from scripts.common import AuthenticationRequired, UsageError
from tests.conftest import record


@dataclass
class Payload:
    name: str
    hidden: str = "kept"


class Choice(Enum):
    ONE = "one"


def test_storage_path_auth_message_and_language(monkeypatch, tmp_path):
    monkeypatch.setenv("NOTEBOOKLM_HOME", str(tmp_path))
    monkeypatch.setenv("NOTEBOOKLM_PROFILE", "work")
    path = common.storage_path()
    assert path == tmp_path / "profiles" / "work" / "storage_state.json"
    assert str(path) in common.authentication_message()
    assert common.normalize_language(None) == "en"
    assert common.normalize_language("zh-TW") == "zh_Hant"
    assert common.normalize_language("de") == "de"


def test_storage_path_legacy_fallback(monkeypatch):
    monkeypatch.setitem(sys.modules, "notebooklm.paths", None)
    assert common.storage_path().name == "storage_state.json"


def test_generic_and_stable_serializers(notebook, source):
    obj = SimpleNamespace(public="yes", _secret="no")
    value = {
        "enum": Choice.ONE,
        "date": date(2026, 7, 18),
        "path": Path("a"),
        "data": Payload("x"),
        "set": {1, 2},
        "object": obj,
    }
    serialized = common.serialize(value)
    assert serialized["enum"] == "one"
    assert serialized["date"] == "2026-07-18"
    assert serialized["path"] == "a"
    assert serialized["data"]["name"] == "x"
    assert serialized["object"] == {"public": "yes"}
    assert common.serialize(object())
    assert common.serialize_notebook(notebook)["sources_count"] == 2
    assert common.serialize_source(source)["url"] == "https://example.com"
    artifact = record(id="a", title="A", kind="audio", status="completed", url="secret")
    assert "url" not in common.serialize_artifact(artifact)


@pytest.mark.asyncio
async def test_resolve_notebook_id_exact_partial_and_errors(client):
    duplicate = record(id="nb-2", title="Research")
    other = record(id="nb-3", title="Research Archive")
    assert (await common.resolve_notebook(client, "nb-1")).id == "nb-1"
    assert (await common.resolve_notebook(client, "research")).id == "nb-1"
    client.notebooks.list.return_value = [record(id="x", title="Unique Project"), other]
    assert (await common.resolve_notebook(client, "unique")).id == "x"
    client.notebooks.list.return_value = [record(id="x", title="Alpha"), record(id="y", title="Alpha two")]
    with pytest.raises(UsageError, match="ambiguous"):
        await common.resolve_notebook(client, "alp")
    client.notebooks.list.return_value = [record(id="x", title="Alpha"), duplicate]
    with pytest.raises(UsageError, match="not found"):
        await common.resolve_notebook(client, "missing")
    with pytest.raises(UsageError, match="empty"):
        await common.resolve_notebook(client, " ")


def test_validate_url():
    assert common.validate_url(" https://example.com/a ") == "https://example.com/a"
    for bad in ("file:///etc/passwd", "example.com", "javascript:alert(1)"):
        with pytest.raises(UsageError, match="Invalid"):
            common.validate_url(bad)


class FakeProcess:
    def __init__(self, stdout=b"[]", stderr=b"", returncode=0):
        self.stdout = stdout
        self.stderr = stderr
        self.returncode = returncode

    async def communicate(self):
        return self.stdout, self.stderr


@pytest.mark.asyncio
async def test_fetch_trends_normalizes_payload(monkeypatch):
    payload = {
        "merged": [
            "One",
            {"keyword": "Two", "score": 9},
            {"query": "Three"},
            {"title": ""},
            7,
        ]
    }
    create = AsyncMock(return_value=FakeProcess(json.dumps(payload).encode()))
    monkeypatch.setattr(asyncio, "create_subprocess_exec", create)
    trends = await common.fetch_trends("TW", 3)
    assert [item["title"] for item in trends] == ["One", "Two", "Three"]
    assert create.await_args.args[-5:] == (
        "trending",
        "--geo",
        "TW",
        "--count",
        "3",
    )


@pytest.mark.asyncio
async def test_fetch_trends_failures(monkeypatch):
    with pytest.raises(UsageError):
        await common.fetch_trends("TW", 0)
    monkeypatch.setenv("TREND_PULSE_CMD", "")
    with pytest.raises(UsageError, match="empty"):
        await common.fetch_trends("TW", 1)
    monkeypatch.setenv("TREND_PULSE_CMD", "missing")
    monkeypatch.setattr(asyncio, "create_subprocess_exec", AsyncMock(side_effect=FileNotFoundError))
    with pytest.raises(RuntimeError, match="not installed"):
        await common.fetch_trends("TW", 1)
    monkeypatch.setattr(
        asyncio,
        "create_subprocess_exec",
        AsyncMock(return_value=FakeProcess(stderr=b"rate limited", returncode=2)),
    )
    with pytest.raises(RuntimeError, match="rate limited"):
        await common.fetch_trends("TW", 1)
    monkeypatch.setattr(asyncio, "create_subprocess_exec", AsyncMock(return_value=FakeProcess(stdout=b"{")))
    with pytest.raises(RuntimeError, match="invalid JSON"):
        await common.fetch_trends("TW", 1)
    monkeypatch.setattr(
        asyncio,
        "create_subprocess_exec",
        AsyncMock(return_value=FakeProcess(stdout=b'{"trends": {"bad": 1}}')),
    )
    with pytest.raises(RuntimeError, match="list"):
        await common.fetch_trends("TW", 1)


class FakeResponse:
    def __init__(self, chunks, status_error=None):
        self.chunks = chunks
        self.status_error = status_error

    async def __aenter__(self):
        return self

    async def __aexit__(self, *_args):
        return False

    def raise_for_status(self):
        if self.status_error:
            raise self.status_error

    async def aiter_bytes(self):
        for chunk in self.chunks:
            yield chunk


class FakeHTTP:
    response = None

    def __init__(self, **kwargs):
        self.kwargs = kwargs

    async def __aenter__(self):
        return self

    async def __aexit__(self, *_args):
        return False

    def stream(self, method, url):
        assert method == "GET" and url.startswith("https://")
        return self.response


@pytest.mark.asyncio
async def test_fetch_rss_entries_and_limits(monkeypatch):
    xml = b"""<rss version='2.0'><channel><item><title>One</title>
    <link>https://example.com/one</link><description>Summary</description>
    <pubDate>Today</pubDate></item></channel></rss>"""
    FakeHTTP.response = FakeResponse([xml])
    monkeypatch.setattr(httpx, "AsyncClient", FakeHTTP)
    entries = await common.fetch_rss_entries("https://example.com/feed", max_entries=1)
    assert entries == [
        {
            "title": "One",
            "link": "https://example.com/one",
            "summary": "Summary",
            "published": "Today",
        }
    ]
    with pytest.raises(UsageError):
        await common.fetch_rss_entries("https://example.com", max_entries=0)
    with pytest.raises(UsageError):
        await common.fetch_rss_entries("https://example.com", timeout=0)
    FakeHTTP.response = FakeResponse([b"123", b"456"])
    with pytest.raises(RuntimeError, match="safety limit"):
        await common.fetch_rss_entries("https://example.com/feed", max_bytes=5)


@pytest.mark.asyncio
async def test_ingest_sources_success_failure_and_validation(client, tmp_path):
    file_path = tmp_path / "paper.pdf"
    file_path.write_bytes(b"pdf")
    client.sources.add_text.side_effect = RuntimeError("text rejected")
    results = await common.ingest_sources(
        client,
        "nb-1",
        urls=["https://example.com"],
        texts=["notes"],
        files=[file_path, tmp_path / "missing"],
        concurrency=2,
    )
    assert [item["status"] for item in results] == ["ok", "failed", "ok", "failed"]
    assert common.source_result_summary(results) == {"requested": 4, "succeeded": 2, "failed": 2}
    client.sources.add_text.assert_awaited_once_with(
        "nb-1", title="Text Source 1", content="notes", wait=True, wait_timeout=180
    )
    with pytest.raises(UsageError):
        await common.ingest_sources(client, "nb", concurrency=0)
    with pytest.raises(UsageError):
        await common.ingest_sources(client, "nb", wait_timeout=0)
    with pytest.raises(UsageError, match="cannot be empty"):
        await common.ingest_sources(client, "nb", texts=[" "])


def test_build_generation_kwargs_and_enums():
    kwargs = common.build_generation_kwargs(
        "audio",
        language="zh-TW",
        instructions="Focus",
        source_ids=["s1"],
        options={"audio_format": "deep-dive", "audio_length": "long"},
    )
    assert kwargs["language"] == "zh_Hant"
    assert kwargs["audio_format"].name == "DEEP_DIVE"
    assert kwargs["audio_length"].name == "LONG"
    assert kwargs["source_ids"] == ["s1"]
    quiz = common.build_generation_kwargs("quiz", language="zh-TW", instructions="Hard", options={"difficulty": "hard"})
    assert "language" not in quiz and quiz["difficulty"].name == "HARD"
    with pytest.raises(UsageError, match="Unknown"):
        common.build_generation_kwargs("missing")
    with pytest.raises(UsageError, match="not supported"):
        common.build_generation_kwargs("audio", options={"style": "kawaii"})
    with pytest.raises(UsageError, match="Invalid"):
        common.build_generation_kwargs("audio", options={"audio_length": "forever"})
    with pytest.raises(UsageError, match="custom-prompt"):
        common.build_generation_kwargs("report", options={"report_format": "custom"})
    with pytest.raises(UsageError, match="style-prompt"):
        common.build_generation_kwargs("video", options={"video_style": "custom"})
    with pytest.raises(UsageError, match="requires"):
        common.build_generation_kwargs("video", options={"style_prompt": "drawn"})
    video = common.build_generation_kwargs("video", options={"video_style": "custom", "style_prompt": "drawn"})
    assert video["style_prompt"] == "drawn"


@pytest.mark.asyncio
async def test_generate_artifact_lifecycles(client):
    detached = await common.generate_artifact(client, "nb", "audio", wait=False)
    assert detached["status"] == "started" and detached["task_id"] == "task-1"
    completed = await common.generate_artifact(client, "nb", "slides")
    assert completed["state"] == "completed"
    immediate = await common.generate_artifact(client, "nb", "mind-map")
    assert immediate["result"]["note_id"] == "note-1"
    with pytest.raises(UsageError):
        await common.generate_artifact(client, "nb", "unknown")
    with pytest.raises(UsageError):
        await common.generate_artifact(client, "nb", "audio", timeout=0)

    client.artifacts.generate_audio.return_value = record(task_id=None, error="quota")
    with pytest.raises(RuntimeError, match="quota"):
        await common.generate_artifact(client, "nb", "audio")
    client.artifacts.generate_audio.return_value = record(task_id="task", status="in_progress")
    client.artifacts.wait_for_completion.return_value = record(status="failed", error="blocked")
    with pytest.raises(RuntimeError, match="blocked"):
        await common.generate_artifact(client, "nb", "audio")


def test_prepare_output_path(tmp_path):
    target = tmp_path / "nested" / "out.txt"
    assert common.prepare_output_path(target) == target
    assert target.parent.is_dir()
    target.write_text("old")
    with pytest.raises(UsageError, match="exists"):
        common.prepare_output_path(target)
    assert common.prepare_output_path(target, force=True) == target
    with pytest.raises(UsageError, match="directory"):
        common.prepare_output_path(tmp_path, force=True)
    symlink = tmp_path / "link"
    symlink.symlink_to(target)
    with pytest.raises(UsageError, match="symlink"):
        common.prepare_output_path(symlink, force=True)


@pytest.mark.asyncio
async def test_download_and_list_artifacts(client, tmp_path):
    path = await common.download_artifact(
        client,
        "nb",
        "slides",
        tmp_path / "deck.pptx",
        artifact_id="deck-1",
        output_format="pptx",
    )
    assert path.endswith("deck.pptx")
    client.artifacts.download_slide_deck.assert_awaited_once_with(
        "nb", path, artifact_id="deck-1", output_format="pptx"
    )
    with pytest.raises(UsageError, match="Unknown"):
        await common.download_artifact(client, "nb", "bad", tmp_path / "x")
    with pytest.raises(UsageError, match="not valid"):
        await common.download_artifact(client, "nb", "audio", tmp_path / "x", output_format="mp3")
    artifacts = await common.list_artifacts(client, "nb", "slides")
    assert artifacts[0]["kind"] == "slide_deck"
    assert client.artifacts.list.await_args.args[1].name == "SLIDE_DECK"
    with pytest.raises(UsageError):
        await common.list_artifacts(client, "nb", "bad")


@pytest.mark.asyncio
async def test_research_lifecycle(client):
    detached = await common.run_research(client, "nb", " evidence ", wait=False)
    assert detached["status"] == "started"
    complete = await common.run_research(client, "nb", "evidence", mode="deep", max_sources=1)
    assert complete["sources_found"] == complete["sources_imported"] == 1
    no_import = await common.run_research(client, "nb", "evidence", import_results=False, max_sources=0)
    assert no_import["sources_imported"] == 0
    for kwargs in (
        {"query": " "},
        {"query": "x", "mode": "slow"},
        {"query": "x", "timeout": 0},
        {"query": "x", "max_sources": -1},
    ):
        query = kwargs.pop("query")
        with pytest.raises(UsageError):
            await common.run_research(client, "nb", query, **kwargs)
    client.research.start.return_value = None
    with pytest.raises(RuntimeError, match="did not create"):
        await common.run_research(client, "nb", "x")
    client.research.start.return_value = record(task_id="r")
    client.research.wait_for_completion.return_value = record(status="failed", sources=[])
    with pytest.raises(RuntimeError, match="failed"):
        await common.run_research(client, "nb", "x")


@pytest.mark.asyncio
async def test_get_client_success_and_auth_normalization(monkeypatch, tmp_path):
    import notebooklm

    class Context:
        async def __aenter__(self):
            return "client"

        async def __aexit__(self, *_args):
            return False

    monkeypatch.setattr(notebooklm.NotebookLMClient, "from_storage", lambda: Context())
    async with common.get_client() as active:
        assert active == "client"

    missing = tmp_path / "missing.json"
    monkeypatch.setattr(common, "storage_path", lambda profile=None: missing)

    class Missing:
        async def __aenter__(self):
            raise FileNotFoundError("missing")

        async def __aexit__(self, *_args):
            return False

    monkeypatch.setattr(notebooklm.NotebookLMClient, "from_storage", lambda: Missing())
    with pytest.raises(AuthenticationRequired):
        async with common.get_client():
            pass
