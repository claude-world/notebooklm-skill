# 範例：熱門話題 → 內容

使用 trend-pulse 發現熱門話題，用 NotebookLM 深度研究，生成多平台內容。

## 流程

```
trend-pulse 發現趨勢 → 選擇話題 → NotebookLM 研究 → 多平台內容
```

## 前置需求

- notebooklm-skill 已安裝並完成驗證（參考 [docs/SETUP.md](../../docs/SETUP.md)）
- [trend-pulse](https://github.com/claude-world/trend-pulse) 執行中（MCP Server 或 CLI）

## 步驟 1：發現熱門話題

透過 trend-pulse 取得即時趨勢：

```bash
# 如果 trend-pulse 作為 MCP 使用（在 Claude Code 中）
# 直接問：「台灣今天有什麼熱門話題？」

# 或在 Pipeline 中自動取得
python scripts/pipeline.py trend-to-content \
  --geo TW \
  --count 3 \
  --platform threads
```

trend-pulse 從 7 個來源取得趨勢：Google Trends、Hacker News、Reddit、Product Hunt 等。

## 步驟 2：手動流程（逐步）

如果想手動控制每一步：

```bash
# 2a. 選一個話題，找相關網址，建立筆記本
python scripts/notebooklm_client.py create \
  --title "Claude Opus 4.6 1M Context" \
  --sources \
    "https://www.anthropic.com/news/claude-opus-4-6" \
    "https://docs.anthropic.com/en/docs/about-claude/models"

# 2b. 加入額外上下文（文字來源）
python scripts/notebooklm_client.py add-source \
  --notebook "Claude Opus 4.6 1M Context" \
  --text "你自己的分析或額外背景資料..." \
  --text-title "個人分析"

# 2c. 深度研究
python scripts/notebooklm_client.py ask \
  --notebook "Claude Opus 4.6 1M Context" \
  --query "這個更新對開發者的實際影響是什麼？"

# 2d. 生成社群貼文草稿
python scripts/notebooklm_client.py ask \
  --notebook "Claude Opus 4.6 1M Context" \
  --query "根據內容寫一則 Threads 貼文（繁中、500字內、口語化、不放網址）"

# 2e. 生成產出物
python scripts/notebooklm_client.py podcast \
  --notebook "Claude Opus 4.6 1M Context" --lang zh-TW --output podcast.m4a

python scripts/notebooklm_client.py generate \
  --notebook "Claude Opus 4.6 1M Context" --type slides

python scripts/notebooklm_client.py download \
  --notebook "Claude Opus 4.6 1M Context" --type slides --output slides.pdf
```

## 步驟 3：自動化 Pipeline

一行指令完成趨勢發現到內容生成：

```bash
python scripts/pipeline.py trend-to-content \
  --geo TW \
  --count 5 \
  --platform threads
```

Pipeline 會自動：
1. 從 trend-pulse 取得 5 個熱門話題
2. 為每個話題建立 NotebookLM 筆記本
3. 加入相關 URL 作為來源
4. 執行研究查詢
5. 生成平台專屬內容草稿
6. 輸出結構化 JSON

## 步驟 4：投影片 + Podcast → YouTube 影片

將產出物合成為 YouTube 影片：

```bash
# PDF 轉 PNG
pdftoppm -png -r 300 slides.pdf slides/slide

# 合成影片（投影片 + 音檔）
ffmpeg -y \
  -loop 1 -t <秒數> -i slides/slide-01.png \
  -loop 1 -t <秒數> -i slides/slide-02.png \
  ... \
  -i podcast.m4a \
  -filter_complex "...[v0];...[v1];...concat=n=N:v=1:a=0[outv]" \
  -map "[outv]" -map N:a \
  -c:v libx264 -c:a aac output.mp4
```

## 每週摘要模式

用多個熱門話題生成每週內容摘要：

```bash
python scripts/pipeline.py trend-to-content \
  --geo TW \
  --count 5 \
  --platform threads
```

這會為每個話題建立筆記本、研究並生成摘要式內容，適合每週電子報。

## 技巧

- **搶先研究**：熱門話題有 24-48 小時的高峰期。早研究、快發布。
- **加入自己的來源**：搭配趨勢的 URL 加入你的獨特觀點。
- **平台優先級**：視覺型話題走 Instagram，討論型走 Threads。
- **批次規劃**：週一跑 5 個話題的 Pipeline，排程整週發布。

## 下一步

- [研究 → 文章](../research-to-article/) — 單一主題深度研究
- [研究 → Threads](../research-to-threads/) — 社群觸及最佳化
