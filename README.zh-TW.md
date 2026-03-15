# notebooklm-skill

> NotebookLM 做研究，Claude 寫內容。

唯一串接「趨勢發現 → NotebookLM 深度研究 → AI 內容創作 → 多平台發布」的工具。可作為 Claude Code Skill 或獨立 MCP Server 使用。

[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)

**[English README](README.md)**

---

## Demo

| 語言 | YouTube | 投影片 |
|------|---------|--------|
| English | [觀看](https://youtu.be/q1kj_OccaVE) | 6 頁，自動生成 |
| 繁體中文 | [觀看](https://youtu.be/6M3K4sxahdE) | 5 頁，自動生成 |

所有投影片、Podcast 和影片都是使用本工具透過 NotebookLM 生成。

---

## 這是什麼？

**notebooklm-skill** 將 NotebookLM 的研究能力與 Claude 的內容生成串接起來。餵入網址、PDF 或熱門話題，它會建立 NotebookLM 筆記本、執行深度研究查詢，再將結構化結果交給 Claude 產出文章、社群貼文、電子報、Podcast 等任何格式。

基於 [notebooklm-py](https://pypi.org/project/notebooklm-py/) v0.3.4 — 純 async Python，無需 OAuth 設定。

```
來源 (URLs, PDFs)            NotebookLM                Claude               產出物 & 平台
+-----------------+    +------------------+    +-----------------+    +----------------------+
| 網頁文章        |--->| 建立筆記本       |--->| 撰寫文章        |--->| 部落格 / CMS          |
| 研究論文        |    | 加入來源         |    | 社群貼文        |    | Threads / X           |
| YouTube 影片    |    | 提問研究         |    | 電子報          |    | Newsletter            |
| 熱門話題        |    | 萃取洞見         |    | 任何格式        |    | 任何平台              |
+-----------------+    +------------------+    +-----------------+    +----------------------+
     階段 1                 階段 2                  階段 3                   階段 4
                                |
                                v
                       +------------------+
                       | 生成產出物        |
                       | 音檔 (Podcast)    |
                       | 影片              |
                       | 投影片            |
                       | 報告              |
                       | 測驗              |
                       | 閃卡              |
                       | 心智圖            |
                       | 資訊圖表          |
                       | 資料表            |
                       | 學習指南          |
                       +------------------+
                            階段 2b
```

## 快速開始

```bash
# 方法 A：pip install（推薦）
git clone https://github.com/claude-world/notebooklm-skill.git
cd notebooklm-skill
pip install .                     # 安裝全域 CLI 命令

# 方法 B：一鍵安裝（pip + Playwright + Claude Code Skill）
./install.sh

# Google 驗證（一次性，會開啟瀏覽器）
python3 -m notebooklm login

# 使用全域命令
notebooklm-skill create --title "我的研究" --sources https://example.com/article
notebooklm-skill ask --notebook "我的研究" --query "這篇文章的關鍵發現是什麼？"
notebooklm-skill podcast --notebook "我的研究" --lang zh-TW --output podcast.m4a
notebooklm-pipeline research-to-article --sources https://example.com --title "主題"
notebooklm-mcp                   # 啟動 MCP Server（stdio 模式）
```

也可直接使用腳本：`python scripts/notebooklm_client.py create ...`

完整安裝指南請參考 [docs/SETUP.zh-TW.md](docs/SETUP.zh-TW.md)。

## 驗證方式

notebooklm-py 使用瀏覽器登入 Google（不需要 OAuth Client ID）：

| 步驟 | 指令 | 說明 |
|------|------|------|
| **登入** | `python3 -m notebooklm login` | 開啟 Chromium，使用者登入 Google |
| **Session 儲存** | 自動 | 儲存至 `~/.notebooklm/storage_state.json` |
| **後續使用** | `NotebookLMClient.from_storage()` | 讀取 Session，純 HTTP 呼叫 |
| **驗證** | `python scripts/auth_helper.py verify` | 載入 Client 並呼叫 `notebooks.list()` |
| **清除** | `python scripts/auth_helper.py clear` | 刪除 `~/.notebooklm/` 目錄 |

Session 通常可維持數週。如遇驗證錯誤，重新執行 `login` 即可。

## 兩種使用方式

| | **Claude Code Skill** | **MCP Server** |
|---|---|---|
| **適合** | Claude Code 使用者，想在工作流中加入 NotebookLM | 任何 MCP 相容客戶端（Cursor、Gemini CLI 等） |
| **設定** | 複製 Skill 到 `.claude/skills/` | 加入 MCP 設定 |
| **觸發** | Claude 自動偵測相關需求 | 工具出現在客戶端工具列表 |
| **設定檔** | `SKILL.md` + `.env` | `.mcp.json` + `.env` |
| **需求** | Python 3.10+, notebooklm-py | Python 3.10+, notebooklm-py |

## 功能

| 功能 | 說明 | 狀態 |
|---|---|---|
| **筆記本 CRUD** | 建立、列出、刪除筆記本 | 可用 |
| **來源匯入** | 加入網址、PDF、YouTube 連結、純文字 | 可用 |
| **研究查詢** | 對筆記本來源提問，附帶引用 | 可用 |
| **結構化萃取** | 取得關鍵事實、論點、時間軸 | 可用 |
| **內容生成** | 將研究結果作為 Claude 的上下文 | 可用 |
| **批次操作** | 一次處理多個來源或查詢 | 可用 |
| **trend-pulse 整合** | 自動發現熱門話題進行研究 | 可用 |
| **threads-viral-agent 整合** | 發布研究支撐的社群貼文 | 可用 |

### 產出物生成（10 種類型）

| 產出物 | 格式 | 說明 |
|---|---|---|
| **音檔** | M4A | AI 生成的 Podcast 對談 |
| **影片** | MP4 | 影片摘要，含視覺素材 |
| **投影片** | PDF | 簡報投影片 |
| **報告** | PDF | 完整書面報告 |
| **測驗** | JSON | 多選題評量 |
| **閃卡** | JSON | 學習用閃卡 |
| **心智圖** | SVG | 視覺概念圖 |
| **資訊圖表** | PNG | 視覺化資料摘要 |
| **資料表** | CSV | 結構化資料萃取 |
| **學習指南** | PDF | 結構化學習教材 |

所有產出物都支援語言選擇（例如 `--lang zh-TW`）。

> **注意**：NotebookLM 回傳的音檔實際上是 MPEG-4 (M4A) 格式，不是 MP3。

## 架構

```
+---------------------------------------------------------------+
|                      notebooklm-skill                          |
|                                                                |
|  +---------+  +--------------+  +----------+  +------------+  |
|  | 階段 1  |  |   階段 2     |  |  階段 3  |  |  階段 4    |  |
|  | 收集     |->|  研究        |->| 生成     |->|  發布      |  |
|  +---------+  +--------------+  +----------+  +------------+  |
|      |              |                |               |         |
|  +--------+  +-------------+  +-----------+  +-----------+    |
|  | URLs   |  | NotebookLM  |  |  Claude    |  | Threads   |    |
|  | PDFs   |  | (via        |  |  內容      |  | Blog      |    |
|  | RSS    |  |  notebooklm |  |  引擎      |  | Email     |    |
|  | 趨勢   |  |  -py 0.3.4) |  |            |  | CMS       |    |
|  +--------+  | - notebooks |  +-----------+  +-----------+    |
|              | - sources   |        |                          |
|              | - chat/ask  |  +-----------+                    |
|              | - artifacts |  | 產出物     |                    |
|              +-------------+  | 音檔       |                    |
|                               | 影片       |                    |
|                               | 投影片     |                    |
|                               | 報告       |                    |
|                               | 測驗       |                    |
|                               | 閃卡       |                    |
|                               | 心智圖     |                    |
|                               | 資訊圖表   |                    |
|                               | 資料表     |                    |
|                               | 學習指南   |                    |
|                               +-----------+                    |
|                                                                |
|  +-----------------------------------------------------------+ |
|  |  介面                                                      | |
|  |  +-- scripts/          CLI 工具 (直接呼叫 notebooklm-py)  | |
|  |  +-- mcp_server/       MCP 協定伺服器                      | |
|  |  +-- SKILL.md          Claude Code Skill 定義              | |
|  +-----------------------------------------------------------+ |
+---------------------------------------------------------------+
         ^                                          ^
         |                                          |
   +-----------+                             +-----------+
   |trend-pulse|                             |threads-   |
   |(選用)     |                             |viral-agent|
   +-----------+                             |(選用)     |
                                             +-----------+
```

## 使用範例

### 1. 研究 → 文章

從多個來源進行研究，生成結構化文章。

```bash
# 完整 Pipeline（建立筆記本、研究、撰寫草稿）
python scripts/pipeline.py research-to-article \
  --sources "https://arxiv.org/abs/2401.00001" \
            "https://blog.example.com/ai-agents" \
  --title "AI Agent 調查"

# 或者用 client 逐步執行：

# 建立筆記本並加入來源
python scripts/notebooklm_client.py create \
  --title "AI Agent 調查" \
  --sources "https://arxiv.org/abs/2401.00001" \
            "https://blog.example.com/ai-agents"

# 提問研究問題
python scripts/notebooklm_client.py ask \
  --notebook "AI Agent 調查" \
  --query "主要的 Agent 架構有哪些？"
```

### 2. 研究 → 社群貼文

研究主題並生成平台最佳化的社群貼文。

```bash
python scripts/pipeline.py research-to-social \
  --sources "https://example.com/ai-news" \
  --platform threads \
  --title "本週 AI 新聞"
```

### 3. 熱門話題 → 內容

結合 trend-pulse 自動化「發現 → 發布」的完整流程。

```bash
python scripts/pipeline.py trend-to-content \
  --geo TW \
  --count 5 \
  --platform threads
```

### 4. RSS 批次摘要

將 RSS feed 轉為電子報風格的摘要。

```bash
python scripts/pipeline.py batch-digest \
  --rss "https://example.com/feed.xml" \
  --title "每週 AI 摘要" \
  --max-entries 15
```

### 5. 生成所有產出物

建立筆記本並生成全部 10 種產出物。

```bash
# 生成全部
python scripts/pipeline.py generate-all \
  --sources "https://example.com/article1" \
            "https://example.com/article2" \
  --title "研究" \
  --output-dir ./output \
  --language zh-TW

# 或只生成特定類型
python scripts/pipeline.py generate-all \
  --sources "https://example.com/article" \
  --types audio slides report \
  --output-dir ./output
```

### 6. 投影片 + Podcast → YouTube 影片

將 NotebookLM 生成的投影片和音檔合成為 YouTube 影片：

```bash
# 1. 生成投影片和 Podcast
python scripts/notebooklm_client.py generate --notebook "研究" --type slides
python scripts/notebooklm_client.py podcast --notebook "研究" --lang zh-TW --output podcast.m4a

# 2. 下載投影片
python scripts/notebooklm_client.py download --notebook "研究" --type slides --output slides.pdf

# 3. PDF 轉 PNG + 合成影片
pdftoppm -png -r 300 slides.pdf slides/slide
ffmpeg -y \
  -loop 1 -t <每張秒數> -i slides/slide-01.png \
  -loop 1 -t <每張秒數> -i slides/slide-02.png \
  ... \
  -i podcast.m4a \
  -filter_complex "[0:v]scale=1920:1080:...[v0]; ... concat=n=N:v=1:a=0[outv]" \
  -map "[outv]" -map N:a \
  -c:v libx264 -c:a aac -movflags +faststart \
  output.mp4
```

## Pipeline 工作流

| 工作流 | 輸入 | 輸出 | 步驟 |
|---|---|---|---|
| `research-to-article` | URLs, 文字 | 文章草稿 JSON | 建立筆記本 → 5 個研究問題 → 文章草稿 |
| `research-to-social` | URLs, 文字 | 社群貼文草稿 | 建立筆記本 → 摘要 → 平台專屬貼文 |
| `trend-to-content` | 地區, 數量 | 每個趨勢的內容 | 取得趨勢 → 建立筆記本 → 研究 → 草稿 |
| `batch-digest` | RSS URL | 電子報摘要 | 取得 RSS → 建立筆記本 → 摘要 + 問答 |
| `generate-all` | URLs, 文字 | 音檔、影片、PDF 等 | 建立筆記本 → 生成所有產出物 → 下載 |

## MCP Server 設定

MCP Server 將 NotebookLM 操作公開為工具，任何 MCP 相容的客戶端都能使用。

`pip install .` 後，加入專案的 `.mcp.json`：

```json
{
  "mcpServers": {
    "notebooklm": {
      "command": "notebooklm-mcp"
    }
  }
}
```

或使用腳本路徑：

```json
{
  "mcpServers": {
    "notebooklm": {
      "command": "python3",
      "args": ["mcp_server/server.py"],
      "cwd": "/path/to/notebooklm-skill"
    }
  }
}
```

適用於 Claude Code、Cursor、Gemini CLI 等任何 MCP 相容客戶端。

## Claude Code Skill 安裝

```bash
# 方法 A：Symlink（git pull 自動更新）
./install.sh

# 方法 B：手動複製
mkdir -p .claude/skills/notebooklm
cp /path/to/notebooklm-skill/SKILL.md .claude/skills/notebooklm/
cp /path/to/notebooklm-skill/scripts/*.py .claude/skills/notebooklm/scripts/
cp /path/to/notebooklm-skill/requirements.txt .claude/skills/notebooklm/

# 驗證（一次性）
python3 -m notebooklm login
```

Claude 會在你詢問研究、NotebookLM 或內容創作相關問題時自動偵測並啟動 Skill。

## 設定

在專案根目錄建立 `.env`（或 Skill 目錄中）：

```bash
# 選用：預設設定
NOTEBOOKLM_DEFAULT_DEPTH=5          # 研究查詢數（1-10）
NOTEBOOKLM_DEFAULT_FORMAT=json      # 輸出格式：json, markdown, text
NOTEBOOKLM_MAX_SOURCES=50           # 每個筆記本最大來源數

# 選用：trend-pulse 整合
TREND_PULSE_URL=http://localhost:3002  # trend-pulse MCP 伺服器 URL

# 選用：threads-viral-agent 整合
THREADS_TOKEN=your-threads-token       # 自動發布到 Threads
```

注意：不需要 Google OAuth 憑證。驗證透過瀏覽器登入處理（`python3 -m notebooklm login`）。

## API 參考

### CLI 指令

| 指令 | 說明 |
|---|---|
| `create` | 建立筆記本並加入 URL/文字來源 |
| `list` | 列出所有筆記本 |
| `delete` | 刪除筆記本 |
| `add-source` | 加入來源（URL、文字或檔案）到現有筆記本 |
| `ask` | 對筆記本提問研究問題（回傳答案 + 引用） |
| `summarize` | 取得筆記本摘要 |
| `generate` | 生成產出物（音檔、影片、投影片等） |
| `download` | 下載已生成的產出物 |
| `research` | 執行深度網頁研究 |
| `podcast` | `generate --type audio` 的快捷指令（含自動下載） |
| `qa` | `generate --type quiz` 的快捷指令 |

### Pipeline 工作流

| 工作流 | 說明 |
|---|---|
| `research-to-article` | 來源 → 筆記本 → 5 個研究問題 → 文章草稿 |
| `research-to-social` | 來源 → 筆記本 → 摘要 → 平台專屬社群貼文 |
| `trend-to-content` | 取得趨勢 → 建立筆記本 → 研究 → 每個趨勢的內容 |
| `batch-digest` | RSS feed → 筆記本 → 電子報摘要 + 問答 |
| `generate-all` | 來源 → 筆記本 → 生成 + 下載所有產出物類型 |

### MCP 工具（13 個）

| 工具 | 說明 |
|---|---|
| `nlm_create_notebook` | 建立筆記本並加入來源 |
| `nlm_list` | 列出所有筆記本 |
| `nlm_delete` | 刪除筆記本 |
| `nlm_add_source` | 加入來源到現有筆記本 |
| `nlm_ask` | 對筆記本提問（回傳答案 + 引用） |
| `nlm_summarize` | 取得筆記本摘要 |
| `nlm_generate` | 生成產出物（10 種類型） |
| `nlm_download` | 下載已生成的產出物 |
| `nlm_list_sources` | 列出筆記本中的來源 |
| `nlm_list_artifacts` | 列出已生成的產出物 |
| `nlm_research` | 執行深度網頁研究 |
| `nlm_research_pipeline` | 完整研究 Pipeline |
| `nlm_trend_research` | 趨勢 → 研究 Pipeline |

## 整合

### trend-pulse

[trend-pulse](https://github.com/claude-world/trend-pulse) 提供即時熱門話題發現。設定後，notebooklm-skill 可以自動：

- 從 7 個來源（Google Trends、HN、Reddit 等）取得熱門話題
- 從熱門 URL 建立 NotebookLM 筆記本
- 將研究結果餵入內容 Pipeline

### threads-viral-agent

搭配 Threads 發布工具，Pipeline 可延伸為自動發布研究支撐的社群貼文，並優化觸及率。

## 貢獻

歡迎貢獻！請：

1. Fork 這個倉庫
2. 建立功能分支（`git checkout -b feature/amazing-feature`）
3. Commit 你的變更（`git commit -m 'Add amazing feature'`）
4. Push 到分支（`git push origin feature/amazing-feature`）
5. 開啟 Pull Request

### 開發環境

```bash
git clone https://github.com/claude-world/notebooklm-skill.git
cd notebooklm-skill
pip install -e .

# 驗證
python3 -m notebooklm login

# 執行測試
python -m pytest tests/
```

## 授權

MIT License。詳見 [LICENSE](LICENSE)。
