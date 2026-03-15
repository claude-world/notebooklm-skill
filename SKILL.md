---
name: notebooklm-research
description: >
  Full-autopilot AI research agent powered by Google NotebookLM (notebooklm-py v0.3.4).
  Ingests sources (URL, text, PDF, DOCX, YouTube, Google Drive), runs deep web research,
  asks cited questions, and generates 10 native artifact types (audio podcast, video,
  cinematic video, slide deck, report, quiz, flashcards, mind map, infographic, data table,
  study guide). Produces original content drafts via Claude, with optional publishing
  to social platforms via threads-viral-agent integration.
  Use this skill when the user mentions: NotebookLM, research with sources, create notebook,
  generate podcast from articles, turn research into content, trending topic research,
  research pipeline, source-based analysis, cited research answers, generate slides,
  generate quiz, make flashcards, deep web research, create infographic, compare sources,
  research report, study guide, source analysis, or knowledge synthesis.
---

# NotebookLM Research Agent

A fully autonomous AI research agent that ingests sources into Google NotebookLM,
runs deep web research, synthesizes knowledge through cited Q&A and 10 artifact types,
creates polished content drafts, and optionally publishes to social platforms.

**Zero-cost research engine** -- NotebookLM is free. No API keys. No per-query charges.

## Authentication

NotebookLM uses RPC/HTTP calls after a one-time browser cookie auth. No browser
automation per operation -- the session is stored and reused.

```
~/.notebooklm/storage_state.json
```

Login once via the built-in CLI:

```bash
notebooklm login              # One-time browser auth, saves session
notebooklm login --check      # Verify stored session is still valid
```

The session persists until Google expires it (typically weeks). All scripts and the
MCP server auto-load the stored session. No API keys or environment variables needed.

## Architecture Overview

**Core Principle: NotebookLM provides cited research, Claude creates content.**

NotebookLM handles source ingestion, indexing, deep web research, cited answers,
and native artifact generation (10 types). Claude uses that research output to write
original articles, social posts, and reports. The pipeline is zero-cost and produces
citation-backed content.

| Component | Role |
|---|---|
| **notebooklm-py** (v0.3.4) | Python client for NotebookLM (8 sub-APIs, 50+ methods, built-in CLI) |
| **notebooklm CLI** | Built-in CLI: `notebooklm login`, `notebook`, `source`, `chat`, `generate`, `download`, `research`, `share` |
| **MCP Server** (mcp_server/) | FastMCP server exposing 13 tools for Claude Code / Cursor / Gemini CLI |
| **Wrapper CLI** (scripts/) | Our higher-level wrappers: `notebooklm_client.py`, `pipeline.py` |
| **LLM** (Claude) | Content creator (writes original text using NotebookLM research) |
| **trend-pulse** (optional) | Trending topic discovery for research-to-content pipelines |
| **threads-viral-agent** (optional) | Social publishing for content distribution |

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
│  File upload │              │ trend-pulse     │  → Markdown file                │
│              │ Artifacts    │  → topic ideas  │  → JSON data                    │
│ Research:    │ (10 types):  │                 │  → Newsletter draft             │
│  web (fast)  │  audio       │ NotebookLM      │  → Podcast MP4                  │
│  web (deep)  │  video       │ artifacts used  │  → Video MP4                    │
│  drive       │  cinematic*  │ directly:       │  → Slide deck PDF               │
│              │  slide_deck  │  → Podcast      │  → Quiz / Flashcards            │
│ Auto-import  │  report      │  → Report       │                                 │
│ discovered   │  quiz        │  → Data table   │                                 │
│ sources      │  flashcards  │  → Infographic   │                                 │
│              │  mind_map    │                 │ * cinematic = Veo 3,            │
│              │  infographic │                 │   AI Ultra only                 │
│              │  data_table  │                 │                                 │
│              │  study_guide │                 │                                 │
└──────────────┴──────────────┴─────────────────┴─────────────────────────────────┘
```

### 8 Sub-APIs (notebooklm-py v0.3.4)

| Sub-API | Accessor | Description |
|---|---|---|
| **Notebooks** | `client.notebooks` | Create, list, get, delete, rename, describe, share |
| **Sources** | `client.sources` | Add URL/text/file/Drive, list, delete, rename, refresh, guide, fulltext, wait |
| **Artifacts** | `client.artifacts` | Generate 10 types, poll status, download, list, delete, rename, revise slides |
| **Chat** | `client.chat` | Ask with citations, follow-up, conversation history, configure persona |
| **Research** | `client.research` | Web/Drive research, poll results, import discovered sources |
| **Notes** | `client.notes` | Create, list, update, delete text notes and mind maps |
| **Settings** | `client.settings` | User settings (output language) |
| **Sharing** | `client.sharing` | Public links, user permissions, view levels |

## Phase 1: INGEST -- Source Collection

Create a notebook and populate it with sources. NotebookLM accepts 8 source types:
URLs, text, PDF, DOCX, Markdown, CSV, YouTube, and Google Drive documents.

### Create Notebook and Add Sources

**Built-in CLI (notebooklm-py):**

```bash
# Create a notebook
notebooklm notebook create "AI Agents Research"

