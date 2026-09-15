#!/usr/bin/env python3
"""산출물에서 생성 도구 표식을 지운다. PDF 와 OOXML(pptx·docx·xlsx) 을 처리한다.

ai-tell-check: skip

  python3 strip-meta.py out.pdf deck.pptx --author "홍길동" --title "제안서"

작성자 필드에 생성 도구 이름이 남은 채로 나간 서류가 실제로 있었다.
받는 쪽은 파일 정보를 연다. 내용보다 먼저 보이는 경우도 있다.

의존성: PDF 처리에 pikepdf (pip install pikepdf). OOXML 은 표준 라이브러리만 쓴다.
"""
import sys, os, re, zipfile, shutil, datetime, argparse

OOXML = {".pptx", ".docx", ".xlsx", ".potx", ".dotx", ".xltx"}

CORE_XML = """<?xml version="1.0" encoding="UTF-8" standalone="yes"?>\
<cp:coreProperties xmlns:cp="http://schemas.openxmlformats.org/package/2006/metadata/core-properties"\
 xmlns:dc="http://purl.org/dc/elements/1.1/" xmlns:dcterms="http://purl.org/dc/terms/"\
 xmlns:dcmitype="http://purl.org/dc/dcmitype/" xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance">\
<dc:title>{title}</dc:title><dc:creator>{author}</dc:creator>\
<cp:lastModifiedBy>{author}</cp:lastModifiedBy>\
<dcterms:created xsi:type="dcterms:W3CDTF">{now}</dcterms:created>\
<dcterms:modified xsi:type="dcterms:W3CDTF">{now}</dcterms:modified></cp:coreProperties>"""


def strip_pdf(path, author, title):
    try:
        import pikepdf
    except ImportError:
        print("  pikepdf 가 없습니다. pip install pikepdf")
        return False
    pdf = pikepdf.open(path, allow_overwriting_input=True)
    with pdf.open_metadata() as m:
        for k in list(m.keys()):
            del m[k]
        if title:
            m["dc:title"] = title
        if author:
            m["dc:creator"] = [author]
    info = pdf.docinfo
    for k in list(info.keys()):
        del info[k]
    if title:
        info["/Title"] = title
    if author:
        info["/Author"] = author
    pdf.save(path)
    return True


def strip_ooxml(path, author, title):
    now = datetime.datetime.now(datetime.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    core = CORE_XML.format(title=title or "", author=author or "", now=now)
    tmp = path + ".tmp"
    with zipfile.ZipFile(path) as zin, zipfile.ZipFile(tmp, "w", zipfile.ZIP_DEFLATED) as zo:
        for it in zin.infolist():
            d = zin.read(it.filename)
            if it.filename == "docProps/core.xml":
                d = core.encode()
            elif it.filename == "docProps/app.xml":
                d = re.sub(rb"<Application>.*?</Application>", b"<Application></Application>", d)
                d = re.sub(rb"<Company>.*?</Company>", b"<Company></Company>", d)
            zo.writestr(it, d)
    shutil.move(tmp, path)
    return True


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("files", nargs="+")
    ap.add_argument("--author", default="")
    ap.add_argument("--title", default="")
    a = ap.parse_args()

    for p in a.files:
        ext = os.path.splitext(p)[1].lower()
        print(p)
        if ext == ".pdf":
            ok = strip_pdf(p, a.author, a.title)
        elif ext in OOXML:
            ok = strip_ooxml(p, a.author, a.title)
        else:
            print("  건너뜀 (지원하지 않는 형식)")
            continue
        print("  정리 완료" if ok else "  실패")

    print("\n영상·이미지는 이 스크립트가 다루지 않습니다.")
    print("영상은 ffmpeg -i in.mp4 -c copy -map_metadata -1 -movflags +faststart out.mp4")
    return 0


if __name__ == "__main__":
    sys.exit(main())
