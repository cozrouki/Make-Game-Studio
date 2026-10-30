#!/usr/bin/env python3
"""content_pattern — 레벨(룸 그래프) · 재사용 패턴 라이브러리 · 콘텐츠 자동화 강도 배치표 검사 (표준 라이브러리만).

기획 데이터(JSON)를 결정적으로 검사한다. 판정(PASS/FAIL)은 스킬 몫이고, 이 도구는 발견(finding)과
'실행하지 못한 검사(not_run)' 를 함께 낸다 — 건너뛴 검사는 이름을 밝힌다 (designlib.print_report).

    python .agent/tools/design/content_pattern.py levels <level.json ...> [--root R] [--json]
    python .agent/tools/design/content_pattern.py patterns <패턴 폴더> <레벨 폴더 또는 파일 ...> [--stale-days N] [--json]
    python .agent/tools/design/content_pattern.py tiers <tiers.json> [--ai-volume N] [--json]

종료 코드: 0 = error 없음 · 1 = error 있음 · 2 = 사용법 오류 · 파일 읽기/파싱 실패.

levels — 레벨 JSON
    {"id": "DUN-crypt", "start": "R01", "goal": "R09", "tags": "design/levels/tags.json",
     "rooms": [{"id": "R01", "type": "entrance", "size": "S", "tags": ["dark"], "connections": ["R02"],
                "oneWay": [], "eventSlots": 1, "patterns": ["PAT-ambush"]}]}
    "tags" 경로는 --root(기본 현재 폴더) 기준, 없으면 레벨 파일 폴더 기준으로 찾는다.
    태그 사전 JSON: {"maxPerRoom": 5, "categories": {"분위기": ["dark", "bright"], "위험": ["trap"]}}
    CP100  입력 구조 — 룸 id 없음 · 중복, start/goal 이 룸 목록에 없음                       error
    CP101  시작 룸에서 목표 룸에 도달 불가                                                   error
    CP102  시작에서 도달할 수 없는 룸(고립)                                                  error
    CP103  막다른 길(연결 1개, 시작 · 목표 아님) — 의도된 보상방일 수 있어 개수만              info
    CP104  양방향 불일치 A→B 인데 B→A 없음 (A 의 oneWay 에 B 가 있으면 의도된 일방이라 제외)  warn
    CP105  없는 룸으로의 연결                                                               error
    CP106  태그가 사전에 없음 — 새 태그는 사전에 먼저 넣는다                                 error
    CP107  룸 태그 수 > maxPerRoom (기본 5)                                                  warn
    CP108  통계 — 길이 3 순환(삼각형) 수 · 분기 폭(연결 수 분포)                              info
    태그 사전이 없으면 CP106 · CP107 은 not_run 으로 남긴다.

patterns — 패턴 폴더의 *.json 과 레벨 JSON 의 룸 "patterns" 사용 현황
    패턴: {"id": "PAT-ambush", "status": "active|deprecated", "kind": "space|npc|event",
           "created": "2026-01-10", "description": "..."}
    레벨 폴더는 하위까지 *.json 을 훑고, "rooms" 목록이 없는 JSON(태그 사전 등)은 건너뛴다.
    CP200  패턴 파일 구조 — id 없음 · 중복(error), status · kind · created 형식 이상(warn)
    CP201  레벨이 없는 패턴 ID 를 씀                                                        error
    CP202  deprecated 패턴 사용 — 기존 사용은 보존이 원칙, 새로 쓰지 않는다                   warn
    CP203  오래됐는데(기본 180일) 사용 0 — deprecated 후보                                    info
    CP204  레벨 파일 수 < 5 — 패턴 라이브러리는 아직 이득이 작다 (차단 아님)                  info
    출력 extra(usage) 에 패턴별 사용 수.

tiers — 콘텐츠 자동화 강도 배치표
    {"items": [{"id": "CNT-npc-bark", "tier": "manual|rulebook|rulebook+ai|ai-first", "volume": 200,
                "consistency": "high|mid|low", "nondeterminism_ok": true, "review_cost": "high|mid|low",
                "incident_cost": "high|mid|low", "reason": "..."}]}
    권장 규칙 (단순 · 설명 가능):
      보수 쪽  사고 비용 high, 또는 일관성 high 이고 비결정성 불가          → manual · rulebook
      AI 쪽    양 ≥ --ai-volume(기본 100) · 검수 비용 low · 비결정성 허용   → rulebook+ai · ai-first
      둘 다 해당하거나 둘 다 아니면 권장 없음(info)
    CP300  항목 구조 — id 없음, 값이 허용 목록 밖, 필드 누락                                 error
    CP301  실제 tier 가 권장 범위 밖 (근거 포함)                                             warn
    CP302  reason 이 비어 있음                                                               warn
"""
import argparse
import datetime
import json
import os
import sys

