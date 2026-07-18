---
name: notebooklm-research
description: >
  Automate source-grounded research with Google NotebookLM. Create notebooks from
  URLs, text, or local files; ask cited questions; run fast or deep web research;
  create articles and social drafts; and generate or download audio, video,
  cinematic video, slides, reports, study guides, quizzes, flashcards, mind maps,
  infographics, and data tables. Use when a user asks for NotebookLM, cited source
  analysis, research-to-content workflows, podcasts, slides, study material,
  artifact generation, RSS digests, or trend research.
---

# NotebookLM Research

Use the installed commands or the 13 MCP tools to turn user-provided sources into
grounded answers and NotebookLM artifacts. Commands emit JSON on stdout and progress
or diagnostics on stderr, so preserve stdout when another tool will consume it.

This integration uses NotebookLM's browser session and unofficial web API through
`notebooklm-py`. Do not promise that Google-side availability, quotas, or generation
time are stable.

## Authentication

Prefer the profile-aware helper:

```bash
notebooklm-auth setup
notebooklm-auth verify
```

Use `notebooklm-auth setup --browser chrome --fresh` when the user explicitly
wants the locally installed Google Chrome instead of bundled Chromium.

For a zero-install login:

```bash
uvx --from notebooklm-py notebooklm login
```

Profiles are supported through `--profile NAME` before the subcommand or through
`NOTEBOOKLM_PROFILE`. Current sessions are normally stored below
`~/.notebooklm/profiles/<profile>/storage_state.json`; never read, print, copy, or
commit that file. If authentication expires, run setup again.

## Core CLI

Create a notebook from mixed sources:

```bash
notebooklm-skill create \
  --title "AI safety evidence" \
  --sources https://example.com/article https://youtu.be/example \
  --files ./paper.pdf \
  --text-sources "A user-supplied observation" \
  --strict
```

Inspect and ask:

```bash
notebooklm-skill list
notebooklm-skill list-sources --notebook "AI safety evidence"
notebooklm-skill summarize --notebook "AI safety evidence"
notebooklm-skill ask --notebook "AI safety evidence" --query "What findings conflict?"
```

Add exactly one source:

```bash
notebooklm-skill add-source --notebook "AI safety evidence" --url https://example.com/new
notebooklm-skill add-source --notebook "AI safety evidence" --file ./appendix.docx
notebooklm-skill add-source --notebook "AI safety evidence" \
  --text "Raw notes" --text-title "Interview notes"
```

Run NotebookLM web research and import results:

```bash
notebooklm-skill research \
  --notebook "AI safety evidence" \
  --query "Recent empirical evaluations" \
  --mode deep --max-sources 10
```

Use `--no-wait` for a task ID without waiting. Use `--no-import-results` when the
research results should not become notebook sources.

Notebook titles may be used only when they resolve uniquely. Prefer IDs in automation.

## Artifact generation

Supported canonical types:

`audio`, `video`, `cinematic`, `slides`, `report`, `study-guide`, `quiz`,
`flashcards`, `mind-map`, `infographic`, `data-table`.

Generate and optionally download in one operation:

```bash
notebooklm-skill generate \
  --notebook "AI safety evidence" \
  --type slides --lang zh-TW \
  --slide-format presenter-slides \
  --output ./output/deck.pptx --output-format pptx
```

Long media jobs can be detached and downloaded later by exact ID:

```bash
notebooklm-skill generate --notebook NOTEBOOK_ID --type audio --no-wait
notebooklm-skill list-artifacts --notebook NOTEBOOK_ID --type audio
notebooklm-skill download --notebook NOTEBOOK_ID --type audio \
  --artifact-id ARTIFACT_ID --output ./output/podcast.m4a
```

Convenience commands:

```bash
notebooklm-skill podcast --notebook NOTEBOOK_ID --output podcast.m4a
notebooklm-skill qa --notebook NOTEBOOK_ID --difficulty hard --output quiz.json
```

Generation supports per-type options. Inspect the live contract before composing an
unfamiliar call:

```bash
notebooklm-skill generate --help
```

Existing output files and symlinks are rejected. Use `--force` only when the user
explicitly wants an overwrite. Quiz and flashcard downloads support JSON, Markdown,
or HTML; slide downloads support PDF or PPTX.

## High-level pipelines

```bash
notebooklm-pipeline research-to-article \
  --sources https://example.com/a https://example.com/b \
  --title "Evidence review" --language zh-TW --audience "engineers"

notebooklm-pipeline research-to-social \
  --sources https://example.com/a --platform threads --variants 3

notebooklm-pipeline batch-digest \
  --rss https://example.com/feed.xml --max-entries 20 --qa-count 5

notebooklm-pipeline generate-all \
  --files ./paper.pdf --types audio slides report mind-map \
  --output-dir ./output --artifact-concurrency 2
```

`trend-to-content` requires a separately installed `trend-pulse` command. Override
its executable safely with `TREND_PULSE_CMD`; the integration does not invoke a shell.

Pipelines create drafts and local artifacts. They do not publish to social networks,
CMS products, or other remote destinations.

## MCP server

Start stdio mode for an MCP client:

```bash
notebooklm-mcp
```

Example configuration:

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

Available tools:

- `nlm_create_notebook`, `nlm_list`, `nlm_delete`
- `nlm_add_source`, `nlm_list_sources`
- `nlm_ask`, `nlm_summarize`
- `nlm_generate`, `nlm_download`, `nlm_list_artifacts`
- `nlm_research`, `nlm_research_pipeline`, `nlm_trend_research`

Notebook deletion requires `confirm=true`. HTTP mode binds only to loopback:

```bash
notebooklm-mcp --http --host 127.0.0.1 --port 8765
```

Do not expose HTTP mode directly to a network. If remote access is unavoidable, put
it behind an authenticated TLS proxy and apply host-level access controls.

## Operating rules

1. Verify authentication before a long workflow.
2. Confirm sources were ingested; treat `partial` or failed source entries honestly.
3. Ask focused questions and retain returned citation metadata.
4. Use exact notebook and artifact IDs in repeated automation.
5. Use bounded source/artifact concurrency; generation is quota-sensitive.
6. Do not delete notebooks or overwrite output without explicit user intent.
7. Do not claim a draft was published; no publishing integration exists here.
8. Return the JSON result or a faithful summary, including partial failures.

## Exit codes and recovery

- `0`: operation completed successfully.
- `2`: invalid or ambiguous arguments.
- `4`: authentication required.
- `1`: upstream, network, generation, or other operational failure.
- `130`: interrupted by the user.

Common recovery:

```bash
notebooklm-auth verify
notebooklm-auth setup                 # missing or expired session
notebooklm-skill list-artifacts --notebook NOTEBOOK_ID  # inspect a timed-out job
```

Use `notebooklm-skill --help`, `notebooklm-pipeline --help`, and the relevant
subcommand's `--help` as the authoritative local command contract.
