# notebooklm-py API Surface Reference

> **Package**: `notebooklm-py` v0.3.4
> **Client**: `NotebookLMClient` (async context manager)
> **Auth**: Playwright `storage_state.json` (browser login)

---

## Client Initialization

```python
from notebooklm import NotebookLMClient

# From stored browser session (recommended)
async with await NotebookLMClient.from_storage() as client:
    notebooks = await client.notebooks.list()

# From stored session at custom path
async with await NotebookLMClient.from_storage(path="/custom/storage_state.json") as client:
    ...

# From AuthTokens directly
from notebooklm.auth import AuthTokens
auth = AuthTokens(cookies, csrf_token, session_id)
async with NotebookLMClient(auth, timeout=30.0) as client:
    ...
```

### Parameters

| Parameter | Type | Default | Description |
|---|---|---|---|
| `path` | `str \| None` | `None` | Path to `storage_state.json`. Default: `~/.notebooklm/storage_state.json` |
| `timeout` | `float` | `30.0` | HTTP request timeout in seconds |

### Properties

| Property | Type | Description |
|---|---|---|
| `auth` | `AuthTokens` | Current authentication tokens |
| `is_connected` | `bool` | Whether the HTTP client is open |

### Methods

| Method | Returns | Description |
|---|---|---|
| `refresh_auth()` | `AuthTokens` | Refresh CSRF token and session ID |

---

## Sub-APIs

The client provides 8 namespaced sub-APIs:

| Sub-API | Accessor | Description |
|---|---|---|
| Notebooks | `client.notebooks` | Create, list, delete, rename notebooks |
| Sources | `client.sources` | Add, list, delete, manage sources |
| Artifacts | `client.artifacts` | Generate and download AI content |
| Chat | `client.chat` | Ask questions, manage conversations |
| Research | `client.research` | Web/Drive research sessions |
| Notes | `client.notes` | User-created notes management |
| Settings | `client.settings` | User settings (output language) |
| Sharing | `client.sharing` | Notebook sharing and permissions |

---

## Notebooks API (`client.notebooks`)

### Methods

| Method | Parameters | Returns | Description |
|---|---|---|---|
| `list()` | -- | `list[Notebook]` | List all notebooks |
| `create(title)` | `title: str` | `Notebook` | Create a new notebook |
| `get(notebook_id)` | `notebook_id: str` | `Notebook` | Get notebook details |
| `delete(notebook_id)` | `notebook_id: str` | `bool` | Delete a notebook |
| `rename(notebook_id, new_title)` | `notebook_id: str, new_title: str` | `Notebook` | Rename a notebook |
| `get_summary(notebook_id)` | `notebook_id: str` | `str` | Get raw summary text |
| `get_description(notebook_id)` | `notebook_id: str` | `NotebookDescription` | Get AI summary + suggested topics |
| `get_metadata(notebook_id)` | `notebook_id: str` | `NotebookMetadata` | Get notebook details + sources list |
| `get_raw(notebook_id)` | `notebook_id: str` | `Any` | Get raw API response |
| `share(notebook_id, public, artifact_id?)` | `notebook_id: str, public: bool, artifact_id: str \| None` | `dict` | Toggle sharing |
| `get_share_url(notebook_id, artifact_id?)` | `notebook_id: str, artifact_id: str \| None` | `str` | Get share URL (no API call) |
| `remove_from_recent(notebook_id)` | `notebook_id: str` | `None` | Remove from recent list |

### Data Types

```python
@dataclass
class Notebook:
    id: str
    title: str
    created_at: datetime | None
    sources_count: int
    is_owner: bool

@dataclass
class NotebookDescription:
    summary: str
    suggested_topics: list[SuggestedTopic]

@dataclass
class SuggestedTopic:
    question: str
    prompt: str

@dataclass
class NotebookMetadata:
    notebook: Notebook
    sources: list[SourceSummary]
    # Properties: id, title, created_at, is_owner
    # Method: to_dict() -> dict
```

---

## Sources API (`client.sources`)

### Methods

