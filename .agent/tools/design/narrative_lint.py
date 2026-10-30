#!/usr/bin/env python3
"""narrative_lint — 대사 · 설정 문서의 기계적 일관성 검사 (표준 라이브러리만).

판정은 사람이 한다. 이 도구는 "의심 후보" 만 낸다 — 진짜 위반인지 · 의도된 변화인지 · 규칙이 과민한지는 사람이 고른다.
그래서 모든 지적은 warn 또는 info 이고, error 는 입력 파일 형식 오류에만 쓴다.

    python .agent/tools/design/narrative_lint.py check --voices <폴더> --dialogue <파일·폴더 ...> [--rulebook <json>] [--root R] [--json]
    python .agent/tools/design/narrative_lint.py stats --voices <폴더> --dialogue <파일·폴더 ...> [--root R] [--json]

입력 (경로를 주지 않으면 --root 기준 기본 경로를 쓴다 — 없으면 해당 검사를 '검사 안 함' 으로 밝힌다)
    보이스 프로필   design/narrative/voices/<캐릭터>.md   프런트매터: character · speech_level · sentence_max · forbidden · forbidden_ok_when
    대사 스크립트   design/narrative/dialogue/*.md|*.txt  `캐릭터: 대사` · `캐릭터 [태그1,태그2]: 대사` · 장면 머리줄 `## 장면 S03 @ T12`
    룰북            design/narrative/rulebook.json        world_forbidden · timeline · facts · factions

규칙
    NL001  캐릭터 금기 어휘 (forbidden_ok_when 태그가 있으면 info '예외 맥락')
    NL002  대사 길이 > sentence_max (공백 포함 글자 수)
    NL003  말 높이 불일치 — 한국어 어미 단순 판정. 판정 불가 문장은 세지 않는다. '혼합' 프로필은 검사 안 함
    NL004  세계 금기어 (모든 캐릭터 · 지문)
    NL005  시간선 위반 — 장면 시간선이 fact.after 보다 앞인데 그 표현이 나옴
    NL006  프로필 없는 캐릭터의 대사 (info)
    NL007  룰북 진영 일방 적대 (A 는 B 를 적대하는데 B 는 A 를 적대하지 않음)

종료 코드: 0 = 입력 형식 오류 없음 (의심 후보가 있어도 0) · 1 = 입력 형식 오류 · 2 = 사용법.
"""
import argparse
import json
import os
import re
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from designlib import ParseError, as_list, finding, parse_frontmatter  # noqa: E402

DEFAULT_VOICES = "design/narrative/voices"
DEFAULT_DIALOGUE = "design/narrative/dialogue"
DEFAULT_RULEBOOK = "design/narrative/rulebook.json"
DIALOGUE_EXT = (".md", ".txt")
TEXT_PREVIEW = 60

RULES = {
    "NL001": "캐릭터 금기 어휘",
    "NL002": "대사 길이 초과",
    "NL003": "말 높이 불일치",
    "NL004": "세계 금기어",
    "NL005": "시간선 위반",
    "NL006": "프로필 없는 캐릭터",
    "NL007": "진영 일방 적대",
}

# ── 말 높이 판정 ──────────────────────────────────────────────
LEVELS = ("해요체", "하십시오체", "해체")
LEVEL_ALIASES = {
    "해요체": "해요체", "하십시오체": "하십시오체", "합쇼체": "하십시오체",
    "해체": "해체", "반말": "해체", "해체(반말)": "해체", "해라체": "해체",
    "혼합": "혼합",
}
# 문장 끝에서 벗겨 낼 문장부호 · 따옴표 · 자모(ㅋㅋ · ㅠㅠ) · 물결
TRAIL_RE = re.compile(r"[\s\"'“”‘’)\]」』>~\-—…,.?!ㄱ-ㅎㅏ-ㅣ]+$")
SENT_SPLIT_RE = re.compile(r"(?<=[.?!…])[\"'”’)\]」』]*\s+")
HAEYO_RE = re.compile(r"(?:요|죠)$")
HASIPSIO_RE = re.compile(r"(?:니다|니까|십시오|읍시다)$")
HAE_RE = re.compile(r"(?:다|야|어|아|여|지|냐|니|래|게|자|해|대|네|군|구나|걸|까|라|고|데|든|마|"
                    r"워|와|봐|줘|돼|려|져|쳐|켜|겨|셔)$")  # 워 · 봐 · 줘 · 돼 … = 어/아 축약
