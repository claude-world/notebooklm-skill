# notebooklm-skill

> 給終端機與 AI Agent 使用的來源導向 NotebookLM 自動化工具。

[![CI](https://github.com/claude-world/notebooklm-skill/actions/workflows/ci.yml/badge.svg)](https://github.com/claude-world/notebooklm-skill/actions/workflows/ci.yml)
[![PyPI](https://img.shields.io/pypi/v/notebooklm-skill)](https://pypi.org/project/notebooklm-skill/)
[![Python](https://img.shields.io/pypi/pyversions/notebooklm-skill)](https://pypi.org/project/notebooklm-skill/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)

[English](README.md)

`notebooklm-skill` 為使用者與 MCP 客戶端提供一致的 Google NotebookLM 介面。
它能從網址、原始文字與本機檔案建立筆記本，回傳含引用資訊的來源導向回答，
完成快速或深度網路研究，並生成或下載 NotebookLM 產出物。

本專案以 `notebooklm-py` 0.7.x 為相容基準，包含：

- JSON-first 核心 CLI；
- 五個端到端研究 Pipeline；
- 含 13 個工具的 FastMCP Server；
- 支援 profile 的驗證與 Skill 安裝器；
- CLI、Pipeline、MCP 共用同一個相容層，不再各自實作而漂移。

> 這是使用 NotebookLM Web API 的非官方整合。Google 可能隨時調整服務、
> 配額、可用性或產出物行為。

## 快速開始

### 隔離式原始碼安裝

安裝器會建立專用虛擬環境、安裝 Chromium、將五個指令連結至
`~/.local/bin`，並以標準目錄結構安裝 Claude Code Skill。

```bash
git clone https://github.com/claude-world/notebooklm-skill.git
cd notebooklm-skill
./install.sh

notebooklm-auth setup
notebooklm-skill list
```

請確認 `~/.local/bin` 已加入 `PATH`。

### PyPI 或 uvx

```bash
# 持久化虛擬環境
python3 -m venv .venv
source .venv/bin/activate
python -m pip install notebooklm-skill
python -m playwright install chromium
notebooklm-auth setup

# 或不建立持久環境直接執行
uvx --from notebooklm-skill notebooklm-auth setup
uvx --from notebooklm-skill notebooklm-skill list
```

也能直接呼叫上游登入：

```bash
uvx --from notebooklm-py notebooklm login
```

驗證支援 profile。請在子命令前指定 `--profile NAME`，或設定
`NOTEBOOKLM_PROFILE`。

若要改用本機安裝的 Google Chrome，而非隨附 Chromium：

```bash
notebooklm-auth setup --browser chrome --fresh
```

## 核心 CLI

成功的指令會將結構化 JSON 寫到 stdout，診斷訊息寫到 stderr。驗證錯誤
回傳 exit code 4，參數錯誤回傳 exit code 2。

```bash
# 混合來源匯入，逐筆回報真實成功/失敗狀態
notebooklm-skill create \
  --title "研究" \
  --sources https://example.com/article \
  --files ./paper.pdf \
  --text-sources "訪談筆記" \
  --strict

notebooklm-skill ask \
  --notebook "研究" \
  --query "哪些結論具有最強證據？"

notebooklm-skill research \
  --notebook "研究" \
  --query "近期獨立評估" \
  --mode deep --max-sources 10

notebooklm-skill generate \
  --notebook "研究" \
  --type slides --lang zh-TW \
  --output ./output/deck.pptx --output-format pptx

notebooklm-skill list-artifacts --notebook "研究" --type slides
```

指令可解析精確 ID、唯一標題或唯一的標題片段；自動化請優先使用 ID。
刪除必須加上 `--yes`；下載預設拒絕覆蓋既有檔案與 symlink，只有明確使用
`--force` 才會覆蓋一般檔案。

### 產出物類型

| 類型 | 預設下載格式 | 說明 |
|---|---:|---|
| `audio` | M4A | deep-dive、brief、critique 或 debate |
| `video` | MP4 | explainer/brief 與多種視覺風格 |
| `cinematic` | MP4 | 電影式影片流程 |
| `slides` | PDF | 可下載 PDF 或 PPTX |
| `report` | Markdown | briefing、study guide、blog 或 custom |
| `study-guide` | Markdown | 學習指南捷徑 |
| `quiz` | JSON | JSON、Markdown 或 HTML |
| `flashcards` | JSON | JSON、Markdown 或 HTML |
| `mind-map` | JSON | 立即回傳生成結果 |
| `infographic` | PNG | 可選方向、細節與風格 |
| `data-table` | CSV | 結構化資料萃取 |

執行 `notebooklm-skill generate --help` 可查看即時參數矩陣。長時間生成可用
`--no-wait` 先取得 task ID，之後用 `--artifact-id` 精確下載。

## Pipeline

```bash
notebooklm-pipeline research-to-article \
  --sources https://example.com/a https://example.com/b \
  --title "證據回顧" --audience "工程師"

notebooklm-pipeline research-to-social \
  --files ./brief.pdf --platform linkedin --variants 3

notebooklm-pipeline batch-digest \
  --rss https://example.com/feed.xml --max-entries 20 --qa-count 5

notebooklm-pipeline generate-all \
  --files ./paper.pdf --types audio slides report mind-map \
  --output-dir ./output --artifact-concurrency 2
```

`trend-to-content` 需要另外安裝 `trend-pulse` 指令。Pipeline 只回傳草稿與本機
產出物，不會發布至社群平台或遠端 CMS。

## MCP Server

預設 stdio transport 適用於 Claude Code、Cursor 與其他 MCP 客戶端：

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

13 個工具涵蓋筆記本 CRUD、混合來源、來源導向問答、摘要、產出物的生成/
列出/下載、完整研究生命週期、研究 Pipeline 與趨勢研究。刪除筆記本必須傳入
`confirm=true`。

選用 HTTP 模式只允許 loopback：

```bash
notebooklm-mcp --http --host 127.0.0.1 --port 8765
```

不可直接暴露到網路。詳見 [SECURITY.md](SECURITY.md)。

## 其他指令

| 指令 | 用途 |
|---|---|
| `notebooklm-auth` | 建立、驗證或清除指定的 auth profile |
| `notebooklm-install-skill` | 安裝使用者或專案 Skill，變更時保留備份 |

```bash
notebooklm-install-skill --scope project
notebooklm-auth --profile work verify
```

## 開發驗證

```bash
python3 -m venv .venv
source .venv/bin/activate
python -m pip install -e '.[dev]'
ruff check .
ruff format --check .
mypy scripts mcp_server
pytest --cov --cov-report=term-missing
python -m build
twine check dist/*
```

延伸文件：[安裝指南](docs/SETUP.zh-TW.md)、[Skill 指令](SKILL.md)、
[API 相容說明](references/api_surface.md)、[變更紀錄](CHANGELOG.md)。

## 授權

[MIT](LICENSE)
