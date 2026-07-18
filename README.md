# notebooklm-skill

> Source-grounded NotebookLM automation for terminals and AI agents.

[![CI](https://github.com/claude-world/notebooklm-skill/actions/workflows/ci.yml/badge.svg)](https://github.com/claude-world/notebooklm-skill/actions/workflows/ci.yml)
[![PyPI](https://img.shields.io/pypi/v/notebooklm-skill)](https://pypi.org/project/notebooklm-skill/)
[![Python](https://img.shields.io/pypi/pyversions/notebooklm-skill)](https://pypi.org/project/notebooklm-skill/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)

[繁體中文](README.zh-TW.md)

`notebooklm-skill` gives humans and MCP clients one consistent interface for Google
NotebookLM. It creates notebooks from URLs, raw text, and local files; asks grounded
questions with citation metadata; completes fast or deep web research; and generates
or downloads NotebookLM artifacts.

The project is built around `notebooklm-py` 0.7.x and includes:

- a JSON-first core CLI;
- five end-to-end research pipelines;
- a 13-tool FastMCP server;
- profile-aware authentication and Skill installers;
- one shared compatibility layer, so CLI, pipelines, and MCP use the same behavior.

> This is an unofficial integration with NotebookLM's web API. Google can change the
> service, availability, quotas, or artifact behavior without notice.

## Quick start

### Isolated source install

The installer creates a dedicated virtual environment, installs Chromium, links five
commands into `~/.local/bin`, and installs the Claude Code Skill using the standard
directory layout.

```bash
git clone https://github.com/claude-world/notebooklm-skill.git
cd notebooklm-skill
./install.sh

notebooklm-auth setup
notebooklm-skill list
```

Ensure `~/.local/bin` is on `PATH`.

### PyPI or uvx

```bash
# Persistent virtual environment
python3 -m venv .venv
source .venv/bin/activate
python -m pip install notebooklm-skill
python -m playwright install chromium
notebooklm-auth setup

# Or run without a persistent install
uvx --from notebooklm-skill notebooklm-auth setup
uvx --from notebooklm-skill notebooklm-skill list
```

Direct upstream login is also available:

```bash
uvx --from notebooklm-py notebooklm login
```

Sessions are profile-aware. Select one with `--profile NAME` before a CLI
subcommand, or set `NOTEBOOKLM_PROFILE`.

To use the locally installed Google Chrome instead of bundled Chromium:

```bash
notebooklm-auth setup --browser chrome --fresh
```

## Core CLI

All successful commands print structured JSON to stdout. Diagnostics go to stderr;
authentication errors return exit code 4 and argument errors return exit code 2.

```bash
# Mixed-source ingestion with truthful per-source outcomes
notebooklm-skill create \
  --title "Research" \
  --sources https://example.com/article \
  --files ./paper.pdf \
  --text-sources "Interview notes" \
  --strict

notebooklm-skill ask \
  --notebook "Research" \
  --query "Which conclusions have the strongest evidence?"

notebooklm-skill research \
  --notebook "Research" \
  --query "Recent independent evaluations" \
  --mode deep --max-sources 10

notebooklm-skill generate \
  --notebook "Research" \
  --type slides --lang zh-TW \
  --output ./output/deck.pptx --output-format pptx

notebooklm-skill list-artifacts --notebook "Research" --type slides
```

Commands resolve an exact ID, unique title, or unique title substring. Use IDs for
repeatable automation. Deletes require `--yes`; downloads refuse existing files or
symlinks unless an explicit safe overwrite is requested with `--force`.

### Artifact types

| Type | Default download | Notes |
|---|---:|---|
| `audio` | M4A | deep-dive, brief, critique, or debate |
| `video` | MP4 | explainer/brief and multiple visual styles |
| `cinematic` | MP4 | cinematic video workflow |
| `slides` | PDF | PDF or PPTX |
| `report` | Markdown | briefing, study guide, blog, or custom |
| `study-guide` | Markdown | report shortcut |
| `quiz` | JSON | JSON, Markdown, or HTML |
| `flashcards` | JSON | JSON, Markdown, or HTML |
| `mind-map` | JSON | immediate generation result |
| `infographic` | PNG | orientation, detail, and style options |
| `data-table` | CSV | structured extraction |

Use `notebooklm-skill generate --help` for the live option matrix. Long-running
generations support `--no-wait`, and later downloads can select `--artifact-id`.

## Pipelines

```bash
notebooklm-pipeline research-to-article \
  --sources https://example.com/a https://example.com/b \
  --title "Evidence review" --audience "engineers"

notebooklm-pipeline research-to-social \
  --files ./brief.pdf --platform linkedin --variants 3

notebooklm-pipeline batch-digest \
  --rss https://example.com/feed.xml --max-entries 20 --qa-count 5

notebooklm-pipeline generate-all \
  --files ./paper.pdf --types audio slides report mind-map \
  --output-dir ./output --artifact-concurrency 2
```

`trend-to-content` requires the optional `trend-pulse` command. Pipelines return
drafts and local artifacts; they do not publish to social platforms or remote CMSs.

## MCP server

The default stdio transport is suitable for Claude Code, Cursor, and other MCP
clients:

```json
{
  "mcpServers": {
    "notebooklm": {
      "command": "uvx",
      "args": ["--from", "notebooklm-skill", "notebooklm-mcp"]
    }
  }
}
```

The 13 tools cover notebook CRUD, mixed sources, grounded chat, summaries, artifact
generation/list/download, full research lifecycles, research pipelines, and trend
research. Notebook deletion requires `confirm=true`.

Optional HTTP mode is deliberately loopback-only:

```bash
notebooklm-mcp --http --host 127.0.0.1 --port 8765
```

Do not expose it directly to a network. See [SECURITY.md](SECURITY.md).

## Additional commands

| Command | Purpose |
|---|---|
| `notebooklm-auth` | Setup, verify, or clear a selected auth profile |
| `notebooklm-install-skill` | Install `SKILL.md` for a user or project, with safe backups |

```bash
notebooklm-install-skill --scope project
notebooklm-auth --profile work verify
```

## Development

```bash
python3 -m venv .venv
source .venv/bin/activate
python -m pip install -e '.[dev]'
ruff check .
ruff format --check .
mypy scripts mcp_server
pytest --cov --cov-report=term-missing
python -m build
twine check dist/*
```

More detail: [setup guide](docs/SETUP.md), [Skill instructions](SKILL.md),
[API compatibility notes](references/api_surface.md), and [changelog](CHANGELOG.md).

## License

[MIT](LICENSE)
