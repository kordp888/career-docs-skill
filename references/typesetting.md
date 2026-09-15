# 변환과 검사

실제로 걸렸던 함정과 그 대응입니다. 명령만 필요하면 `tools/` 의 스크립트를 쓰면 됩니다.

## HTML → PDF

```bash
"/Applications/Google Chrome.app/Contents/MacOS/Google Chrome" \
  --headless=new --disable-gpu --no-sandbox --no-pdf-header-footer \
  --print-to-pdf="$OUT" "file://$ABS_IN"
```

Playwright 가 받아 두는 `chromium_headless_shell` 은 버전이 올라가면 옛 경로가
사라집니다. 어제 되던 명령이 오늘 없는 파일을 가리킵니다. 시스템 Chrome 을 직접
부르는 쪽이 오래 갑니다.

CSS 에 두 가지가 없으면 결과가 어긋납니다. `@page { size: A4 portrait; margin: 0 }`
가 없으면 여백이 생기고, `print-color-adjust: exact` 가 없으면 배경색이 빠집니다.
화면에서는 멀쩡해 보이므로 PDF 를 열어서 확인합니다.

폰트는 시스템에 설치된 것만 씁니다. 웹폰트를 링크로 걸면 헤드리스에서 로드 전에
인쇄가 끝나는 경우가 있습니다. 본문 한글 서체는 설치본을 쓰는 쪽이 안전합니다.

## PPTX → PDF

```bash
soffice -env:UserInstallation="file://$TMP/profile" \
  --headless --norestore --convert-to pdf --outdir "$OUTDIR" "$IN"
```

`-env:UserInstallation` 이 핵심입니다. GUI LibreOffice 를 한 번 띄운 적이 있으면
폰트 목록이 캐시되어 있고, 방금 설치한 폰트를 못 봅니다. 변환마다 빈 프로필을
새로 만들면 목록을 다시 읽습니다.

없는 서체는 경고 없이 대체됩니다. Liberation 이나 엉뚱한 손글씨체로 바뀐 PDF 가
그대로 나갑니다. 설치된 서체 이름이 파일 안의 선언과 다르면, 변환용 사본에서만
이름을 바꿉니다. 원본 PPTX 의 선언은 그대로 두어야 원래 환경에서 정상으로 열립니다.

```python
import zipfile
with zipfile.ZipFile(src) as zin, zipfile.ZipFile(out, "w", zipfile.ZIP_DEFLATED) as zo:
    for it in zin.infolist():
        d = zin.read(it.filename)
        if it.filename.endswith((".xml", ".rels")):
            d = d.replace(b"Noto Sans CJK KR", b"Noto Sans KR")
        zo.writestr(it, d)
```

## 가변 폰트

굵게 지정한 제목이 가늘게 나오면 가변 폰트가 원인입니다. LibreOffice 는 wght 축을
따르지 않고 기본 인스턴스만 씁니다. `tools/make-static-weights.py` 로 Regular 와
Bold 를 만들어 폰트 디렉터리에 두고, 가변 폰트 원본은 치웁니다. 둘이 같이 있으면
어느 쪽이 잡힐지 정해지지 않습니다.

이름 테이블만 고치면 부족합니다. `OS/2.fsSelection` 의 BOLD 비트와 `head.macStyle`
까지 세워야 굵게 인식됩니다.

## 검사

```bash
pdfinfo out.pdf | grep -E 'Pages|Title|Author|Producer'
pdffonts out.pdf | awk 'NR>2{print $1}' | sort -u
pdftoppm -png -r 50 out.pdf page          # 눈으로 확인
python3 tools/ai-tell-check.py docs/*.html deck.pptx
```

`pdffonts` 결과에 Regular 만 있고 Bold 가 없으면 제목이 굵지 않다는 뜻입니다.
Thin 이 섞여 있으면 가변 폰트 문제입니다. 목록만 보고 끝내지 말고 페이지를 이미지로
뽑아 한 번 봅니다. 구조가 맞아도 글자가 깨지는 경우가 있습니다.

`pdfinfo` 의 Producer 와 Creator 에 변환 도구 이름이 남습니다. 내보내기 직전에
`tools/strip-meta.py` 를 돌립니다.

## 산출물 보관

빌드 스크립트를 임시 디렉터리에 두지 않습니다. 결과 파일만 남고 다시 만들 방법이
사라집니다. 스크립트는 저장소 안에 두고, 임시 디렉터리에는 중간 렌더만 둡니다.
