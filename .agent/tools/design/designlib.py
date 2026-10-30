"""designlib — 기획 문서 도구 공통 기반 (표준 라이브러리만).

기획 문서(design/ 아래 .md)의 프런트매터를 읽는 최소 YAML 파서와 문서 수집 · 보고 출력 형식을 둔다.
표준(필드 · 허용 값)은 이 파일이 아니라 `.agent/tools/design/standard.json` 이 정본이다 — 기준을 바꿀 때 코드를 고치지 않는다.

지원하는 프런트매터 문법 (PyYAML 없이 읽을 수 있는 부분집합):
    key: 값                    문자열 (따옴표 벗김) · 숫자처럼 보여도 문자열로 둔다
    key: [a, b, "c d"]         인라인 목록
    key:                       블록 목록
      - a
    key:                       한 단계 맵 (값은 문자열 또는 인라인/블록 목록)
      sub: x
      sub2: [a, b]
      sub3:
        - c
    # 주석 · 빈 줄
그 밖의 문법(여러 줄 문자열 · 깊은 중첩 · 앵커)은 지원하지 않는다 — 만나면 ParseError 로 줄 번호를 알린다.
"""
import json
import os
import re

TOOL_DIR = os.path.dirname(os.path.abspath(__file__))
STANDARD_FILE = os.path.join(TOOL_DIR, "standard.json")


class ParseError(Exception):
    def __init__(self, path, line, msg):
        super().__init__(f"{path}:{line}: {msg}")
        self.path, self.line, self.msg = path, line, msg


def load_standard(path=STANDARD_FILE):
    with open(path, encoding="utf-8") as f:
        return json.load(f)


def _scalar(v):
    v = v.strip()
    if len(v) >= 2 and v[0] == v[-1] and v[0] in "\"'":
        return v[1:-1]
    return v


def _inline_list(v, path, line):
    inner = v.strip()[1:-1].strip()
    if not inner:
        return []
    out, cur, quote = [], "", None
    for ch in inner:
        if quote:
            cur += ch
            if ch == quote:
                quote = None
        elif ch in "\"'":
            quote = ch
            cur += ch
        elif ch == ",":
            out.append(_scalar(cur))
            cur = ""
        else:
            cur += ch
    if quote:
        raise ParseError(path, line, "닫히지 않은 따옴표")
    out.append(_scalar(cur))
    return [x for x in out if x != ""]


def _strip_comment(s):
    """따옴표 밖의 ' #' 뒤를 버린다."""
    quote = None
    for i, ch in enumerate(s):
        if quote:
            if ch == quote:
                quote = None
        elif ch in "\"'":
            quote = ch
        elif ch == "#" and (i == 0 or s[i - 1] in " \t"):
            return s[:i].rstrip()
    return s.rstrip()


def _value(raw, path, line):
    raw = raw.strip()
    if raw.startswith("["):
        if not raw.endswith("]"):
            raise ParseError(path, line, "인라인 목록이 ] 로 끝나지 않음")
        return _inline_list(raw, path, line)
    return _scalar(raw)


