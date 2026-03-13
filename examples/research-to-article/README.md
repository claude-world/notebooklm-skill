# 範例：研究 → 文章

從 3 個網址建立 NotebookLM 筆記本，提問 5 個研究問題，生成結構化文章草稿。

## 流程

```
3 個來源 URL → NotebookLM 筆記本 → 5 個研究查詢 → 結構化 JSON → 文章草稿
```

## 前置需求

- notebooklm-skill 已安裝並完成驗證（參考 [docs/SETUP.md](../../docs/SETUP.md)）

## 步驟 1：建立筆記本並加入來源

選擇 3 個涵蓋不同角度的網址。這個範例研究 AI 程式助手。

```bash
python scripts/notebooklm_client.py create \
  --title "AI 程式助手 2026" \
  --sources \
    "https://www.anthropic.com/news/claude-code" \
    "https://github.blog/2024-06-05-github-copilot-research/" \
    "https://cursor.com/blog/building-with-ai"
```

## 步驟 2：提問研究問題

提出 5 個有針對性的問題，為撰寫全面的文章收集素材。

```bash
python scripts/notebooklm_client.py ask \
  --notebook "AI 程式助手 2026" \
  --query "主要的 AI 程式助手有什麼關鍵差異？"

python scripts/notebooklm_client.py ask \
  --notebook "AI 程式助手 2026" \
  --query "衡量 AI 程式助手效果的指標有哪些？"

python scripts/notebooklm_client.py ask \
  --notebook "AI 程式助手 2026" \
  --query "開發者如何在工作流中使用 AI 程式工具？"

python scripts/notebooklm_client.py ask \
  --notebook "AI 程式助手 2026" \
  --query "AI 程式助手的主要批評和限制是什麼？"

python scripts/notebooklm_client.py ask \
  --notebook "AI 程式助手 2026" \
  --query "AI 輔助開發的新興趨勢有哪些？"
```

每個查詢都會回傳 JSON，包含 `answer`（答案）和 `references`（引用來源）。

## 步驟 3：使用 Pipeline 自動化

如果不想逐步執行，可以用 Pipeline 一次完成：

```bash
python scripts/pipeline.py research-to-article \
  --sources \
    "https://www.anthropic.com/news/claude-code" \
    "https://github.blog/2024-06-05-github-copilot-research/" \
    "https://cursor.com/blog/building-with-ai" \
  --title "AI 程式助手 2026"
```

Pipeline 會自動：
1. 建立筆記本並加入 3 個來源
2. 提出 5 個預設研究問題
3. 生成文章草稿
4. 輸出結構化 JSON（含研究發現 + 文章草稿）

## 步驟 4：生成產出物（選用）

從研究內容生成投影片、Podcast 等：

```bash
# 生成投影片
python scripts/notebooklm_client.py generate \
  --notebook "AI 程式助手 2026" --type slides

# 生成 Podcast（繁中）
python scripts/notebooklm_client.py podcast \
  --notebook "AI 程式助手 2026" --lang zh-TW --output podcast.m4a

# 下載投影片
python scripts/notebooklm_client.py download \
  --notebook "AI 程式助手 2026" --type slides --output slides.pdf
```

## 技巧

- **問對比性問題**：「優點是什麼？」+「批評是什麼？」能得到平衡的報導。
- **問具體問題**：「有哪些衡量 X 的指標？」比「告訴我 X」產出更具體的素材。
- **3-7 個來源最佳**：太少缺乏深度，太多則焦點分散。
- **先檢視研究結果**：在生成內容前檢查 JSON 輸出，確保素材品質。

## 下一步

- [研究 → Threads](../research-to-threads/) — 將研究轉為社群貼文
- [趨勢 → 內容](../trend-to-content/) — 從熱門話題開始，而非手動指定 URL
