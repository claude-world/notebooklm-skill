from __future__ import annotations

import json
from pathlib import Path

import pytest

from scripts import skill_installer


def source_file(tmp_path):
    source = tmp_path / "source" / "SKILL.md"
    source.parent.mkdir()
    source.write_text("---\nname: test\n---\n")
    return source


def test_default_targets(monkeypatch, tmp_path):
    monkeypatch.chdir(tmp_path)
    monkeypatch.setattr(Path, "home", classmethod(lambda cls: tmp_path / "home"))
    assert skill_installer._default_target("project") == (
        tmp_path / ".claude" / "skills" / "notebooklm-research" / "SKILL.md"
    )
    assert "home" in str(skill_installer._default_target("user"))


def test_version_option(monkeypatch, capsys):
    monkeypatch.setattr(skill_installer, "version", lambda _name: "9.9.9")
    with pytest.raises(SystemExit) as exc_info:
        skill_installer.build_parser().parse_args(["--version"])
    assert exc_info.value.code == 0
    assert capsys.readouterr().out.strip() == "pytest 9.9.9"


def test_install_dry_run_install_up_to_date_and_backup(monkeypatch, tmp_path):
    source = source_file(tmp_path)
    monkeypatch.setattr(skill_installer, "_find_skill_source", lambda: source)
    target_dir = tmp_path / "target"
    preview = skill_installer.install_skill(target=str(target_dir), dry_run=True)
    assert preview["action"] == "would-install" and not target_dir.exists()

    installed = skill_installer.install_skill(target=str(target_dir))
    target = target_dir / "SKILL.md"
    assert installed["action"] == "installed" and target.read_bytes() == source.read_bytes()
    assert skill_installer.install_skill(target=str(target))["action"] == "up-to-date"

    target.write_text("custom")
    with pytest.raises(RuntimeError, match="different content"):
        skill_installer.install_skill(target=str(target))
    replaced = skill_installer.install_skill(target=str(target), force=True)
    assert target.read_bytes() == source.read_bytes()
    assert Path(replaced["backup"]).read_text() == "custom"


def test_install_refuses_symlink(monkeypatch, tmp_path):
    source = source_file(tmp_path)
    monkeypatch.setattr(skill_installer, "_find_skill_source", lambda: source)
    actual = tmp_path / "actual"
    actual.write_text("x")
    link = tmp_path / "SKILL.md"
    link.symlink_to(actual)
    with pytest.raises(RuntimeError, match="symlink"):
        skill_installer.install_skill(target=str(link), force=True)


def test_find_source_from_checkout():
    assert skill_installer._find_skill_source().name == "SKILL.md"


def test_parser_and_run(monkeypatch, tmp_path, capsys):
    source = source_file(tmp_path)
    monkeypatch.setattr(skill_installer, "_find_skill_source", lambda: source)
    target = tmp_path / "installed"
    assert skill_installer.run(["--target", str(target)]) == 0
    assert json.loads(capsys.readouterr().out)["status"] == "ok"
    monkeypatch.setattr(
        skill_installer,
        "install_skill",
        lambda **_kwargs: (_ for _ in ()).throw(RuntimeError("blocked")),
    )
    assert skill_installer.run(["--dry-run"]) == 1
    assert json.loads(capsys.readouterr().out)["code"] == "INSTALL_ERROR"
