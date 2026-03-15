# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

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

[1.1.0]: https://github.com/claude-world/notebooklm-skill/compare/v1.0.1...v1.1.0
[1.0.1]: https://github.com/claude-world/notebooklm-skill/compare/v1.0.0...v1.0.1
[1.0.0]: https://github.com/claude-world/notebooklm-skill/releases/tag/v1.0.0