| Method | Parameters | Returns | Description |
|---|---|---|---|
| `list(notebook_id)` | `notebook_id: str` | `list[Source]` | List all sources |
| `get(notebook_id, source_id)` | `notebook_id: str, source_id: str` | `Source \| None` | Get source details |
| `add_url(notebook_id, url, wait?, wait_timeout?)` | `notebook_id: str, url: str, wait: bool=False, wait_timeout: float=120.0` | `Source` | Add URL source (auto-detects YouTube) |
| `add_text(notebook_id, title, content, wait?, wait_timeout?)` | `notebook_id: str, title: str, content: str, wait: bool=False, wait_timeout: float=120.0` | `Source` | Add pasted text source |
| `add_file(notebook_id, file_path, mime_type?, wait?, wait_timeout?)` | `notebook_id: str, file_path: str \| Path, mime_type: str \| None=None, wait: bool=False, wait_timeout: float=120.0` | `Source` | Upload file (PDF, Markdown, DOCX) |
| `add_drive(notebook_id, file_id, title, mime_type?, wait?, wait_timeout?)` | `notebook_id: str, file_id: str, title: str, mime_type: str="application/vnd.google-apps.document", wait: bool=False, wait_timeout: float=120.0` | `Source` | Add Google Drive document |
| `delete(notebook_id, source_id)` | `notebook_id: str, source_id: str` | `bool` | Delete a source |
| `rename(notebook_id, source_id, new_title)` | `notebook_id: str, source_id: str, new_title: str` | `Source` | Rename a source |
| `refresh(notebook_id, source_id)` | `notebook_id: str, source_id: str` | `bool` | Refresh source content |
| `check_freshness(notebook_id, source_id)` | `notebook_id: str, source_id: str` | `bool` | Check if source needs refresh |
| `get_guide(notebook_id, source_id)` | `notebook_id: str, source_id: str` | `dict` | Get AI summary + keywords |
| `get_fulltext(notebook_id, source_id)` | `notebook_id: str, source_id: str` | `SourceFulltext` | Get full indexed text content |
| `wait_until_ready(notebook_id, source_id, timeout?, ...)` | `notebook_id: str, source_id: str, timeout: float=120.0` | `Source` | Poll until source is ready |
| `wait_for_sources(notebook_id, source_ids, timeout?, ...)` | `notebook_id: str, source_ids: list[str], timeout: float=120.0` | `list[Source]` | Wait for multiple sources in parallel |

### Data Types

```python
@dataclass
class Source:
    id: str
    title: str | None
    url: str | None
    created_at: datetime | None
    status: int          # SourceStatus: 1=processing, 2=ready, 3=error, 4=preparing
    # Properties:
    kind: SourceType     # "web_page", "pdf", "youtube", "pasted_text", etc.
    is_ready: bool
    is_processing: bool
    is_error: bool

@dataclass
class SourceFulltext:
    source_id: str
    title: str
    content: str         # Full indexed text
    url: str | None
    char_count: int
    kind: SourceType
    # Method: find_citation_context(cited_text, context_chars=200) -> list[tuple[str, int]]

class SourceType(str, Enum):
    GOOGLE_DOCS = "google_docs"
    GOOGLE_SLIDES = "google_slides"
    GOOGLE_SPREADSHEET = "google_spreadsheet"
    PDF = "pdf"
    PASTED_TEXT = "pasted_text"
    WEB_PAGE = "web_page"
    YOUTUBE = "youtube"
    MARKDOWN = "markdown"
    DOCX = "docx"
    CSV = "csv"
    IMAGE = "image"
    MEDIA = "media"
    UNKNOWN = "unknown"

class DriveMimeType(Enum):
    GOOGLE_DOC = "application/vnd.google-apps.document"
    GOOGLE_SLIDES = "application/vnd.google-apps.presentation"
    GOOGLE_SHEETS = "application/vnd.google-apps.spreadsheet"
    PDF = "application/pdf"
```

### Source Guide Response

```python
{
    "summary": "AI-generated summary with **bold** keywords (markdown)",
    "keywords": ["topic1", "topic2", "topic3"]
}
```

