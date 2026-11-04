#!/usr/bin/env python3
"""godot_doc_audit — Godot 게임 코드(GDScript)의 문서 주석(`##`)이 빠진 곳과 문법 실수를 찾는다 (표준 라이브러리만).

`/ko-godot-doc` 스킬이 쓰는 결정적 검사다. 문서 주석 문법의 출처는 Godot 4.7 공식 문서
"GDScript documentation comments" 다 (docs.godotengine.org — 2026-11-04 확인). 정규식 기반이라 파서 수준 분석은 아니다 —
오탐이 나면 그 줄이나 바로 윗줄에 `# godot-doc: ignore GD001` 처럼 적어 끈다.

    python .agent/tools/godot/godot_doc_audit.py <파일 · 폴더 ...>
    python .agent/tools/godot/godot_doc_audit.py --json src

규칙
    GD001  공개 멤버에 문서 주석이 없다 — signal · const · enum · @export var · 공개 var · 공개 func · 내부 class
    GD002  스크립트 설명(맨 위 `##` 블록)이 없다 — class_name 이 있는 스크립트만 (전역 클래스는 에디터 도움말에 뜬다)
    GD003  태그 이름과 콜론 사이에 공백 — `@tutorial  :` 은 무효로 무시된다
    GD004  한 멤버에 @deprecated 와 @experimental 을 같이 붙였다
    GD005  [codeblock] 안에 탭 — 파서가 탭을 지운다. 공백 4칸으로 들여 쓴다
    GD006  금지어 — 정보 없이 길이만 늘리는 말 (simple · easy · just · 단순히 · 그냥 · 쉽게 …). 경고만
    GD007  설명이 멤버 이름을 되풀이할 뿐이다 — `## Sets the speed.` (set_speed) · `## speed` 처럼. 경고만

`_` 로 시작하는 멤버(비공개 · 엔진 콜백)와 @onready 노드 참조는 GD001 에서 뺀다 — 문서가 없으면 도움말에서도 숨는다.
C# (.cs) 은 검사하지 않는다. 결과에 "C# 파일 N개 검사 안 함" 으로 따로 적는다.

판정: GD001~005 가 없으면 PASS · 있으면 CONCERNS · 검사한 .gd 가 0개면 NOT ASSESSED. 종료 코드는 판정과 무관하게 0
(인수 오류만 2) — 문서 누락은 커밋을 막을 일이 아니다.
"""
import argparse
import fnmatch
import json
import os
import re
import sys

RULES = {
    "GD001": "공개 멤버에 문서 주석(##)이 없다 — 바로 윗줄에 ## 로 무엇을 하는지 쓴다. 모르면 비워 두고 목록에 남긴다",
    "GD002": "class_name 스크립트에 스크립트 설명이 없다 — 맨 위(extends · class_name 아래)에 ## 짧은 설명 한 줄",
    "GD003": "태그 이름과 콜론 사이 공백 — 태그가 무효로 무시된다. `@tutorial(제목): url` 처럼 붙여 쓴다",
    "GD004": "@deprecated 와 @experimental 을 함께 쓰지 않는다 — 하나만 고른다",
    "GD005": "[codeblock] 안의 탭은 파서가 지운다 — 공백 4칸으로 들여 쓴다",
    "GD006": "금지어 — 정보 없이 길이만 늘린다. 지우거나 구체적인 말로 바꾼다",
    "GD007": "멤버 이름을 되풀이할 뿐인 설명 — 결과 · 조건 · 단위 · 반환값을 쓴다",
}
WARN_ONLY = ("GD006", "GD007")
EXCLUDE = ["addons/**", ".godot/**", "**/.godot/**", "**/addons/**"]

# Godot 문서 작성 지침(Ban these 8 words)의 금지어 + 한국어 대응어
BANNED_EN = ("obvious", "obviously", "simple", "simply", "basic", "basically", "easy", "easily",
             "actual", "actually", "just", "clear", "clearly")
BANNED_KO = ("단순히", "간단히", "간단하게", "그냥", "쉽게", "쉬운", "당연히", "물론", "명확히", "기본적으로", "사실상", "실제로")
BANNED_RE = re.compile(r"(?<![A-Za-z])(" + "|".join(BANNED_EN) + r")(?![A-Za-z])|(" + "|".join(BANNED_KO) + r")",
                       re.IGNORECASE)

DECL_RE = re.compile(
    r"^(?P<indent>\s*)(?P<annot>(?:@\w+(?:\([^)]*\))?\s+)*)"
    r"(?:(?P<static>static)\s+)?(?P<kind>signal|const|enum|var|func|class)\s+(?P<name>[A-Za-z_]\w*)")
