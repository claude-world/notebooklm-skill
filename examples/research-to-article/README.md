# 範例：研究到文章

從多種來源建立 NotebookLM 筆記本，保留引用資訊並產生文章草稿。

## 前置檢查

```bash
notebooklm-auth verify
```

## 一次完成

```bash
notebooklm-pipeline research-to-article \
  --sources \
    https://example.com/official-documentation \
    https://example.com/independent-study \
  --files ./local-paper.pdf \
  --title "AI 程式助手證據回顧" \
  --language zh-TW \
  --audience "軟體工程師" \
  --tone "精確、平衡、清楚區分證據與推論" \
  > article-result.json
```

Pipeline 會建立筆記本、逐筆回報來源匯入結果、並行詢問五個研究問題，再要求
NotebookLM 根據來源撰寫文章。它不會把草稿發布到外部服務。

## 驗證結果

```bash
jq '{status, source_summary, finding_states: [.research_findings[].status], article: .article.status}' \
  article-result.json
jq -r '.article.answer' article-result.json > article.md
```

只有 `.status == "ok"`、每個來源/問題狀態可接受，且引用與原始來源相符時，
才把草稿視為完成。`partial` 表示需要人工補來源或重跑失敗問題。

## 手動補強

從 Pipeline 回傳的 `.notebook.id` 取得 ID：

```bash
NOTEBOOK_ID=$(jq -r '.notebook.id' article-result.json)

notebooklm-skill add-source \
  --notebook "$NOTEBOOK_ID" \
  --url https://example.com/additional-evidence

notebooklm-skill ask \
  --notebook "$NOTEBOOK_ID" \
  --query "哪些結論只有單一來源支持？請保留引用。"

notebooklm-skill generate \
  --notebook "$NOTEBOOK_ID" \
  --type slides --lang zh-TW \
  --output ./output/slides.pdf
```

## 注意事項

- 自動化請使用 notebook ID，避免同名標題歧義。
- 至少混合官方資料與獨立資料，不要把同一來源的重述當成多份證據。
- JSON 中的 `references` 必須與文章主張一起保存。
- 來源失敗不會被隱藏；先處理 `source_summary.failed` 再使用草稿。
