from __future__ import annotations

import json
from types import SimpleNamespace
from unittest.mock import AsyncMock

import pytest

from scripts import notebooklm_client as cli
from scripts.common import AuthenticationRequired, UsageError
from tests.conftest import client_context


def use_client(monkeypatch, client):
    monkeypatch.setattr(cli, "get_client", lambda: client_context(client))


def test_parser_exposes_every_command_and_profile():
    parser = cli.build_parser()
    expected = set(cli.COMMANDS)
    parsed = {parser.parse_args([command, "--help"]).command for command in ()}
    assert parsed == set()
    choices = next(action for action in parser._actions if action.dest == "command").choices
    assert set(choices) == expected
    args = parser.parse_args(["--profile", "work", "create", "--title", "T"])
    assert (args.profile, args.command, args.title) == ("work", "create", "T")


@pytest.mark.asyncio
async def test_create_reports_partial_and_strict(monkeypatch, client):
    use_client(monkeypatch, client)
    monkeypatch.setattr(
        cli,
        "ingest_sources",
        AsyncMock(
            return_value=[
                {"status": "ok", "source_type": "url"},
                {"status": "failed", "source_type": "file", "error": "bad"},
            ]
        ),
    )
    args = cli.build_parser().parse_args(["create", "--title", "T", "--sources", "https://example.com", "--strict"])
    result = await cli.cmd_create(args)
    assert result["status"] == "failed"
    assert result["source_summary"] == {"requested": 2, "succeeded": 1, "failed": 1}
    assert result["notebook"]["sources_count"] == 1
    args.title = " "
    with pytest.raises(UsageError, match="title"):
        await cli.cmd_create(args)


@pytest.mark.asyncio
async def test_list_delete_and_confirmation(monkeypatch, client):
    use_client(monkeypatch, client)
    listed = await cli.cmd_list(cli.build_parser().parse_args(["list"]))
    assert listed["count"] == 1

    args = cli.build_parser().parse_args(["delete", "--notebook", "Research"])
    with pytest.raises(UsageError, match="--yes"):
        await cli.cmd_delete(args)
    args.yes = True
    deleted = await cli.cmd_delete(args)
    assert deleted["deleted"] is True
    client.notebooks.delete.assert_awaited_once_with(notebook_id="nb-1")


@pytest.mark.asyncio
@pytest.mark.parametrize("kind", ["url", "text", "file"])
async def test_add_each_source_kind(monkeypatch, client, tmp_path, kind):
    use_client(monkeypatch, client)
    argv = ["add-source", "--notebook", "nb-1"]
    if kind == "url":
        argv += ["--url", "https://example.com/source"]
    elif kind == "text":
        argv += ["--text", "notes", "--text-title", "Notes"]
    else:
        path = tmp_path / "paper.pdf"
        path.write_bytes(b"pdf")
        argv += ["--file", str(path)]
    result = await cli.cmd_add_source(cli.build_parser().parse_args(argv))
    assert result["source"]["id"] == "src-1"


@pytest.mark.asyncio
async def test_add_source_rejects_empty_text_and_missing_file(monkeypatch, client, tmp_path):
    use_client(monkeypatch, client)
    empty = cli.build_parser().parse_args(["add-source", "--notebook", "nb-1", "--text", "   "])
    with pytest.raises(UsageError, match="empty"):
        await cli.cmd_add_source(empty)
    missing = cli.build_parser().parse_args(["add-source", "--notebook", "nb-1", "--file", str(tmp_path / "missing")])
    with pytest.raises(UsageError, match="not found"):
        await cli.cmd_add_source(missing)


