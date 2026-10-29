"""스튜디오 하네스 — 래칫(반복 실수 → 구조 수정) · 하네스 지표 · 쓰기 시점 가드.

래칫:  같은 종류의 실수(리뷰 지적 · 검수 반려 · 버그 원인)를 `lesson add` 로 기록한다. 같은 종류가 ratchetAfter(기본 2)번
       쌓이면 디렉터에게 "하네스 개선" 티켓이 자동으로 나간다. 디렉터는 룰 · 훅 · 테스트 · 분석기 · 헌장 중 하나로
       그 실수를 구조적으로 막고 `lesson resolve` 로 닫는다. 닫힌 뒤 다시 나오면(재발) 한 번 만에 다시 티켓이 나간다.
지표:  티켓 기록에서 검수 반려율 · 다시 열림 · 차단 · 스토리 소요 시간 · 래칫 현황을 계산한다 (하네스를 바꾼 효과 판단).
가드:  Claude Code PreToolUse(Write|Edit) 훅이 호출한다. 역할 세션이 자기 쓰기 영역(+ 공유 영역) 밖의 추적 대상 파일을
       고치려 하면 막는다. git 무시 파일(세션 상태 · 로컬 설정 · 생성 원본)과 역할을 모르는 세션은 막지 않는다.
"""
import json
import os
import re
import statistics
import subprocess

from studio import ACTIVE, DIRECTOR, StudioError, now, parse_time, read_json, write_json

LESSONS_FILE = "lessons.json"
KIND_RE = re.compile(r"^[0-9a-z가-힣][0-9a-z가-힣._-]{1,47}$")
DEFAULTS = {"ratchetAfter": 2}
HARNESS_TITLE = "하네스 개선: "


def settings(st):
    return dict(DEFAULTS, **st.cfg.get("harness", {}))


# ---------------------------------------------------------------- 래칫
def _lessons_path(st):
    return os.path.join(st.dir, LESSONS_FILE)


def load_lessons(st):
    return read_json(_lessons_path(st), {"version": 1, "kinds": {}})


def _ticket_active(st, tid):
    if not tid:
        return False
    try:
        return st.load_ticket(tid)["status"] in ACTIVE
    except StudioError:
        return False


def add_lesson(st, by, kind, note, ref=""):
    """실수 1건 기록. 임계값에 닿으면 디렉터 티켓을 낸다. → {kind, count, sinceResolve, ticket}"""
    st.check_role(by, allow_director=True)
    kind = kind.strip().lower()
    if not KIND_RE.match(kind):
        raise StudioError("kind 는 소문자 · 숫자 · 한글 · . _ - 2~48자 (예: update-alloc, acceptance-mismatch)")
    if not note.strip():
        raise StudioError("--note 필수 — 무엇이 어디서 반복됐는지")
    data = load_lessons(st)
    k = data["kinds"].setdefault(kind, {"events": [], "status": "open", "ticket": None})
    k["events"].append({"at": now(), "by": by, "ref": ref, "note": note.strip().replace("\n", " ")})
    # 막은 시점의 기록 개수로 나눈다 — 시각(초 단위)으로 나누면 막은 직후 같은 초의 재발을 놓친다
    since = k["events"][k.get("resolvedCount", 0):]
    threshold = 1 if k["status"] in ("resolved", "recurred") else settings(st)["ratchetAfter"]
    if k["status"] == "resolved":
        k["status"] = "recurred"  # 구조로 막았는데 다시 나왔다 — 그 장치가 부족했다는 뜻
    ticket = None
    if len(since) >= threshold and not _ticket_active(st, k.get("ticket")) and by != DIRECTOR:
        recurred = k["status"] == "recurred"
        body = "\n".join([
            f"같은 종류의 실수가 {'래칫 후 다시' if recurred else f'{len(since)}번'} 나왔다 — 말로 부탁하는 대신 구조로 막는다 "
            "(`AGENTS.md` §3-1 · 하네스 래칫).",
            "",
            f"**종류**: `{kind}`",
            "",
            "**기록** (`production/studio/lessons.json`):",
            *[f"- {e['at'][:16]} [{e['by']}] {e['note']}" + (f" ({e['ref']})" if e["ref"] else "") for e in since],
            "",
            "**막는 방법 (결정적인 것부터)**: 커밋 · 쓰기 훅 / 정적 검사 규칙(`.agent/tools/lint` 의 blocking 승격) / "
            "회귀 테스트 / `.claude/rules` 룰 / 헌장 · 스킬 문구.",
            "결정하면 `studio.py lesson resolve " + kind + " --how \"<바꾼 파일 · 장치>\"` 로 닫는다.",
        ])
        ticket = st.new_ticket(by, DIRECTOR, "task", HARNESS_TITLE + kind, body, "P1")
        k["ticket"] = ticket["id"]
    data["kinds"][kind] = k
    write_json(_lessons_path(st), data)
    st.log("lesson.add", kind=kind, by=by, ticket=ticket and ticket["id"])
    return {"kind": kind, "count": len(k["events"]), "sinceResolve": len(since), "status": k["status"],
            "ticket": ticket and ticket["id"]}


