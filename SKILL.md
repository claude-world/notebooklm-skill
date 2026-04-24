---
name: notebooklm-research
description: "Full-autopilot AI research agent powered by Google NotebookLM (notebooklm-py v0.3.4). Ingests sources (URL, text, PDF, DOCX, YouTube, Google Drive), runs deep web research, asks cited questions, and generates 10 native artifact types (audio podcast, video, cinematic video, slide deck, report, quiz, flashcards, mind map, infographic, data table, study guide). Produces original content drafts via Claude, with optional publishing to social platforms via threads-viral-agent integration. Use this skill when the user mentions: NotebookLM, research with sources, create notebook, generate podcast from articles, turn research into content, trending topic research, research pipeline, source-based analysis, cited research answers, generate slides, generate quiz, make flashcards, deep web research, create infographic, compare sources, research report, study guide, source analysis, or knowledge synthesis."
---

# NotebookLM Research Agent

A fully autonomous AI research agent that ingests sources into Google NotebookLM,
runs deep web research, synthesizes knowledge through cited Q&A and 9 downloadable artifact types,
creates polished content drafts, and optionally publishes to social platforms.

**Zero-cost research engine** -- NotebookLM is free. No API keys. No per-query charges.

## Authentication

NotebookLM uses RPC/HTTP calls after a one-time browser cookie auth. The session
is stored at `~/.notebooklm/storage_state.json` and reused automatically.

```bash
notebooklm login              # One-time browser auth, saves session
notebooklm login --check      # Verify stored session is still valid
```

The session persists until Google expires it (typically weeks). No API keys or
environment variables needed.

## Architecture Overview

**Core Principle: NotebookLM provides cited research, Claude creates content.**

| Component | Role |
|---|---|
| **notebooklm-py** (v0.3.4) | Python client (8 sub-APIs, 50+ methods, built-in CLI) |
| **notebooklm CLI** | Built-in: `login`, `notebook`, `source`, `chat`, `generate`, `download`, `research`, `share` |
| **MCP Server** (mcp_server/) | FastMCP server exposing 13 tools for Claude Code / Cursor / Gemini CLI |
| **Wrapper CLI** (scripts/) | Higher-level wrappers: `notebooklm_client.py`, `pipeline.py` |
| **LLM** (Claude) | Content creator using NotebookLM research output |
| **trend-pulse** (optional) | Trending topic discovery |
| **threads-viral-agent** (optional) | Social publishing |

```
┌──────────────────────────────────────────────────────────────────────────────────┐
│                          NOTEBOOKLM RESEARCH AGENT                              │
├──────────────┬──────────────┬─────────────────┬─────────────────────────────────┤
│  Phase 1     │  Phase 2     │   Phase 3       │    Phase 4                      │
│  INGEST      │  SYNTHESIZE  │   CREATE        │    PUBLISH (optional)           │
│              │              │                 │                                 │
│ Sources:     │ Chat:        │ Claude writes:  │ threads-viral-agent:            │
│  URL         │  ask()       │  Articles ────→ │  → Threads                      │
│  Text        │  → cited     │  Social posts → │  → Instagram                    │
│  PDF/DOCX    │    answers   │  Newsletters  → │  → Facebook                     │
│  YouTube     │  → follow-up │  Reports ─────→ │                                 │
│  Google Drive│  → citations │                 │ Direct output:                  │
│  File upload │              │ NotebookLM      │  → Markdown / JSON / CSV        │
│              │ Artifacts    │ artifacts used  │  → Podcast M4A / Video MP4      │
│ Research:    │ (9 types):   │ directly:       │  → Slide deck PDF               │
│  web (fast)  │  audio       │  → Podcast      │                                 │
│  web (deep)  │  video       │  → Report       │ * cinematic = Veo 3,            │
│  drive       │  cinematic*  │  → Data table   │   AI Ultra only                 │
│              │  slide_deck  │  → Infographic   │                                 │
│              │  report/quiz │                 │                                 │
│              │  flashcards  │                 │                                 │
│              │  mind_map    │                 │                                 │
│              │  data_table  │                 │                                 │
│              │  study_guide │                 │                                 │
└──────────────┴──────────────┴─────────────────┴─────────────────────────────────┘
```

> For full Python API details, enums, and data types see [references/api_surface.md](references/api_surface.md).
> For JSON output format specs see [references/output_formats.md](references/output_formats.md).

## Phase 1: INGEST -- Source Collection

Create a notebook and populate it with sources (max 50 per notebook).

