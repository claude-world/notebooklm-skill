from __future__ import annotations

import re
from pathlib import Path

import pytest
import yaml

ROOT = Path(__file__).resolve().parent.parent

# Agent Skills specification limits, as enforced by Anthropic's skill validator.
ALLOWED_KEYS = {"name", "description", "license", "allowed-tools", "metadata", "compatibility"}


def frontmatter(path: Path) -> dict:
    match = re.match(r"^---\n(.*?)\n---\n", path.read_text(encoding="utf-8"), re.DOTALL)
    assert match, f"{path} has no YAML frontmatter"
    data = yaml.safe_load(match.group(1))
    assert isinstance(data, dict)
    return data


def test_skill_frontmatter_follows_agent_skills_spec():
    data = frontmatter(ROOT / "SKILL.md")
    assert set(data) <= ALLOWED_KEYS
    name = data["name"]
    assert re.fullmatch(r"[a-z0-9]+(-[a-z0-9]+)*", name) and len(name) <= 64
    description = data["description"].strip()
    assert 0 < len(description) <= 1024
    assert "<" not in description and ">" not in description
    assert len(data.get("compatibility", "")) <= 500


def test_installed_skill_directory_matches_skill_name():
    from scripts.skill_installer import _default_target

    assert _default_target("user").parent.name == frontmatter(ROOT / "SKILL.md")["name"]


@pytest.mark.asyncio
async def test_skill_documents_every_mcp_tool_and_command():
    from mcp_server import server

    text = (ROOT / "SKILL.md").read_text(encoding="utf-8")
    for tool in await server.registered_tools():
        assert f"`{tool.name}`" in text, tool.name
    for command in ("notebooklm-skill", "notebooklm-pipeline", "notebooklm-mcp", "notebooklm-auth"):
        assert command in text
