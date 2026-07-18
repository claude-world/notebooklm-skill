from __future__ import annotations

import json
import subprocess
from types import SimpleNamespace

import pytest

from scripts import auth_helper
from scripts.common import AuthenticationRequired, UsageError
from tests.conftest import client_context


def test_upstream_command_and_parser():
    assert auth_helper._upstream_command(None, "login")[-2:] == ["notebooklm", "login"]
    command = auth_helper._upstream_command("work", "auth", "logout")
    assert command[-5:] == ["notebooklm", "--profile", "work", "auth", "logout"]
    args = auth_helper.build_parser().parse_args(["--profile", "work", "clear", "--yes"])
    assert args.profile == "work" and args.yes


def test_version_option(monkeypatch, capsys):
    monkeypatch.setattr(auth_helper, "version", lambda _name: "9.9.9")
    with pytest.raises(SystemExit) as exc_info:
        auth_helper.build_parser().parse_args(["--version"])
    assert exc_info.value.code == 0
    assert capsys.readouterr().out.strip() == "pytest 9.9.9"


def test_setup_success_and_failures(monkeypatch, tmp_path):
    session = tmp_path / "state.json"
    session.write_text("{}")
    monkeypatch.setattr(auth_helper, "storage_path", lambda profile=None: session)
    monkeypatch.setattr(subprocess, "run", lambda *args, **kwargs: SimpleNamespace(returncode=0))
    args = auth_helper.build_parser().parse_args(["--profile", "work", "setup"])
    result = auth_helper.cmd_setup(args)
    assert result["profile"] == "work"

    monkeypatch.setattr(subprocess, "run", lambda *args, **kwargs: SimpleNamespace(returncode=2))
    with pytest.raises(RuntimeError, match="code 2"):
        auth_helper.cmd_setup(args)

    def timeout(*_args, **_kwargs):
        raise subprocess.TimeoutExpired("login", 1)

    monkeypatch.setattr(subprocess, "run", timeout)
    with pytest.raises(TimeoutError, match="timed out"):
        auth_helper.cmd_setup(args)

    monkeypatch.setattr(subprocess, "run", lambda *args, **kwargs: SimpleNamespace(returncode=0))
    monkeypatch.setattr(auth_helper, "storage_path", lambda profile=None: tmp_path / "missing")
    with pytest.raises(RuntimeError, match="not created"):
        auth_helper.cmd_setup(args)


def test_setup_forwards_local_browser_options(monkeypatch, tmp_path):
    session = tmp_path / "state.json"
    session.write_text("{}")
    commands = []

    def run(command, **_kwargs):
        commands.append(command)
        return SimpleNamespace(returncode=0)

    monkeypatch.setattr(auth_helper, "storage_path", lambda profile=None: session)
    monkeypatch.setattr(subprocess, "run", run)
    args = auth_helper.build_parser().parse_args(["--profile", "work", "setup", "--browser", "chrome", "--fresh"])
    assert auth_helper.cmd_setup(args)["status"] == "ok"
    assert commands == [
        [
            auth_helper.sys.executable,
            "-m",
            "notebooklm",
            "--profile",
            "work",
            "login",
            "--browser",
            "chrome",
            "--fresh",
        ]
    ]


@pytest.mark.asyncio
async def test_verify_success_and_missing(monkeypatch, client, tmp_path):
    session = tmp_path / "state.json"
    session.write_text("{}")
    monkeypatch.setattr(auth_helper, "storage_path", lambda profile=None: session)
    monkeypatch.setattr(auth_helper, "get_client", lambda: client_context(client))
    args = auth_helper.build_parser().parse_args(["--profile", "work", "verify"])
    result = await auth_helper.cmd_verify(args)
    assert result["valid"] and result["notebooks_count"] == 1
    session.unlink()
    with pytest.raises(AuthenticationRequired, match="No authentication"):
        await auth_helper.cmd_verify(args)


def test_clear_confirmation_success_and_failure(monkeypatch, tmp_path):
    path = tmp_path / "state.json"
    path.write_text("{}")
    monkeypatch.setattr(auth_helper, "storage_path", lambda profile=None: path)
    args = auth_helper.build_parser().parse_args(["clear"])
    with pytest.raises(Exception, match="--yes"):
        auth_helper.cmd_clear(args)
    args.yes = True

    def logout(*_args, **_kwargs):
        path.unlink(missing_ok=True)
        return SimpleNamespace(returncode=0)

    monkeypatch.setattr(subprocess, "run", logout)
    assert auth_helper.cmd_clear(args)["removed"] is True
    monkeypatch.setattr(subprocess, "run", lambda *args, **kwargs: SimpleNamespace(returncode=3))
    with pytest.raises(RuntimeError, match="code 3"):
        auth_helper.cmd_clear(args)


@pytest.mark.parametrize(
    ("operation", "exception", "exit_code", "code"),
    [
        ("verify", AuthenticationRequired("login"), 4, "AUTH_REQUIRED"),
        ("clear", UsageError("bad"), 2, "INVALID_ARGUMENT"),
        ("setup", TimeoutError("slow"), 1, "TIMEOUT"),
        ("setup", RuntimeError("boom"), 1, "AUTH_ERROR"),
        ("setup", KeyboardInterrupt(), 130, "CANCELLED"),
    ],
)
def test_run_error_contract(monkeypatch, capsys, operation, exception, exit_code, code):
    if operation == "verify":

        async def fail(_args):
            raise exception

        monkeypatch.setattr(auth_helper, "cmd_verify", fail)
        argv = ["verify"]
    elif operation == "clear":
        monkeypatch.setattr(auth_helper, "cmd_clear", lambda _args: (_ for _ in ()).throw(exception))
        argv = ["clear", "--yes"]
    else:
        monkeypatch.setattr(auth_helper, "cmd_setup", lambda _args: (_ for _ in ()).throw(exception))
        argv = ["setup"]
    assert auth_helper.run(argv) == exit_code
    assert json.loads(capsys.readouterr().out)["code"] == code


def test_run_success(monkeypatch, capsys):
    monkeypatch.setattr(auth_helper, "cmd_setup", lambda _args: {"status": "ok"})
    assert auth_helper.run(["--profile", "work", "setup"]) == 0
    assert json.loads(capsys.readouterr().out)["status"] == "ok"
