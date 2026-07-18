# 安裝指南

本指南會安裝 `notebooklm-skill` 1.3.x、驗證 NotebookLM profile，並設定
Claude Code Skill 或 MCP Server。

## 系統需求

- Python 3.10 以上
- 可使用 NotebookLM 的 Google 帳號
- 互動登入流程所需的 Chromium
- 僅在使用 `scripts/make_video.sh` 時需要 `ffmpeg` 與 Poppler

NotebookLM 採瀏覽器驗證，不需要應用程式 API Key。儲存的 browser state
含有 session cookie，必須視同密碼保護。

## 安裝

### 從原始碼安裝

```bash
git clone https://github.com/claude-world/notebooklm-skill.git
cd notebooklm-skill
./install.sh
```

安裝器使用 `${XDG_DATA_HOME:-~/.local/share}/notebooklm-skill/venv` 專用環境，
不會因 PEP 668 而修改失敗的系統 Python。指令會連結至
`${XDG_BIN_HOME:-~/.local/bin}`；如有需要，請將它加入 `PATH`。

可用 `NOTEBOOKLM_INSTALL_ROOT`、`XDG_BIN_HOME` 或 `NOTEBOOKLM_PYTHON` 覆寫位置。
預設安裝完成後不依賴原始碼目錄；開發者可設定 `NOTEBOOKLM_INSTALL_EDITABLE=1`
改用 editable install。

Headless 或分階段安裝可設定 `NOTEBOOKLM_SKIP_BROWSER=1`、
`NOTEBOOKLM_SKIP_SKILL=1` 或 `NOTEBOOKLM_SKIP_AUTH_CHECK=1`。若略過 Chromium，
必須先在安裝環境執行 `python -m playwright install chromium`，瀏覽器 setup 才可用。

### 從 PyPI 安裝

```bash
python3 -m venv .venv
source .venv/bin/activate
python -m pip install notebooklm-skill
python -m playwright install chromium
```

### 使用 uvx

以臨時隔離環境執行：

```bash
uvx --from notebooklm-skill notebooklm-skill --help
uvx --from notebooklm-skill notebooklm-mcp --help
```

## 驗證

已安裝套件：

```bash
notebooklm-auth setup
notebooklm-auth verify
```

若隨附 Chromium 不適用，可改用系統安裝的 Google Chrome：

```bash
notebooklm-auth setup --browser chrome --fresh
```

零安裝的上游登入：

```bash
uvx --from notebooklm-py notebooklm login
```

用具名 profile 分隔帳號：

```bash
notebooklm-auth --profile work setup
notebooklm-auth --profile work verify
notebooklm-skill --profile work list
```

也可用 `NOTEBOOKLM_PROFILE=work` 選擇 profile。目前的 `notebooklm-py` 通常將
profile 儲存在 `~/.notebooklm/profiles/<profile>/storage_state.json`。不可提交或
分享這些檔案。

只登出指定 profile：

```bash
notebooklm-auth --profile work clear --yes
```

## 驗證 CLI

```bash
notebooklm-skill list
notebooklm-skill create --title "安裝測試" --text-sources "Hello NotebookLM" --strict
notebooklm-skill ask --notebook "安裝測試" --query "這個來源在說什麼？"
notebooklm-skill delete --notebook "安裝測試" --yes
```

每個指令都將 JSON 寫到 stdout。非零 exit code 表示未完整達成契約；來源層級
的部分失敗也會如實寫入 JSON。

## 安裝 Claude Code Skill

原始碼安裝器會自動完成。PyPI 或專案內安裝可執行：

```bash
# 使用者範圍：~/.claude/skills/notebooklm-research/SKILL.md
notebooklm-install-skill

# 專案範圍：.claude/skills/notebooklm-research/SKILL.md
notebooklm-install-skill --scope project
```

內容不同時必須指定 `--force` 才會覆寫，且會先建立 timestamp 備份。安裝器
拒絕 symlink 目標。

## 設定 MCP

使用專案的 `.mcp.json` 或等效設定：

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

若已在本機安裝，將 `command` 改為 `notebooklm-mcp` 並移除 `args`。

重啟 MCP 客戶端後呼叫 `nlm_list`。操作例外會成為真正的 MCP tool error，
不會偽裝成成功字典；刪除筆記本必須傳入 `confirm=true`。

HTTP 模式僅供本機整合：

```bash
notebooklm-mcp --http --host 127.0.0.1 --port 8765
```

非 loopback 綁定會被拒絕。除非前方已有驗證過的 TLS reverse proxy 與主機存取
控制，否則不可繞過此限制。

## 選用趨勢整合

`notebooklm-pipeline trend-to-content` 與 `nlm_trend_research` 需要
`trend-pulse` 執行檔：

```bash
export TREND_PULSE_CMD=/absolute/path/to/trend-pulse
notebooklm-pipeline trend-to-content --geo TW --count 5 --platform threads
```

此值會解析為執行檔與參數，絕不傳入 shell。Pipeline 只產生草稿，不會發布。

## 疑難排解

### 驗證不存在或過期

```bash
notebooklm-auth verify
notebooklm-auth setup
```

確認 setup 與失敗指令使用同一個 `--profile` 或 `NOTEBOOKLM_PROFILE`。

### 執行 `./install.sh` 後找不到指令

將指令目錄加入 shell 設定：

```bash
export PATH="$HOME/.local/bin:$PATH"
```

### 產出物生成逾時

Google 端任務可能仍在執行。列出產出物，出現後以精確 ID 下載：

```bash
notebooklm-skill list-artifacts --notebook NOTEBOOK_ID
notebooklm-skill download --notebook NOTEBOOK_ID --type slides \
  --artifact-id ARTIFACT_ID --output deck.pdf
```

### 輸出檔已存在

換一個路徑，或只在確實要覆寫時加上 `--force`。Symlink 目的地永遠會被拒絕。

### 缺少瀏覽器

在安裝 `notebooklm-skill` 的同一環境執行：

```bash
python -m playwright install chromium
```

一般缺陷請使用 repository issue template；漏洞請依 [SECURITY.md](../SECURITY.md)
提供的私人管道回報。
