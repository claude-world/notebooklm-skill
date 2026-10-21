# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [1.4.0] — 2026-10-21

### Changed

- Upgraded to `notebooklm-py` 0.8.5 (`>=0.8.5,<0.9`) and its 0.8 error contract: generation
  refusals and research start failures now surface as operation errors, and expired or
  signed-out sessions are reported as `AUTH_REQUIRED` more reliably
- Upgraded the MCP server to FastMCP 4 (`fastmcp>=4.1,<5`), which runs on the MCP Python
  SDK 2.x; MCP tool names, parameters, and results are unchanged
- Raised runtime floors to tested versions (`python-dotenv>=1.1`, `httpx>=0.28`,
  `feedparser>=6.0.12`) and refreshed development tools (mypy 2, pytest 9, pytest-asyncio
  1.3+, pytest-cov 7, Ruff 0.17, Twine 7, build 1.3+)
- Pinned Ruff to one minor series so a new Ruff release cannot reformat the code base
  between CI runs
- CI now tests Python 3.10 through 3.15, smoke-tests the built wheel's MCP server over stdio
  and its authentication error contract, and uses current GitHub Actions (checkout v7,
  setup-python v7, CodeQL v4 without autobuild, action-gh-release v3)
- Dependabot now runs monthly and groups minor and patch updates
- The build backend now requires setuptools 77 or newer, the first release that supports the
  PEP 639 license metadata the project already declares

### Added

- `--video-format short` (vertical short video) and `--quantity more` (larger quizzes and
  flashcard sets) CLI choices; MCP `nlm_generate` accepts the same option values
- Upfront validation that rejects `--video-style` and `--style-prompt` for short videos with
  exit code 2 instead of an upstream error
- Offline upstream contract tests for every `notebooklm-py` signature, enum, and result type
  the compatibility layer relies on, plus MCP tool-schema, MCP client round-trip, and
  SKILL.md frontmatter tests
- `license` and `compatibility` fields in the SKILL.md frontmatter
- Python 3.15 classifier

### Fixed

- `generate --output`, `podcast --output`, and `qa --output` now reject an existing output
  file, an invalid `--output-format`, or invalid generation options before opening a session
  or starting a generation job; previously these errors appeared only after the job finished,
  and an unauthenticated run reported `AUTH_REQUIRED` instead of the invalid argument
- `generate-all` checks every download destination before creating a notebook, so a
  leftover file in `--output-dir` no longer fails downloads after all generations ran
- MCP `nlm_generate` validates the artifact type and options before opening a session
- `ruff format --check` failing on the Python example in `references/api_surface.md` under
  Ruff 0.17, which now formats Markdown code blocks
- Stale `notebooklm-py` 0.7.x references and an inaccurate project layout in the docs
- Coverage data files are no longer left untracked in the working tree

## [1.3.0] — 2026-07-18

### Added

- Shared `notebooklm-py` 0.7.x compatibility layer used by CLI, pipelines, and MCP
- Profile-aware `notebooklm-auth` setup, verification, and scoped logout command
- Selectable system Chrome/Edge login with an optional fresh NotebookLM browser profile
- Safe `notebooklm-install-skill` command with standard layout, atomic writes, and backups
- Mixed URL, text, and local-file ingestion with bounded concurrency and per-source results
- Exact artifact listing and ID-based downloads for 11 canonical artifact types
- Full research lifecycle support: start, wait, terminal-state validation, and source import
- Type-specific generation options, detached jobs, bounded RSS reads, and safe trend command execution

### Changed

- Updated dependency contract to `notebooklm-py>=0.7.3,<0.8` and FastMCP 2/3 compatibility
- Rebuilt all five pipelines as real async workflows with truthful partial-failure states
- Made CLI output consistently JSON-first with meaningful exit codes and explicit destructive flags
- Restricted MCP HTTP mode to loopback and converted operational failures to MCP tool errors
- Replaced the system-Python installer with a PEP 668-safe isolated environment
- Rewrote bilingual docs and the packaged Skill against the executable command contract

### Fixed

- Current profile session discovery, `add_text` argument order, delete success reporting,
  artifact listing, mind-map generation, research polling/import, and infographic downloads
- Newly created notebook responses now report the successfully ingested source count
- Shell injection risk in `make_video.sh`
- Duplicate release-triggered PyPI publishing

### Security

- Downloads reject symlinks and existing files by default
- Notebook deletion requires explicit confirmation on CLI and MCP surfaces
- Local file and HTTP MCP trust boundaries are now documented

## [1.2.2] — 2026-03-21

### Changed

- Disabled the `infographic` artifact type across the CLI, pipelines, and MCP server because
  its downloads were unreliable (restored in 1.3.0)

## [1.2.1] — 2026-03-17

### Added

- **MCP Server**: AI-friendly `[AUTH_REQUIRED]` error when Google session is missing — AI clients (Claude Code, Cursor) now guide users to run `uvx notebooklm login`
- **MCP Server**: Server instructions include authentication flow so AI knows upfront

### Changed

