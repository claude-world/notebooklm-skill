#!/usr/bin/env python3
"""Install the packaged Claude Code Skill using the standard directory layout."""

from __future__ import annotations

import argparse
import json
import os
import shutil
import tempfile
from datetime import datetime, timezone
from importlib.metadata import PackageNotFoundError, distribution, version
from pathlib import Path
from typing import Any


def _json_out(data: dict[str, Any]) -> None:
    print(json.dumps(data, ensure_ascii=False, indent=2))


def _package_version() -> str:
    try:
        return version("notebooklm-skill")
    except PackageNotFoundError:
        return "development"


def _find_skill_source() -> Path:
    checkout_source = Path(__file__).resolve().parent.parent / "SKILL.md"
    if checkout_source.is_file():
        return checkout_source
    try:
        package = distribution("notebooklm-skill")
    except PackageNotFoundError as exc:
        raise RuntimeError("Could not locate the notebooklm-skill distribution.") from exc
    for entry in package.files or ():
        if entry.as_posix().endswith("share/notebooklm-skill/SKILL.md"):
            candidate = Path(str(package.locate_file(entry)))
            if candidate.is_file():
                return candidate
    raise RuntimeError("The installed distribution does not contain SKILL.md.")


def _default_target(scope: str) -> Path:
    if scope == "project":
        return Path.cwd() / ".claude" / "skills" / "notebooklm-research" / "SKILL.md"
    return Path.home() / ".claude" / "skills" / "notebooklm-research" / "SKILL.md"


def install_skill(
    *,
    scope: str = "user",
    target: str | None = None,
    force: bool = False,
    dry_run: bool = False,
) -> dict[str, Any]:
    """Install atomically, preserving a timestamped backup on forced updates."""
    source = _find_skill_source()
    destination = Path(target).expanduser() if target else _default_target(scope)
    if destination.name != "SKILL.md":
        destination = destination / "SKILL.md"
    content = source.read_bytes()
    if destination.is_symlink():
        raise RuntimeError(f"Refusing to replace a symlink: {destination}")
    if destination.is_file() and destination.read_bytes() == content:
        return {
            "status": "ok",
            "action": "up-to-date",
            "source": str(source),
            "target": str(destination),
        }
    if destination.exists() and not force:
        raise RuntimeError(f"Target already exists with different content: {destination}")
    result: dict[str, Any] = {
        "status": "ok",
        "action": "would-install" if dry_run else "installed",
        "source": str(source),
        "target": str(destination),
    }
    if dry_run:
        return result

    destination.parent.mkdir(parents=True, exist_ok=True)
    if destination.exists():
        timestamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
        backup = destination.with_name(f"SKILL.md.backup-{timestamp}")
        shutil.copy2(destination, backup)
        result["backup"] = str(backup)
    descriptor, temporary_name = tempfile.mkstemp(prefix=".SKILL.md.", dir=destination.parent)
    temporary = Path(temporary_name)
    try:
        with os.fdopen(descriptor, "wb") as handle:
            handle.write(content)
            handle.flush()
            os.fsync(handle.fileno())
        temporary.chmod(0o644)
        os.replace(temporary, destination)
    finally:
        if temporary.exists():
            temporary.unlink()
    return result


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Install the notebooklm-research Skill")
    parser.add_argument("--version", action="version", version=f"%(prog)s {_package_version()}")
    parser.add_argument("--scope", choices=("user", "project"), default="user")
    parser.add_argument("--target", help="Custom SKILL.md path or containing directory")
    parser.add_argument("--force", action="store_true", help="Back up and replace changed content")
    parser.add_argument("--dry-run", action="store_true", help="Preview without writing")
    return parser


def run(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    try:
        result = install_skill(
            scope=args.scope,
            target=args.target,
            force=args.force,
            dry_run=args.dry_run,
        )
    except Exception as exc:
        _json_out({"status": "failed", "error": str(exc), "code": "INSTALL_ERROR"})
        return 1
    _json_out(result)
    return 0


def main() -> None:
    raise SystemExit(run())


if __name__ == "__main__":
    main()