# Add sources
notebooklm source add NOTEBOOK_ID --url "https://arxiv.org/abs/2401.12345"
notebooklm source add NOTEBOOK_ID --url "https://youtube.com/watch?v=VIDEO_ID"
notebooklm source add NOTEBOOK_ID --text "Custom Notes" --content "Full text here..."
notebooklm source add NOTEBOOK_ID --file /path/to/document.pdf
```

**Our wrapper CLI (global command or scripts/notebooklm_client.py):**

```bash
# After pip install ., use global commands:
# notebooklm-skill create --title "AI Agents Research" --sources url1 url2

# Or use scripts directly:
python3 scripts/notebooklm_client.py create \
  --title "AI Agents Research" \
  --sources \
    "https://arxiv.org/abs/2401.12345" \
    "https://blog.example.com/ai-agents-2026"

# Add more sources to existing notebook
python3 scripts/notebooklm_client.py add-source \
  --notebook NOTEBOOK_ID \
  --url "https://another-source.com/article"

# Add text source (pasted content)
python3 scripts/notebooklm_client.py add-source \
  --notebook NOTEBOOK_ID \
  --text "Full text content here..." \
  --text-title "Title of Source"

# Add file (PDF, Markdown, DOCX, CSV)
python3 scripts/notebooklm_client.py add-source \
  --notebook NOTEBOOK_ID \
  --file "/path/to/document.pdf"

# Add YouTube video (auto-extracts transcript)
python3 scripts/notebooklm_client.py add-source \
  --notebook NOTEBOOK_ID \
  --url "https://youtube.com/watch?v=VIDEO_ID"

# Add Google Drive document
python3 scripts/notebooklm_client.py add-source \
  --notebook NOTEBOOK_ID \
  --drive-id "DRIVE_FILE_ID" \
  --drive-title "Document Title"
```

### Deep Web Research (auto-discover sources)

NotebookLM can search the web or Google Drive and auto-import relevant sources.
This is one of the most powerful features -- it finds sources you did not know existed.

**Built-in CLI:**

```bash
notebooklm research start NOTEBOOK_ID "latest advances in AI agents"
notebooklm research poll NOTEBOOK_ID
```

**Our wrapper CLI:**

```bash
# Fast web research (quick scan, returns URLs)
python3 scripts/notebooklm_client.py research \
  --notebook NOTEBOOK_ID \
  --query "latest advances in AI agents" \
  --source web \
  --mode fast

# Deep web research (thorough analysis, returns report + URLs)
python3 scripts/notebooklm_client.py research \
  --notebook NOTEBOOK_ID \
  --query "comparison of agent frameworks" \
  --source web \
  --mode deep

# Google Drive research
python3 scripts/notebooklm_client.py research \
  --notebook NOTEBOOK_ID \
  --query "project notes on agent design" \
  --source drive

# Poll results and auto-import top discovered sources
python3 scripts/notebooklm_client.py research-poll \
  --notebook NOTEBOOK_ID \
  --import-top 5
```

**Research modes:**

| Mode | Speed | Output | Best For |
|---|---|---|---|
| `fast` | 10-30 sec | URL list + brief summary | Quick source discovery |
| `deep` | 1-5 min | Full research report (Markdown) + URLs | Thorough analysis, complex topics |

Deep research returns a comprehensive Markdown report synthesizing findings
across all discovered sources -- usable as-is or as input for Claude.

### Source Types Reference

| Type | Method | CLI Flag | Notes |
|---|---|---|---|
| Web URL | `add_url(url)` | `--url` | Any web page, auto-indexes content |
| YouTube | `add_url(youtube_url)` | `--url` | Auto-detects YouTube, extracts transcript |
| PDF | `add_file(path)` | `--file` | Resumable upload, large files OK |
| DOCX | `add_file(path)` | `--file` | Word documents |
| Markdown | `add_file(path)` | `--file` | .md files |
| CSV | `add_file(path)` | `--file` | Spreadsheet data |
| Text | `add_text(title, content)` | `--text --content` | Pasted/copied content |
| Google Docs | `add_drive(file_id, title)` | `--drive-id --drive-title` | Requires Drive access |
| Google Slides | `add_drive(file_id, title, mime)` | `--drive-id --drive-title` | Presentation content |
| Google Sheets | `add_drive(file_id, title, mime)` | `--drive-id --drive-title` | Spreadsheet data |
| Image | `add_file(path)` | `--file` | Image content (OCR) |

### Source Limits and Wait Behavior

- Max 50 sources per notebook
- Sources require processing time (5-60 seconds depending on size/type)
- Use `--wait` flag to block until source is ready
- Use `wait_for_sources()` for batch operations
- Source statuses: 1=processing, 2=ready, 3=error, 4=preparing

### Python API (for custom scripts)

```python
from notebooklm import NotebookLMClient