@pytest.mark.asyncio
async def test_ask_summary_and_lists(monkeypatch, client):
    use_client(monkeypatch, client)
    ask = await cli.cmd_ask(cli.build_parser().parse_args(["ask", "--notebook", "nb-1", "--query", " Evidence? "]))
    assert ask["answer"].startswith("Grounded") and ask["references"]
    with pytest.raises(UsageError):
        args = cli.build_parser().parse_args(["ask", "--notebook", "nb-1", "--query", "   "])
        await cli.cmd_ask(args)
    summary = await cli.cmd_summarize(cli.build_parser().parse_args(["summarize", "--notebook", "nb-1"]))
    sources = await cli.cmd_list_sources(cli.build_parser().parse_args(["list-sources", "--notebook", "nb-1"]))
    artifacts = await cli.cmd_list_artifacts(
        cli.build_parser().parse_args(["list-artifacts", "--notebook", "nb-1", "--type", "slides"])
    )
    assert summary["summary"] == "Notebook summary"
    assert sources["count"] == artifacts["count"] == 1


@pytest.mark.asyncio
async def test_generate_download_research_and_shortcuts(monkeypatch, client, tmp_path):
    use_client(monkeypatch, client)
    output = tmp_path / "deck.pdf"
    generated = await cli.cmd_generate(
        cli.build_parser().parse_args(
            [
                "generate",
                "--notebook",
                "nb-1",
                "--type",
                "slides",
                "--slide-format",
                "presenter-slides",
                "--output",
                str(output),
            ]
        )
    )
    assert generated["state"] == "completed"
    client.artifacts.download_slide_deck.assert_awaited_once()

    detached = cli.build_parser().parse_args(
        ["generate", "--notebook", "nb-1", "--type", "audio", "--no-wait", "--output", "x"]
    )
    with pytest.raises(UsageError, match="requires waiting"):
        await cli.cmd_generate(detached)

    downloaded = await cli.cmd_download(
        cli.build_parser().parse_args(
            [
                "download",
                "--notebook",
                "nb-1",
                "--type",
                "quiz",
                "--artifact-id",
                "quiz-1",
                "--output",
                str(tmp_path / "quiz.json"),
            ]
        )
    )
    assert downloaded["artifact_id"] == "quiz-1"

    research = await cli.cmd_research(
        cli.build_parser().parse_args(["research", "--notebook", "nb-1", "--query", "evidence", "--mode", "deep"])
    )
    assert research["sources_imported"] == 1

    podcast = await cli.cmd_podcast(cli.build_parser().parse_args(["podcast", "--notebook", "nb-1"]))
    qa = await cli.cmd_qa(cli.build_parser().parse_args(["qa", "--notebook", "nb-1"]))
    assert podcast["action"] == "podcast"
    assert qa["action"] == "qa"


@pytest.mark.asyncio
async def test_dispatch_uses_command_table(monkeypatch):
    handler = AsyncMock(return_value={"status": "ok"})
    monkeypatch.setitem(cli.COMMANDS, "list", handler)
    args = SimpleNamespace(command="list")
    assert await cli.dispatch(args) == {"status": "ok"}
    handler.assert_awaited_once_with(args)


@pytest.mark.parametrize(
    ("exception", "exit_code", "code"),
    [
        (AuthenticationRequired("login"), 4, "AUTH_REQUIRED"),
        (UsageError("bad"), 2, "INVALID_ARGUMENT"),
        (TimeoutError("slow"), 1, "TIMEOUT"),
        (RuntimeError("boom"), 1, "OPERATION_ERROR"),
        (KeyboardInterrupt(), 130, "CANCELLED"),
    ],
)
def test_run_error_contract(monkeypatch, capsys, exception, exit_code, code):
    async def fail(_args):
        raise exception

    monkeypatch.setattr(cli, "dispatch", fail)
    assert cli.run(["list"]) == exit_code
    assert json.loads(capsys.readouterr().out)["code"] == code


def test_run_success_failure_and_profile(monkeypatch, capsys):
    async def result(args):
        return {"status": "failed" if args.profile == "bad" else "ok"}

    monkeypatch.setattr(cli, "dispatch", result)
    assert cli.run(["--profile", "work", "list"]) == 0
    assert json.loads(capsys.readouterr().out)["status"] == "ok"
    assert cli.run(["--profile", "bad", "list"]) == 1
    assert json.loads(capsys.readouterr().out)["status"] == "failed"


def test_package_version_fallback(monkeypatch):
    monkeypatch.setattr(cli, "version", lambda _name: "9.9.9")
    assert cli._package_version() == "9.9.9"