```bash
# Create a notebook
notebooklm notebook create "AI Agents Research"

# Add sources (URL, text, file, YouTube auto-detected)
notebooklm source add NOTEBOOK_ID --url "https://arxiv.org/abs/2401.12345"
notebooklm source add NOTEBOOK_ID --url "https://youtube.com/watch?v=VIDEO_ID"
notebooklm source add NOTEBOOK_ID --text "Notes" --content "Full text here..."
notebooklm source add NOTEBOOK_ID --file /path/to/document.pdf
```

**Validation gate**: Sources require 5-60s processing. Poll status before proceeding:
- Source statuses: 1=processing, 2=ready, 3=error, 4=preparing
- Use `--wait` flag to block until source is ready
- For batch: use `wait_for_sources()` in Python API
- **Do not proceed to Phase 2 until all sources show status=2 (ready)**

### Deep Web Research

NotebookLM can search the web or Google Drive and auto-import relevant sources.

```bash
notebooklm research start NOTEBOOK_ID "latest advances in AI agents"
notebooklm research poll NOTEBOOK_ID
```

| Mode | Speed | Output | Best For |
|---|---|---|---|
| `fast` | 10-30 sec | URL list + brief summary | Quick source discovery |
| `deep` | 1-5 min | Full Markdown research report + URLs | Thorough analysis |

**Validation gate**: Poll `research poll` until status is `"completed"` before importing sources.

## Phase 2: SYNTHESIZE -- Research & Analysis

### Ask Questions (Cited Answers)

Every answer includes source citations with exact passage references.

```bash
notebooklm chat NOTEBOOK_ID "What are the key differences between ReAct and Reflexion?"
notebooklm chat NOTEBOOK_ID "Can you elaborate on point 3?" --conversation CONV_ID
```

### Generate Artifacts (10 Types)

NotebookLM natively generates artifacts from ingested sources -- server-side by Google, zero LLM cost.

> **Warning:** `infographic` generation works but download is unreliable. Use `slides` instead.

```bash
notebooklm generate audio NOTEBOOK_ID
notebooklm generate video NOTEBOOK_ID
notebooklm generate report NOTEBOOK_ID --format briefing_doc
notebooklm generate quiz NOTEBOOK_ID
notebooklm generate flashcards NOTEBOOK_ID
notebooklm generate slide-deck NOTEBOOK_ID
notebooklm generate data-table NOTEBOOK_ID
notebooklm generate mind-map NOTEBOOK_ID
notebooklm generate study-guide NOTEBOOK_ID
```

**Validation gate**: Artifact generation is async. Use `wait_for_completion()` or poll
`poll_status()` until artifact status is `"completed"` before attempting download.

### Download Artifacts

```bash
notebooklm download audio NOTEBOOK_ID output.m4a
notebooklm download video NOTEBOOK_ID output.mp4
notebooklm download slide-deck NOTEBOOK_ID output.pdf
notebooklm download report NOTEBOOK_ID output.md
notebooklm download quiz NOTEBOOK_ID output.json
notebooklm download flashcards NOTEBOOK_ID output.json
notebooklm download mind-map NOTEBOOK_ID output.json
notebooklm download data-table NOTEBOOK_ID output.csv
```

### Artifact Quick Reference

| Type | CLI Command | Output | Processing Time |
|---|---|---|---|
| Audio (podcast) | `generate audio` / `download audio` | M4A | 3-10 min |
| Video | `generate video` / `download video` | MP4 | 5-15 min |
| Cinematic Video | `generate cinematic-video` | MP4 | 10-20 min (AI Ultra only) |
| Slide Deck | `generate slide-deck` / `download slide-deck` | PDF | 30-120 sec |
| Report | `generate report` / `download report` | Markdown | 10-60 sec |
| Study Guide | `generate study-guide` / `download study-guide` | Markdown | 10-60 sec |
| Quiz | `generate quiz` / `download quiz` | JSON | 10-30 sec |
| Flashcards | `generate flashcards` / `download flashcards` | JSON | 10-30 sec |
| Mind Map | `generate mind-map` / `download mind-map` | JSON | 5-15 sec |
| Data Table | `generate data-table` / `download data-table` | CSV | 10-30 sec |

> For generation options (audio formats, video styles, report types, quiz difficulty, etc.)
> see the enums in [references/api_surface.md](references/api_surface.md).

## Phase 3: CREATE -- Content Generation

Claude uses research output from Phase 2 to write original content. NotebookLM
artifacts can also be used directly (reports, podcasts, slide decks).

### Pipeline Commands