TOOL_DIR = os.path.dirname(os.path.abspath(__file__))
if TOOL_DIR not in sys.path:
    sys.path.insert(0, TOOL_DIR)

from designlib import finding, print_report  # noqa: E402

TIERS = ("manual", "rulebook", "rulebook+ai", "ai-first")
LEVELS3 = ("high", "mid", "low")
PATTERN_STATUS = ("active", "deprecated")
PATTERN_KIND = ("space", "npc", "event")
DEFAULT_MAX_PER_ROOM = 5
DEFAULT_STALE_DAYS = 180
DEFAULT_AI_VOLUME = 100
MIN_LEVELS_FOR_PATTERNS = 5


class InputError(Exception):
    """사용법 · 파일 읽기 · 파싱 실패 — 종료 코드 2."""


def _rel(path, root):
    p = os.path.abspath(path)
    try:
        r = os.path.relpath(p, root)
    except ValueError:  # 다른 드라이브
        r = p
    if r.startswith(".."):
        r = p
    return r.replace("\\", "/")


def load_json(path):
    try:
        with open(path, encoding="utf-8") as f:
            return json.load(f)
    except FileNotFoundError:
        raise InputError(f"파일 없음: {path}")
    except UnicodeDecodeError:
        raise InputError(f"UTF-8 이 아님: {path}")
    except json.JSONDecodeError as e:
        raise InputError(f"JSON 파싱 실패: {path}:{e.lineno}: {e.msg}")


def _list(v):
    if v is None:
        return []
    return v if isinstance(v, list) else [v]


# ---------------------------------------------------------------- levels

def _resolve_tags(level, level_path, root):
    """태그 사전 경로를 찾는다. (경로 또는 None, 못 찾은 이유)."""
    tags = level.get("tags")
    if not tags:
        return None, "레벨에 \"tags\" 경로 없음"
    if os.path.isabs(tags):
        cands = [tags]
    else:
        cands = [os.path.join(root, tags), os.path.join(os.path.dirname(os.path.abspath(level_path)), tags)]
    for c in cands:
        if os.path.isfile(c):
            return c, ""
    return None, f"태그 사전 파일 없음: {tags}"


def count_triangles(adj):
    """무방향 단순 그래프의 길이 3 순환 수. adj: {id: set(id)} (대칭)."""
    order = {n: i for i, n in enumerate(sorted(adj))}
    n = 0
    for a in adj:
        for b in adj[a]:
            if order[b] <= order[a]:
                continue
            for c in adj[a] & adj[b]:
                if order[c] > order[b]:
                    n += 1
    return n


def reachable(start, edges):
    seen, stack = {start}, [start]
    while stack:
        cur = stack.pop()
        for nxt in edges.get(cur, ()):
            if nxt not in seen:
                seen.add(nxt)
                stack.append(nxt)
    return seen


