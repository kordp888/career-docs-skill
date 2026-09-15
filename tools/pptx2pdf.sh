#!/usr/bin/env bash
# PPTX -> PDF (LibreOffice). 사용: ./pptx2pdf.sh deck.pptx [out_dir] [원본서체=대체서체]
#
# 두 가지 함정을 피한다.
#   1. GUI LibreOffice 가 한 번 뜨면 폰트 목록을 캐시한다. 새로 설치한 폰트를
#      못 보고 조용히 다른 서체로 대체한다. 변환마다 별도 프로필을 만들어 막는다.
#   2. 설치된 적 없는 서체는 경고 없이 대체된다. 세 번째 인자로 변환용 사본에서만
#      서체 이름을 바꾼다. 원본 PPTX 의 선언은 건드리지 않는다.
set -euo pipefail

IN="${1:?사용: pptx2pdf.sh deck.pptx [out_dir] [원본서체=대체서체]}"
OUTDIR="${2:-$(dirname "$IN")}"
SWAP="${3:-}"

SOFFICE=""
for c in /opt/homebrew/bin/soffice /usr/local/bin/soffice \
         "/Applications/LibreOffice.app/Contents/MacOS/soffice" \
         "$(command -v soffice || true)" "$(command -v libreoffice || true)"
do
  [ -n "$c" ] && [ -x "$c" ] && SOFFICE="$c" && break
done
[ -n "$SOFFICE" ] || { echo "LibreOffice 를 찾지 못했습니다."; exit 1; }

TMP="$(mktemp -d)"
trap 'rm -rf "$TMP"' EXIT
SRC="$IN"

if [ -n "$SWAP" ]; then
  FROM="${SWAP%%=*}"; TO="${SWAP#*=}"
  SRC="$TMP/render.pptx"
  python3 - "$IN" "$SRC" "$FROM" "$TO" <<'PY'
import sys, zipfile
src, out, a, b = sys.argv[1:5]
with zipfile.ZipFile(src) as zin, zipfile.ZipFile(out, "w", zipfile.ZIP_DEFLATED) as zo:
    for it in zin.infolist():
        d = zin.read(it.filename)
        if it.filename.endswith((".xml", ".rels")):
            d = d.replace(a.encode(), b.encode())
        zo.writestr(it, d)
print(f"서체 치환(변환용 사본): {a} -> {b}")
PY
fi

"$SOFFICE" -env:UserInstallation="file://$TMP/profile" \
  --headless --norestore --convert-to pdf --outdir "$OUTDIR" "$SRC" >/dev/null 2>&1

RESULT="$OUTDIR/$(basename "${SRC%.*}").pdf"
WANT="$OUTDIR/$(basename "${IN%.*}").pdf"
[ "$RESULT" = "$WANT" ] || mv "$RESULT" "$WANT"

echo "생성: $WANT"
if command -v pdffonts >/dev/null; then
  echo "임베드된 서체:"
  pdffonts "$WANT" | awk 'NR>2{print "  " $1}' | sort -u
  echo "Liberation 이나 의도하지 않은 서체가 보이면 폰트 대체가 일어난 것이다."
fi
