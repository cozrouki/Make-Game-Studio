#!/usr/bin/env python3
"""unity_lint — `.claude/rules/gameplay-code.md` · `AGENTS.md` §3 규칙을 기계로 잡는 가벼운 C# 검사 (표준 라이브러리만).

말로만 있던 규칙을 결정적 검사로 옮긴 것이다 (하네스: 결정적 제약). 정규식 기반이라 컴파일러 수준 분석은 아니다 —
오탐이 나면 그 줄이나 바로 윗줄에 `// unity-lint: ignore UL003` 처럼 적어 끈다.

    python .agent/tools/lint/unity_lint.py <파일 · 폴더 ...>     # 지정 범위
    python .agent/tools/lint/unity_lint.py --staged             # git 스테이징된 .cs 만
    python .agent/tools/lint/unity_lint.py --json ...

규칙 (핫 패스 = Update · LateUpdate · FixedUpdate · OnGUI 본문)
    UL001  핫 패스 LINQ (using System.Linq 파일만)
    UL002  핫 패스 힙 할당 — 컬렉션 · 배열 · StringBuilder · WaitForSeconds new
    UL003  핫 패스 문자열 생성 — 보간 · string.Format/Concat/Join · 문자열 + 변수 · ToString (리터럴끼리 + 는 제외)
    UL004  핫 패스 탐색 — GetComponent* · Find* · Camera.main (지연 초기화 `if (x == null) x = …` · 충돌 결과 대상은 제외)
    UL005  Animator · Material 파라미터를 문자열로 (StringToHash · PropertyToID 캐싱 안 함) — 전체
    UL006  Rigidbody 조작을 Update/LateUpdate 에서 (FixedUpdate 아님)
    UL007  MonoBehaviour · ScriptableObject 의 public 튜닝 필드 ([SerializeField] private 권장)
    UL008  핫 패스 Debug.Log — 매 프레임 문자열 · 스택 수집 (진단 로그는 조건부 컴파일이나 플래그로)
에디터 코드(Editor 폴더 · EditorWindow/Editor 파생)는 핫 패스 규칙(UL001~004 · UL006 · UL008)에서 뺀다.

차단(종료 코드 1)은 lint.config.json 의 "blocking" 에 든 규칙만이다. 처음에는 모두 경고이고, 래칫(같은 지적이 반복됨)으로
디렉터가 규칙을 blocking 으로 올린다 — `studio.py lesson`.
"""
import argparse
import fnmatch
import json
import os
import re
import subprocess
import sys

TOOL_DIR = os.path.dirname(os.path.abspath(__file__))
CONFIG_FILE = os.path.join(TOOL_DIR, "lint.config.json")
DEFAULT_CONFIG = {"blocking": [], "disabled": [], "exclude": ["Packages/**", "Library/**", "**/Plugins/**", "**/ThirdParty/**"]}

RULES = {
    "UL001": "핫 패스 LINQ — 매 프레임 할당 · 열거자 생성. 미리 만든 리스트를 for 로 돈다",
    "UL002": "핫 패스 힙 할당 — 필드에 미리 만들어 재사용하거나 풀을 쓴다",
    "UL003": "핫 패스 문자열 생성 — 값이 바뀔 때만 만들거나 캐싱한다",
    "UL004": "핫 패스 탐색 — Awake/Start 에서 한 번 찾아 필드에 캐싱한다",
    "UL005": "Animator · Material 파라미터 문자열 — static readonly int X = Animator.StringToHash(\"X\") · Shader.PropertyToID 로 캐싱한다",
    "UL006": "Rigidbody 조작은 FixedUpdate 에서 — Update 에서는 입력만 읽어 둔다",
    "UL007": "public 튜닝 필드 — [SerializeField] private 로 바꾼다 (외부 노출이 필요하면 프로퍼티)",
    "UL008": "핫 패스 Debug.Log — 매 프레임 문자열 · 스택 수집. 진단은 [Conditional] 래퍼나 플래그 뒤로",
}
HOT_RULES = ("UL001", "UL002", "UL003", "UL004", "UL006", "UL008")
EDITOR_CLASS_RE = re.compile(r":\s*(?:EditorWindow|Editor|PropertyDrawer|AssetPostprocessor|ScriptableWizard)\b")
LAZY_INIT_RE = re.compile(r"if\s*\(\s*([\w.]+)\s*==\s*null[^)]*\)\s*\1\s*=|\?\?=")
EVENT_TARGET_RE = re.compile(r"\b\w*(?:hit|Hit|col|Col|collider|Collider|other|Other|collision|Collision)\w*\s*\.\s*"
                             r"(?:collider\s*\.\s*|gameObject\s*\.\s*|transform\s*\.\s*)?$")