def check_level(level, path, root, tag_cache=None):
    """(findings, not_run, stats). 레벨 하나를 검사한다."""
    fs, not_run = [], []
    rel = _rel(path, root)
    if not isinstance(level, dict) or not isinstance(level.get("rooms"), list):
        raise InputError(f"레벨 형식이 아님(\"rooms\" 목록 없음): {path}")
    lid = level.get("id") or rel

    rooms, order = {}, []
    for i, r in enumerate(level["rooms"]):
        if not isinstance(r, dict) or not r.get("id"):
            fs.append(finding("CP100", "error", rel, f"{i + 1}번째 룸에 id 없음"))
            continue
        if r["id"] in rooms:
            fs.append(finding("CP100", "error", rel, f"룸 id 중복: {r['id']}", room=r["id"]))
            continue
        rooms[r["id"]] = r
        order.append(r["id"])

    # 연결 · CP105
    edges = {}
    for rid in order:
        targets = []
        for t in _list(rooms[rid].get("connections")):
            if t not in rooms:
                fs.append(finding("CP105", "error", rel, f"{rid} → {t}: 없는 룸으로의 연결", room=rid, target=t))
                continue
            if t != rid and t not in targets:
                targets.append(t)
        edges[rid] = targets

    # CP104 양방향 불일치
    for a in order:
        one_way = set(_list(rooms[a].get("oneWay")))
        for b in edges[a]:
            if a not in edges[b] and b not in one_way:
                fs.append(finding("CP104", "warn", rel,
                                  f"{a} → {b} 인데 {b} → {a} 없음 (의도된 일방이면 {a}.oneWay 에 {b} 를 넣는다)",
                                  room=a, target=b))

    # 도달성 CP101 · CP102
    start, goal = level.get("start"), level.get("goal")
    for key, val in (("start", start), ("goal", goal)):
        if not val:
            fs.append(finding("CP100", "error", rel, f"\"{key}\" 가 비어 있음"))
        elif val not in rooms:
            fs.append(finding("CP100", "error", rel, f"{key} 룸 {val} 이 룸 목록에 없음"))
    if start in rooms:
        seen = reachable(start, edges)
        if goal in rooms and goal not in seen:
            fs.append(finding("CP101", "error", rel, f"시작 {start} 에서 목표 {goal} 에 도달할 수 없음"))
        isolated = [r for r in order if r not in seen]
        for r in isolated:
            fs.append(finding("CP102", "error", rel, f"{r}: 시작 {start} 에서 도달할 수 없는 룸(고립)", room=r))
    else:
        not_run.append(f"CP101 · CP102 ({rel}: 시작 룸이 없어 도달성 검사 안 함)")

    # CP103 막다른 길 — 무방향 이웃 기준
    adj = {r: set() for r in order}
    for a in order:
        for b in edges[a]:
            adj[a].add(b)
            adj[b].add(a)
    dead = [r for r in order if len(adj[r]) == 1 and r not in (start, goal)]
    if dead:
        fs.append(finding("CP103", "info", rel, f"막다른 길 {len(dead)}개 (의도된 보상방인지 확인): {', '.join(dead)}",
                          count=len(dead), rooms=dead))

    # CP108 통계
    tri = count_triangles(adj)
    branching = {}
    for r in order:
        d = len(adj[r])
        branching[d] = branching.get(d, 0) + 1
    dist = ", ".join(f"{k}연결 {branching[k]}개" for k in sorted(branching))
    fs.append(finding("CP108", "info", rel, f"룸 {len(order)}개 · 길이 3 순환 {tri}개 · 분기 폭: {dist or '-'}",
                      triangles=tri, branching={str(k): v for k, v in sorted(branching.items())}))

    # CP106 · CP107 태그
    tag_path, why = _resolve_tags(level, path, root)
    if tag_path is None:
        not_run.append(f"CP106 · CP107 태그 검사 ({rel}: {why})")
    else:
        if tag_cache is not None and tag_path in tag_cache:
            tags = tag_cache[tag_path]
        else:
            tags = load_json(tag_path)
            if tag_cache is not None:
                tag_cache[tag_path] = tags
        if not isinstance(tags, dict) or not isinstance(tags.get("categories"), dict):
            raise InputError(f"태그 사전 형식이 아님(\"categories\" 맵 없음): {tag_path}")
        known = set()
        for vals in tags["categories"].values():
            known.update(_list(vals))
        mx = tags.get("maxPerRoom", DEFAULT_MAX_PER_ROOM)
        for rid in order:
            rtags = _list(rooms[rid].get("tags"))
            for t in rtags:
                if t not in known:
                    fs.append(finding("CP106", "error", rel, f"{rid}: 태그 '{t}' 가 사전에 없음 (사전에 먼저 넣는다)",
                                      room=rid, tag=t))
            if isinstance(mx, int) and len(rtags) > mx:
                fs.append(finding("CP107", "warn", rel, f"{rid}: 태그 {len(rtags)}개 > maxPerRoom {mx}", room=rid))

    stats = {"id": lid, "path": rel, "rooms": len(order), "triangles": tri,
             "branching": {str(k): v for k, v in sorted(branching.items())}, "deadEnds": len(dead)}
    return fs, not_run, stats


