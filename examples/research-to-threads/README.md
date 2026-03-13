# 範例：研究 → Threads 貼文

用 NotebookLM 研究主題，生成 Threads 平台最佳化的社群貼文，有真實來源支撐。

## 流程

```
主題 → NotebookLM 研究 → 關鍵洞見 → Threads 貼文 → （選用）發布
```

## 前置需求

- notebooklm-skill 已安裝並完成驗證（參考 [docs/SETUP.md](../../docs/SETUP.md)）
- （選用）Threads API token，用於自動發布

## 步驟 1：建立筆記本並研究

```bash
# 建立筆記本
python scripts/notebooklm_client.py create \
  --title "MCP Server 深度解析" \
  --sources \
    "https://modelcontextprotocol.io/docs" \
    "https://docs.anthropic.com/en/docs/claude-code/mcp"

# 取得摘要
python scripts/notebooklm_client.py ask \
  --notebook "MCP Server 深度解析" \
  --query "用 3 個關鍵重點摘要 MCP 的核心概念"
```

## 步驟 2：生成 Threads 貼文草稿

請 NotebookLM 直接生成平台最佳化的貼文：

```bash
python scripts/notebooklm_client.py ask \
  --notebook "MCP Server 深度解析" \
  --query "根據筆記本內容，寫一則 Threads 貼文（500 字以內、繁體中文、口語化、不放網址、不放 hashtag）。要有一個吸引人的開頭，分享一個關鍵洞見，讓讀者想了解更多。"
```

## 步驟 3：使用 Pipeline 自動化

一行指令完成研究到貼文草稿：

```bash
python scripts/pipeline.py research-to-social \
  --sources \
    "https://modelcontextprotocol.io/docs" \
    "https://docs.anthropic.com/en/docs/claude-code/mcp" \
  --platform threads \
  --title "MCP Server 深度解析"
```

Pipeline 輸出 JSON，包含 `summary`（摘要）和 `social_draft`（貼文草稿）。

## 步驟 4：審閱後發布

發布前請確認：

- 每個主張都有研究支撐嗎？
- 語氣符合你的風格嗎？
- 字數在 500 字以內嗎？
- 你自己會對這則貼文感興趣嗎？

使用 threads-viral-agent 發布：

```bash
python3 scripts/threads_api.py publish \
  --account cw \
  --text "你的貼文內容" \
  --link-comment "https://相關連結.com"
```

## 技巧

- **貼文正文不要放網址**：Threads 演算法會降低含網址貼文的觸及。把連結放在 `--link-comment` 自動回覆中。
- **300 字以內最佳**：Threads 獎勵簡潔、有衝擊力的內容。
- **開頭要大膽**：研究結果給你信心做出強烈且準確的陳述。
- **一則貼文一個洞見**：其他洞見留給後續貼文。
- **先用 `--dry-run`**：發布前先預覽。

## 下一步

- [研究 → 文章](../research-to-article/) — 將研究轉為長篇內容
- [趨勢 → 內容](../trend-to-content/) — 從熱門話題開始