async with await NotebookLMClient.from_storage() as client:
    # Create notebook
    nb = await client.notebooks.create("AI Research")

    # Add sources
    src1 = await client.sources.add_url(nb.id, "https://example.com", wait=True)
    src2 = await client.sources.add_text(nb.id, "Notes", "Content...", wait=True)
    src3 = await client.sources.add_file(nb.id, "/path/to/doc.pdf", wait=True)

    # Deep web research
    task = await client.research.start(nb.id, "AI agents 2026", mode="deep")
    results = await client.research.poll(nb.id)  # Poll until complete
    imported = await client.research.import_sources(nb.id, task["task_id"], results["sources"][:5])
```

## Phase 2: SYNTHESIZE -- Research & Analysis

Once sources are ingested, use NotebookLM to extract knowledge through cited Q&A
and generate 10 types of native artifacts.

### Ask Questions (Cited Answers)

Every answer includes source citations with exact passage references.

**Built-in CLI:**

```bash
notebooklm chat NOTEBOOK_ID "What are the key differences between ReAct and Reflexion?"
notebooklm chat NOTEBOOK_ID "Can you elaborate on point 3?" --conversation CONV_ID
```

**Our wrapper CLI:**

```bash
# Ask a question -- answer includes source citations
python3 scripts/notebooklm_client.py ask \
  --notebook NOTEBOOK_ID \
  --query "What are the key differences between ReAct and Reflexion agents?"

# Ask with specific sources only
python3 scripts/notebooklm_client.py ask \
  --notebook NOTEBOOK_ID \
  --query "Summarize the main findings" \
  --sources SOURCE_ID_1 SOURCE_ID_2

# Follow-up question (maintains conversation context)
python3 scripts/notebooklm_client.py ask \
  --notebook NOTEBOOK_ID \
  --query "Can you elaborate on point 3?" \
  --conversation CONVERSATION_ID
```

### Chat Configuration

NotebookLM's chat can be configured for different interaction styles:

| Mode | Description | Use Case |
|---|---|---|
| `default` | Balanced answers | General research |
| `learning_guide` | Socratic, asks follow-up questions | Study, learning |
| `concise` | Short, direct answers | Quick lookups |
| `detailed` | Thorough, comprehensive answers | Deep analysis |

**Python API:**

```python
from notebooklm.models import ChatMode, ChatResponseLength

await client.chat.set_mode(nb.id, ChatMode.LEARNING_GUIDE)
await client.chat.configure(nb.id, response_length=ChatResponseLength.LONGER)
```

### Generate Artifacts (10 Types)

NotebookLM natively generates 10 artifact types from ingested sources. These are
generated server-side by Google -- no LLM cost on our end.

**Built-in CLI:**

```bash
notebooklm generate audio NOTEBOOK_ID
notebooklm generate video NOTEBOOK_ID
notebooklm generate report NOTEBOOK_ID --format briefing_doc
notebooklm generate quiz NOTEBOOK_ID
notebooklm generate flashcards NOTEBOOK_ID
notebooklm generate infographic NOTEBOOK_ID
notebooklm generate slide-deck NOTEBOOK_ID
notebooklm generate data-table NOTEBOOK_ID
notebooklm generate mind-map NOTEBOOK_ID
```

**Our wrapper CLI:**

```bash
# 1. Audio Overview (podcast-style discussion)
python3 scripts/notebooklm_client.py generate audio \
  --notebook NOTEBOOK_ID \
  --language en \
  --format deep_dive \
  --length default \
  --instructions "Focus on practical implications"

# 2. Video Overview
python3 scripts/notebooklm_client.py generate video \
  --notebook NOTEBOOK_ID \
  --format explainer \
  --style whiteboard

# 3. Cinematic Video (Veo 3, requires AI Ultra subscription)
python3 scripts/notebooklm_client.py generate cinematic-video \
  --notebook NOTEBOOK_ID \
  --instructions "Dramatic visual storytelling"

# 4. Slide Deck
python3 scripts/notebooklm_client.py generate slide-deck \
  --notebook NOTEBOOK_ID \
  --format detailed_deck

# 5. Report (Briefing Doc / Study Guide / Blog Post / Custom)
python3 scripts/notebooklm_client.py generate report \
  --notebook NOTEBOOK_ID \
  --format briefing_doc

