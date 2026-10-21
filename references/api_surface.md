# notebooklm-py compatibility surface

> Project contract: `notebooklm-py>=0.8.5,<0.9`

The private NotebookLM web API changes frequently. Application code should use
`scripts/common.py` instead of calling `notebooklm-py` independently from each public
surface. This document lists the upstream calls the compatibility layer relies on.
`tests/test_upstream_contract.py` checks these signatures, enums, and result types
against the installed release on every CI run.

## Client and authentication

```python
from notebooklm import NotebookLMClient

async with NotebookLMClient.from_storage() as client:
    notebooks = await client.notebooks.list()
```

`from_storage()` is itself an async context manager; do not write
`async with await NotebookLMClient.from_storage()`. Profile resolution is delegated to
`notebooklm.paths.get_storage_path()` and respects `NOTEBOOKLM_PROFILE`,
`NOTEBOOKLM_HOME`, and upstream auth configuration.

The project normalizes upstream authentication exceptions to
`AuthenticationRequired` with a safe message that never includes cookies. A missing
session file raises `FileNotFoundError` upstream and is reported the same way.

## Error contract (0.8.x)

notebooklm-py 0.8 raises instead of returning sentinel values:

- `artifacts.generate_*` raises `RateLimitError` or `RPCError` when NotebookLM refuses
  a generation, instead of returning `GenerationStatus(status="failed")`;
- `research.start` raises `DecodingError` instead of returning `None`;
- expired sessions and HTTP 401/403 artifact downloads raise `AuthError`.

The wrappers let refusals propagate as operation errors (CLI exit 1, MCP tool error,
or a failed pipeline item) and map `AuthError` to `AUTH_REQUIRED` (CLI exit 4). The
older `task_id` and `None` checks remain as defensive guards.

## Notebook and source APIs

| Operation | Upstream call |
|---|---|
| Create | `client.notebooks.create(title=...)` |
| List | `client.notebooks.list()` |
| Delete | `client.notebooks.delete(notebook_id=...)` — success returns `None` |
| Summary | `client.notebooks.get_summary(notebook_id=...)` |
| List sources | `client.sources.list(notebook_id)` |
| Add URL | `add_url(notebook_id, url, wait=True, wait_timeout=...)` |
| Add text | `add_text(notebook_id, title, content, wait=True, wait_timeout=...)` |
| Add file | `add_file(notebook_id, file_path=Path(...), wait=True, wait_timeout=...)` |

Mixed source ingestion validates URLs, checks local files, runs with bounded
concurrency, preserves input order, and returns one result per attempted source.

## Chat API

```python
answer = await client.chat.ask(notebook_id, question="...")
```

The public wrappers retain `answer.answer`, `answer.references`, and
`answer.conversation_id`. Citation objects are serialized without assuming a fixed
set of upstream fields.

## Artifact APIs

The wrappers expose 11 canonical names while mapping them to current upstream
generators and downloaders:

| Canonical type | Generator | Downloader | Default extension |
|---|---|---|---:|
| `audio` | `generate_audio` | `download_audio` | `m4a` |
| `video` | `generate_video` | `download_video` | `mp4` |
| `cinematic` | `generate_cinematic_video` | `download_video` | `mp4` |
| `slides` | `generate_slide_deck` | `download_slide_deck` | `pdf` |
| `report` | `generate_report` | `download_report` | `md` |
| `study-guide` | `generate_study_guide` | `download_report` | `md` |
| `quiz` | `generate_quiz` | `download_quiz` | `json` |
| `flashcards` | `generate_flashcards` | `download_flashcards` | `json` |
| `mind-map` | `generate_mind_map` | `download_mind_map` | `json` |
| `infographic` | `generate_infographic` | `download_infographic` | `png` |
| `data-table` | `generate_data_table` | `download_data_table` | `csv` |

All task-based generators return a `GenerationStatus`. The compatibility layer checks
for `task_id`, waits with
`client.artifacts.wait_for_completion(notebook_id, task_id, timeout=...)`, and accepts
only a `completed` terminal state. `artifacts.generate_mind_map` remains the
synchronous, note-backed mind-map path in 0.8.x and is handled separately; its
`note_id` is the artifact ID used for downloads.

Artifacts are listed with `client.artifacts.list(notebook_id, ArtifactType | None)`.
Signed download URLs are deliberately omitted from serialized output. Downloads pass
the exact selected `artifact_id` where supplied, validate output formats, reject
symlinks, and refuse accidental overwrites.

### Type-specific enum options

- audio: `AudioFormat`, `AudioLength`
- video: `VideoFormat` (including `SHORT`), `VideoStyle`, plus custom `style_prompt`
- slides: `SlideDeckFormat`, `SlideDeckLength`
- report: `ReportFormat`, plus `custom_prompt`
- quiz/flashcards: `QuizQuantity` (including `MORE`), `QuizDifficulty`
- infographic: `InfographicOrientation`, `InfographicDetail`, `InfographicStyle`

User-facing kebab-case values are validated and converted to upstream enums. The
wrappers reject upstream-invalid combinations before any network call: a custom
video style needs `style_prompt`, cinematic videos take no `style_prompt`, and short
videos have a fixed style.

## Research API

The complete lifecycle is:

```python
started = await client.research.start(notebook_id, query=query, source="web", mode="deep")
final = await client.research.wait_for_completion(notebook_id, task_id=started.task_id, timeout=1800)
imported = await client.research.import_sources(notebook_id, started.task_id, final.sources[:max_sources])
```

`mode` is `"fast"` or `"deep"`. `ResearchTask` and `ResearchSource` are attribute-only
dataclasses in 0.8.x; the wrappers never subscript them.

The wrapper validates terminal status, caps imported sources, and supports returning
immediately with the task ID. It never reports a non-terminal or failed task as
completed.

## Serialization contract

Serialization accepts mappings, sequences, dataclasses, enums, paths, dates, and
typed upstream objects. Stable public subsets are used for notebooks, sources, and
artifacts. Unknown non-private fields are retained only by the generic serializer.

## Upgrade checklist

When raising the upper dependency bound:

1. inspect every signature listed above;
2. run the contract tests against both the minimum and newest supported versions;
3. verify enum names/values and terminal states;
4. verify profile path behavior and authentication exceptions;
5. exercise one real read-only session plus an artifact list;
6. update this file, CLI help snapshots, and the version bound together.
