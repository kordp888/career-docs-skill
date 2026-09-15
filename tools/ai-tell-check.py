#!/usr/bin/env python3
"""AI 티 검사기. 산출물을 내보내기 전에 돌린다.

ai-tell-check: skip  (이 파일은 규칙 목록 자체를 담고 있어 검사 대상이 아니다)

  python3 tools/ai-tell-check.py <파일 또는 글롭> ...
  python3 tools/ai-tell-check.py "docs/**/*.md" out.html deck.pptx

md·txt·html·css·js·json·yaml 은 원문을, pptx·docx·xlsx 는 내부 XML 을 검사한다.
위반이 있으면 종료 코드 1. CI 나 커밋 훅에 그대로 걸 수 있다.
"""
import re, sys, glob, os, zipfile

# (이름, 정규식, 심각도, 고치는 법)
RULES = [
 ("em-dash",      r"—",                          "E", "콜론·쉼표·괄호·마침표로 바꾼다. 제목은 콜론"),
 ("emoji-head",   r"(?m)^#{1,6}\s*[\U0001F300-\U0001FAFF]", "E", "제목은 글자로 쓴다"),
 ("emoji-marker", r"class=\"emoji\"|<div[^>]*>\s*[\U0001F300-\U0001FAFF]\s*</div>", "E", "이모지 섹션 마커를 지운다"),
 ("를-통해",       r"[을를]\s*통[해하]",                "W", "'~로', '~써서'"),
 ("에-있어서",     r"에\s*있어서",                      "W", "'~에서', '~은'"),
 ("핵심은",        r"핵심은",                           "W", "'요는' 또는 삭제"),
 ("결론적으로",    r"결론적으로|종합하면",               "W", "삭제"),
 ("할-수-있습니다", r"라고\s*할\s*수\s*있",              "W", "'입니다'"),
 ("본질적으로",    r"본질적으로|중요한\s*것은",          "W", "삭제"),
 ("과장어",        r"패러다임|혁신적|강력[한히]|획기적", "W", "구체적 사실로 대체"),
 ("대구-반복",     r"[가이]\s*아니라\s",                "C", "문서당 1회까지. 넘으면 '말고'로"),
 ("영문-마케팅어", r"(?i)\b(empower|seamless|leverage|cutting[- ]edge|game[- ]?chang|revolutioniz|unlock|elevate|delve|tapestry|robust solution)\b", "W", "구체적 동사로"),
 ("해라체",        r"(?m)(했다|한다|이다|였다|된다)\.\s*$", "N", "존댓말. 사람이 읽는 산문만 해당"),
]
# 디자인 기본값 (코드 파일에만 적용)
DESIGN = [
 ("Apple기본블루",  r"#0071[eE]3",                     "W", "주제에서 끌어온 색으로"),
 ("크림+테라코타",  r"#[fF]4[fF]1[eE][aA]|#[eE]9[eE]5[dD][cC]", "W", "AI 생성 디자인 집중 조합"),
 ("보라→파랑그라디언트", r"linear-gradient\([^)]*#[89aAbB][0-9a-fA-F]{5}[^)]*#[0-9a-fA-F]*[eEfF]{2}\)", "C", "그라디언트 히어로 금지"),
 ("전부-가운데정렬", r"text-align:\s*center",           "C", "좌측 정렬 기본"),
 ("기본서체",       r"font-family:[^;]*\b(Inter|Space Grotesk)\b", "W", "주제에서 서체를 고른다"),
]
OOXML = {".pptx",".docx",".xlsx"}
# 기술 기록체가 관례인 곳은 해라체를 묻지 않는다. 코드 주석·독스트링·테스트가 대상이다.
CODEISH_EXT  = {".py",".ts",".js",".tsx",".jsx",".go",".rs",".sh",".yaml",".yml",".json",".svg"}
CODEISH_PATH = re.compile(r"(^|/)(scripts|tests|test|lib|src|bin|tools|migrations)(/|$)")
def haerache_exempt(path):
    return (os.path.splitext(path)[1].lower() in CODEISH_EXT
            or bool(CODEISH_PATH.search(path.replace(os.sep,"/"))))
TEXT  = {".md",".txt",".html",".htm",".css",".js",".ts",".json",".yaml",".yml",".py",".svg"}

def read(path):
    ext=os.path.splitext(path)[1].lower()
    if ext in OOXML:
        try:
            with zipfile.ZipFile(path) as z:
                parts=[n for n in z.namelist() if n.endswith(".xml") and ("slides/" in n or "document" in n or "sharedStrings" in n)]
                return "\n".join(z.read(n).decode("utf-8","ignore") for n in parts)
        except Exception as e: return ""
    if ext in TEXT or ext=="":
        try: return open(path,encoding="utf-8",errors="ignore").read()
        except Exception: return ""
    return ""

_FENCE=re.compile(r"```.*?```|~~~.*?~~~", re.S)
_INLINE=re.compile(r"`[^`\n]+`")
def strip_quoted(s):
    """코드 블록과 인라인 코드는 검사 대상이 아니다.
    규칙 문서가 금지어를 '나열'하는 것까지 위반으로 잡히면 게이트를 못 쓴다."""
    s=_FENCE.sub(lambda m: "\n"*m.group(0).count("\n"), s)
    return _INLINE.sub(" ", s)

SKIP=re.compile(r"ai-tell-check:\s*skip")
def check(path):
    s=read(path)
    if not s: return []
    # 규칙 목록 자체를 담은 파일은 건너뛴다. 첫 20줄에 표식을 둔다.
    if SKIP.search("\n".join(s.split("\n")[:20])): return []
    if os.path.splitext(path)[1].lower() in {".md",".txt"}: s=strip_quoted(s)
    ext=os.path.splitext(path)[1].lower()
    rules = RULES + (DESIGN if ext in {".html",".htm",".css",".js",".ts",".svg"} else [])
    out=[]
    for name,pat,sev,fix in rules:
        ms=list(re.finditer(pat,s))
        if not ms: continue
        if name=="대구-반복" and len(ms)<=1: continue
        if name=="해라체" and (ext in OOXML or haerache_exempt(path)): continue
        ln=s[:ms[0].start()].count("\n")+1
        out.append((sev,name,len(ms),ln,fix))
    return out

def main(argv):
    paths=[]
    for a in argv:
        paths += glob.glob(a,recursive=True) if any(c in a for c in "*?[") else [a]
    bad=0
    for p in sorted(set(paths)):
        if not os.path.isfile(p): continue
        hits=check(p)
        if not hits: continue
        print(f"\n{p}")
        for sev,name,n,ln,fix in sorted(hits,key=lambda h:{"E":0,"C":1,"W":2,"N":3}[h[0]]):
            print(f"  [{sev}] {name:16} {n:3}건  첫 위치 {ln}행   → {fix}")
            if sev=="E": bad+=n
    print("\n등급  E 무조건 고친다 · C 확인한다 · W 표현을 다듬는다 · N 참고")
    if bad: print(f"실패: E {bad}건. 고치고 다시 돌린다."); return 1
    print("통과" if paths else "대상 없음"); return 0

if __name__=="__main__": sys.exit(main(sys.argv[1:]))
