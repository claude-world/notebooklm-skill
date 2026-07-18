This Python project provides a JSON-first CLI, five async pipelines, and 13 MCP tools
for NotebookLM. Keep all `notebooklm-py` API adaptation in `scripts/common.py` so the
three public surfaces stay consistent. Follow the Ruff and mypy configuration, use
typed async code, and add behavior-focused pytest tests. Never log browser-state
cookies, overwrite output silently, or report partial upstream work as success.