def run_levels(paths, root):
    fs, not_run, stats, cache = [], [], [], {}
    for p in paths:
        level = load_json(p)
        f, nr, st = check_level(level, p, root, cache)
        fs += f
        not_run += nr
        stats.append(st)
    return fs, not_run, {"levels": stats}


# ---------------------------------------------------------------- patterns

def _iter_json(target):
    if os.path.isfile(target):
        return [target]
    if not os.path.isdir(target):
        raise InputError(f"파일 · 폴더 없음: {target}")
    out = []
    for dirpath, dirnames, filenames in os.walk(target):
        dirnames.sort()
        for n in sorted(filenames):
            if n.endswith(".json"):
                out.append(os.path.join(dirpath, n))
    return out


def _parse_date(s):
    try:
        return datetime.date.fromisoformat(str(s))
    except ValueError:
        return None


def run_patterns(pattern_dir, level_targets, root, stale_days=DEFAULT_STALE_DAYS, today=None):
    if not os.path.isdir(pattern_dir):
        raise InputError(f"패턴 폴더 없음: {pattern_dir}")
    today = today or datetime.date.today()
    fs, not_run = [], []

    patterns = {}  # id -> (pattern, rel)
    for p in _iter_json(pattern_dir):
        rel = _rel(p, root)
        pat = load_json(p)
        if not isinstance(pat, dict) or not pat.get("id"):
            fs.append(finding("CP200", "error", rel, "패턴에 id 없음"))
            continue
        pid = pat["id"]
        if pid in patterns:
            fs.append(finding("CP200", "error", rel, f"패턴 id 중복: {pid} (먼저: {patterns[pid][1]})", pattern=pid))
            continue
        patterns[pid] = (pat, rel)
        if pat.get("status") not in PATTERN_STATUS:
            fs.append(finding("CP200", "warn", rel, f"{pid}: status '{pat.get('status')}' 는 {'|'.join(PATTERN_STATUS)} 가 아님",
                              pattern=pid))
        if pat.get("kind") not in PATTERN_KIND:
            fs.append(finding("CP200", "warn", rel, f"{pid}: kind '{pat.get('kind')}' 는 {'|'.join(PATTERN_KIND)} 가 아님",
                              pattern=pid))

    usage = {pid: 0 for pid in patterns}
    level_files = []
    for t in level_targets:
        for p in _iter_json(t):
            data = load_json(p)
            if not isinstance(data, dict) or not isinstance(data.get("rooms"), list):
                continue  # 태그 사전 등 레벨이 아닌 JSON
            rel = _rel(p, root)
            level_files.append(rel)
            for r in data["rooms"]:
                if not isinstance(r, dict):
                    continue
                rid = r.get("id", "?")
                for pid in _list(r.get("patterns")):
                    if pid not in patterns:
                        fs.append(finding("CP201", "error", rel, f"{rid}: 없는 패턴 {pid}", room=rid, pattern=pid))
                        continue
                    usage[pid] += 1
                    if patterns[pid][0].get("status") == "deprecated":
                        fs.append(finding("CP202", "warn", rel,
                                          f"{rid}: deprecated 패턴 {pid} 사용 (기존 사용은 보존 — 새로 쓰지 않는다)",
                                          room=rid, pattern=pid))

    stale_skipped = []
    for pid, (pat, rel) in patterns.items():
        if usage[pid] or pat.get("status") == "deprecated":
            continue
        created = _parse_date(pat.get("created"))
        if created is None:
            stale_skipped.append(pid)
            fs.append(finding("CP200", "warn", rel, f"{pid}: created '{pat.get('created')}' 가 YYYY-MM-DD 가 아님",
                              pattern=pid))
            continue
        age = (today - created).days
        if age >= stale_days:
            fs.append(finding("CP203", "info", rel, f"{pid}: 만든 지 {age}일인데 사용 0 — deprecated 후보", pattern=pid))
    if stale_skipped:
        not_run.append(f"CP203 오래된 미사용 판정 ({', '.join(stale_skipped)}: created 날짜를 읽지 못함)")

    if len(level_files) < MIN_LEVELS_FOR_PATTERNS:
        fs.append(finding("CP204", "info", "-",
                          f"레벨 파일 {len(level_files)}개 < {MIN_LEVELS_FOR_PATTERNS} — 패턴 라이브러리는 아직 이득이 작다 "
                          "(규모가 커질 때 도입)", levels=len(level_files)))
    extra = {"usage": dict(sorted(usage.items())), "levelFiles": level_files,
             "patterns": {pid: patterns[pid][0].get("status") for pid in sorted(patterns)}}
    return fs, not_run, extra