---

## Artifacts API (`client.artifacts`)

### List/Get Methods

| Method | Parameters | Returns | Description |
|---|---|---|---|
| `list(notebook_id, artifact_type?)` | `notebook_id: str, artifact_type: ArtifactType \| None` | `list[Artifact]` | List all artifacts |
| `get(notebook_id, artifact_id)` | `notebook_id: str, artifact_id: str` | `Artifact \| None` | Get specific artifact |
| `list_audio(notebook_id)` | `notebook_id: str` | `list[Artifact]` | List audio artifacts only |
| `list_video(notebook_id)` | `notebook_id: str` | `list[Artifact]` | List video artifacts only |
| `list_reports(notebook_id)` | `notebook_id: str` | `list[Artifact]` | List report artifacts only |
| `list_quizzes(notebook_id)` | `notebook_id: str` | `list[Artifact]` | List quiz artifacts only |
| `list_flashcards(notebook_id)` | `notebook_id: str` | `list[Artifact]` | List flashcard artifacts only |
| `list_infographics(notebook_id)` | `notebook_id: str` | `list[Artifact]` | List infographic artifacts only |
| `list_slide_decks(notebook_id)` | `notebook_id: str` | `list[Artifact]` | List slide deck artifacts only |
| `list_data_tables(notebook_id)` | `notebook_id: str` | `list[Artifact]` | List data table artifacts only |

### Generate Methods

| Method | Key Parameters | Returns | Description |
|---|---|---|---|
| `generate_audio(notebook_id, ...)` | `source_ids?, language="en", instructions?, audio_format?, audio_length?` | `GenerationStatus` | Generate Audio Overview (podcast) |
| `generate_video(notebook_id, ...)` | `source_ids?, language="en", instructions?, video_format?, video_style?` | `GenerationStatus` | Generate Video Overview |
| `generate_cinematic_video(notebook_id, ...)` | `source_ids?, language="en", instructions?` | `GenerationStatus` | Generate Cinematic Video (Veo 3, AI Ultra only) |
| `generate_report(notebook_id, ...)` | `report_format=BRIEFING_DOC, source_ids?, language="en", custom_prompt?, extra_instructions?` | `GenerationStatus` | Generate report |
| `generate_study_guide(notebook_id, ...)` | `source_ids?, language="en", extra_instructions?` | `GenerationStatus` | Generate study guide (convenience) |
| `generate_quiz(notebook_id, ...)` | `source_ids?, instructions?, quantity?, difficulty?` | `GenerationStatus` | Generate quiz |
| `generate_flashcards(notebook_id, ...)` | `source_ids?, instructions?, quantity?, difficulty?` | `GenerationStatus` | Generate flashcards |
| `generate_infographic(notebook_id, ...)` | `source_ids?, language="en", instructions?, orientation?, detail_level?, style?` | `GenerationStatus` | Generate infographic |
| `generate_slide_deck(notebook_id, ...)` | `source_ids?, language="en", instructions?, slide_format?, slide_length?` | `GenerationStatus` | Generate slide deck |
| `generate_data_table(notebook_id, ...)` | `source_ids?, language="en", instructions?` | `GenerationStatus` | Generate data table |
| `generate_mind_map(notebook_id, ...)` | `source_ids?` | `dict` | Generate mind map (returns data + note_id) |

### Status/Download Methods