# 문장 마지막 낱말이 이것이면 감탄사 · 응답어로 보고 판정하지 않는다
INTERJECTIONS = {"아", "아아", "오", "오오", "음", "흠", "흐음", "네", "예", "응", "어", "야", "헉", "앗", "윽", "으",
                 "에", "에이", "하", "하하", "후", "휴", "와", "우와", "흥", "쳇", "엇", "어머", "저런"}


def classify_sentence(sentence):
    """한 문장의 말 높이: '해요체' · '하십시오체' · '해체' · None(판정 불가)."""
    s = TRAIL_RE.sub("", sentence.strip())
    if not s or not re.search(r"[가-힣]$", s):
        return None
    if s.split()[-1] in INTERJECTIONS:
        return None
    if HAEYO_RE.search(s):
        return "해요체"
    if HASIPSIO_RE.search(s):
        return "하십시오체"
    if HAE_RE.search(s):
        return "해체"
    return None


def split_sentences(text):
    return [p for p in SENT_SPLIT_RE.split(text.strip()) if p.strip()]


def classify_line(text):
    """[(문장, 높이|None), ...]"""
    return [(s, classify_sentence(s)) for s in split_sentences(text)]


# ── 입력 읽기 ────────────────────────────────────────────────
SCENE_RE = re.compile(r"^##\s*장면\s+(?P<scene>[^\s@]+)?\s*(?:@\s*(?P<tl>\S+))?\s*$")
LINE_RE = re.compile(r"^(?P<name>[^\s#:：\[\]][^:：\[\]]{0,29}?)\s*(?:\[(?P<tags>[^\]]*)\])?\s*[:：]\s*(?P<text>.*\S)\s*$")


def _rel(path, root):
    try:
        return os.path.relpath(path, root).replace("\\", "/")
    except ValueError:  # 다른 드라이브
        return os.path.abspath(path).replace("\\", "/")


def _preview(text):
    return text if len(text) <= TEXT_PREVIEW else text[:TEXT_PREVIEW] + "…"