# ---------------------------------------------------------------- tiers

def recommend(item, ai_volume=DEFAULT_AI_VOLUME):
    """(권장 tier 목록 또는 None, 근거 문자열)."""
    vol = item.get("volume")
    nd = item.get("nondeterminism_ok")
    cons, rev, inc = item.get("consistency"), item.get("review_cost"), item.get("incident_cost")
    cons_why = []
    if inc == "high":
        cons_why.append("사고 비용 high")
    if cons == "high" and not nd:
        cons_why.append("일관성 high · 비결정성 불가")
    ai_ok = isinstance(vol, (int, float)) and vol >= ai_volume and rev == "low" and nd is True
    ai_why = f"양 {vol} ≥ {ai_volume} · 검수 비용 low · 비결정성 허용"
    if cons_why and ai_ok:
        return None, f"보수 근거({' · '.join(cons_why)})와 AI 근거({ai_why})가 함께 있어 애매함"
    if cons_why:
        return ["manual", "rulebook"], " · ".join(cons_why)
    if ai_ok:
        return ["rulebook+ai", "ai-first"], ai_why
    return None, "보수 · AI 어느 조건에도 뚜렷이 해당하지 않음"


def run_tiers(path, root, ai_volume=DEFAULT_AI_VOLUME):
    data = load_json(path)
    if not isinstance(data, dict) or not isinstance(data.get("items"), list):
        raise InputError(f"배치표 형식이 아님(\"items\" 목록 없음): {path}")
    rel = _rel(path, root)
    fs, recs = [], []
    for i, it in enumerate(data["items"]):
        if not isinstance(it, dict) or not it.get("id"):
            fs.append(finding("CP300", "error", rel, f"{i + 1}번째 항목에 id 없음"))
            continue
        iid = it["id"]
        bad = []
        if it.get("tier") not in TIERS:
            bad.append(f"tier '{it.get('tier')}' ({'|'.join(TIERS)})")
        for k in ("consistency", "review_cost", "incident_cost"):
            if it.get(k) not in LEVELS3:
                bad.append(f"{k} '{it.get(k)}' (high|mid|low)")
        if not isinstance(it.get("volume"), (int, float)) or isinstance(it.get("volume"), bool):
            bad.append(f"volume '{it.get('volume')}' (숫자)")
        if not isinstance(it.get("nondeterminism_ok"), bool):
            bad.append(f"nondeterminism_ok '{it.get('nondeterminism_ok')}' (true|false)")
        if not str(it.get("reason") or "").strip():
            fs.append(finding("CP302", "warn", rel, f"{iid}: reason 이 비어 있음 — 강도를 고른 이유를 적는다", item=iid))
        if bad:
            fs.append(finding("CP300", "error", rel, f"{iid}: 값 이상 — {'; '.join(bad)}", item=iid))
            recs.append({"id": iid, "tier": it.get("tier"), "recommended": None, "why": "입력 오류로 판정 안 함"})
            continue
        rec, why = recommend(it, ai_volume)
        recs.append({"id": iid, "tier": it["tier"], "recommended": rec, "why": why})
        if rec is None:
            fs.append(finding("CP301", "info", rel, f"{iid}: 권장 없음 — {why} (현재 {it['tier']})", item=iid))
        elif it["tier"] not in rec:
            fs.append(finding("CP301", "warn", rel,
                              f"{iid}: tier {it['tier']} 는 권장({' · '.join(rec)}) 밖 — 근거: {why}", item=iid,
                              recommended=rec))
    return fs, [], {"recommendations": recs}


