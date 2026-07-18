#!/usr/bin/env python3
"""Profile-aware NotebookLM authentication setup, verification, and logout."""

from __future__ import annotations

import argparse
import asyncio
import json
import os
import subprocess
import sys
from importlib.metadata import PackageNotFoundError, version
from typing import Any

from scripts.common import AuthenticationRequired, UsageError, get_client, storage_path


def _json_out(data: dict[str, Any]) -> None:
    print(json.dumps(data, ensure_ascii=False, indent=2))


def _err(message: str) -> None:
    print(f"[auth] {message}", file=sys.stderr)


def _package_version() -> str:
    try:
        return version("notebooklm-skill")
    except PackageNotFoundError:
        return "development"


def _upstream_command(profile: str | None, *arguments: str) -> list[str]:
    command = [sys.executable, "-m", "notebooklm"]
    if profile:
        command.extend(("--profile", profile))
    command.extend(arguments)
    return command


def cmd_setup(args: argparse.Namespace) -> dict[str, Any]:
    """Run notebooklm-py's browser login for the selected profile."""
    _err("Opening the NotebookLM browser login flow...")
    login_arguments = ["login"]
    if args.browser:
        login_arguments.extend(("--browser", args.browser))
    if args.fresh:
        login_arguments.append("--fresh")
    try:
        completed = subprocess.run(
            _upstream_command(args.profile, *login_arguments),
            stdout=sys.stderr,
            stderr=sys.stderr,
            timeout=args.timeout,
            check=False,
        )
    except subprocess.TimeoutExpired as exc:
        raise TimeoutError(f"Login timed out after {args.timeout:g} seconds.") from exc
    if completed.returncode != 0:
        raise RuntimeError(f"NotebookLM login exited with code {completed.returncode}.")
    path = storage_path(args.profile)
    if not path.is_file():
        raise RuntimeError(f"Login finished but the active session file was not created: {path}")
    return {
        "status": "ok",
        "action": "setup",
        "profile": args.profile or os.getenv("NOTEBOOKLM_PROFILE") or "default",
        "storage_state_file": str(path),
        "message": "Authentication setup completed.",
    }


async def cmd_verify(args: argparse.Namespace) -> dict[str, Any]:
    """Verify the selected profile with a real, read-only API call."""
    if args.profile:
        os.environ["NOTEBOOKLM_PROFILE"] = args.profile
    path = storage_path(args.profile)
    if not path.is_file() and not os.getenv("NOTEBOOKLM_AUTH_JSON"):
        raise AuthenticationRequired(f"No authentication session was found at {path}. Run the setup command first.")
    async with get_client() as client:
        notebooks = list(await client.notebooks.list() or [])
    return {
        "status": "ok",
        "action": "verify",
        "valid": True,
        "profile": args.profile or os.getenv("NOTEBOOKLM_PROFILE") or "default",
        "storage_state_file": str(path),
        "notebooks_count": len(notebooks),
    }


def cmd_clear(args: argparse.Namespace) -> dict[str, Any]:
    """Use upstream profile-aware logout instead of deleting ~/.notebooklm."""
    if not args.yes:
        raise UsageError("Logout removes the selected profile's session. Re-run with --yes.")
    path = storage_path(args.profile)
    completed = subprocess.run(
        _upstream_command(args.profile, "auth", "logout"),
        stdout=sys.stderr,
        stderr=sys.stderr,
        timeout=60,
        check=False,
    )
    if completed.returncode != 0:
        raise RuntimeError(f"NotebookLM logout exited with code {completed.returncode}.")
    return {
        "status": "ok",
        "action": "clear",
        "profile": args.profile or os.getenv("NOTEBOOKLM_PROFILE") or "default",
        "storage_state_file": str(path),
        "removed": not path.exists(),
    }


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="NotebookLM authentication helper")
    parser.add_argument("--version", action="version", version=f"%(prog)s {_package_version()}")
    parser.add_argument("--profile", help="NotebookLM auth profile")
    subparsers = parser.add_subparsers(dest="command", required=True)
    setup = subparsers.add_parser("setup", help="Open browser login")
    setup.add_argument("--timeout", type=float, default=600)
    setup.add_argument(
        "--browser",
        choices=("chromium", "chrome", "msedge"),
        help="Browser channel; use chrome for the locally installed Google Chrome",
    )
    setup.add_argument(
        "--fresh",
        action="store_true",
        help="Reset only the NotebookLM-managed browser profile before login",
    )
    subparsers.add_parser("verify", help="Verify auth with a read-only API call")
    clear = subparsers.add_parser("clear", help="Log out the selected profile")
    clear.add_argument("--yes", action="store_true", help="Confirm profile logout")
    return parser


def run(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    if args.profile:
        os.environ["NOTEBOOKLM_PROFILE"] = args.profile
    try:
        if args.command == "setup":
            result = cmd_setup(args)
        elif args.command == "verify":
            result = asyncio.run(cmd_verify(args))
        else:
            result = cmd_clear(args)
    except AuthenticationRequired as exc:
        _json_out({"status": "failed", "valid": False, "error": str(exc), "code": "AUTH_REQUIRED"})
        return 4
    except UsageError as exc:
        _json_out({"status": "failed", "error": str(exc), "code": "INVALID_ARGUMENT"})
        return 2
    except TimeoutError as exc:
        _json_out({"status": "failed", "error": str(exc), "code": "TIMEOUT"})
        return 1
    except KeyboardInterrupt:
        _json_out({"status": "failed", "error": "Authentication cancelled.", "code": "CANCELLED"})
        return 130
    except Exception as exc:
        _json_out({"status": "failed", "error": str(exc), "code": "AUTH_ERROR"})
        return 1
    _json_out(result)
    return 0


def main() -> None:
    raise SystemExit(run())


if __name__ == "__main__":
    main()
