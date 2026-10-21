from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock

import pytest
from fastmcp import Client
from fastmcp.exceptions import ToolError

from mcp_server import server


def test_version_option(monkeypatch, capsys):
    monkeypatch.setattr(server, "version", lambda _name: "9.9.9")
    with pytest.raises(SystemExit) as exc_info:
        server.build_parser().parse_args(["--version"])
    assert exc_info.value.code == 0
    assert capsys.readouterr().out.strip() == "pytest 9.9.9"


@pytest.mark.asyncio
async def test_registered_tool_contract():
    names = {tool.name for tool in await server.registered_tools()}
    assert names == {
        "nlm_create_notebook",
        "nlm_list",
        "nlm_delete",
        "nlm_add_source",
        "nlm_ask",
        "nlm_summarize",
        "nlm_list_sources",
        "nlm_generate",
        "nlm_download",
        "nlm_list_artifacts",
        "nlm_research",
        "nlm_research_pipeline",
        "nlm_trend_research",
    }


@pytest.mark.asyncio
async def test_tool_parameter_contract():
    expected = {
        "nlm_create_notebook": (["title"], ["title", "sources", "text_sources", "file_sources"]),
        "nlm_list": ([], []),
        "nlm_delete": (["notebook"], ["notebook", "confirm"]),
        "nlm_add_source": (["notebook"], ["notebook", "url", "text", "text_title", "file_path"]),
        "nlm_ask": (["notebook", "query"], ["notebook", "query"]),
        "nlm_summarize": (["notebook"], ["notebook"]),
        "nlm_list_sources": (["notebook"], ["notebook"]),
        "nlm_generate": (
            ["notebook", "type"],
            ["notebook", "type", "lang", "instructions", "source_ids", "options", "wait", "timeout"],
        ),
        "nlm_download": (
            ["notebook", "type", "output_path"],
            ["notebook", "type", "output_path", "output_format", "artifact_id", "force"],
        ),
        "nlm_list_artifacts": (["notebook"], ["notebook", "type"]),
        "nlm_research": (
            ["notebook", "query"],
            ["notebook", "query", "mode", "wait", "import_results", "max_sources", "timeout"],
        ),
        "nlm_research_pipeline": (
            ["sources", "questions"],
            ["sources", "questions", "output_format", "title"],
        ),
        "nlm_trend_research": ([], ["geo", "count", "platform"]),
    }
    tools = {tool.name: tool for tool in await server.registered_tools()}
    for name, (required, properties) in expected.items():
        schema = tools[name].parameters
        assert sorted(schema.get("required", [])) == sorted(required), name
        assert list(schema.get("properties", {})) == properties, name
    research = tools["nlm_research"].parameters["properties"]
    assert research["mode"]["enum"] == ["fast", "deep"] and research["mode"]["default"] == "fast"
    assert tools["nlm_delete"].parameters["properties"]["confirm"]["default"] is False


@pytest.mark.asyncio
async def test_mcp_client_round_trip_and_tool_errors(monkeypatch):
    monkeypatch.setattr(server, "list_notebooks", AsyncMock(return_value={"status": "ok", "notebooks": [], "count": 0}))
    async with Client(server.mcp) as client:
        assert len(await client.list_tools()) == 13
        listed = await client.call_tool("nlm_list", {})
        assert listed.structured_content == {"status": "ok", "notebooks": [], "count": 0}
        confirmation = await client.call_tool("nlm_delete", {"notebook": "nb"})
        assert confirmation.structured_content["status"] == "requires_confirmation"
        failed = await client.call_tool("nlm_ask", {"notebook": "nb", "query": " "}, raise_on_error=False)
        assert failed.is_error
        assert "Query cannot be empty" in failed.content[0].text


@pytest.mark.asyncio
async def test_invoke_success_and_error():
    async def okay():
        return {"status": "ok"}

    async def fail():
        raise RuntimeError("boom")

    assert await server._invoke(okay()) == {"status": "ok"}
    with pytest.raises(ToolError, match="boom"):
        await server._invoke(fail())


@pytest.mark.asyncio
async def test_delete_confirmation(monkeypatch):
    delete = AsyncMock(return_value={"status": "ok", "deleted": True})
    monkeypatch.setattr(server, "delete_notebook", delete)
    required = await server.nlm_delete("nb")
    assert required["status"] == "requires_confirmation"
    assert (await server.nlm_delete("nb", confirm=True))["deleted"] is True


@pytest.mark.asyncio
async def test_tool_wrappers_forward(monkeypatch, tmp_path):
    names = [
        "create_notebook",
        "list_notebooks",
        "add_source",
        "ask",
        "summarize",
        "list_sources",
        "generate_artifact",
        "download_artifact",
        "list_artifacts",
        "research",
        "research_pipeline",
        "trend_research",
    ]
    mocks = {}
    for name in names:
        mock = AsyncMock(return_value={"status": "ok", "operation": name})
        monkeypatch.setattr(server, name, mock)
        mocks[name] = mock
    assert (await server.nlm_create_notebook("T"))["operation"] == "create_notebook"
    assert (await server.nlm_list())["operation"] == "list_notebooks"
    assert (await server.nlm_add_source("nb", text="x"))["operation"] == "add_source"
    assert (await server.nlm_ask("nb", "q"))["operation"] == "ask"
    assert (await server.nlm_summarize("nb"))["operation"] == "summarize"
    assert (await server.nlm_list_sources("nb"))["operation"] == "list_sources"
    assert (await server.nlm_generate("nb", "audio", wait=False))["operation"] == "generate_artifact"
    assert (await server.nlm_download("nb", "audio", str(tmp_path / "a"), artifact_id="a"))[
        "operation"
    ] == "download_artifact"
    assert (await server.nlm_list_artifacts("nb", "audio"))["operation"] == "list_artifacts"
    assert (await server.nlm_research("nb", "q"))["operation"] == "research"
    assert (await server.nlm_research_pipeline(["https://x"], ["q"], "report"))["operation"] == "research_pipeline"
    assert (await server.nlm_trend_research())["operation"] == "trend_research"


def test_parser_defaults_and_main_transports(monkeypatch):
    args = server.build_parser().parse_args([])
    assert args.host == "127.0.0.1" and args.port == 8765 and not args.http

    run = MagicMock()
    monkeypatch.setattr(server.mcp, "run", run)
    monkeypatch.setattr("sys.argv", ["notebooklm-mcp"])
    server.main()
    run.assert_called_once_with(transport="stdio")

    run.reset_mock()
    monkeypatch.setattr("sys.argv", ["notebooklm-mcp", "--http", "--host", "localhost", "--port", "9000"])
    server.main()
    run.assert_called_once_with(transport="http", host="localhost", port=9000)

    run.side_effect = KeyboardInterrupt
    monkeypatch.setattr("sys.argv", ["notebooklm-mcp"])
    server.main()


@pytest.mark.parametrize(
    "argv",
    [
        ["notebooklm-mcp", "--port", "0"],
        ["notebooklm-mcp", "--http", "--host", "0.0.0.0"],
    ],
)
def test_main_rejects_invalid_network_args(monkeypatch, argv):
    monkeypatch.setattr("sys.argv", argv)
    with pytest.raises(SystemExit) as exc:
        server.main()
    assert exc.value.code == 2