# 6. Study Guide (convenience shortcut for report format=study_guide)
python3 scripts/notebooklm_client.py generate report \
  --notebook NOTEBOOK_ID \
  --format study_guide

# 7. Quiz
python3 scripts/notebooklm_client.py generate quiz \
  --notebook NOTEBOOK_ID \
  --quantity standard \
  --difficulty medium

# 8. Flashcards
python3 scripts/notebooklm_client.py generate flashcards \
  --notebook NOTEBOOK_ID

# 9. Mind Map
python3 scripts/notebooklm_client.py generate mind-map \
  --notebook NOTEBOOK_ID

# 10. Infographic
python3 scripts/notebooklm_client.py generate infographic \
  --notebook NOTEBOOK_ID \
  --orientation landscape \
  --detail standard

# 11. Data Table
python3 scripts/notebooklm_client.py generate data-table \
  --notebook NOTEBOOK_ID \
  --instructions "Compare frameworks by features, performance, and community size"
```

### Artifact Generation Options

**Audio formats:**

| Format | Duration | Style | Best For |
|---|---|---|---|
| `deep_dive` | 15-30 min | Thorough exploration | Complex topics |
| `brief` | 3-5 min | Quick overview | News updates |
| `critique` | 10-20 min | Critical analysis | Reviews, evaluations |
| `debate` | 10-20 min | Two opposing views | Controversial topics |

**Audio lengths:** `short` (~5 min), `default` (~10-15 min), `long` (~20-30 min)

**Video formats:** `explainer`, `brief`, `cinematic` (AI Ultra only)

**Video styles:** `auto_select`, `classic`, `whiteboard`, `conversational`, `dynamic`

**Report formats:** `briefing_doc`, `study_guide`, `blog_post`, `custom` (with `--prompt`)

**Quiz options:** quantity (`fewer`, `standard`, `more`), difficulty (`easy`, `medium`, `hard`)

**Infographic options:** orientation (`landscape`, `portrait`, `square`), detail (`concise`, `standard`, `detailed`)

**Slide deck formats:** `detailed_deck`, `presenter_slides`

### Download Artifacts

**Built-in CLI:**

```bash
notebooklm download audio NOTEBOOK_ID output.m4a
notebooklm download video NOTEBOOK_ID output.mp4
```

**Our wrapper CLI:**

```bash
# Download audio (M4A)
python3 scripts/notebooklm_client.py download audio \
  --notebook NOTEBOOK_ID \
  --output podcast.m4a

# Download video (MP4)
python3 scripts/notebooklm_client.py download video \
  --notebook NOTEBOOK_ID \
  --output video.mp4

# Download slide deck (PDF)
python3 scripts/notebooklm_client.py download slide-deck \
  --notebook NOTEBOOK_ID \
  --output slides.pdf

# Get report content (Markdown)
python3 scripts/notebooklm_client.py download report \
  --notebook NOTEBOOK_ID \
  --output report.md

# Export quiz as JSON
python3 scripts/notebooklm_client.py download quiz \
  --notebook NOTEBOOK_ID \
  --format json \
  --output quiz.json

# Export flashcards
python3 scripts/notebooklm_client.py download flashcards \
  --notebook NOTEBOOK_ID \
  --output flashcards.json

# Export mind map as JSON
python3 scripts/notebooklm_client.py download mind-map \
  --notebook NOTEBOOK_ID \
  --output mindmap.json

# Export data table as CSV
python3 scripts/notebooklm_client.py download data-table \
  --notebook NOTEBOOK_ID \
  --output comparison.csv
```

### Notebook Management

```bash
# List all notebooks
python3 scripts/notebooklm_client.py list
notebooklm notebook list

# Get notebook summary and suggested topics
python3 scripts/notebooklm_client.py describe --notebook NOTEBOOK_ID

# List sources in a notebook
python3 scripts/notebooklm_client.py sources --notebook NOTEBOOK_ID

# Get source guide (AI summary + keywords for a specific source)
python3 scripts/notebooklm_client.py source-guide --notebook NOTEBOOK_ID --source SOURCE_ID

# Get full indexed text of a source
python3 scripts/notebooklm_client.py fulltext --notebook NOTEBOOK_ID --source SOURCE_ID

# Rename notebook
python3 scripts/notebooklm_client.py rename --notebook NOTEBOOK_ID --title "New Title"

# Delete notebook
python3 scripts/notebooklm_client.py delete --notebook NOTEBOOK_ID