| Method | Parameters | Returns | Description |
|---|---|---|---|
| `poll_status(notebook_id, task_id)` | `notebook_id: str, task_id: str` | `GenerationStatus` | Check generation progress |
| `wait_for_completion(notebook_id, task_id, ...)` | `notebook_id: str, task_id: str, timeout: float=300.0` | `GenerationStatus` | Wait until artifact is done |
| `download_audio(notebook_id, output_path, artifact_id?)` | `notebook_id: str, output_path: str, artifact_id: str \| None` | `str` | Download audio to file (.m4a) |
| `download_video(notebook_id, output_path, artifact_id?)` | `notebook_id: str, output_path: str, artifact_id: str \| None` | `str` | Download video to file (.mp4) |
| `download_slide_deck(notebook_id, output_path, artifact_id?, output_format?)` | `notebook_id: str, output_path: str, artifact_id: str \| None, output_format: str="pdf"` | `str` | Download slides (PDF or PPTX) |
| `download_report(notebook_id, output_path, artifact_id?)` | `notebook_id: str, output_path: str, artifact_id: str \| None` | `str` | Download report (Markdown) |
| `download_quiz(notebook_id, output_path, artifact_id?, output_format?)` | `notebook_id: str, output_path: str, artifact_id: str \| None, output_format: str="json"` | `str` | Download quiz (JSON, Markdown, or HTML) |
| `download_flashcards(notebook_id, output_path, artifact_id?, output_format?)` | `notebook_id: str, output_path: str, artifact_id: str \| None, output_format: str="json"` | `str` | Download flashcards (JSON, Markdown, or HTML) |
| `download_mind_map(notebook_id, output_path, artifact_id?)` | `notebook_id: str, output_path: str, artifact_id: str \| None` | `str` | Download mind map (JSON) |
| `download_infographic(notebook_id, output_path, artifact_id?)` | `notebook_id: str, output_path: str, artifact_id: str \| None` | `str` | Download infographic (PNG) |
| `download_data_table(notebook_id, output_path, artifact_id?)` | `notebook_id: str, output_path: str, artifact_id: str \| None` | `str` | Download data table (CSV) |
| `get_report_content(notebook_id, artifact_id?)` | `notebook_id: str, artifact_id: str \| None` | `str` | Get report markdown text |
| `get_quiz_data(notebook_id, artifact_id?)` | `notebook_id: str, artifact_id: str \| None` | `dict` | Get quiz as structured data |
| `get_flashcard_data(notebook_id, artifact_id?)` | `notebook_id: str, artifact_id: str \| None` | `dict` | Get flashcards as structured data |
| `get_mind_map_data(notebook_id, artifact_id?)` | `notebook_id: str, artifact_id: str \| None` | `dict` | Get mind map JSON |
| `get_data_table(notebook_id, artifact_id?)` | `notebook_id: str, artifact_id: str \| None` | `dict` | Get data table (headers + rows) |
| `rename(notebook_id, artifact_id, new_title)` | `notebook_id: str, artifact_id: str, new_title: str` | `bool` | Rename artifact |
| `delete(notebook_id, artifact_id)` | `notebook_id: str, artifact_id: str` | `bool` | Delete artifact |
| `get_suggested_report_formats(notebook_id)` | `notebook_id: str` | `list[ReportSuggestion]` | Get AI-suggested report formats |
| `revise_slide(notebook_id, artifact_id, slide_index, prompt)` | `notebook_id: str, artifact_id: str, slide_index: int, prompt: str` | `GenerationStatus` | Revise individual slide |

### Enums for Generate Methods

```python
class AudioFormat(Enum):
    DEEP_DIVE = 1
    BRIEF = 2
    CRITIQUE = 3
    DEBATE = 4

class AudioLength(Enum):
    SHORT = 1
    DEFAULT = 2
    LONG = 3

class VideoFormat(Enum):
    EXPLAINER = 1
    BRIEF = 2
    CINEMATIC = 3       # Requires AI Ultra

class VideoStyle(Enum):
    AUTO_SELECT = 1
    CLASSIC = 2
    WHITEBOARD = 3
    CONVERSATIONAL = 4
    DYNAMIC = 5

class ReportFormat(Enum):
    BRIEFING_DOC = 1
    STUDY_GUIDE = 2
    BLOG_POST = 3
    CUSTOM = 4

class QuizQuantity(Enum):
    FEWER = 1
    STANDARD = 2
    MORE = 3

class QuizDifficulty(Enum):
    EASY = 1
    MEDIUM = 2
    HARD = 3

class InfographicOrientation(Enum):
    LANDSCAPE = 1
    PORTRAIT = 2
    SQUARE = 3

class InfographicDetail(Enum):
    CONCISE = 1
    STANDARD = 2
    DETAILED = 3

class InfographicStyle(Enum):
    # Multiple visual presets available

class SlideDeckFormat(Enum):
    DETAILED_DECK = 1
    PRESENTER_SLIDES = 2

class SlideDeckLength(Enum):
    DEFAULT = 1
    SHORT = 2
```