- **Docs**: All documentation (README, README.zh-TW, SETUP, SETUP.zh-TW) now show `uvx notebooklm login` as the recommended auth method

## [1.2.0] — 2026-03-17

### Added

- **PyPI publishing**: Package now published to PyPI — `pip install notebooklm-skill` works without cloning
- **uvx support**: Zero-install MCP server via `uvx --from notebooklm-skill notebooklm-mcp`
- **pyproject.toml**: Added `authors`, `keywords`, `classifiers`, and `[project.urls]` for PyPI metadata

### Changed

- **MCP config**: `.mcp.json` now defaults to `uvx` invocation (no pre-install required)
- **README**: Reordered Quick Start — uvx first, pip second, source third
- **Release workflow**: Added `pypa/gh-action-pypi-publish` with trusted publishing (OIDC)

## [1.1.0] — 2026-03-15

### Added

- **pyproject.toml**: `pip install .` support with three global CLI commands:
  - `notebooklm-skill` — core CLI operations
  - `notebooklm-pipeline` — workflow orchestration
  - `notebooklm-mcp` — MCP server
- **install.sh**: One-line installer (pip + Playwright + Claude Code Skill symlink)
- **.mcp.json**: MCP auto-discovery file for Claude Code / Cursor / Gemini CLI
- **AGENTS.md**: Codex CLI integration (project context for `codex` CLI)
- **requirements.txt**: Added missing `feedparser>=6.0` dependency

### Fixed

- **MCP Server**: `research_pipeline()` assembled empty content — was reading `"text"` key instead of `"answer"` from serialized results
- **Packaging**: Fixed PyPI dependency name `notebooklm` → `notebooklm-py` — `pip install .` would fail without this
- **MCP Server**: `nlm_download` docstring incorrectly stated audio format as `.mp3` (actually `.m4a`)
- **MCP Server**: `nlm_research` docstring said mode `"thorough"` — correct value is `"deep"`
- **SKILL.md**: Fixed `--question` flag references → `--query` (matching actual CLI argparse)
- **SKILL.md**: Fixed `add-source` example using non-existent `--content` flag → `--text` + `--text-title`
- **SKILL.md**: Fixed audio artifact format references (`.mp4` / `MP4` → `.m4a` / `M4A`)

### Changed

- **BREAKING**: Renamed `mcp-server/` to `mcp_server/` for Python package compatibility
  - Update MCP configs: `mcp-server/server.py` -> `mcp_server/server.py`
  - Or use the new global command: `notebooklm-mcp`
- **MCP Server**: Updated import from `from tools import ...` to `from mcp_server.tools import ...`
- Updated all documentation to reflect new install methods and directory name

## [1.0.1] — 2026-03-14

### Fixed

- **MCP Server**: `trend_research()` used `answer.text` instead of `answer.answer`, causing AttributeError
- **Pipeline**: `generate-all` workflow used wrong method names (`generate_slides`/`download_slides` → `generate_slide_deck`/`download_slide_deck`)
- **Tests**: `test_list_returns_json_array` called async `cmd_list` without await (coroutine never executed)
- **Tests**: replaced deprecated `asyncio.iscoroutinefunction()` with `inspect.iscoroutinefunction()`

## [1.0.0] — 2026-03-14

Initial public release of notebooklm-skill.

### Added

- 4-phase Research-to-Content pipeline: Ingest, Synthesize, Create, Publish
- 11 CLI commands for notebook and content management
- 13 MCP tools for Claude Code integration
- 10 artifact types: articles, social posts, newsletters, podcasts, videos, and more
- Browser-based NotebookLM authentication via Playwright (no API key needed)
- Integration with trend-pulse MCP and threads-viral-agent
- Video synthesis tool (multi-image + audio to MP4 via ffmpeg)
- Bilingual documentation: English and Traditional Chinese (zh-TW)
- Setup guides for both languages (`SETUP.md` / `SETUP.zh-TW.md`)
- MIT license

### Commits

- `5503d09` feat: notebooklm-skill v1.0.0 — NotebookLM as a Claude Code Skill + MCP Server
- `e75f8ea` docs: full zh-TW localization, doc fixes, video synthesis tool
- `0f8edce` docs: add bilingual README and SETUP (EN + zh-TW)

[1.4.0]: https://github.com/claude-world/notebooklm-skill/compare/v1.3.0...v1.4.0
[1.3.0]: https://github.com/claude-world/notebooklm-skill/compare/v1.2.2...v1.3.0
[1.2.2]: https://github.com/claude-world/notebooklm-skill/compare/v1.2.1...v1.2.2
[1.2.1]: https://github.com/claude-world/notebooklm-skill/compare/v1.2.0...v1.2.1
[1.2.0]: https://github.com/claude-world/notebooklm-skill/compare/v1.1.0...v1.2.0
[1.1.0]: https://github.com/claude-world/notebooklm-skill/compare/v1.0.1...v1.1.0
[1.0.1]: https://github.com/claude-world/notebooklm-skill/compare/v1.0.0...v1.0.1
[1.0.0]: https://github.com/claude-world/notebooklm-skill/releases/tag/v1.0.0