HOT_METHODS = ("Update", "LateUpdate", "FixedUpdate", "OnGUI")
IGNORE_RE = re.compile(r"unity-lint:\s*ignore\s+((?:UL\d{3}[\s,]*)+)")

HOT_PATTERNS = {
    "UL001": re.compile(r"(?<![A-Za-z_])(?<!Mathf)(?<!Math)\.(?:Where|Select|SelectMany|Any|All|First|FirstOrDefault|Last|"
                        r"LastOrDefault|Single|OrderBy|OrderByDescending|ThenBy|ToList|ToArray|ToDictionary|ToHashSet|Count|"
                        r"Sum|Max|Min|Average|Distinct|GroupBy|Skip|Take|Concat|Aggregate|Contains)\s*\("),
    "UL002": re.compile(r"\bnew\s+(?:(?:List|Dictionary|HashSet|Queue|Stack|LinkedList|SortedList|SortedDictionary)\s*<|"
                        r"StringBuilder\s*\(|WaitForSeconds(?:Realtime)?\s*\(|WaitForEndOfFrame\s*\(|WaitForFixedUpdate\s*\(|"
                        r"[A-Za-z_][\w.]*\s*\[\s*[^\]\s])"),
    "UL004": re.compile(r"\b(?:GetComponents?(?:InChildren|InParent)?\s*[<(]|FindObjects?OfType\s*[<(]|"
                        r"Find(?:First|Any)ObjectByType\s*[<(]|FindObjectsByType\s*[<(]|"
                        r"GameObject\.Find(?:WithTag|GameObjectsWithTag)?\s*\(|Camera\.main\b)"),
    "UL006": re.compile(r"\.(?:AddForce|AddTorque|AddRelativeForce|AddRelativeTorque|MovePosition|MoveRotation)\s*\(|"
                        r"\.(?:velocity|linearVelocity|angularVelocity)\s*[+\-]?=(?!=)"),
}
STRING_PATTERNS = re.compile(r"\$@?\"|@\$\"|\bstring\.(?:Format|Concat|Join)\s*\(|\.ToString\s*\(")
DEBUG_LOG_RE = re.compile(r"\bDebug\.Log(?:Warning|Error|Format|Exception)?\s*\(")
ANIMATOR_RE = re.compile(r"\.(?:SetFloat|SetBool|SetInteger|SetTrigger|ResetTrigger|GetFloat|GetBool|GetInteger|Play|CrossFade|"
                         r"SetColor|SetVector|SetTexture|SetInt|GetColor|GetVector|GetTexture|GetInt)"
                         r"\s*\(\s*\"")
PUBLIC_FIELD_RE = re.compile(r"^\s*public\s+(?!const\b|static\b|readonly\b|override\b|abstract\b|virtual\b|event\b|class\b|"
                             r"struct\b|enum\b|interface\b|delegate\b)(?:float|int|bool|double|long|string|Vector[234]|"
                             r"Vector[23]Int|Color|AnimationCurve|LayerMask)\s+\w+\s*(?:=[^>]|;)")
UNITY_CLASS_RE = re.compile(r":\s*(?:MonoBehaviour|ScriptableObject|NetworkBehaviour)\b")


def strip_code(src):
    """(주석 제거본, 주석 · 문자열 제거본) — 길이와 줄 위치를 그대로 유지한다."""
    out_nc, out_blank = [], []
    i, n = 0, len(src)
    while i < n:
        c = src[i]
        two = src[i:i + 2]
        if two == "//":
            j = src.find("\n", i)
            j = n if j < 0 else j
            pad = " " * (j - i)
            out_nc.append(pad); out_blank.append(pad); i = j
        elif two == "/*":
            j = src.find("*/", i + 2)
            j = n if j < 0 else j + 2
            pad = re.sub(r"[^\n]", " ", src[i:j])
            out_nc.append(pad); out_blank.append(pad); i = j
        elif c == '"' or (c in "$@" and src[i + 1:i + 2] == '"') or (two in ("$@", "@$") and src[i + 2:i + 3] == '"'):
            prefix = 0 if c == '"' else (1 if src[i + 1] == '"' else 2)
            verbatim = "@" in src[i:i + prefix + 1]
            j = i + prefix + 1
            while j < n:
                if verbatim and src[j] == '"' and src[j + 1:j + 2] == '"':
                    j += 2
                    continue
                if not verbatim and src[j] == "\\":
                    j += 2
                    continue
                if src[j] == '"' or (not verbatim and src[j] == "\n"):
                    j += 1
                    break
                j += 1
            seg = src[i:j]
            out_nc.append(seg)
            out_blank.append(seg[:prefix + 1] + re.sub(r"[^\n]", " ", seg[prefix + 1:-1]) + seg[-1:] if len(seg) > prefix + 1 else seg)
            i = j
        elif c == "'":
            j = i + 1
            while j < n and src[j] != "'" and src[j] != "\n":
                j += 2 if src[j] == "\\" else 1
            j = min(j + 1, n)
            out_nc.append(src[i:j]); out_blank.append("'" + " " * max(0, j - i - 2) + ("'" if j - i > 1 else "")); i = j
        else:
            out_nc.append(c); out_blank.append(c); i += 1
    return "".join(out_nc), "".join(out_blank)