### Data Types

```python
@dataclass
class Artifact:
    id: str
    title: str
    status: int         # 1=processing, 2=pending, 3=completed, 4=failed
    created_at: datetime | None
    url: str | None
    # Properties:
    kind: ArtifactType  # "audio", "video", "report", "quiz", "flashcards", etc.
    is_completed: bool
    is_processing: bool
    is_pending: bool
    is_failed: bool
    status_str: str     # "in_progress", "pending", "completed", "failed"
    is_quiz: bool
    is_flashcards: bool
    report_subtype: str | None  # "briefing_doc", "study_guide", "blog_post"

class ArtifactType(str, Enum):
    AUDIO = "audio"
    VIDEO = "video"
    REPORT = "report"
    QUIZ = "quiz"
    FLASHCARDS = "flashcards"
    MIND_MAP = "mind_map"
    INFOGRAPHIC = "infographic"
    SLIDE_DECK = "slide_deck"
    DATA_TABLE = "data_table"
    UNKNOWN = "unknown"

@dataclass
class GenerationStatus:
    task_id: str        # Same as artifact_id
    status: str         # "pending", "in_progress", "completed", "failed"
    url: str | None
    error: str | None
    error_code: str | None
    metadata: dict | None
    # Properties:
    is_complete: bool
    is_failed: bool
    is_pending: bool
    is_in_progress: bool
    is_rate_limited: bool

@dataclass
class ReportSuggestion:
    title: str
    description: str
    prompt: str
    audience_level: int  # 1=beginner, 2=advanced
```

---

## Chat API (`client.chat`)

### Methods

| Method | Parameters | Returns | Description |
|---|---|---|---|
| `ask(notebook_id, question, source_ids?, conversation_id?)` | `notebook_id: str, question: str, source_ids: list[str] \| None, conversation_id: str \| None` | `AskResult` | Ask a question, get cited answer |
| `get_conversation_id(notebook_id)` | `notebook_id: str` | `str \| None` | Get most recent conversation ID |
| `get_conversation_turns(notebook_id, conversation_id, limit?)` | `notebook_id: str, conversation_id: str, limit: int=2` | `Any` | Get raw turn data |
| `get_history(notebook_id, limit?, conversation_id?)` | `notebook_id: str, limit: int=100, conversation_id: str \| None` | `list[tuple[str, str]]` | Get Q&A pairs, oldest-first |
| `get_cached_turns(conversation_id)` | `conversation_id: str` | `list[ConversationTurn]` | Get locally cached turns |
| `clear_cache(conversation_id?)` | `conversation_id: str \| None` | `bool` | Clear conversation cache |
| `configure(notebook_id, goal?, response_length?, custom_prompt?)` | `notebook_id: str, goal: ChatGoal \| None, response_length: ChatResponseLength \| None, custom_prompt: str \| None` | `None` | Configure chat persona |
| `set_mode(notebook_id, mode)` | `notebook_id: str, mode: ChatMode` | `None` | Set predefined chat mode |

### Data Types

```python
@dataclass
class AskResult:
    answer: str                      # AI-generated answer text
    conversation_id: str             # UUID for follow-up questions
    turn_number: int
    is_follow_up: bool
    references: list[ChatReference]  # Source citations
    raw_response: str                # First 1000 chars (debug)

@dataclass
class ChatReference:
    source_id: str                   # Source UUID
    citation_number: int | None      # [1], [2], etc.
    cited_text: str | None           # Passage from source
    start_char: int | None           # Position in source
    end_char: int | None
    chunk_id: str | None             # Internal (debug)

@dataclass
class ConversationTurn:
    query: str
    answer: str
    turn_number: int

class ChatMode(Enum):
    DEFAULT = "default"
    LEARNING_GUIDE = "learning_guide"
    CONCISE = "concise"
    DETAILED = "detailed"

class ChatGoal(Enum):
    DEFAULT = 1
    CUSTOM = 2
    LEARNING_GUIDE = 3

class ChatResponseLength(Enum):
    SHORTER = 1
    DEFAULT = 2
    LONGER = 3
```

