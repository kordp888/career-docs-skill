#!/usr/bin/env python3
"""가변 폰트에서 정적 굵기 인스턴스를 만든다.

ai-tell-check: skip

  python3 make-static-weights.py NotoSansKR-Variable.ttf --weights 400 500 700

LibreOffice 와 일부 PDF 경로는 가변 폰트의 wght 축을 따르지 않는다. 굵게 지정한
제목이 가늘게 나오는데 경고가 없다. 정적 인스턴스를 만들어 폰트 디렉터리에 두고
가변 폰트 원본은 치운다. 두 개가 같이 있으면 어느 쪽이 잡힐지 정해지지 않는다.

의존성: fonttools (pip install fonttools)
"""
import sys, os, argparse

NAMES = {100: "Thin", 200: "ExtraLight", 300: "Light", 400: "Regular",
         500: "Medium", 600: "SemiBold", 700: "Bold", 800: "ExtraBold", 900: "Black"}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("src")
    ap.add_argument("--weights", nargs="+", type=int, default=[400, 700])
    ap.add_argument("--outdir", default=".")
    ap.add_argument("--family", default=None, help="지정하지 않으면 원본 패밀리명을 쓴다")
    a = ap.parse_args()

    from fontTools.ttLib import TTFont
    from fontTools.varLib import instancer

    base = TTFont(a.src)
    family = a.family or base["name"].getDebugName(16) or base["name"].getDebugName(1)

    for w in a.weights:
        style = NAMES.get(w, str(w))
        inst = instancer.instantiateVariableFont(TTFont(a.src), {"wght": w}, inplace=False)
        for rec in inst["name"].names:
            if rec.nameID in (1, 16):
                rec.string = family
            elif rec.nameID in (2, 17):
                rec.string = style
            elif rec.nameID == 4:
                rec.string = f"{family} {style}"
            elif rec.nameID == 6:
                rec.string = f"{family.replace(' ', '')}-{style}"
        os2 = inst["OS/2"]
        os2.usWeightClass = w
        # Bold 비트는 이름만으로 정해지지 않는다. 직접 세운다.
        if w >= 700:
            os2.fsSelection = (os2.fsSelection | 0x20) & ~0x40
            inst["head"].macStyle |= 0x1
        else:
            os2.fsSelection = (os2.fsSelection | 0x40) & ~0x20
            inst["head"].macStyle &= ~0x1
        out = os.path.join(a.outdir, f"{family.replace(' ', '')}-{style}.ttf")
        inst.save(out)
        print(f"생성: {out}")

    print("\n폰트 디렉터리에 옮긴 뒤 가변 폰트 원본은 치웁니다.")
    print("확인: fc-scan --format '%{family} | %{style} | w%{weight}\\n' <파일>")
    return 0


if __name__ == "__main__":
    sys.exit(main())