def resolve_lesson(st, kind, how, by=DIRECTOR):
    """디렉터가 구조로 막은 뒤 닫는다. how = 바꾼 장치(파일 · 규칙 id)."""
    if by != DIRECTOR:
        raise StudioError("lesson resolve 는 director 만 — 룰 · 훅 · 도구는 디렉터 영역이다")
    if not how.strip():
        raise StudioError("--how 필수 — 무엇을 바꿔 막았는지 (파일 · 규칙 id)")
    data = load_lessons(st)
    kind = kind.strip().lower()
    if kind not in data["kinds"]:
        raise StudioError(f"기록 없는 종류: {kind}")
    k = data["kinds"][kind]
    k.update(status="resolved", resolvedAt=now(), resolvedCount=len(k["events"]), how=how.strip())
    k.setdefault("history", []).append({"at": k["resolvedAt"], "how": how.strip()})
    write_json(_lessons_path(st), data)
    st.log("lesson.resolve", kind=kind, how=how.strip())
    return dict(k, kind=kind)


# ---------------------------------------------------------------- 지표
_STATUS_RE = re.compile(r"^(\S+) \[[^\]]+\] .*?status (\S+)→(\S+)")


def _transitions(t):
    out = []
    for e in t["thread"]:
        m = _STATUS_RE.match(e)
        if m:
            out.append((parse_time(m.group(1)), m.group(2), m.group(3)))
    return out


def metrics(st):
    """티켓 기록으로 계산하는 하네스 지표. 규칙을 바꾼 전후를 비교하는 근거다."""
    tickets = st.tickets()
    stories = [t for t in tickets if t["type"] == "story"]
    reviews = [t for t in tickets if t["type"] == "review" and t["to"] == "planning"]
    rejects = [t for t in tickets if t["type"] == "bug" and t["from"] == "planning"]
    reopened = blocked = 0
    cycle = []
    for t in tickets:
        tr = _transitions(t)
        reopened += sum(1 for _at, a, b in tr if a == "done" and b != "done")
        blocked += sum(1 for _at, _a, b in tr if b == "blocked")
        if t["type"] == "story" and t["status"] == "done":
            starts = [at for at, _a, b in tr if b == "in-progress" and at]
            ends = [at for at, _a, b in tr if b == "done" and at]
            if starts and ends and ends[-1] >= starts[0]:
                cycle.append((ends[-1] - starts[0]).total_seconds() / 3600)
    reviews_done = sum(1 for t in reviews if t["status"] == "done")
    kinds = load_lessons(st)["kinds"]
    harness_tickets = [t for t in tickets if t["title"].startswith(HARNESS_TITLE)]
    by_role = {}
    for t in tickets:
        if t["status"] == "done":
            by_role[t["to"]] = by_role.get(t["to"], 0) + 1
    return {
        "tickets": len(tickets),
        "stories": {"total": len(stories), "done": sum(1 for t in stories if t["status"] == "done"),
                    "medianHours": round(statistics.median(cycle), 1) if cycle else None},
        "review": {"requested": len(reviews), "done": reviews_done, "rejects": len(rejects),
                   "rejectRate": round(len(rejects) / reviews_done, 2) if reviews_done else None},
        "reopened": reopened,
        "blockedEvents": blocked,
        "doneByRole": by_role,
        "lessons": {"kinds": len(kinds), "events": sum(len(k["events"]) for k in kinds.values()),
                    "resolved": sum(1 for k in kinds.values() if k["status"] == "resolved"),
                    "recurred": sorted(n for n, k in kinds.items() if k["status"] == "recurred"),
                    "top": sorted(((n, len(k["events"])) for n, k in kinds.items()), key=lambda x: -x[1])[:5],
                    "harnessTickets": {"total": len(harness_tickets),
                                       "open": sum(1 for t in harness_tickets if t["status"] in ACTIVE)}},
    }