```bash
# Full pipeline: sources -> research -> article
python3 scripts/pipeline.py research-to-article \
  --sources "https://url1.com" "https://url2.com" \
  --title "AI Agent Frameworks in 2026" \
  --output article.md

# Research -> social posts
python3 scripts/pipeline.py research-to-social \
  --sources "https://url1.com" "https://url2.com" \
  --platform threads \
  --output posts.json

# Trending topics -> research -> content (requires trend-pulse MCP)
python3 scripts/pipeline.py trend-to-content \
  --geo TW --count 3 --platform threads --output content.json

# RSS feed -> notebook -> digest
python3 scripts/pipeline.py batch-digest \
  --rss "https://example.com/feed.xml" --title "Weekly AI Digest" --max-entries 15
```

> For full pipeline recipes with step-by-step commands see [references/pipeline_recipes.md](references/pipeline_recipes.md).

### Research-and-Write Workflow

1. Create notebook with relevant URLs
2. Run deep web research to discover additional sources
3. **Gate**: Poll research until complete, then import top discovered sources
4. **Gate**: Verify all sources are ready (status=2) before querying
5. Ask 3-5 research questions covering key angles
6. Generate relevant artifacts (report, data table, etc.)
7. **Gate**: Wait for artifact completion before download
8. Claude writes article using cited answers + artifacts + original analysis
9. Output polished markdown with source citations

### Artifacts as Direct Content

| Artifact | Direct Use | Claude Enhancement |
|---|---|---|
| Audio (podcast) | Distribute as-is | Show notes, companion article |
| Video | Distribute as-is | Description, social posts |
| Report | Publish as blog post | Edit tone, add opinion, localize |
| Slide deck | Present as-is (PDF) | Speaker notes, handout |
| Quiz | Training/education | Social engagement (polls) |
| Flashcards | Study | Threads carousel |
| Data table | Embed in articles | Narrate findings, add analysis |

## Phase 4: PUBLISH -- Distribution (Optional)

### With threads-viral-agent

```bash
python3 scripts/pipeline.py research-to-social \
  --notebook NOTEBOOK_ID --topic "Topic" --publish --account cw
```

### Direct Output (No Social Integration)

Markdown articles, social post JSON, newsletter drafts, or any downloaded artifact
(M4A, MP4, PDF, JSON, CSV).

## MCP Server

The `mcp_server/` directory exposes NotebookLM operations as 13 MCP tools for
Claude Code, Cursor, Gemini CLI, and any MCP-compatible client.

### Configuration

After `pip install .`:

```json
{
  "mcpServers": {
    "notebooklm": {
      "command": "notebooklm-mcp"
    }
  }
}
```

HTTP mode (for remote / multi-client access):

```bash
notebooklm-mcp --http --port 8765
```

### MCP Tools Summary

**Core (7):** `nlm_create_notebook`, `nlm_list`, `nlm_delete`, `nlm_add_source`, `nlm_ask`, `nlm_summarize`, `nlm_list_sources`

**Artifacts (3):** `nlm_generate`, `nlm_download`, `nlm_list_artifacts`

**Research (1):** `nlm_research`

**Pipelines (2):** `nlm_research_pipeline`, `nlm_trend_research`

> For full MCP tool parameters and Python API see [references/api_surface.md](references/api_surface.md).

## Rate Limits

Estimated safe limits (undocumented, may vary). Wait 60s and retry on `RateLimitError`.

| Operation | Limit | Operation | Limit |
|---|---|---|---|
| Notebook creation | ~10/hr | Audio generation | ~5/hr |
| Source addition | ~20/hr | Video generation | ~3/hr |
| Chat questions | ~30/hr | Cinematic video | ~2/hr |
| Reports/Quiz/Flashcards | ~10/hr | Slide deck/Infographic | ~5/hr |
| Web research (fast) | ~10/hr | Web research (deep) | ~5/hr |

## Error Handling

Common errors and fixes (full hierarchy in [references/api_surface.md](references/api_surface.md)):

| Error | Fix |
|---|---|
| `AuthError` | Run `notebooklm login` to refresh session |
| `SourceTimeoutError` | Increase `wait_timeout` or check source URL |
| `RateLimitError` | Wait 60 seconds, then retry |
| `ArtifactNotReadyError` | Use `wait_for_completion()` instead of immediate download |

## Component Reference

| Component | Path | Purpose |
|---|---|---|
| `scripts/notebooklm_client.py` | scripts/ | Core CLI (`notebooklm-skill` after pip install) |
| `scripts/pipeline.py` | scripts/ | Pipelines (`notebooklm-pipeline` after pip install) |
| `mcp_server/server.py` | mcp_server/ | FastMCP server (`notebooklm-mcp` after pip install) |
| `references/api_surface.md` | references/ | Full Python API + CLI reference (8 sub-APIs, all methods) |
| `references/output_formats.md` | references/ | JSON output format specifications |
| `references/pipeline_recipes.md` | references/ | 7 pipeline recipes with full command sequences |
| `docs/SETUP.md` | docs/ | Installation and setup guide |