def load_voices(folder, root):
    """(profiles {캐릭터: dict}, errors [finding], infos [finding])."""
    profiles, errors, infos = {}, [], []
    for n in sorted(os.listdir(folder)):
        p = os.path.join(folder, n)
        if not (os.path.isfile(p) and n.endswith(".md")) or n in ("README.md", "CLAUDE.md"):
            continue
        rel = _rel(p, root)
        try:
            with open(p, encoding="utf-8-sig") as f:
                meta, _, _ = parse_frontmatter(f.read(), rel)
        except ParseError as e:
            errors.append(finding("INPUT", "error", rel, f"프런트매터 형식 오류 ({e.line}행): {e.msg}", line=e.line))
            continue
        except UnicodeDecodeError:
            errors.append(finding("INPUT", "error", rel, "UTF-8 이 아님"))
            continue
        if not meta:
            infos.append(finding("INPUT", "info", rel, "프런트매터 없음 — 보이스 프로필이 아니어서 건너뜀"))
            continue
        if meta.get("type") not in (None, "", "voice"):
            infos.append(finding("INPUT", "info", rel, f"type 이 voice 가 아님({meta.get('type')}) — 건너뜀"))
            continue
        char = meta.get("character")
        if not isinstance(char, str) or not char.strip():
            errors.append(finding("INPUT", "error", rel, "보이스 프로필에 character 가 없음"))
            continue
        char = char.strip()
        if char in profiles:
            errors.append(finding("INPUT", "error", rel, f"캐릭터 '{char}' 프로필이 중복됨 (먼저: {profiles[char]['path']})"))
            continue
        prof = {"path": rel, "character": char, "speech_level": None, "sentence_max": None,
                "forbidden": [], "forbidden_ok_when": []}
        lvl = meta.get("speech_level")
        if lvl not in (None, ""):
            if not isinstance(lvl, str) or lvl.replace(" ", "") not in LEVEL_ALIASES:
                errors.append(finding("INPUT", "error", rel,
                                      f"speech_level 값을 알 수 없음: {lvl} (해요체 · 하십시오체 · 해체(반말) · 혼합)"))
                continue
            prof["speech_level"] = LEVEL_ALIASES[lvl.replace(" ", "")]
        smax = meta.get("sentence_max")
        if smax not in (None, ""):
            if not isinstance(smax, str) or not smax.isdigit() or int(smax) <= 0:
                errors.append(finding("INPUT", "error", rel, f"sentence_max 는 양의 정수여야 함: {smax}"))
                continue
            prof["sentence_max"] = int(smax)
        bad = False
        for key in ("forbidden", "forbidden_ok_when"):
            v = meta.get(key)
            if isinstance(v, dict):
                errors.append(finding("INPUT", "error", rel, f"{key} 는 목록이어야 함"))
                bad = True
                break
            prof[key] = [x.strip() for x in as_list(v) if isinstance(x, str) and x.strip()]
        if bad:
            continue
        profiles[char] = prof
    return profiles, errors, infos


def collect_dialogue(paths, root):
    """(파일 목록, errors)."""
    files, errors = [], []
    for p in paths:
        ap = p if os.path.isabs(p) else os.path.join(root, p)
        if os.path.isfile(ap):
            files.append(ap)
        elif os.path.isdir(ap):
            for dirpath, dirnames, filenames in os.walk(ap):
                dirnames.sort()
                for n in sorted(filenames):
                    if n.endswith(DIALOGUE_EXT) and n not in ("README.md", "CLAUDE.md"):
                        files.append(os.path.join(dirpath, n))
        else:
            errors.append(finding("INPUT", "error", p.replace("\\", "/"), "대사 경로가 없음"))
    seen, out = set(), []
    for f in files:
        k = os.path.normcase(os.path.abspath(f))
        if k not in seen:
            seen.add(k)
            out.append(f)
    return out, errors


def parse_dialogue(text, rel):
    """대사 파일 한 개 → {'lines': [...], 'other': n}. 줄 항목: kind(dialogue|other), line, character, tags, text, scene, timeline."""
    lines = text.split("\n")
    start = 0
    if lines and lines[0].strip() == "---":
        _, _, body_start = parse_frontmatter(text, rel)  # ParseError 는 호출자가 처리
        start = body_start - 1
    scene, tl = None, None
    out, other = [], 0
    in_fence = False
    for i in range(start, len(lines)):
        n = i + 1
        s = lines[i].strip()
        if s.startswith("```"):
            in_fence = not in_fence
            continue
        if in_fence or not s:
            continue
        m = SCENE_RE.match(s)
        if m:
            scene, tl = m.group("scene"), m.group("tl")
            continue
        if s.startswith("#"):
            continue
        m = LINE_RE.match(s)
        if m:
            tags = [t.strip() for t in (m.group("tags") or "").split(",") if t.strip()]
            out.append({"kind": "dialogue", "line": n, "character": m.group("name").strip(), "tags": tags,
                        "text": m.group("text").strip(), "scene": scene, "timeline": tl})
        else:
            other += 1
            out.append({"kind": "other", "line": n, "character": None, "tags": [], "text": s,
                        "scene": scene, "timeline": tl})
    return {"lines": out, "other": other}