def format_metrics(m):
    s, r, l = m["stories"], m["review"], m["lessons"]
    rate = f"{r['rejectRate'] * 100:.0f}%" if r["rejectRate"] is not None else "-"
    lines = [
        f"티켓 {m['tickets']} · 스토리 완료 {s['done']}/{s['total']}"
        + (f" (중앙값 {s['medianHours']}시간)" if s["medianHours"] is not None else ""),
        f"검수: 요청 {r['requested']} · 완료 {r['done']} · 반려(bug) {r['rejects']} · 반려율 {rate}",
        f"다시 열림 {m['reopened']} · 차단 발생 {m['blockedEvents']}",
        f"래칫: 실수 종류 {l['kinds']} · 기록 {l['events']} · 구조로 막음 {l['resolved']}"
        + (f" · 재발 {', '.join(l['recurred'])}" if l["recurred"] else "")
        + f" · 하네스 티켓 {l['harnessTickets']['open']}/{l['harnessTickets']['total']} 열림",
    ]
    if l["top"]:
        lines.append("  많은 순: " + " · ".join(f"{n} {c}" for n, c in l["top"]))
    return "\n".join(lines)


# ---------------------------------------------------------------- 가드
def _pattern_regex(pattern):
    """git pathspec glob → 정규식 (** 는 여러 단계, * 는 한 단계)."""
    out, i = "", 0
    while i < len(pattern):
        if pattern.startswith("**/", i):
            out += "(?:.*/)?"
            i += 3
        elif pattern.startswith("/**", i) and i + 3 == len(pattern):
            out += "(?:/.*)?"
            i += 3
        elif pattern.startswith("**", i):
            out += ".*"
            i += 2
        elif pattern[i] == "*":
            out += "[^/]*"
            i += 1
        elif pattern[i] == "?":
            out += "[^/]"
            i += 1
        else:
            out += re.escape(pattern[i])
            i += 1
    return re.compile("^" + out + "$")


def spec_matches(path, spec):
    """(제외 여부, 일치 여부) — config 의 git pathspec 표기(:(glob) · :(exclude) · :(exclude,glob) · 경로 접두)."""
    magic, pattern = set(), spec
    if spec.startswith(":("):
        head, _, pattern = spec[2:].partition(")")
        magic = {m.strip() for m in head.split(",")}
    exclude = "exclude" in magic
    if "glob" in magic:
        hit = bool(_pattern_regex(pattern).match(path))
    else:
        p = pattern.rstrip("/")
        hit = path == p or path.startswith(p + "/")
    return exclude, hit


def path_allowed(path, specs):
    included = any(hit for exc, hit in (spec_matches(path, s) for s in specs) if not exc)
    excluded = any(hit for exc, hit in (spec_matches(path, s) for s in specs) if exc)
    return included and not excluded


def resolve_role(st, session_id="", env=None):
    """STUDIO_ROLE 환경 변수 → launch 가 남긴 역할별 세션 ID. 모르면 None (가드하지 않음)."""
    env = os.environ if env is None else env
    role = env.get("STUDIO_ROLE", "").strip()
    if role:
        return role
    if session_id:
        state = read_json(os.path.join(st.dir, "locks", "launch.json"), {}) or {}
        for r, info in (state.get("roles") or {}).items():
            if info.get("sessionId") == session_id:
                return r
    return None


def _ignored(st, rel):
    p = subprocess.run(["git", "-C", st.root, "check-ignore", "-q", "--", rel], capture_output=True)
    return p.returncode == 0


def guard(st, file_path, role):
    """(허용 여부, 사유). 역할이 없거나 저장소 밖 · git 무시 파일이면 허용."""
    if not role or not file_path:
        return True, "역할 미상 — 가드 안 함"
    if role != DIRECTOR and role not in st.roles:
        return True, f"알 수 없는 역할 {role} — 가드 안 함"
    full = os.path.abspath(file_path if os.path.isabs(file_path) else os.path.join(st.root, file_path))
    rel = os.path.relpath(full, st.root).replace("\\", "/")
    if rel.startswith("../") or rel == "..":
        return True, "프로젝트 밖"
    if _ignored(st, rel):
        return True, "git 무시 파일"
    if path_allowed(rel, st.pathspecs(role)):
        return True, f"{role} 영역"
    owners = [r for r in list(st.roles) + [DIRECTOR] if r != role and path_allowed(rel, st.pathspecs(r))]
    owner = owners[0] if owners else "주인 없음"
    return False, (f"[studio 가드] {rel} 는 {role} 의 쓰기 영역 밖이다 (주인: {owner}). "
                   f"직접 고치지 말고 `studio.py new --from {role} --to {owners[0] if owners else DIRECTOR} "
                   f"--type task --title \"…\"` 로 요청한다. 영역 정의: studio.config.json roles.*.owns")


def guard_hook(st, payload, env=None):
    """PreToolUse 훅 입력(JSON) → (허용, 사유)."""
    tool_input = payload.get("tool_input") or {}
    path = tool_input.get("file_path") or tool_input.get("notebook_path") or ""
    role = resolve_role(st, payload.get("session_id", ""), env)
    return guard(st, path, role)


__all__ = ["add_lesson", "resolve_lesson", "load_lessons", "metrics", "format_metrics", "guard", "guard_hook",
           "resolve_role", "path_allowed", "spec_matches"]
