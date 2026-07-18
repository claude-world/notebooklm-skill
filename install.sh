#!/usr/bin/env bash
set -euo pipefail

# Install notebooklm-skill into an isolated virtual environment. This avoids
# mutating an externally managed Python installation (PEP 668) and works on
# systems without pipx or uv.

PROJECT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
INSTALL_ROOT="${NOTEBOOKLM_INSTALL_ROOT:-${XDG_DATA_HOME:-$HOME/.local/share}/notebooklm-skill}"
INSTALL_VENV="$INSTALL_ROOT/venv"
COMMAND_DIR="${XDG_BIN_HOME:-$HOME/.local/bin}"
TASK_PYTHON="${NOTEBOOKLM_PYTHON:-$(command -v python3 2>/dev/null || command -v python 2>/dev/null || true)}"

fail() {
    printf 'Error: %s\n' "$1" >&2
    exit 1
}

if [ -z "$TASK_PYTHON" ] || ! "$TASK_PYTHON" --version >/dev/null 2>&1; then
    fail "Python 3.10+ was not found. Install Python or set NOTEBOOKLM_PYTHON."
fi

if ! "$TASK_PYTHON" -c 'import sys; raise SystemExit(sys.version_info < (3, 10))'; then
    fail "Python 3.10+ is required."
fi

printf '%s\n' '=== notebooklm-skill installer ==='
printf '[1/5] Creating isolated environment at %s\n' "$INSTALL_VENV"
mkdir -p "$INSTALL_ROOT"
if [ ! -x "$INSTALL_VENV/bin/python" ]; then
    "$TASK_PYTHON" -m venv "$INSTALL_VENV"
fi

printf '%s\n' '[2/5] Installing notebooklm-skill and dependencies...'
"$INSTALL_VENV/bin/python" -m pip install --upgrade pip
if [ "${NOTEBOOKLM_INSTALL_EDITABLE:-0}" = "1" ]; then
    "$INSTALL_VENV/bin/python" -m pip install --editable "$PROJECT_DIR"
else
    "$INSTALL_VENV/bin/python" -m pip install --upgrade "$PROJECT_DIR"
fi

printf '%s\n' '[3/5] Installing Playwright Chromium for browser login...'
if [ "${NOTEBOOKLM_SKIP_BROWSER:-0}" = "1" ]; then
    printf '%s\n' '  skipped (NOTEBOOKLM_SKIP_BROWSER=1)'
else
    "$INSTALL_VENV/bin/python" -m playwright install chromium
fi

printf '[4/5] Linking commands into %s\n' "$COMMAND_DIR"
mkdir -p "$COMMAND_DIR"
for command_name in notebooklm-skill notebooklm-pipeline notebooklm-mcp notebooklm-auth notebooklm-install-skill; do
    command_source="$INSTALL_VENV/bin/$command_name"
    command_target="$COMMAND_DIR/$command_name"
    [ -x "$command_source" ] || fail "Expected command is missing: $command_source"
    if [ -e "$command_target" ] || [ -L "$command_target" ]; then
        if [ -L "$command_target" ] && [ "$(readlink "$command_target")" = "$command_source" ]; then
            continue
        fi
        printf '  warning: leaving existing command untouched: %s\n' "$command_target" >&2
        continue
    fi
    ln -s "$command_source" "$command_target"
done

printf '%s\n' '[5/5] Installing the Claude Code Skill and checking authentication...'
if [ "${NOTEBOOKLM_SKIP_SKILL:-0}" = "1" ]; then
    printf '%s\n' '  Skill install skipped (NOTEBOOKLM_SKIP_SKILL=1)'
else
    "$INSTALL_VENV/bin/notebooklm-install-skill" --force
fi
if [ "${NOTEBOOKLM_SKIP_AUTH_CHECK:-0}" = "1" ]; then
    printf '%s\n' '  Authentication check skipped (NOTEBOOKLM_SKIP_AUTH_CHECK=1)'
elif "$INSTALL_VENV/bin/notebooklm-auth" verify; then
    printf '%s\n' '  Authentication is valid.'
else
    printf '%s\n' '  Authentication is not ready. Run: notebooklm-auth setup' >&2
fi

printf '\n%s\n' '=== Installation complete ==='
printf 'Ensure %s is on PATH, then try:\n' "$COMMAND_DIR"
printf '%s\n' \
    '  notebooklm-auth setup' \
    '  notebooklm-skill list' \
    '  notebooklm-pipeline --help' \
    '  notebooklm-mcp --help'