def load_dialogue(files, root):
    """(docs [{'path', 'lines', 'other'}], errors)."""
    docs, errors = [], []
    for p in files:
        rel = _rel(p, root)
        try:
            with open(p, encoding="utf-8-sig") as f:
                text = f.read()
            d = parse_dialogue(text, rel)
        except ParseError as e:
            errors.append(finding("INPUT", "error", rel, f"프런트매터 형식 오류 ({e.line}행): {e.msg}", line=e.line))
            continue
        except UnicodeDecodeError:
            errors.append(finding("INPUT", "error", rel, "UTF-8 이 아님"))
            continue
        d["path"] = rel
        docs.append(d)
    return docs, errors


def _term_entries(v, key, rel, errors):
    """world_forbidden · facts 공통 — 문자열 또는 {"term", "reason", "except"} 를 정규화."""
    out = []
    if v is None:
        return out
    if not isinstance(v, list):
        errors.append(finding("INPUT", "error", rel, f"{key} 는 목록이어야 함"))
        return out
    for i, e in enumerate(v):
        if isinstance(e, str):
            e = {"term": e}
        if not isinstance(e, dict) or not isinstance(e.get("term"), str) or not e["term"].strip():
            errors.append(finding("INPUT", "error", rel, f"{key}[{i}] 에 term(문자열)이 없음"))
            continue
        exc = e.get("except", [])
        if not isinstance(exc, list) or not all(isinstance(x, str) for x in exc):
            errors.append(finding("INPUT", "error", rel, f"{key}[{i}].except 는 문자열 목록이어야 함"))
            continue
        out.append(dict(e, term=e["term"].strip(), reason=str(e.get("reason", "")), **{"except": exc}))
    return out


def load_rulebook(path, root):
    """(rulebook dict, errors). 형식 오류가 있는 항목은 빼고 나머지로 검사한다."""
    rel = _rel(path, root)
    errors = []
    try:
        with open(path, encoding="utf-8-sig") as f:
            raw = json.load(f)
    except (json.JSONDecodeError, UnicodeDecodeError) as e:
        return None, [finding("INPUT", "error", rel, f"JSON 형식 오류: {e}")]
    if not isinstance(raw, dict):
        return None, [finding("INPUT", "error", rel, "룰북 최상위는 객체여야 함")]
    rb = {"path": rel, "world_forbidden": _term_entries(raw.get("world_forbidden"), "world_forbidden", rel, errors),
          "timeline": {}, "facts": [], "factions": {}}
    tl = raw.get("timeline")
    if tl is not None and not isinstance(tl, list):
        errors.append(finding("INPUT", "error", rel, "timeline 은 목록이어야 함"))
        tl = []
    for i, e in enumerate(tl or []):
        if not isinstance(e, dict) or not isinstance(e.get("id"), str) or isinstance(e.get("order"), bool) \
                or not isinstance(e.get("order"), (int, float)):
            errors.append(finding("INPUT", "error", rel, f"timeline[{i}] 에 id(문자열) · order(숫자)가 필요함"))
            continue
        if e["id"] in rb["timeline"]:
            errors.append(finding("INPUT", "error", rel, f"timeline id 중복: {e['id']}"))
            continue
        rb["timeline"][e["id"]] = e
    for i, f in enumerate(_term_entries(raw.get("facts"), "facts", rel, errors)):
        if f.get("after") not in rb["timeline"]:
            errors.append(finding("INPUT", "error", rel, f"facts 의 '{f['term']}' — after 시간선 ID 가 timeline 에 없음: {f.get('after')}"))
            continue
        rb["facts"].append(f)
    fa = raw.get("factions")
    if fa is not None and not isinstance(fa, dict):
        errors.append(finding("INPUT", "error", rel, "factions 는 객체여야 함"))
        fa = {}
    for name, v in (fa or {}).items():
        hostile = v.get("hostile", []) if isinstance(v, dict) else None
        if not isinstance(hostile, list) or not all(isinstance(x, str) for x in hostile):
            errors.append(finding("INPUT", "error", rel, f"factions.{name}.hostile 은 문자열 목록이어야 함"))
            continue
        rb["factions"][name] = {"hostile": hostile}
    return rb, errors