def hot_bodies(blank):
    """[(메서드 이름, 시작 오프셋, 끝 오프셋)] — 핫 패스 메서드 본문 (중괄호 짝 맞춤)."""
    out = []
    for m in re.finditer(r"\b(?:void|async\s+void)\s+(" + "|".join(HOT_METHODS) + r")\s*\(\s*\)\s*\{", blank):
        depth, j = 0, m.end() - 1
        while j < len(blank):
            if blank[j] == "{":
                depth += 1
            elif blank[j] == "}":
                depth -= 1
                if depth == 0:
                    break
            j += 1
        out.append((m.group(1), m.end(), j))
    return out


def _line_of(text, offset):
    return text.count("\n", 0, offset) + 1


def lint_source(src, path="<memory>", disabled=()):
    nocomment, blank = strip_code(src)
    lines = src.splitlines()
    findings = []

    def add(rule, offset):
        if rule in disabled:
            return
        ln = _line_of(src, offset)
        for k in (ln, ln - 1):  # 같은 줄 또는 바로 윗줄의 무시 표시
            if 1 <= k <= len(lines):
                m = IGNORE_RE.search(lines[k - 1])
                if m and rule in m.group(1):
                    return
        if any(f["rule"] == rule and f["line"] == ln for f in findings):
            return
        findings.append({"path": path, "line": ln, "rule": rule, "message": RULES[rule],
                         "code": lines[ln - 1].strip() if ln <= len(lines) else ""})

    has_linq = re.search(r"^\s*using\s+System\.Linq\s*;", nocomment, re.M) is not None
    is_editor = "/Editor/" in "/" + path.replace("\\", "/") or EDITOR_CLASS_RE.search(blank) is not None
    for name, start, end in ([] if is_editor else hot_bodies(blank)):
        body_blank, body_nc = blank[start:end], nocomment[start:end]
        for rule, pat in HOT_PATTERNS.items():
            if rule == "UL001" and not has_linq:
                continue
            if rule == "UL006" and name == "FixedUpdate":
                continue
            for m in pat.finditer(body_blank):
                at = start + m.start()
                if rule == "UL004" and _ul004_exempt(blank, at):
                    continue
                add(rule, at)
        # Debug.Log 인자 안의 문자열은 UL008 하나로 본다 (같은 원인을 두 번 세지 않게)
        log_spans = []
        for m in DEBUG_LOG_RE.finditer(body_blank):
            add("UL008", start + m.start())
            log_spans.append((m.start(), _call_end(body_blank, m.end() - 1)))

        def in_log(i):
            return any(a <= i < b for a, b in log_spans)

        for m in STRING_PATTERNS.finditer(body_nc):
            if not in_log(m.start()):
                add("UL003", start + m.start())
        for at in _string_concat(body_nc):
            if not in_log(at):
                add("UL003", start + at)
    for m in ANIMATOR_RE.finditer(nocomment):
        add("UL005", m.start())
    if UNITY_CLASS_RE.search(blank):
        offset = 0
        for line in blank.splitlines(True):
            if PUBLIC_FIELD_RE.match(line):
                add("UL007", offset + len(line) - len(line.lstrip()))
            offset += len(line)
    return sorted(findings, key=lambda f: (f["line"], f["rule"]))


def _ul004_exempt(blank, at):
    """지연 초기화(if (x == null) x = …) · 충돌 · 레이캐스트 결과 대상(hit.collider. …)은 캐싱할 수 없거나 이미 캐싱이다."""
    line_start = blank.rfind("\n", 0, at) + 1
    line_end = blank.find("\n", at)
    line = blank[line_start:line_end if line_end >= 0 else len(blank)]
    if LAZY_INIT_RE.search(line):
        return True
    return EVENT_TARGET_RE.search(blank[line_start:at]) is not None