def parse_frontmatter(text, path="<text>"):
    """(meta dict, body str, body_start_line). 프런트매터가 없으면 ({}, text, 1)."""
    lines = text.split("\n")
    if not lines or lines[0].strip() != "---":
        return {}, text, 1
    end = next((i for i in range(1, len(lines)) if lines[i].strip() == "---"), None)
    if end is None:
        raise ParseError(path, 1, "프런트매터가 --- 로 닫히지 않음")
    meta, key, sub = {}, None, None
    for i in range(1, end):
        n = i + 1
        raw = _strip_comment(lines[i].replace("\t", "  "))
        if not raw.strip():
            continue
        indent = len(raw) - len(raw.lstrip(" "))
        s = raw.strip()
        if indent == 0:
            m = re.match(r"^([A-Za-z_][\w-]*)\s*:\s*(.*)$", s)
            if not m:
                raise ParseError(path, n, f"최상위 키 형식이 아님: {s}")
            key, sub = m.group(1), None
            meta[key] = _value(m.group(2), path, n) if m.group(2).strip() else None
            continue
        if key is None:
            raise ParseError(path, n, "키 없이 들여쓴 줄")
        if s.startswith("- "):
            item = _value(s[2:], path, n)
            if sub is not None:
                cur = meta[key].get(sub)
                if cur is None:
                    meta[key][sub] = cur = []
                if not isinstance(cur, list):
                    raise ParseError(path, n, f"{key}.{sub} 는 목록이 아님")
                cur.append(item)
            else:
                if meta[key] is None:
                    meta[key] = []
                if not isinstance(meta[key], list):
                    raise ParseError(path, n, f"{key} 는 목록이 아님")
                meta[key].append(item)
            continue
        m = re.match(r"^([A-Za-z_][\w-]*)\s*:\s*(.*)$", s)
        if not m:
            raise ParseError(path, n, f"지원하지 않는 형식: {s}")
        if meta[key] is None:
            meta[key] = {}
        if not isinstance(meta[key], dict):
            raise ParseError(path, n, f"{key} 는 맵이 아님")
        sub = m.group(1)
        meta[key][sub] = _value(m.group(2), path, n) if m.group(2).strip() else None
    body = "\n".join(lines[end + 1:])
    return meta, body, end + 2


def read_doc(path, root):
    with open(path, encoding="utf-8") as f:
        text = f.read()
    rel = os.path.relpath(path, root).replace("\\", "/")
    meta, body, start = parse_frontmatter(text, rel)
    return {"path": rel, "meta": meta, "body": body, "bodyStart": start}


def iter_docs(root, dirs=("design",), skip=("design/registry",)):
    """root 기준 dirs 아래의 .md 를 (경로순) 읽는다. 파싱 오류는 문서 대신 {'path', 'error'} 로 돌려준다."""
    out = []
    for d in dirs:
        base = os.path.join(root, *d.split("/"))
        for dirpath, dirnames, filenames in os.walk(base):
            dirnames.sort()
            rel_dir = os.path.relpath(dirpath, root).replace("\\", "/")
            if any(rel_dir == s or rel_dir.startswith(s + "/") for s in skip):
                dirnames[:] = []
                continue
            for n in sorted(filenames):
                if not n.endswith(".md") or n == "CLAUDE.md":
                    continue
                p = os.path.join(dirpath, n)
                try:
                    out.append(read_doc(p, root))
                except ParseError as e:
                    out.append({"path": e.path, "error": f"{e.line}행: {e.msg}"})
                except UnicodeDecodeError:
                    out.append({"path": os.path.relpath(p, root).replace("\\", "/"), "error": "UTF-8 이 아님"})
    return out


def as_list(v):
    if v is None or v == "":
        return []
    return v if isinstance(v, list) else [v]


def finding(rule, severity, path, msg, **extra):
    """보고 한 줄. severity: error(차단 후보) · warn · info. 판정(PASS/FAIL)은 스킬 몫이다."""
    d = {"rule": rule, "severity": severity, "path": path, "message": msg}
    d.update(extra)
    return d


def print_report(title, findings, not_run=(), as_json=False, extra=None):
    """findings 와 '실행하지 못한 검사(not_run)' 를 함께 낸다 — 건너뛴 검사는 이름을 밝힌다."""
    if as_json:
        out = {"title": title, "findings": findings, "notRun": list(not_run)}
        if extra:
            out.update(extra)
        print(json.dumps(out, ensure_ascii=False, indent=1))
        return
    print(f"# {title}")
    if not findings:
        print("- 발견 없음")
    for f in findings:
        mark = {"error": "✖", "warn": "!", "info": "·"}.get(f["severity"], "?")
        print(f"{mark} [{f['rule']}] {f['path']} — {f['message']}")
    for nr in not_run:
        print(f"⊘ 검사 안 함: {nr}")
