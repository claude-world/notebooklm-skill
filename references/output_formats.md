# JSON output contract

CLI commands write exactly one JSON document to stdout. Progress and diagnostics go
to stderr. Fields not available from NotebookLM are omitted instead of invented.

## Status values

- `ok`: requested work completed.
- `started`: an asynchronous job was created and the caller chose not to wait.
- `partial`: at least one independent source/question/artifact failed.
- `failed`: the workflow could not produce its primary result.

Operational exceptions use a nonzero process exit and this envelope:

```json
{
  "status": "failed",
  "error": "Human-readable explanation",
  "code": "INVALID_ARGUMENT"
}
```

Codes include `INVALID_ARGUMENT`, `AUTH_REQUIRED`, `CANCELLED`, `TIMEOUT`,
`OPERATION_ERROR`, `PIPELINE_ERROR`, `AUTH_ERROR`, and `INSTALL_ERROR` depending on
the entry point.

## Notebook creation

```json
{
  "status": "partial",
  "action": "create",
  "notebook": {"id": "nb-id", "title": "Research"},
  "source_summary": {"requested": 2, "succeeded": 1, "failed": 1},
  "sources": [
    {
      "status": "ok",
      "source_type": "url",
      "input": "https://example.com",
      "source": {"id": "source-id", "title": "Example", "kind": "web_page"}
    },
    {
      "status": "failed",
      "source_type": "file",
      "input": "missing.pdf",
      "error": "Source file not found: missing.pdf"
    }
  ]
}
```

## Grounded answer

```json
{
  "status": "ok",
  "action": "ask",
  "notebook_id": "nb-id",
  "query": "What evidence conflicts?",
  "answer": "...",
  "references": [
    {"source_id": "source-id", "citation_number": 1, "cited_text": "..."}
  ],
  "conversation_id": "conversation-id"
}
```

Reference fields are upstream-defined and may evolve. Consumers should tolerate
additional or missing optional fields.

## Generation

Detached task:

```json
{
  "status": "started",
  "state": "in_progress",
  "artifact_type": "audio",
  "task_id": "artifact-id",
  "action": "generate",
  "notebook_id": "nb-id"
}
```

Completed task with an automatic download:

```json
{
  "status": "ok",
  "state": "completed",
  "artifact_type": "slides",
  "task_id": "artifact-id",
  "result": {"task_id": "artifact-id", "status": "completed"},
  "action": "generate",
  "notebook_id": "nb-id",
  "output_path": "output/deck.pdf"
}
```

Signed upstream URLs are never included.

## Research

```json
{
  "status": "ok",
  "task_id": "research-task-id",
  "mode": "deep",
  "query": "Recent evaluations",
  "state": "completed",
  "result": {"status": "completed", "sources": []},
  "sources_found": 8,
  "sources_imported": 5,
  "imported": [{"id": "source-id", "title": "Imported source"}],
  "action": "research",
  "notebook_id": "nb-id"
}
```

## Pipeline outputs

Every pipeline includes `status`, `workflow`, serialized notebook metadata, source
results, and the primary result:

- `research-to-article`: `research_findings` and `article`;
- `research-to-social`: `summary`, `social`, and `platform_specs`;
- `trend-to-content`: one result per trend, including research and draft states;
- `batch-digest`: feed entries, `digest`, raw `qa`, and parsed `qa_pairs`;
- `generate-all`: per-artifact generation/download results and aggregate counts.

Consumers must check both the top-level status and nested per-item statuses.