def _contains(text, entry):
    """except 에 든 낱말(예: '총' 에 대한 '총명')을 지운 뒤 term 이 남아 있는지."""
    t = text
    for x in entry.get("except", []):
        t = t.replace(x, "")
    return entry["term"] in t


# ── 검사 ────────────────────────────────────────────────────
def _resolve(arg, default, root, multi=False):
    """명시 경로(없으면 오류) 또는 기본 경로(없으면 None). (경로 | 경로 목록 | None, explicit)"""
    if arg:
        return arg, True
    p = os.path.join(root, *default.split("/"))
    if os.path.exists(p):
        return ([p] if multi else p), False
    return None, False


def gather(args):
    """공통 입력 로드 → dict. errors · infos · not_run 를 모은다."""
    root = os.path.abspath(args.root)
    errors, infos, not_run = [], [], []
    profiles = {}
    voices, explicit = _resolve(args.voices, DEFAULT_VOICES, root)
    if voices is not None:
        vp = voices if os.path.isabs(voices) else os.path.join(root, voices)
        if not os.path.isdir(vp):
            errors.append(finding("INPUT", "error", voices.replace("\\", "/"), "보이스 프로필 폴더가 없음"))
        else:
            profiles, e, i = load_voices(vp, root)
            errors += e
            infos += i
    if not profiles:
        not_run.append("NL001 · NL002 · NL003 프로필 기반 검사 — 보이스 프로필 없음"
                       + ("" if voices else f" (--voices 미지정 · 기본 {DEFAULT_VOICES} 없음)"))
    dpaths, _ = _resolve(args.dialogue, DEFAULT_DIALOGUE, root, multi=True)
    docs = []
    if dpaths is None:
        not_run.append(f"대사 검사 전체 — 대사 스크립트 없음 (--dialogue 미지정 · 기본 {DEFAULT_DIALOGUE} 없음)")
    else:
        files, e = collect_dialogue(dpaths, root)
        errors += e
        if not files and not e:
            not_run.append("대사 검사 전체 — 대사 경로에 .md · .txt 파일 없음")
        docs, e = load_dialogue(files, root)
        errors += e
    return {"root": root, "profiles": profiles, "docs": docs, "errors": errors, "infos": infos, "not_run": not_run}


def _f(rule, sev, d, ln, msg, **extra):
    return finding(rule, sev, d["path"], msg, line=ln["line"], character=ln["character"],
                   text=_preview(ln["text"]), **extra)


