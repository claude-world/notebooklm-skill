# notebooklm-skill

> NotebookLM research automation — CLI, MCP server, and Claude Code Skill.

## Overview

This project bridges Google NotebookLM's research capabilities with AI content generation.
Feed it URLs, PDFs, or trending topics — it creates NotebookLM notebooks, runs deep research,
and produces structured output: articles, social posts, podcasts, videos, slides, and more.

Built on [notebooklm-py](https://pypi.org/project/notebooklm-py/) v0.3.4 — pure async Python.

## Authentication

NotebookLM uses browser-based Google login (no API keys needed):

```bash
python3 -m notebooklm login          # One-time browser auth
python scripts/auth_helper.py verify  # Verify session
```

Session stored at `~/.notebooklm/storage_state.json`. Lasts weeks.

## CLI Commands

Three global commands are available after `pip install .`:

### `notebooklm-skill` — Core Operations

```bash
notebooklm-skill create --title "Research" --sources https://example.com
notebooklm-skill list
notebooklm-skill ask --notebook "Research" --query "Key findings?"
notebooklm-skill generate audio --notebook "Research" --language en
notebooklm-skill download audio --notebook "Research" --output podcast.m4a
notebooklm-skill delete --notebook "Research"
```

### `notebooklm-pipeline` — Workflow Orchestration

```bash
notebooklm-pipeline research-to-article --sources url1 url2 --title "Topic"
notebooklm-pipeline research-to-social --sources url1 --platform threads
notebooklm-pipeline trend-to-content --geo TW --count 5 --platform threads
notebooklm-pipeline batch-digest --rss https://example.com/feed.xml
notebooklm-pipeline generate-all --sources url1 --title "Research" --output-dir ./output
```

### `notebooklm-mcp` — MCP Server

```bash
notebooklm-mcp            # stdio mode (Claude Code, Cursor)
notebooklm-mcp --http     # HTTP mode on port 8765
```

## MCP Tools (13)

| Tool | Description |
|------|-------------|
| `nlm_create_notebook` | Create notebook with sources |
| `nlm_list` | List all notebooks |
| `nlm_delete` | Delete a notebook |
| `nlm_add_source` | Add source to existing notebook |
| `nlm_ask` | Ask question (returns answer + citations) |
| `nlm_summarize` | Get notebook summary |
| `nlm_generate` | Generate artifact (10 types) |
| `nlm_download` | Download generated artifact |
| `nlm_list_sources` | List sources in notebook |
| `nlm_list_artifacts` | List generated artifacts |
| `nlm_research` | Deep web research |
| `nlm_research_pipeline` | Full research pipeline |
| `nlm_trend_research` | Trend-to-research pipeline |

## Artifact Types (10)

audio, video, slides, report, quiz, flashcards, mind-map, infographic, data-table, study-guide

## Project Structure

```
scripts/                  CLI wrappers (notebooklm_client.py, pipeline.py)
mcp_server/               FastMCP server (server.py, tools.py)
SKILL.md                  Claude Code Skill definition
docs/                     Setup guides (EN + zh-TW)
tests/                    Test suite
output/                   Default output directory
```

## Output Format

All CLI commands output JSON to stdout. Progress messages go to stderr.
Use `--output` to save artifacts to files.