CLASS_NAME_RE = re.compile(r"^\s*(?:@\w+(?:\([^)]*\))?\s+)*class_name\s+\w+")
HEADER_RE = re.compile(r"^\s*(?:@tool|@icon\([^)]*\)|@static_unload|extends\b|class_name\b)")
ANNOT_ONLY_RE = re.compile(r"^\s*@\w+(?:\([^)]*\))?\s*$")
TAG_SPACE_RE = re.compile(r"^\s*##\s*@(tutorial(?:\([^)]*\))?|deprecated|experimental)\s+:")
IGNORE_RE = re.compile(r"godot-doc:\s*ignore\s+((?:GD\d{3}[\s,]*)+)")


def _ignored(lines, i, rule):
    for j in (i, i - 1):
        if 0 <= j < len(lines):
            m = IGNORE_RE.search(lines[j])
            if m and rule in m.group(1):
                return True
    return False


def _indent(s):
    return len(s) - len(s.lstrip(" \t"))


def _doc_above(lines, i):
    """선언 i 바로 위의 ## 블록(위→아래 순서). 어노테이션만 있는 줄은 건너뛴다. 빈 줄을 만나면 끊긴다."""
    j = i - 1
    while j >= 0 and ANNOT_ONLY_RE.match(lines[j]):
        j -= 1
    block = []
    while j >= 0 and lines[j].lstrip().startswith("##"):
        block.append(lines[j].lstrip()[2:].strip())
        j -= 1
    return list(reversed(block))


def _inline_doc(line):
    """같은 줄 뒤의 ## 설명 (문자열 안의 ## 는 대충 피한다: 따옴표가 짝수 개인 위치만)."""
    idx = line.find("##")
    while idx != -1:
        before = line[:idx]
        if before.count('"') % 2 == 0 and before.count("'") % 2 == 0 and before.strip():
            return line[idx + 2:].strip()
        idx = line.find("##", idx + 2)
    return None


def _restates(name, text):
    """설명이 이름만 되풀이하는가 — 이름 단어를 빼면 남는 내용 단어가 없거나, 'Sets the X.' 꼴."""
    words = [w for w in re.split(r"[_\s]+", name.lower()) if w]
    body = re.sub(r"\[/?\w+[^\]]*\]", " ", text.lower())
    body_words = [w for w in re.findall(r"[a-z가-힣0-9]+", body)]
    filler = {"the", "a", "an", "of", "this", "value", "sets", "set", "gets", "get", "returns", "return",
              "설정한다", "설정", "값", "반환한다", "반환", "가져온다", "을", "를", "의", "이", "가"}
    rest = [w for w in body_words if w not in words and w not in filler]
    return bool(body_words) and not rest


def audit_source(src, path="x.gd"):
    lines = src.splitlines()
    findings = []

    def add(rule, i, msg, name=None):
        if not _ignored(lines, i, rule):
            findings.append({"rule": rule, "line": i + 1, "path": path, "name": name, "msg": msg,
                             "severity": "warn" if rule in WARN_ONLY else "concern"})

    # GD002: class_name 스크립트의 스크립트 설명
    has_class_name = any(CLASS_NAME_RE.match(l) for l in lines)
    if has_class_name:
        k = 0
        while k < len(lines) and (not lines[k].strip() or HEADER_RE.match(lines[k])
                                  or (lines[k].lstrip().startswith("#") and not lines[k].lstrip().startswith("##"))):
            k += 1
        ok = k < len(lines) and lines[k].lstrip().startswith("##")
        if ok:
            # 블록 바로 뒤(어노테이션 줄 건너뜀)가 선언이면 그 블록은 멤버 설명이다
            e = k
            while e < len(lines) and lines[e].lstrip().startswith("##"):
                e += 1
            while e < len(lines) and ANNOT_ONLY_RE.match(lines[e]):
                e += 1
            ok = not (e < len(lines) and DECL_RE.match(lines[e]))
        if not ok:
            add("GD002", 0, RULES["GD002"])

    # 줄 단위 문법 검사 (GD003 · GD005 · GD006)
    in_codeblock = False
    for i, l in enumerate(lines):
        s = l.lstrip()
        if not s.startswith("##") and _inline_doc(l) is None:
            continue
        text = s[2:] if s.startswith("##") else _inline_doc(l)
        if TAG_SPACE_RE.match(l):
            add("GD003", i, RULES["GD003"])
        if "[codeblock" in text:
            in_codeblock = True
        if in_codeblock and "\t" in text:
            add("GD005", i, RULES["GD005"])
        if "[/codeblock]" in text:
            in_codeblock = False
            continue
        if not in_codeblock:
            clean = re.sub(r"\[code\].*?\[/code\]", " ", text)
            m = BANNED_RE.search(clean)
            if m:
                add("GD006", i, f"{RULES['GD006']} ('{m.group(0)}')")

    # 선언 검사 (GD001 · GD004 · GD007). 함수 본문 안의 var 는 멤버가 아니다 — 스코프 들여쓰기로 거른다
    scopes = [0]          # 멤버를 선언할 수 있는 들여쓰기 (최상위 0, 내부 class 본문)
    body_of = None        # 지금 건너뛰는 func 본문의 기준 들여쓰기
    pending_class = None
    for i, l in enumerate(lines):
        if not l.strip() or l.lstrip().startswith("#"):
            continue
        ind = _indent(l)
        if pending_class is not None:
            if ind > pending_class:
                scopes.append(ind)
            pending_class = None
        while len(scopes) > 1 and ind < scopes[-1]:
            scopes.pop()
        if body_of is not None:
            if ind > body_of:
                continue
            body_of = None
        m = DECL_RE.match(l)
        if not m:
            continue
        kind, name, annot = m.group("kind"), m.group("name"), m.group("annot") or ""
        if kind == "func":
            body_of = ind
        if kind == "class":
            pending_class = ind
        if ind != scopes[-1]:
            continue
        doc = _doc_above(lines, i)
        inline = _inline_doc(l)
        if inline:
            doc = doc + [inline]
        prev_annots = []
        j = i - 1
        while j >= 0 and ANNOT_ONLY_RE.match(lines[j]):
            prev_annots.append(lines[j].strip())
            j -= 1
        all_annot = annot + " " + " ".join(prev_annots)
        private = name.startswith("_")
        onready = "@onready" in all_annot
        if not doc:
            if not private and not (kind == "var" and onready):
                add("GD001", i, f"{RULES['GD001']} — {kind} {name}", name)
            continue
        joined = " ".join(doc)
        if "@deprecated" in joined and "@experimental" in joined:
            add("GD004", i, RULES["GD004"], name)
        first = next((d for d in doc if d and not d.startswith("@")), "")
        if first and _restates(name, first):
            add("GD007", i, f"{RULES['GD007']} — {name}: '{first}'", name)
    return findings