def _call_end(blank, open_paren):
    """여는 괄호 위치 → 짝이 되는 닫는 괄호 다음 위치 (주석 · 문자열은 이미 지워진 본문)."""
    depth = 0
    for j in range(open_paren, len(blank)):
        if blank[j] == "(":
            depth += 1
        elif blank[j] == ")":
            depth -= 1
            if depth == 0:
                return j + 1
    return len(blank)


def _string_concat(nc):
    """문자열과 비문자열을 + 로 잇는 위치. 리터럴끼리(\"a\" + \"b\")는 컴파일 때 합쳐지므로 뺀다."""
    out = []
    for m in re.finditer(r"\+(?![+=])", nc):
        i, j = m.start() - 1, m.end()
        while i >= 0 and nc[i] in " \t\r\n":
            i -= 1
        while j < len(nc) and nc[j] in " \t\r\n":
            j += 1
        left = i >= 0 and nc[i] == '"'
        right = j < len(nc) and (nc[j] == '"' or nc[j:j + 2] in ('$"', '@"'))
        if left != right:
            out.append(m.start())
    return out


def load_config():
    cfg = dict(DEFAULT_CONFIG)
    if os.path.isfile(CONFIG_FILE):
        with open(CONFIG_FILE, encoding="utf-8") as f:
            cfg.update(json.load(f))
    return cfg


def _excluded(rel, patterns):
    rel = rel.replace("\\", "/")
    return any(fnmatch.fnmatch(rel, p) or fnmatch.fnmatch("/" + rel, "*/" + p.lstrip("*/")) for p in patterns)


def collect(paths, root, exclude):
    out = []
    for p in paths:
        full = p if os.path.isabs(p) else os.path.join(root, p)
        if os.path.isdir(full):
            for base, dirs, files in os.walk(full):
                dirs[:] = [d for d in dirs if d not in ("Library", "Temp", "obj", ".git")]
                out += [os.path.join(base, f) for f in files if f.endswith(".cs")]
        elif full.endswith(".cs") and os.path.isfile(full):
            out.append(full)
    rels = sorted({os.path.relpath(f, root).replace("\\", "/") for f in out})
    return [r for r in rels if not _excluded(r, exclude)]


def staged(root):
    p = subprocess.run(["git", "-C", root, "diff", "--cached", "--name-only", "--diff-filter=ACM"],
                       capture_output=True, text=True, encoding="utf-8")
    return [f for f in p.stdout.splitlines() if f.endswith(".cs")]


def run(paths, root, cfg=None):
    """→ {"files", "findings", "blocking"} — 다른 도구(studio.py commit · 훅)가 import 해서 쓴다."""
    cfg = cfg or load_config()
    findings = []
    files = collect(paths, root, cfg["exclude"])
    for rel in files:
        try:
            with open(os.path.join(root, rel), encoding="utf-8-sig") as f:
                findings += lint_source(f.read(), rel, cfg["disabled"])
        except (OSError, UnicodeDecodeError):
            continue
    blocking = [f for f in findings if f["rule"] in cfg["blocking"]]
    return {"files": len(files), "findings": findings, "blocking": blocking}


def format_result(r):
    lines = [f"{f['path']}:{f['line']}: {f['rule']}{' [차단]' if f in r['blocking'] else ''} {f['message']}\n    {f['code']}"
             for f in r["findings"]]
    lines.append(f"unity-lint: 파일 {r['files']} · 지적 {len(r['findings'])} · 차단 {len(r['blocking'])}")
    return "\n".join(lines)


def main(argv=None):
    for stream in (sys.stdout, sys.stderr):
        try:
            stream.reconfigure(encoding="utf-8")
        except (AttributeError, ValueError):
            pass
    ap = argparse.ArgumentParser(description="Unity C# 규칙 검사 (gameplay-code.md · AGENTS.md §3)")
    ap.add_argument("paths", nargs="*")
    ap.add_argument("--root", default=os.getcwd())
    ap.add_argument("--staged", action="store_true", help="git 스테이징된 .cs 만")
    ap.add_argument("--strict", action="store_true", help="모든 지적을 차단으로 (종료 코드 1)")
    ap.add_argument("--json", action="store_true")
    a = ap.parse_args(argv)
    root = os.path.abspath(a.root)
    paths = staged(root) if a.staged else (a.paths or ["Assets"])
    r = run(paths, root)
    if a.strict:
        r["blocking"] = list(r["findings"])
    print(json.dumps(r, ensure_ascii=False, indent=1) if a.json else format_result(r))
    return 1 if r["blocking"] else 0


if __name__ == "__main__":
    sys.exit(main())