def check(args):
    g = gather(args)
    root, profiles, docs = g["root"], g["profiles"], g["docs"]
    findings, not_run = list(g["errors"]) + list(g["infos"]), list(g["not_run"])

    rb = None
    rpath, explicit = _resolve(args.rulebook, DEFAULT_RULEBOOK, root)
    if rpath is not None:
        ap = rpath if os.path.isabs(rpath) else os.path.join(root, rpath)
        if not os.path.isfile(ap):
            findings.append(finding("INPUT", "error", rpath.replace("\\", "/"), "룰북 파일이 없음"))
        else:
            rb, e = load_rulebook(ap, root)
            findings += e
    if rb is None:
        not_run.append("NL004 · NL005 · NL007 룰북 검사 — 룰북 없음"
                       + ("" if rpath else f" (--rulebook 미지정 · 기본 {DEFAULT_RULEBOOK} 없음)"))
    else:
        if not rb["world_forbidden"]:
            not_run.append("NL004 세계 금기어 — 룰북에 world_forbidden 없음")
        if not rb["facts"]:
            not_run.append("NL005 시간선 위반 — 룰북에 facts 없음")
        if not rb["factions"]:
            not_run.append("NL007 진영 정합성 — 룰북에 factions 없음")

    dialogue = [(d, ln) for d in docs for ln in d["lines"] if ln["kind"] == "dialogue"]
    all_lines = [(d, ln) for d in docs for ln in d["lines"]]

    # NL006 — 프로필 없는 캐릭터
    if profiles:
        missing = {}
        for d, ln in dialogue:
            if ln["character"] not in profiles:
                missing.setdefault(ln["character"], []).append((d, ln))
        for ch, occ in missing.items():
            d, ln = occ[0]
            findings.append(_f("NL006", "info", d, ln, f"'{ch}' 보이스 프로필 없음 — 대사 {len(occ)}줄 (첫 등장)"))
        if missing:
            not_run.append("NL001 · NL002 · NL003 프로필 기반 검사 — 프로필 없는 캐릭터: " + ", ".join(missing))

    # NL003 사전 집계 — 캐릭터별 판정 가능 대사 · 불일치 대사
    lvl_info = {}
    for d, ln in dialogue:
        p = profiles.get(ln["character"])
        if not p or p["speech_level"] in (None, "혼합"):
            continue
        levels = [lv for _, lv in classify_line(ln["text"]) if lv]
        if not levels:
            continue
        st = lvl_info.setdefault(ln["character"], {"judged": 0, "off": []})
        st["judged"] += 1
        off = sorted({lv for lv in levels if lv != p["speech_level"]})
        if off:
            st["off"].append((d, ln, off))
    for ch, p in profiles.items():
        if p["speech_level"] is None:
            not_run.append(f"NL003 말 높이 — '{ch}' 프로필에 speech_level 없음")
        elif p["speech_level"] == "혼합":
            not_run.append(f"NL003 말 높이 — '{ch}' 프로필이 '혼합' (설계상 검사 안 함)")
        if p["sentence_max"] is None:
            not_run.append(f"NL002 대사 길이 — '{ch}' 프로필에 sentence_max 없음")

    for d, ln in dialogue:
        p = profiles.get(ln["character"])
        if not p:
            continue
        text = ln["text"]
        for term in p["forbidden"]:
            if term not in text:
                continue
            ok = sorted(set(ln["tags"]) & set(p["forbidden_ok_when"]))
            if ok:
                findings.append(_f("NL001", "info", d, ln, f"금기 어휘 '{term}' — 예외 맥락 [{', '.join(ok)}] 이라 생략",
                                   term=term, exceptTags=ok))
            else:
                findings.append(_f("NL001", "warn", d, ln, f"금기 어휘 '{term}' ({p['path']})", term=term))
        if p["sentence_max"] is not None and len(text) > p["sentence_max"]:
            findings.append(_f("NL002", "warn", d, ln, f"대사 {len(text)}자 > sentence_max {p['sentence_max']}",
                               length=len(text), limit=p["sentence_max"]))
    for ch, st in lvl_info.items():
        n_off, judged = len(st["off"]), st["judged"]
        ratio = round(100 * n_off / judged) if judged else 0
        expect = profiles[ch]["speech_level"]
        for d, ln, off in st["off"]:
            findings.append(_f("NL003", "warn", d, ln,
                               f"말 높이 {'/'.join(off)} — 프로필은 {expect} (판정 가능 대사 {judged}줄 중 {n_off}줄 {ratio}% 다름)",
                               expected=expect, found=off, judged=judged, offCount=n_off, offRatio=ratio))

    if rb is not None:
        for d, ln in all_lines:
            for e in rb["world_forbidden"]:
                if _contains(ln["text"], e):
                    who = ln["character"] or "지문"
                    findings.append(_f("NL004", "warn", d, ln,
                                       f"세계 금기어 '{e['term']}' ({who}){' — ' + e['reason'] if e['reason'] else ''}",
                                       term=e["term"]))
        if rb["facts"]:
            no_tl = [(d, ln) for d, ln in all_lines if not ln["timeline"]]
            unknown = {}
            for d, ln in all_lines:
                tl = ln["timeline"]
                if not tl:
                    continue
                if tl not in rb["timeline"]:
                    unknown.setdefault((d["path"], tl), ln["line"])
                    continue
                order = rb["timeline"][tl]["order"]
                for fa in rb["facts"]:
                    after = rb["timeline"][fa["after"]]
                    if order < after["order"] and _contains(ln["text"], fa):
                        findings.append(_f("NL005", "warn", d, ln,
                                           f"'{fa['term']}' — 장면 시간선 {tl}(order {order}) 은 {fa['after']}"
                                           f"(order {after['order']}) 보다 앞{' — ' + fa['reason'] if fa['reason'] else ''}",
                                           term=fa["term"], timeline=tl))
            for (path, tl), line in unknown.items():
                findings.append(finding("INPUT", "error", path, f"장면 시간선 ID '{tl}' 가 룰북 timeline 에 없음", line=line))
            if no_tl:
                files = sorted({d["path"] for d, _ in no_tl})
                not_run.append(f"NL005 시간선 위반 — 장면 시간선(`## 장면 X @ T..`) 없는 줄 {len(no_tl)}개: " + ", ".join(files))
        for a, v in rb["factions"].items():
            for b in v["hostile"]:
                if b not in rb["factions"] or a not in rb["factions"][b]["hostile"]:
                    findings.append(finding("NL007", "warn", rb["path"], f"일방 적대 — '{a}' 는 '{b}' 를 적대하지만 반대는 아님",
                                            faction=a, target=b))

    findings.sort(key=lambda f: (f["severity"] != "error", f["path"], f.get("line") or 0))
    summary = {"profiles": len(profiles), "dialogueFiles": len(docs), "dialogueLines": len(dialogue),
               "otherLines": sum(d["other"] for d in docs),
               "otherLinesByFile": {d["path"]: d["other"] for d in docs if d["other"]}}
    return findings, not_run, summary