---

## Research API (`client.research`)

### Methods

| Method | Parameters | Returns | Description |
|---|---|---|---|
| `start(notebook_id, query, source?, mode?)` | `notebook_id: str, query: str, source: str="web", mode: str="fast"` | `dict \| None` | Start research session |
| `poll(notebook_id)` | `notebook_id: str` | `dict` | Poll for results |
| `import_sources(notebook_id, task_id, sources)` | `notebook_id: str, task_id: str, sources: list[dict]` | `list[dict]` | Import discovered sources |

### Parameters

- `source`: `"web"` or `"drive"`
- `mode`: `"fast"` or `"deep"` (deep only for web)

### Response Formats

**start() returns:**
```python
{
    "task_id": "abc123",
    "report_id": "def456",
    "notebook_id": "NOTEBOOK_ID",
    "query": "search query",
    "mode": "fast"
}
```

**poll() returns:**
```python
{
    "task_id": "abc123",
    "status": "completed",  # "in_progress", "completed", "no_research"
    "query": "search query",
    "sources": [
        {
            "url": "https://...",
            "title": "Source Title",
            "result_type": 1,          # 1=web, 2=drive, 5=report
            "research_task_id": "abc123",
            "report_markdown": "..."   # Only for deep research reports
        }
    ],
    "summary": "Research summary text",
    "report": "Deep research report markdown",
    "tasks": [...]  # All parsed research tasks
}
```

---

## Notes API (`client.notes`)

### Methods

| Method | Parameters | Returns | Description |
|---|---|---|---|
| `list(notebook_id)` | `notebook_id: str` | `list[Note]` | List text notes (excludes mind maps) |
| `get(notebook_id, note_id)` | `notebook_id: str, note_id: str` | `Note \| None` | Get specific note |
| `create(notebook_id, title?, content?)` | `notebook_id: str, title: str="New Note", content: str=""` | `Note` | Create a note |
| `update(notebook_id, note_id, content, title)` | `notebook_id: str, note_id: str, content: str, title: str` | `None` | Update note content and title |
| `delete(notebook_id, note_id)` | `notebook_id: str, note_id: str` | `bool` | Delete a note |
| `list_mind_maps(notebook_id)` | `notebook_id: str` | `list[Any]` | List mind maps (raw data) |
| `delete_mind_map(notebook_id, mind_map_id)` | `notebook_id: str, mind_map_id: str` | `bool` | Delete a mind map |

### Data Types

```python
@dataclass
class Note:
    id: str
    notebook_id: str
    title: str
    content: str
    created_at: datetime | None
```

---

## Sharing API (`client.sharing`)

### Methods

| Method | Parameters | Returns | Description |
|---|---|---|---|
| `get_status(notebook_id)` | `notebook_id: str` | `ShareStatus` | Get current sharing config |
| `set_public(notebook_id, public)` | `notebook_id: str, public: bool` | `ShareStatus` | Enable/disable public link |
| `set_view_level(notebook_id, level)` | `notebook_id: str, level: ShareViewLevel` | `ShareStatus` | Set what viewers can access |
| `add_user(notebook_id, email, permission?, notify?, welcome_message?)` | `notebook_id: str, email: str, permission: SharePermission=VIEWER, notify: bool=True, welcome_message: str=""` | `ShareStatus` | Share with user |
| `update_user(notebook_id, email, permission)` | `notebook_id: str, email: str, permission: SharePermission` | `ShareStatus` | Update user permission |
| `remove_user(notebook_id, email)` | `notebook_id: str, email: str` | `ShareStatus` | Remove user access |

### Enums

```python
class ShareAccess(Enum):
    RESTRICTED = 0
    ANYONE_WITH_LINK = 1

class SharePermission(Enum):
    OWNER = 1
    EDITOR = 2
    VIEWER = 3

class ShareViewLevel(Enum):
    FULL_NOTEBOOK = 1
    CHAT_ONLY = 2
```