# ---------------------------------------------------------------- CLI

def main(argv=None):
    for stream in (sys.stdout, sys.stderr):
        try:
            stream.reconfigure(encoding="utf-8")
        except (AttributeError, ValueError):
            pass
    ap = argparse.ArgumentParser(description="레벨 · 패턴 라이브러리 · 콘텐츠 자동화 강도 검사")
    sub = ap.add_subparsers(dest="cmd")
    pl = sub.add_parser("levels", help="레벨(룸 그래프) 검사")
    pl.add_argument("files", nargs="+")
    pp = sub.add_parser("patterns", help="패턴 라이브러리 사용 현황")
    pp.add_argument("pattern_dir")
    pp.add_argument("levels", nargs="+")
    pp.add_argument("--stale-days", type=int, default=DEFAULT_STALE_DAYS)
    pp.add_argument("--today", help="기준 날짜 YYYY-MM-DD (기본 오늘 — 테스트용)")
    pt = sub.add_parser("tiers", help="콘텐츠 자동화 강도 배치표 검사")
    pt.add_argument("file")
    pt.add_argument("--ai-volume", type=int, default=DEFAULT_AI_VOLUME)
    for p in (pl, pp, pt):
        p.add_argument("--root", default=os.getcwd())
        p.add_argument("--json", action="store_true")
    try:
        a = ap.parse_args(argv)
    except SystemExit as e:
        return 0 if e.code == 0 else 2
    if not a.cmd:
        ap.print_usage(sys.stderr)
        return 2
    root = os.path.abspath(a.root)
    try:
        if a.cmd == "levels":
            fs, nr, extra = run_levels(a.files, root)
            title = "레벨 검사"
        elif a.cmd == "patterns":
            today = None
            if a.today:
                today = _parse_date(a.today)
                if today is None:
                    raise InputError(f"--today 형식이 아님: {a.today}")
            fs, nr, extra = run_patterns(a.pattern_dir, a.levels, root, a.stale_days, today)
            title = "패턴 라이브러리 사용 현황"
        else:
            fs, nr, extra = run_tiers(a.file, root, a.ai_volume)
            title = "콘텐츠 자동화 강도 배치표"
    except InputError as e:
        print(f"오류: {e}", file=sys.stderr)
        return 2
    print_report(title, fs, nr, a.json, extra)
    if not a.json:
        if a.cmd == "patterns":
            print("\n| 패턴 | 상태 | 사용 수 |\n|---|---|---|")
            for pid, n in extra["usage"].items():
                print(f"| {pid} | {extra['patterns'].get(pid)} | {n} |")
        elif a.cmd == "tiers":
            print("\n| 항목 | 현재 | 권장 | 근거 |\n|---|---|---|---|")
            for r in extra["recommendations"]:
                rec = " · ".join(r["recommended"]) if r["recommended"] else "-"
                print(f"| {r['id']} | {r['tier']} | {rec} | {r['why']} |")
    return 1 if any(f["severity"] == "error" for f in fs) else 0


if __name__ == "__main__":
    sys.exit(main())
