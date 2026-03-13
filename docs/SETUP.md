# 安裝指南

notebooklm-skill 的完整安裝說明。

---

## 前置需求

- **Python 3.10+**（`python3 --version`）
- **pip**（`pip --version`）
- **Google 帳號**，可存取 [NotebookLM](https://notebooklm.google.com/)

## 1. 安裝依賴

```bash
git clone https://github.com/claude-world/notebooklm-skill.git
cd notebooklm-skill
pip install -r requirements.txt
```

驗證安裝：

```bash
python scripts/notebooklm_client.py list
```

## 2. Google 驗證

notebooklm-py 使用瀏覽器登入 Google（不需要 OAuth Client ID 或 Google Cloud 專案）。

### 步驟 2a：執行登入

```bash
python3 -m notebooklm login
```

這會：
1. 開啟 Chromium 瀏覽器
2. 顯示 Google 登入頁面 — 使用你的 Google 帳號登入
3. 登入後自動儲存 Session 至 `~/.notebooklm/storage_state.json`
4. 之後所有操作都是純 HTTP 呼叫（不再需要瀏覽器）

### 步驟 2b：驗證登入狀態

```bash
python scripts/auth_helper.py verify
```

預期輸出：

```
[auth] Verifying NotebookLM authentication...
[auth] Authentication OK — found N notebooks.
```

### 步驟 2c：（選用）建立 .env

```bash
cp .env.example .env
```

編輯 `.env` 設定預設值：

```bash
# 選用：預設設定
NOTEBOOKLM_DEFAULT_DEPTH=5
NOTEBOOKLM_DEFAULT_FORMAT=json
NOTEBOOKLM_MAX_SOURCES=50

# 選用：trend-pulse 整合
TREND_PULSE_URL=http://localhost:3002

# 選用：threads-viral-agent 整合
THREADS_TOKEN=your-threads-token
```

> **注意**：不需要 Google API 金鑰或 OAuth 憑證。驗證完全透過瀏覽器 Session 處理。

## 3. 驗證設定

```bash
# 列出現有 NotebookLM 筆記本（可能是空的）
python scripts/notebooklm_client.py list

# 建立測試筆記本
python scripts/notebooklm_client.py create \
  --title "測試筆記本" \
  --sources "https://zh.wikipedia.org/wiki/大型語言模型"

# 提問
python scripts/notebooklm_client.py ask \
  --notebook "測試筆記本" \
  --query "什麼是大型語言模型？"

# 清理
python scripts/notebooklm_client.py delete --notebook "測試筆記本"
```

如果所有指令都成功，你的設定就完成了。

## 4. （選用）MCP Server 設定

MCP Server 讓任何 MCP 相容的客戶端（Claude Code、Cursor、Gemini CLI）能使用 NotebookLM 作為工具。

### 啟動 Server

```bash
python -m mcp-server
```

Server 預設使用 stdio（標準 MCP 傳輸協定）。

### 註冊到 Claude Code

加入專案的 `.mcp.json`：

```json
{
  "mcpServers": {
    "notebooklm": {
      "command": "python",
      "args": ["-m", "mcp-server"],
      "cwd": "/absolute/path/to/notebooklm-skill"
    }
  }
}
```

重啟 Claude Code，你應該能看到 `notebooklm` 工具。

### 註冊到 Cursor

加入 `~/.cursor/mcp.json`：

```json
{
  "mcpServers": {
    "notebooklm": {
      "command": "python",
      "args": ["-m", "mcp-server"],
      "cwd": "/absolute/path/to/notebooklm-skill"
    }
  }
}
```

## 5. （選用）Claude Code Skill 安裝

如果你想以 Claude Code Skill 使用（不需要 MCP Server）：

```bash
# 從你的專案根目錄
mkdir -p .claude/skills/notebooklm
cp /path/to/notebooklm-skill/SKILL.md .claude/skills/notebooklm/
cp -r /path/to/notebooklm-skill/scripts/ .claude/skills/notebooklm/scripts/
cp /path/to/notebooklm-skill/requirements.txt .claude/skills/notebooklm/
```

Claude 會自動偵測 Skill。當你提到 NotebookLM 研究或內容創作時就會觸發。

## 6. （選用）trend-pulse 整合

[trend-pulse](https://github.com/claude-world/trend-pulse) 提供熱門話題發現。啟用整合：

1. 安裝並執行 trend-pulse（參考其 README）
2. 加入 `.env`：

```bash
TREND_PULSE_URL=http://localhost:3002
```

## 7. 疑難排解

### 「瀏覽器沒有開啟」

```
Error: Browser not found
```

**修復**：安裝 Playwright 瀏覽器：

```bash
python3 -m playwright install chromium
```

### 「Session 過期」

```
Error: Authentication failed
```

**修復**：重新登入：

```bash
python scripts/auth_helper.py clear
python3 -m notebooklm login
```

### 「MCP Server 無法連線」

**修復**：確認：
1. MCP 設定中的 `cwd` 路徑是絕對路徑
2. Shell 中可使用 Python 3.10+（`python --version`）
3. 已安裝依賴（`pip install -r requirements.txt`）

### 「產出物生成超時」

音檔和影片生成可能需要 5-10 分鐘。如果客戶端超時（600 秒），產出物可能仍在 NotebookLM 伺服器上生成。稍後用 `download` 指令嘗試下載：

```bash
python scripts/notebooklm_client.py download \
  --notebook "你的筆記本" \
  --type audio \
  --output podcast.m4a
```

### 「音檔無法播放」

NotebookLM 回傳的音檔實際上是 MPEG-4 (M4A) 格式，不是 MP3。請使用 `.m4a` 副檔名：

```bash
# 如果儲存為 .mp3，改名即可
mv podcast.mp3 podcast.m4a
```

### 需要更多幫助？

在 [github.com/claude-world/notebooklm-skill/issues](https://github.com/claude-world/notebooklm-skill/issues) 開 Issue。