### Data Types

```python
@dataclass
class ShareStatus:
    notebook_id: str
    is_public: bool
    access: ShareAccess
    view_level: ShareViewLevel
    shared_users: list[SharedUser]
    share_url: str | None

@dataclass
class SharedUser:
    email: str
    permission: SharePermission
    display_name: str | None
    avatar_url: str | None
```

---

## Error Hierarchy

```
NotebookLMError (base)
├── AuthError              # Authentication expired or invalid
├── ClientError            # Client-side errors
│   ├── ConfigurationError # Invalid configuration
│   └── ValidationError    # Invalid parameters
├── NetworkError           # Connection/timeout issues
├── RPCError               # Google RPC call failures
│   ├── RPCTimeoutError    # RPC timed out
│   └── UnknownRPCMethodError
├── NotebookError
│   └── NotebookNotFoundError
├── SourceError
│   ├── SourceAddError     # Failed to add source
│   ├── SourceProcessingError  # Source processing failed
│   ├── SourceTimeoutError     # Wait timed out
│   └── SourceNotFoundError
├── ArtifactError
│   ├── ArtifactNotFoundError
│   ├── ArtifactNotReadyError
│   ├── ArtifactParseError
│   └── ArtifactDownloadError
├── ChatError              # Chat request failures
└── ServerError            # Google server-side errors
    └── RateLimitError     # Rate limit exceeded
```

---

## CLI Reference

The `notebooklm` CLI mirrors the Python API:

```bash
# Authentication
notebooklm login              # Browser login, saves storage_state.json
notebooklm login --check      # Verify stored session

# Notebooks
notebooklm notebook list
notebooklm notebook create "Title"
notebooklm notebook get NOTEBOOK_ID
notebooklm notebook delete NOTEBOOK_ID
notebooklm notebook rename NOTEBOOK_ID "New Title"

# Sources
notebooklm source list NOTEBOOK_ID
notebooklm source add NOTEBOOK_ID --url "https://..."
notebooklm source add NOTEBOOK_ID --text "Title" --content "..."
notebooklm source add NOTEBOOK_ID --file /path/to/file.pdf
notebooklm source delete NOTEBOOK_ID SOURCE_ID
notebooklm source guide NOTEBOOK_ID SOURCE_ID
notebooklm source fulltext NOTEBOOK_ID SOURCE_ID

# Chat
notebooklm chat NOTEBOOK_ID "What is this about?"
notebooklm chat NOTEBOOK_ID "Follow up" --conversation CONV_ID

# Artifacts
notebooklm generate audio NOTEBOOK_ID
notebooklm generate video NOTEBOOK_ID
notebooklm generate report NOTEBOOK_ID --format briefing_doc
notebooklm generate quiz NOTEBOOK_ID
notebooklm generate flashcards NOTEBOOK_ID
notebooklm generate infographic NOTEBOOK_ID
notebooklm generate slide-deck NOTEBOOK_ID
notebooklm generate data-table NOTEBOOK_ID
notebooklm generate mind-map NOTEBOOK_ID
notebooklm generate study-guide NOTEBOOK_ID
notebooklm download audio NOTEBOOK_ID output.m4a
notebooklm download video NOTEBOOK_ID output.mp4
notebooklm download slide-deck NOTEBOOK_ID output.pdf
notebooklm download report NOTEBOOK_ID output.md
notebooklm download study-guide NOTEBOOK_ID output.md
notebooklm download quiz NOTEBOOK_ID output.json
notebooklm download flashcards NOTEBOOK_ID output.json
notebooklm download mind-map NOTEBOOK_ID output.json
notebooklm download infographic NOTEBOOK_ID output.png
notebooklm download data-table NOTEBOOK_ID output.csv

# Research
notebooklm research start NOTEBOOK_ID "query"
notebooklm research poll NOTEBOOK_ID

# Sharing
notebooklm share NOTEBOOK_ID --public
notebooklm share NOTEBOOK_ID --add user@example.com
```
