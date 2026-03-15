#!/usr/bin/env bash
set -euo pipefail

# notebooklm-skill installer
# Installs the package, browser dependencies, and Claude Code Skill symlink.

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
SKILL_LINK="$HOME/.claude/skills/notebooklm-research.md"

echo "=== notebooklm-skill installer ==="
echo ""

# 1. Install Python package in editable mode
echo "[1/4] Installing Python package..."
PIP="${PIP:-}"
if [ -z "$PIP" ]; then
    PIP="$(command -v pip3 2>/dev/null || command -v pip 2>/dev/null || true)"
fi
if [ -z "$PIP" ]; then
    echo "Error: pip not found. Install pip or set PIP env var." >&2; exit 1
fi
"$PIP" install -e "$SCRIPT_DIR"
echo "  -> notebooklm-skill, notebooklm-pipeline, notebooklm-mcp commands installed"
echo ""

# 2. Install Playwright Chromium (needed for first-time auth)
echo "[2/4] Installing Playwright Chromium..."
PYTHON="$(dirname "$PIP")/python3"
if ! command -v "$PYTHON" >/dev/null 2>&1; then
    PYTHON="python3"
fi
"$PYTHON" -m playwright install chromium
echo ""

# 3. Symlink Claude Code Skill
echo "[3/4] Installing Claude Code Skill..."
mkdir -p "$(dirname "$SKILL_LINK")"
if [ -L "$SKILL_LINK" ] || [ -f "$SKILL_LINK" ]; then
    echo "  -> Symlink already exists, updating..."
    rm "$SKILL_LINK"
fi
ln -s "$SCRIPT_DIR/SKILL.md" "$SKILL_LINK"
echo "  -> $SKILL_LINK -> $SCRIPT_DIR/SKILL.md"
echo ""

# 4. Check authentication
echo "[4/4] Checking authentication..."
if [ -f "$HOME/.notebooklm/storage_state.json" ]; then
    echo "  -> Session file found: ~/.notebooklm/storage_state.json"
    echo "  -> Run 'notebooklm-skill list' to confirm it's still valid"
else
    echo "  -> No session found. Run: python3 -m notebooklm login"
fi
echo ""

echo "=== Installation complete ==="
echo ""
echo "Quick start:"
echo "  notebooklm-skill --help        # CLI help"
echo "  notebooklm-pipeline --help     # Pipeline help"
echo "  notebooklm-mcp --help          # MCP server help"
echo "  python3 -m notebooklm login    # First-time auth (if needed)"
