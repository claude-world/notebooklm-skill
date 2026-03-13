#!/bin/bash
# make_video.sh — 將 NotebookLM 投影片 + Podcast 合成 YouTube 影片
#
# 用法：
#   ./scripts/make_video.sh slides.pdf podcast.m4a output.mp4
#
# 需求：
#   - ffmpeg (brew install ffmpeg)
#   - pdftoppm (brew install poppler)

set -euo pipefail

if [ $# -lt 3 ]; then
  echo "用法: $0 <slides.pdf> <podcast.m4a> <output.mp4>"
  echo ""
  echo "範例:"
  echo "  $0 output/slides.pdf output/podcast-zh.m4a output/youtube-zh.mp4"
  exit 1
fi

PDF="$1"
AUDIO="$2"
OUTPUT="$3"

# 檢查依賴
command -v ffmpeg >/dev/null 2>&1 || { echo "錯誤: 需要 ffmpeg (brew install ffmpeg)"; exit 1; }
command -v pdftoppm >/dev/null 2>&1 || { echo "錯誤: 需要 pdftoppm (brew install poppler)"; exit 1; }
command -v ffprobe >/dev/null 2>&1 || { echo "錯誤: 需要 ffprobe (隨 ffmpeg 一起安裝)"; exit 1; }

# 建立暫存目錄
TMPDIR=$(mktemp -d)
trap "rm -rf $TMPDIR" EXIT

echo "[1/4] 轉換 PDF 為 PNG..."
pdftoppm -png -r 300 "$PDF" "$TMPDIR/slide"

# 計算頁數和每頁時長
SLIDE_COUNT=$(ls "$TMPDIR"/slide-*.png 2>/dev/null | wc -l | tr -d ' ')
if [ "$SLIDE_COUNT" -eq 0 ]; then
  echo "錯誤: PDF 轉換失敗，沒有產生任何 PNG"
  exit 1
fi

echo "[2/4] 取得音檔長度..."
AUDIO_DURATION=$(ffprobe -v quiet -show_entries format=duration -of csv=p=0 "$AUDIO")
PER_SLIDE=$(echo "$AUDIO_DURATION / $SLIDE_COUNT" | bc -l)
echo "  音檔: ${AUDIO_DURATION}s, ${SLIDE_COUNT} 頁, 每頁 ${PER_SLIDE}s"

echo "[3/4] 合成影片..."

# 建構 ffmpeg 輸入參數
INPUTS=""
FILTERS=""
CONCAT_INPUTS=""
IDX=0

for PNG in "$TMPDIR"/slide-*.png; do
  INPUTS="$INPUTS -loop 1 -t $PER_SLIDE -framerate 1 -i $PNG"
  FILTERS="$FILTERS [${IDX}:v]scale=1920:1080:force_original_aspect_ratio=decrease,pad=1920:1080:(ow-iw)/2:(oh-ih)/2:color=F5F3EE,setsar=1,format=yuv420p[v${IDX}];"
  CONCAT_INPUTS="${CONCAT_INPUTS}[v${IDX}]"
  IDX=$((IDX + 1))
done

FILTER_COMPLEX="${FILTERS} ${CONCAT_INPUTS}concat=n=${SLIDE_COUNT}:v=1:a=0[outv]"

eval ffmpeg -y $INPUTS \
  -i "$AUDIO" \
  -filter_complex "\"$FILTER_COMPLEX\"" \
  -map '"[outv]"' -map "${IDX}:a" \
  -c:v libx264 -preset fast -crf 28 \
  -c:a aac -b:a 192k \
  -movflags +faststart \
  "$OUTPUT" 2>&1 | tail -3

echo "[4/4] 完成！"
echo ""
ls -lh "$OUTPUT"
DURATION=$(ffprobe -v quiet -show_entries format=duration -of csv=p=0 "$OUTPUT")
MINUTES=$(echo "$DURATION / 60" | bc)
echo "  長度: ${MINUTES} 分鐘"
echo "  可直接上傳 YouTube"
