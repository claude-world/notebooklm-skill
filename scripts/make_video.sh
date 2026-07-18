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

if [ $# -lt 3 ] || [ $# -gt 4 ]; then
  echo "用法: $0 <slides.pdf> <podcast.m4a> <output.mp4> [--force]"
  echo ""
  echo "範例:"
  echo "  $0 output/slides.pdf output/podcast-zh.m4a output/youtube-zh.mp4"
  exit 1
fi

PDF="$1"
AUDIO="$2"
OUTPUT="$3"
FORCE=false
if [ $# -eq 4 ]; then
  if [ "$4" != "--force" ]; then
    echo "錯誤: 第四個參數只能是 --force" >&2
    exit 2
  fi
  FORCE=true
fi

if [ ! -f "$PDF" ]; then
  echo "錯誤: 找不到投影片 PDF: $PDF" >&2
  exit 1
fi
if [ ! -f "$AUDIO" ]; then
  echo "錯誤: 找不到音檔: $AUDIO" >&2
  exit 1
fi
if [ -L "$OUTPUT" ]; then
  echo "錯誤: 拒絕寫入符號連結: $OUTPUT" >&2
  exit 1
fi
if [ -d "$OUTPUT" ]; then
  echo "錯誤: 輸出路徑是目錄: $OUTPUT" >&2
  exit 1
fi
if [ -e "$OUTPUT" ] && [ "$FORCE" != true ]; then
  echo "錯誤: 輸出檔已存在: $OUTPUT（使用 --force 才會覆寫）" >&2
  exit 1
fi

# 檢查依賴
command -v ffmpeg >/dev/null 2>&1 || { echo "錯誤: 需要 ffmpeg (brew install ffmpeg)"; exit 1; }
command -v pdftoppm >/dev/null 2>&1 || { echo "錯誤: 需要 pdftoppm (brew install poppler)"; exit 1; }
command -v ffprobe >/dev/null 2>&1 || { echo "錯誤: 需要 ffprobe (隨 ffmpeg 一起安裝)"; exit 1; }

# 建立可精確清理的暫存目錄
VIDEO_WORK_DIR=$(mktemp -d "${TMPDIR:-/tmp}/notebooklm-video.XXXXXX")
cleanup() {
  rm -rf -- "$VIDEO_WORK_DIR"
}
trap cleanup EXIT

VIDEO_DPI=${VIDEO_DPI:-200}
if ! [[ "$VIDEO_DPI" =~ ^[0-9]+$ ]] || [ "$VIDEO_DPI" -lt 72 ] || [ "$VIDEO_DPI" -gt 600 ]; then
  echo "錯誤: VIDEO_DPI 必須是 72 到 600 的整數" >&2
  exit 2
fi

echo "[1/4] 轉換 PDF 為 PNG..."
pdftoppm -png -r "$VIDEO_DPI" "$PDF" "$VIDEO_WORK_DIR/slide"

# 計算頁數和每頁時長
shopt -s nullglob
SLIDES=("$VIDEO_WORK_DIR"/slide-*.png)
SLIDE_COUNT=${#SLIDES[@]}
if [ "$SLIDE_COUNT" -eq 0 ]; then
  echo "錯誤: PDF 轉換失敗，沒有產生任何 PNG"
  exit 1
fi

echo "[2/4] 取得音檔長度..."
AUDIO_DURATION=$(ffprobe -v quiet -show_entries format=duration -of csv=p=0 "$AUDIO")
if ! [[ "$AUDIO_DURATION" =~ ^[0-9]+([.][0-9]+)?$ ]] || [ "$AUDIO_DURATION" = "0" ]; then
  echo "錯誤: 無法取得有效音檔長度" >&2
  exit 1
fi
PER_SLIDE=$(awk -v duration="$AUDIO_DURATION" -v count="$SLIDE_COUNT" 'BEGIN { printf "%.6f", duration / count }')
echo "  音檔: ${AUDIO_DURATION}s, ${SLIDE_COUNT} 頁, 每頁 ${PER_SLIDE}s"

echo "[3/4] 合成影片..."

# 建構 ffmpeg 輸入參數
FILTERS=""
CONCAT_INPUTS=""
IDX=0
FFMPEG_ARGS=()

for PNG in "${SLIDES[@]}"; do
  FFMPEG_ARGS+=(-loop 1 -t "$PER_SLIDE" -framerate 1 -i "$PNG")
  FILTERS="$FILTERS [${IDX}:v]scale=1920:1080:force_original_aspect_ratio=decrease,pad=1920:1080:(ow-iw)/2:(oh-ih)/2:color=F5F3EE,setsar=1,format=yuv420p[v${IDX}];"
  CONCAT_INPUTS="${CONCAT_INPUTS}[v${IDX}]"
  IDX=$((IDX + 1))
done

FILTER_COMPLEX="${FILTERS}${CONCAT_INPUTS}concat=n=${SLIDE_COUNT}:v=1:a=0[outv]"

mkdir -p "$(dirname "$OUTPUT")"
if [ "$FORCE" = true ]; then
  OVERWRITE_FLAG=-y
else
  OVERWRITE_FLAG=-n
fi
ffmpeg "$OVERWRITE_FLAG" "${FFMPEG_ARGS[@]}" \
  -i "$AUDIO" \
  -filter_complex "$FILTER_COMPLEX" \
  -map "[outv]" -map "${IDX}:a" \
  -c:v libx264 -preset fast -crf 28 \
  -c:a aac -b:a 192k \
  -movflags +faststart \
  "$OUTPUT" 2>&1 | tail -3

echo "[4/4] 完成！"
echo ""
ls -lh "$OUTPUT"
DURATION=$(ffprobe -v quiet -show_entries format=duration -of csv=p=0 "$OUTPUT")
MINUTES=$(awk -v duration="$DURATION" 'BEGIN { printf "%.1f", duration / 60 }')
echo "  長度: ${MINUTES} 分鐘"
echo "  可直接上傳 YouTube"
