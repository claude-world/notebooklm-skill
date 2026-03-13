# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

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
- Setup guides for both languages (`SETUP.md` / `SETUP-zh-TW.md`)
- MIT license

### Commits

- `5503d09` feat: notebooklm-skill v1.0.0 — NotebookLM as a Claude Code Skill + MCP Server
- `e75f8ea` docs: full zh-TW localization, doc fixes, video synthesis tool
- `0f8edce` docs: add bilingual README and SETUP (EN + zh-TW)

[1.0.0]: https://github.com/claude-world/notebooklm-skill/releases/tag/v1.0.0