def stats(args):
    g = gather(args)
    profiles = g["profiles"]
    chars = {}
    for d in g["docs"]:
        for ln in d["lines"]:
            if ln["kind"] != "dialogue":
                continue
            c = chars.setdefault(ln["character"], {"lines": 0, "totalLen": 0, "maxLen": 0, "lengths": [],
                                                   "levels": {k: 0 for k in LEVELS + ("판정 불가",)}})
            n = len(ln["text"])
            c["lines"] += 1
            c["totalLen"] += n
            c["maxLen"] = max(c["maxLen"], n)
            c["lengths"].append(n)
            for _, lv in classify_line(ln["text"]):
                c["levels"][lv or "판정 불가"] += 1
    out = {}
    for ch, c in chars.items():
        ls = sorted(c["lengths"])
        p90 = ls[min(len(ls) - 1, int(0.9 * len(ls)))] if ls else 0
        judged = sum(v for k, v in c["levels"].items() if k != "판정 불가")
        top = max(LEVELS, key=lambda k: c["levels"][k]) if judged else None
        p = profiles.get(ch)
        out[ch] = {"lines": c["lines"], "avgLen": round(c["totalLen"] / c["lines"], 1), "maxLen": c["maxLen"], "p90Len": p90,
                   "levels": c["levels"], "dominantLevel": top,
                   "dominantRatio": round(100 * c["levels"][top] / judged) if top else None,
                   "profile": p["path"] if p else None}
    return g["errors"] + g["infos"], g["not_run"], out


# ── 출력 ────────────────────────────────────────────────────
MARK = {"error": "✖", "warn": "!", "info": "·"}


