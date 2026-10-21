"""Offline contract checks against the installed notebooklm-py release.

Live NotebookLM calls need a Google login, so CI cannot exercise them. These
tests pin the upstream surface that ``scripts/common.py`` adapts instead:
client namespaces, method signatures, enum members, exception types, and the
serialization of real result types. A failure means the compatibility layer
must be reviewed before the dependency range moves.
"""

from __future__ import annotations

import inspect
import json
import typing
from datetime import datetime, timezone

import notebooklm
import pytest
from notebooklm.client import NotebookLMClient
from notebooklm.paths import get_storage_path

from scripts import common
from scripts import notebooklm_client as cli

NAMESPACES = typing.get_type_hints(NotebookLMClient)


def parameters(namespace: str, method: str) -> dict[str, inspect.Parameter]:
    return dict(inspect.signature(getattr(NAMESPACES[namespace], method)).parameters)


def test_client_namespaces_storage_and_auth_types():
    assert {"notebooks", "sources", "chat", "artifacts", "research"} <= set(NAMESPACES)
    assert "profile" in inspect.signature(NotebookLMClient.from_storage).parameters
    assert "profile" in inspect.signature(get_storage_path).parameters
    assert issubclass(notebooklm.AuthError, Exception)
    assert issubclass(notebooklm.AuthExtractionError, Exception)


@pytest.mark.parametrize(
    ("namespace", "method", "keywords"),
    [
        ("notebooks", "create", {"title"}),
        ("notebooks", "list", set()),
        ("notebooks", "delete", {"notebook_id"}),
        ("notebooks", "get_summary", {"notebook_id"}),
        ("sources", "list", set()),
        ("sources", "add_url", {"wait", "wait_timeout"}),
        ("sources", "add_text", {"title", "content", "wait", "wait_timeout"}),
        ("sources", "add_file", {"file_path", "wait", "wait_timeout"}),
        ("chat", "ask", {"question"}),
        ("artifacts", "list", set()),
        ("artifacts", "wait_for_completion", {"timeout"}),
        ("research", "start", {"query", "source", "mode"}),
        ("research", "wait_for_completion", {"task_id", "timeout"}),
        ("research", "import_sources", set()),
    ],
)
def test_called_methods_accept_our_keywords(namespace, method, keywords):
    assert keywords <= set(parameters(namespace, method))


@pytest.mark.parametrize("artifact_type", sorted(common.ARTIFACT_SPECS))
def test_artifact_specs_match_upstream_methods(artifact_type):
    spec = common.ARTIFACT_SPECS[artifact_type]
    generator = parameters("artifacts", spec.generator)
    assert "source_ids" in generator
    assert ("language" in generator) is spec.language
    if spec.instructions_parameter:
        assert spec.instructions_parameter in generator
    for _enum_name, api_name in common._GENERATION_OPTIONS.get(artifact_type, {}).values():
        assert api_name in generator
    downloader = parameters("artifacts", spec.downloader)
    assert "artifact_id" in downloader
    assert ("output_format" in downloader) is bool(spec.output_formats)
    assert hasattr(notebooklm.ArtifactType, common._ARTIFACT_FILTERS[artifact_type])


def test_cli_generation_choices_map_to_upstream_enums():
    parser = cli.build_parser()
    commands = next(action for action in parser._actions if action.dest == "command").choices
    choices = {action.dest: action.choices for action in commands["generate"]._actions if action.choices}
    enum_names = {
        option: enum_name
        for rules in common._GENERATION_OPTIONS.values()
        for option, (enum_name, _api_name) in rules.items()
        if enum_name
    }
    for option, enum_name in enum_names.items():
        assert option in choices
        members = {common._enum_option(enum_name, choice) for choice in choices[option]}
        assert len(members) == len(choices[option])


def test_status_enums_compare_as_plain_strings():
    assert str(notebooklm.ResearchStatus.COMPLETED).casefold() == "completed"
    completed = notebooklm.GenerationStatus(task_id="task", status="completed")
    assert str(completed.status).casefold() == "completed"


def test_serializers_handle_real_result_types():
    created = datetime(2026, 10, 21, tzinfo=timezone.utc)
    reference = notebooklm.ChatReference(source_id="src-1", citation_number=1, cited_text="quote")
    research = notebooklm.ResearchTask(
        task_id="research-1",
        status=notebooklm.ResearchStatus.COMPLETED,
        sources=(notebooklm.ResearchSource(url="https://example.com", title="Example"),),
        created_at=created,
    )
    status = notebooklm.GenerationStatus(task_id="task-1", status="completed", url="https://signed.example")
    mind_map = notebooklm.MindMapResult(mind_map={"name": "Root"}, note_id="note-1")
    artifact = notebooklm.Artifact(id="a-1", title="Deck", _artifact_type=8, status=3, url="https://signed")

    serialized_research = common.serialize(research)
    assert serialized_research["status"] == "completed"
    assert serialized_research["sources"][0]["url"] == "https://example.com"
    assert serialized_research["created_at"] == created.isoformat()
    assert common.serialize([reference])[0]["source_id"] == "src-1"
    assert common.serialize(mind_map)["note_id"] == "note-1"
    assert common.serialize_generation_status(status) == {"task_id": "task-1", "status": "completed"}
    assert common.serialize_artifact(artifact) == {"id": "a-1", "title": "Deck", "kind": "slide_deck", "status": 3}
    json.dumps([serialized_research, common.serialize(reference), common.serialize(mind_map)])