# Share notebook (public link)
python3 scripts/notebooklm_client.py share --notebook NOTEBOOK_ID --public
notebooklm share NOTEBOOK_ID --public
notebooklm share NOTEBOOK_ID --add user@example.com
```

## Phase 3: CREATE -- Content Generation

Claude uses research output from Phase 2 to write original content. NotebookLM
artifacts can also be used directly (reports, podcasts, slide decks).

### Research-to-Article Pipeline

```bash
# Full pipeline: create notebook -> ask questions -> write article
python3 scripts/pipeline.py research-to-article \
  --sources "https://url1.com" "https://url2.com" \
  --title "AI Agent Frameworks in 2026" \
  --output article.md

# From existing notebook
python3 scripts/pipeline.py research-to-article \
  --notebook NOTEBOOK_ID \
  --topic "AI Agent Frameworks" \
  --output article.md
```

### Research-to-Social Pipeline

```bash
# Research -> social posts for Threads/IG/FB
python3 scripts/pipeline.py research-to-social \
  --sources "https://url1.com" "https://url2.com" \
  --platform threads \
  --output posts.json
```

### Trend-to-Content Pipeline (requires trend-pulse MCP)

```bash
# Discover trending topic -> research it -> create content
python3 scripts/pipeline.py trend-to-content \
  --geo TW \
  --count 3 \
  --platform threads \
  --output content.json
```

The trend-to-content pipeline:
1. Calls trend-pulse `get_trending(geo="TW", count=20)` to discover hot topics
2. Claude picks the best topic for the target niche
3. Creates a NotebookLM notebook with relevant URLs (from trend sources)
4. Asks research questions to build understanding
5. Claude writes platform-specific content using cited research

### Batch Digest Pipeline

```bash
# RSS feed -> notebook -> digest summary
python3 scripts/pipeline.py batch-digest \
  --rss "https://example.com/feed.xml" \
  --title "Weekly AI Digest" \
  --max-entries 15
```

### Integration with trend-pulse MCP

When trend-pulse MCP is available, use its tools directly:

```
get_trending(sources="hackernews,reddit", geo="TW", count=20)
-> Pick relevant topics
-> Feed URLs into NotebookLM notebook
-> Research and create content
```

### Research-and-Write Workflow (Manual)

```
User: "Research AI agent frameworks and write a blog post"

1. Create notebook with relevant URLs (from search or user-provided)
2. Run deep web research to discover additional sources
3. Import top discovered sources into the notebook
4. Ask 3-5 research questions covering key angles
5. Generate a briefing doc report for structured overview
6. Generate a data table for feature comparison
7. Claude writes article using:
   - Cited answers from step 4
   - Report summary from step 5
   - Data table from step 6
   - Original analysis and opinion
8. Output polished markdown article with source citations
```

### Artifacts as Direct Content

Some NotebookLM artifacts are usable directly without Claude rewriting:

| Artifact | Direct Use | Claude Enhancement |
|---|---|---|
| Audio (podcast) | Distribute as-is | Generate show notes, write companion article |
| Video | Distribute as-is | Write video description, social posts |
| Report (briefing doc) | Publish as blog post | Edit tone, add opinion, localize |
| Slide deck | Present as-is (PDF) | Add speaker notes, create handout |
| Quiz | Use for training/education | Adapt for social engagement (polls) |
| Flashcards | Use for study | Convert to Threads carousel |
| Mind map | Visual overview | Narrate as article outline |
| Infographic | Share on social media | Write accompanying caption |
| Data table | Embed in articles | Narrate findings, add analysis |
| Study guide | Distribute for learning | Condense into social-sized tips |

## Phase 4: PUBLISH -- Distribution (Optional)

### Integration with threads-viral-agent

If the threads-viral-agent skill is available, pipe content directly:

```bash
# Research -> social post -> publish to Threads
python3 scripts/pipeline.py research-to-social \
  --notebook NOTEBOOK_ID \
  --topic "Topic" \
  --publish \
  --account cw
```

### Direct Output Formats

Without social integration, output as files:

| Format | Use Case | Output |
|---|---|---|
| Markdown article | Blog post, website | `.md` file |
| Social post JSON | Manual posting | `.json` with platform-specific text |
| Newsletter draft | Email campaign | `.md` with sections |
| Report (briefing doc) | Internal use, blog | Markdown from NotebookLM |
| Podcast audio | Distribution | `.m4a` from NotebookLM audio artifact |
| Video | Social media, YouTube | `.mp4` from NotebookLM video artifact |
| Slide deck | Presentations | `.pdf` from NotebookLM slide deck |
| Quiz / Flashcards | Education, training | `.json` structured data |
| Infographic | Social media, reports | Image from NotebookLM |
| Data table | Analysis, spreadsheets | `.csv` export |

## Full Auto-Pilot Mode

When the user says anything like "research this topic", "create a notebook about X",
"turn these articles into a post", "research pipeline", "generate a podcast from these
sources", "make a quiz", execute the complete flow.

### Single Run

1. Collect source URLs from user or trend-pulse
2. Create notebook: `notebooklm_client.py create --title "Topic" --sources url1 url2`
3. Optionally run deep web research to discover more sources
4. Wait for source processing
5. Ask research questions: `notebooklm_client.py ask --query "Q1"`
6. Generate requested artifacts (audio, video, report, quiz, slides, etc.)
7. Claude writes content using research answers (with citations)
8. Output article/posts/report + downloadable artifacts

### Deep Research Flow

```
User: "Deep dive into AI coding assistants"