def _excluded(rel):
    rel = rel.replace("\\", "/")
    return any(fnmatch.fnmatch(rel, pat) or fnmatch.fnmatch("/" + rel, "*/" + pat) for pat in EXCLUDE)


def collect(paths):
    gd, cs = [], []
    for p in paths:
        if os.path.isfile(p):
            (gd if p.endswith(".gd") else cs if p.endswith(".cs") else []).append(p)
            continue
        for dp, dns, fns in os.walk(p):
            # 숨김 폴더(.godot · .git · .claude · .agent 등 — 엔진 캐시 · 도구 자산)와 서드파티 addons 는 게임 코드가 아니다
            dns[:] = [d for d in dns if not d.startswith(".") and d != "addons"]
            for fn in fns:
                full = os.path.join(dp, fn)
                if _excluded(os.path.relpath(full, p)):
                    continue
                if fn.endswith(".gd"):
                    gd.append(full)
                elif fn.endswith(".cs"):
                    cs.append(full)
    return sorted(gd), sorted(cs)


def run(paths):
    gd, cs = collect(paths)
    findings, members = [], 0
    for f in gd:
        with open(f, encoding="utf-8", errors="replace") as fh:
            src = fh.read()
        findings += audit_source(src, f)
        members += sum(1 for l in src.splitlines() if DECL_RE.match(l))
    concerns = [f for f in findings if f["severity"] == "concern"]
    if not gd:
        verdict = "NOT ASSESSED"
        reason = "검사할 .gd 파일이 없다" + (f" (C# {len(cs)}개만 있음 — C# 은 검사하지 않는다)" if cs else "")
    else:
        verdict = "CONCERNS" if concerns else "PASS"
        reason = ""
    return {"verdict": verdict, "reason": reason, "gd_files": len(gd), "cs_files_not_checked": len(cs),
            "declarations": members, "findings": findings}


def main(argv=None):
    ap = argparse.ArgumentParser(description="Godot GDScript 문서 주석 검사")
    ap.add_argument("paths", nargs="+")
    ap.add_argument("--json", action="store_true")
    a = ap.parse_args(argv)
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")
    for p in a.paths:
        if not os.path.exists(p):
            print(f"경로 없음: {p}", file=sys.stderr)
            return 2
    r = run(a.paths)
    if a.json:
        print(json.dumps(r, ensure_ascii=False, indent=2))
        return 0
    for f in r["findings"]:
        tag = "볼 것" if f["severity"] == "warn" else "누락"
        print(f"{f['path']}:{f['line']}: {f['rule']} [{tag}] {f['msg']}")
    by = {}
    for f in r["findings"]:
        by[f["rule"]] = by.get(f["rule"], 0) + 1
    print(f"\n.gd {r['gd_files']}개 · 선언 {r['declarations']}개 · 지적 " +
          (", ".join(f"{k} {v}" for k, v in sorted(by.items())) or "0"))
    if r["cs_files_not_checked"]:
        print(f"C# 파일 {r['cs_files_not_checked']}개 검사 안 함 — C# 문서 주석은 이 도구 범위 밖")
    print(f"판정: {r['verdict']}" + (f" — {r['reason']}" if r["reason"] else ""))
    return 0


if __name__ == "__main__":
    sys.exit(main())
