#!/usr/bin/env bash
# HTML -> PDF (인쇄 품질). 사용: ./html2pdf.sh in.html [out.pdf]
#
# Playwright 의 headless_shell 은 버전이 바뀌면 경로가 사라진다.
# 시스템에 설치된 Chrome 을 직접 부르는 쪽이 오래 간다.
set -euo pipefail

IN="${1:?사용: html2pdf.sh in.html [out.pdf]}"
OUT="${2:-${IN%.*}.pdf}"

CHROME=""
for c in \
  "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome" \
  "/Applications/Chromium.app/Contents/MacOS/Chromium" \
  "$(command -v google-chrome || true)" \
  "$(command -v chromium || true)" \
  "$(command -v chromium-browser || true)"
do
  [ -n "$c" ] && [ -x "$c" ] && CHROME="$c" && break
done
[ -n "$CHROME" ] || { echo "Chrome 을 찾지 못했습니다."; exit 1; }

ABS="$(cd "$(dirname "$IN")" && pwd)/$(basename "$IN")"

"$CHROME" --headless=new --disable-gpu --no-sandbox \
  --no-pdf-header-footer --print-to-pdf="$OUT" "file://$ABS" 2>/dev/null

command -v pdfinfo >/dev/null && pdfinfo "$OUT" | grep -E '^(Pages|Page size)'
echo "생성: $OUT"

# CSS 에 이 둘이 없으면 결과가 어긋난다.
#   @page { size: A4 portrait; margin: 0 }   여백
#   print-color-adjust: exact                배경색