def format_check(findings, not_run, summary):
    lines = ["# narrative-lint 검사 — 의심 후보 (판정은 사람이: 진짜 위반 · 의도된 변화 · 규칙 과민)"]
    for f in findings:
        loc = f"{f['path']}:{f['line']}" if f.get("line") else f["path"]
        who = f" {f['character']}" if f.get("character") else ""
        txt = f"\n    \"{f['text']}\"" if f.get("text") else ""
        lines.append(f"{MARK.get(f['severity'], '?')} {loc} [{f['rule']}]{who} — {f['message']}{txt}")
    if not findings:
        lines.append("- 발견 없음")
    for nr in not_run:
        lines.append(f"⊘ 검사 안 함: {nr}")
    cnt = {s: sum(1 for f in findings if f["severity"] == s) for s in ("error", "warn", "info")}
    lines.append(f"narrative-lint: 프로필 {summary['profiles']} · 대사 파일 {summary['dialogueFiles']} · "
                 f"대사 {summary['dialogueLines']}줄 · 그 밖의 줄(지문 · 형식 밖, 캐릭터 검사 제외) {summary['otherLines']}줄 · "
                 f"입력 오류 {cnt['error']} · 의심 {cnt['warn']} · 참고 {cnt['info']}")
    return "\n".join(lines)


def format_stats(findings, not_run, out):
    lines = ["# narrative-lint 통계 — 캐릭터별 (프로필 작성 보조)"]
    for f in findings:
        lines.append(f"{MARK.get(f['severity'], '?')} {f['path']} — {f['message']}")
    if not out:
        lines.append("- 대사 없음")
    for ch, s in sorted(out.items(), key=lambda kv: -kv[1]["lines"]):
        lv = " · ".join(f"{k} {v}" for k, v in s["levels"].items())
        dom = f" → 주 높이 {s['dominantLevel']} {s['dominantRatio']}%" if s["dominantLevel"] else ""
        prof = s["profile"] or "프로필 없음"
        lines.append(f"- {ch}: 대사 {s['lines']}줄 · 평균 {s['avgLen']}자 · 90% {s['p90Len']}자 · 최대 {s['maxLen']}자 | "
                     f"문장 높이 {lv}{dom} | {prof}")
    for nr in not_run:
        if nr.startswith("대사 검사 전체"):
            lines.append(f"⊘ 검사 안 함: {nr}")
    return "\n".join(lines)


def main(argv=None):
    for stream in (sys.stdout, sys.stderr):
        try:
            stream.reconfigure(encoding="utf-8")
        except (AttributeError, ValueError):
            pass
    ap = argparse.ArgumentParser(description="대사 · 설정 문서 일관성 검사 — 의심 후보만 낸다 (판정은 사람)")
    sub = ap.add_subparsers(dest="cmd")
    for name, hlp in (("check", "규칙 NL001~NL007 검사"), ("stats", "캐릭터별 대사 수 · 길이 · 말 높이 분포")):
        p = sub.add_parser(name, help=hlp)
        p.add_argument("--voices", help=f"보이스 프로필 폴더 (기본 {DEFAULT_VOICES})")
        p.add_argument("--dialogue", nargs="+", help=f"대사 파일 · 폴더 (기본 {DEFAULT_DIALOGUE})")
        if name == "check":
            p.add_argument("--rulebook", help=f"룰북 JSON (기본 {DEFAULT_RULEBOOK})")
        p.add_argument("--root", default=os.getcwd(), help="상대 경로 · 기본 경로의 기준 (기본: 현재 폴더)")
        p.add_argument("--json", action="store_true")
    a = ap.parse_args(argv)
    if not a.cmd:
        ap.print_help()
        return 2
    if a.cmd == "check":
        findings, not_run, summary = check(a)
        if a.json:
            print(json.dumps({"title": "narrative-lint check", "findings": findings, "notRun": not_run,
                              "summary": summary}, ensure_ascii=False, indent=1))
        else:
            print(format_check(findings, not_run, summary))
    else:
        findings, not_run, out = stats(a)
        if a.json:
            print(json.dumps({"title": "narrative-lint stats", "findings": findings, "notRun": not_run,
                              "characters": out}, ensure_ascii=False, indent=1))
        else:
            print(format_stats(findings, not_run, out))
    return 1 if any(f["severity"] == "error" for f in findings) else 0


if __name__ == "__main__":
    sys.exit(main())
