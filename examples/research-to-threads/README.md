# 範例：研究到 Threads 草稿

用 NotebookLM 來源生成適合 Threads 的草稿。此專案不包含發布 API；輸出必須
先人工審閱，再交給使用者選定的發布工具。

## 生成草稿

```bash
notebooklm-auth verify

notebooklm-pipeline research-to-social \
  --sources \
    https://modelcontextprotocol.io/docs \
    https://example.com/independent-analysis \
  --title "MCP 證據整理" \
  --platform threads \
  --language zh-TW \
  --variants 3 \
  > threads-result.json
```

檢查狀態與內容：

```bash
jq '{status, source_summary, summary: .summary.status, social: .social.status}' \
  threads-result.json
jq -r '.social.answer' threads-result.json
```

## 精確追問

```bash
NOTEBOOK_ID=$(jq -r '.notebook.id' threads-result.json)

notebooklm-skill ask \
  --notebook "$NOTEBOOK_ID" \
  --query "列出草稿中每個可驗證主張及對應引用；指出沒有足夠來源支持的句子。"
```

## 發布前檢核

- Top-level 與 nested status 都不是 `failed` 或未處理的 `partial`。
- 每個事實主張均可追到 `references` 中的來源。
- 字數、語氣與平台規範符合當下需求。
- 不誇大 NotebookLM 沒有提供的結論。
- 外部連結、標籤與 CTA 經人工確認。
- 使用者明確選定帳號與發布工具後才進行遠端發布。

Pipeline 只產生研究摘要與草稿，不會讀取 Threads token，也不會自動發布。