1. Create notebook with user-provided or searched URLs
2. Run deep web research: research --mode deep --query "AI coding assistants 2026"
3. Poll results, import top 5 discovered sources
4. Ask 3-5 probing questions
5. Generate podcast (deep_dive format, long length)
6. Generate briefing doc report
7. Generate data table (feature comparison)
8. Download all artifacts
9. Claude writes companion article using cited research
10. Output: article.md + podcast.m4a + report.md + comparison.csv
```

### Artifact Generation Flow

```
User: "Generate a quiz and flashcards from my notebook"

1. Find notebook by name or ID
2. Generate quiz: generate quiz --quantity standard --difficulty medium
3. Generate flashcards: generate flashcards
4. Wait for both to complete (poll_status / wait_for_completion)
5. Download quiz: download quiz --output quiz.json
6. Download flashcards: download flashcards --output flashcards.json
7. Output both files
```

## MCP Server

The `mcp_server/` directory contains a FastMCP server that exposes NotebookLM
operations as MCP tools. Works with Claude Code, Cursor, Gemini CLI, and any
MCP-compatible client.

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

Or using script path:

```json
{
  "mcpServers": {
    "notebooklm": {
      "command": "python3",
      "args": ["/path/to/notebooklm-skill/mcp_server/server.py"]
    }
  }
}
```

HTTP mode (for remote / multi-client access):

```bash
notebooklm-mcp --http --port 8765
```

```json
{
  "mcpServers": {
    "notebooklm": {
      "url": "http://localhost:8765/mcp"
    }
  }
}
```

### MCP Tools (13 tools)

**Core notebook operations (7):**

| Tool | Parameters | Description |
|---|---|---|
| `nlm_create_notebook(title, sources[], text_sources?)` | title, URL list, optional text list | Create notebook and add sources |
| `nlm_list()` | -- | List all notebooks |
| `nlm_delete(notebook)` | notebook ID or title | Delete a notebook (irreversible) |
| `nlm_add_source(notebook, url?, text?, file_path?)` | notebook + source | Add a source to existing notebook |
| `nlm_ask(notebook, query)` | notebook ID/title, question | Ask question, get cited answer |
| `nlm_summarize(notebook)` | notebook ID or title | Get comprehensive summary |
| `nlm_list_sources(notebook)` | notebook ID or title | List all sources in notebook |

**Artifact operations (3):**

| Tool | Parameters | Description |
|---|---|---|
| `nlm_generate(notebook, type, lang?, instructions?)` | notebook, artifact type | Generate any of 10 artifact types |
| `nlm_download(notebook, type, output_path)` | notebook, artifact type, output | Download artifact to file |
| `nlm_list_artifacts(notebook, type?)` | notebook ID, optional type filter | List artifacts in notebook |

**Research operations (1):**

| Tool | Parameters | Description |
|---|---|---|
| `nlm_research(notebook, query, mode?)` | notebook, search query, mode | Run web research (fast or deep) |

**Pipeline operations (2):**

| Tool | Parameters | Description |
|---|---|---|
| `nlm_research_pipeline(sources[], questions[], output_format?)` | URLs, questions, format | Full research-to-content pipeline |
| `nlm_trend_research(geo?, count?, platform?)` | region, count, platform | Trending topics to researched content |

## Built-in CLI Reference (notebooklm-py)

The `notebooklm` CLI is installed with `pip install notebooklm` and mirrors the
Python API directly.

### Authentication

```bash
notebooklm login                              # One-time browser auth
notebooklm login --check                      # Verify stored session
```

### Notebooks

```bash
notebooklm notebook list                      # List all notebooks
notebooklm notebook create "Title"            # Create notebook
notebooklm notebook get NOTEBOOK_ID           # Get notebook details
notebooklm notebook delete NOTEBOOK_ID        # Delete notebook
notebooklm notebook rename NOTEBOOK_ID "New"  # Rename notebook
```

### Sources

```bash
notebooklm source list NOTEBOOK_ID                         # List sources
notebooklm source add NOTEBOOK_ID --url "https://..."      # Add URL
notebooklm source add NOTEBOOK_ID --text "T" --content "." # Add text
notebooklm source add NOTEBOOK_ID --file /path/to/doc.pdf  # Add file
notebooklm source delete NOTEBOOK_ID SOURCE_ID             # Delete source
notebooklm source guide NOTEBOOK_ID SOURCE_ID              # AI summary + keywords
notebooklm source fulltext NOTEBOOK_ID SOURCE_ID           # Full indexed text
```

### Chat

```bash
notebooklm chat NOTEBOOK_ID "Question?"                    # Ask question
notebooklm chat NOTEBOOK_ID "Follow up" --conversation ID  # Follow-up
```

### Artifact Generation

```bash
notebooklm generate audio NOTEBOOK_ID                      # Podcast
notebooklm generate video NOTEBOOK_ID                      # Video
notebooklm generate report NOTEBOOK_ID --format briefing_doc
notebooklm generate quiz NOTEBOOK_ID
notebooklm generate flashcards NOTEBOOK_ID
notebooklm generate infographic NOTEBOOK_ID
notebooklm generate slide-deck NOTEBOOK_ID
notebooklm generate data-table NOTEBOOK_ID
notebooklm generate mind-map NOTEBOOK_ID
```

### Download

```bash
notebooklm download audio NOTEBOOK_ID output.m4a           # Download podcast
notebooklm download video NOTEBOOK_ID output.mp4           # Download video
notebooklm download slide-deck NOTEBOOK_ID output.pdf      # Download slides
```

### Research

```bash
notebooklm research start NOTEBOOK_ID "query"              # Start research
notebooklm research poll NOTEBOOK_ID                       # Poll results
```

### Sharing

```bash
notebooklm share NOTEBOOK_ID --public                      # Enable public link
notebooklm share NOTEBOOK_ID --add user@example.com        # Share with user
```

## Our Wrapper CLI Reference (scripts/)

### notebooklm_client.py -- Core Operations

| Subcommand | Description | Key Flags |
|---|---|---|
| `create` | Create notebook with sources | `--title`, `--sources`, `--text-sources` |
| `ask` | Ask question, get cited answer | `--notebook`, `--query`, `--sources`, `--conversation` |
| `summarize` | Summarize notebook content | `--notebook` |
| `podcast` | Generate audio overview | `--notebook`, `--lang` |
| `qa` | Generate Q&A pairs | `--notebook`, `--count` |
| `list` | List all notebooks | -- |
| `delete` | Delete a notebook | `--notebook` |
| `add-source` | Add source to notebook | `--notebook`, `--url`/`--text`/`--file`/`--drive-id` |
| `describe` | Get AI summary + topics | `--notebook` |
| `sources` | List sources in notebook | `--notebook` |
| `source-guide` | Get AI summary of source | `--notebook`, `--source` |
| `fulltext` | Get full source text | `--notebook`, `--source` |
| `rename` | Rename notebook | `--notebook`, `--title` |
| `share` | Share notebook | `--notebook`, `--public` |
| `generate` | Generate any artifact type | `--notebook`, `--type`, `--format`, `--language` |
| `download` | Download artifact | `--notebook`, `--type`, `--output` |
| `research` | Start web/drive research | `--notebook`, `--query`, `--source`, `--mode` |
| `research-poll` | Poll research results | `--notebook`, `--import-top` |

### pipeline.py -- Higher-Level Workflows

| Workflow | Description | Key Flags |
|---|---|---|
| `research-to-article` | Sources -> research -> article | `--sources`, `--title`, `--output` |
| `research-to-social` | Sources -> summarize -> social post | `--sources`, `--platform`, `--output` |
| `trend-to-content` | Trends -> research -> content | `--geo`, `--count`, `--platform` |
| `batch-digest` | RSS feed -> digest summary | `--rss`, `--title`, `--max-entries` |

## Rate Limits

These are estimated safe limits. Actual limits are undocumented and may vary.
If you receive rate limit errors, wait 60 seconds and retry.

| Operation | Limit | Notes |
|---|---|---|
| Notebook creation | ~10/hour | Suggested safe rate |
| Source addition | ~20/hour | Per notebook |
| Chat questions | ~30/hour | Across all notebooks |
| Audio generation | ~5/hour | Resource-intensive, 3-10 min processing |
| Video generation | ~3/hour | Very resource-intensive, 5-15 min processing |
| Cinematic video | ~2/hour | Veo 3 rendering, AI Ultra only |
| Report generation | ~10/hour | Moderate, 10-60 sec processing |
| Quiz/Flashcards | ~10/hour | Moderate |
| Slide deck | ~5/hour | Moderate-heavy |
| Infographic | ~5/hour | Moderate-heavy |
| Data table | ~10/hour | Moderate |
| Mind map | ~10/hour | Lightweight |
| Web research (fast) | ~10/hour | Google search backend |
| Web research (deep) | ~5/hour | Extended processing |

**Rate limit detection**: The API returns `is_rate_limited: true` in `GenerationStatus`.
The error code is `"USER_DISPLAYABLE_ERROR"`. Wait 60 seconds and retry.

## Error Handling

The API provides a structured error hierarchy:

```
NotebookLMError (base)
+-- AuthError              # Session expired -> run `notebooklm login`
+-- RPCError               # Google RPC failures
|   +-- RPCTimeoutError    # Increase timeout
+-- SourceError
|   +-- SourceAddError     # Bad URL or file format
|   +-- SourceTimeoutError # Source took too long to process
+-- ArtifactError
|   +-- ArtifactNotReadyError  # Poll again or wait
+-- RateLimitError         # Wait 60s and retry
```

Common fixes:
- **AuthError**: Run `notebooklm login` to refresh the session
- **SourceTimeoutError**: Increase `wait_timeout` or check source URL
- **RateLimitError**: Wait 60 seconds, then retry
- **ArtifactNotReadyError**: Use `wait_for_completion()` instead of immediate download

## Quick Reference: All Components

| Component | Path | Purpose |
|---|---|---|
| `scripts/notebooklm_client.py` | scripts/ | Core CLI (also: `notebooklm-skill` after pip install) |
| `scripts/pipeline.py` | scripts/ | Higher-level pipelines (also: `notebooklm-pipeline` after pip install) |
| `mcp_server/server.py` | mcp_server/ | FastMCP server (also: `notebooklm-mcp` after pip install) |
| `mcp_server/tools.py` | mcp_server/ | MCP tool implementations |
| `scripts/auth_helper.py` | scripts/ | Authentication helper |
| `references/api_surface.md` | references/ | Full notebooklm-py v0.3.4 API documentation (8 sub-APIs, all methods) |
| `references/output_formats.md` | references/ | JSON output format specifications for all API responses |
| `references/pipeline_recipes.md` | references/ | 7 common pipeline recipes with full command sequences |
| `docs/SETUP.md` | docs/ | Installation and setup guide |

## Quick Reference: 10 Artifact Types

| Type | Generate | Download | Output Format | Processing Time |
|---|---|---|---|---|
| Audio (podcast) | `generate audio` | `download audio` | M4A | 3-10 min |
| Video | `generate video` | `download video` | MP4 | 5-15 min |
| Cinematic Video | `generate cinematic-video` | `download video` | MP4 | 10-20 min |
| Slide Deck | `generate slide-deck` | `download slide-deck` | PDF | 30-120 sec |
| Report | `generate report` | `download report` | Markdown | 10-60 sec |
| Study Guide | `generate report --format study_guide` | `download report` | Markdown | 10-60 sec |
| Quiz | `generate quiz` | `download quiz` | JSON (structured) | 10-30 sec |
| Flashcards | `generate flashcards` | `download flashcards` | JSON (structured) | 10-30 sec |
| Mind Map | `generate mind-map` | `download mind-map` | JSON (tree) | 5-15 sec |
| Infographic | `generate infographic` | `download infographic` | Image | 30-120 sec |
| Data Table | `generate data-table` | `download data-table` | CSV/JSON | 10-30 sec |

## Trigger Patterns

### English

- "Research X using NotebookLM"
- "Create a notebook about X"
- "Turn these articles into a blog post"
- "Generate a podcast from these sources"
- "Generate a video overview of X"
- "Make a slide deck from this research"
- "Create a quiz from this material"
- "Generate flashcards for studying X"
- "Create an infographic about X"
- "Build a mind map of X"
- "Generate a data table comparing X and Y"
- "Write a report on X"
- "Deep research on X"
- "Find sources about X"
- "What does the research say about X?"
- "Research and write about X"
- "Summarize these sources"
- "Research pipeline for X"
- "Compare these sources"
- "Turn this into a study guide"
- "Research trending topics and write content"
- "Create a weekly digest from these feeds"

### ZH-TW

- "用 NotebookLM 研究 X"
- "建立一個關於 X 的筆記本"
- "把這些文章變成部落格文章"
- "從這些來源生成 Podcast"
- "幫我做一個影片摘要"
- "做一份簡報 / 投影片"
- "從這些資料出題 / 出考卷"
- "幫我做閃卡 / 字卡"
- "做一張資訊圖表"
- "畫一個心智圖"
- "做一個比較表格"
- "寫一份報告"
- "深入研究 X"
- "幫我找 X 的資料"
- "研究 X 並寫一篇文章"
- "幫我整理這些資料"
- "研究流水線"
- "比較這些來源"
- "做一份讀書指南"
- "研究熱門趨勢並寫內容"
- "做每週摘要"
