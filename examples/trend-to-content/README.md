# 範例：趨勢到來源導向內容

使用 `trend-pulse` 找到話題，再由 NotebookLM 搜尋、匯入研究來源並生成草稿。

## 前置需求

```bash
notebooklm-auth verify
command -v trend-pulse
```

若執行檔不在 `PATH`：

```bash
export TREND_PULSE_CMD=/absolute/path/to/trend-pulse
```

## 執行 Pipeline

```bash
notebooklm-pipeline trend-to-content \
  --geo TW \
  --count 5 \
  --platform threads \
  --language zh-TW \
  --research-mode deep \
  --max-research-sources 10 \
  > trends-result.json
```

每個趨勢會各自建立筆記本。Pipeline 會先匯入 trend-pulse 提供的有效網址；
沒有網址時加入描述文字，接著執行 NotebookLM web research、等待完成、匯入結果，
最後才生成平台草稿。

## 檢查部分失敗

```bash
jq '{status, processed: .trends_processed, failed: .trends_failed}' trends-result.json
jq '.results[] | {topic, status, research_error, source_summary: .initial_source_summary}' \
  trends-result.json
```

單一話題失敗不會抹掉其他結果，因此 top-level `partial` 是重要訊號。不要只看
輸出檔是否存在。

## 延伸產出物

從選定結果取得 notebook ID：

```bash
NOTEBOOK_ID=$(jq -r '.results[] | select(.status == "ok") | .notebook.id' \
  trends-result.json | head -n 1)

notebooklm-skill generate \
  --notebook "$NOTEBOOK_ID" --type slides --lang zh-TW \
  --output ./output/slides.pdf

notebooklm-skill podcast \
  --notebook "$NOTEBOOK_ID" --lang zh-TW \
  --output ./output/podcast.m4a

./scripts/make_video.sh \
  ./output/slides.pdf ./output/podcast.m4a ./output/video.mp4
```

`make_video.sh` 需要 `ffmpeg`、`ffprobe` 與 Poppler 的 `pdftoppm`。既有輸出不會
被覆寫，除非明確傳入第四個參數 `--force`。

## 注意事項

- 趨勢資料只是選題訊號；最終主張必須來自已匯入的研究來源。
- 內容具有時效性，發布前重新確認日期、事件狀態與引用。
- 本 Pipeline 只生成草稿，不會發佈到社群平台。
