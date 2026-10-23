"""스튜디오 유지보수 — 쓰기 영역 감사(audit) · 프로토콜 변경 기록(protocol) · 템플릿 업그레이드(upgrade).

리허설에서 확인된 문제:
  - 프로토콜 · 지침 파일(설정 · 도구 · 헌장 · CLAUDE.md)은 어느 역할에도 없어서, 바뀌어도 기록 · 커밋할 주체가 없었다.
  - 영역 밖 쓰기를 커밋 시점에야 발견해 미커밋 파일이 쌓였다.
  - 템플릿 갱신을 실행 중인 프로젝트에 직접 덮어써 디렉터 결정이 되돌려졌다.
그래서 디렉터 영역(directorOwns)을 두고, 변경을 지문으로 감지해 기록하며, 갱신은 upgrade 로만 한다.
"""
import datetime
import fnmatch
import glob
import hashlib
import json
import os
import re
import shutil
import subprocess

from studio import DIRECTOR, SYSTEM, StudioError, deep_merge, now, read_json, write_json

PROTOCOL_FILE = "protocol.json"
DEFAULT_PROTOCOL_FILES = [
    ".agent/tools/studio/*.py", ".agent/tools/studio/studio.config.json", ".agent/tools/studio/README.md",
    ".agent/tools/studio/roles/*.md", ".agent/tools/studio/prompts/*.md",
    ".agent/tools/artgen/artgen.config.json", ".agent/tools/artgen/artgen_lib/*.py",
    ".agent/tools/artgen/artgen_lib/providers/*.py",
    ".claude/skills/studio-*/SKILL.md", ".claude/skills/ko-art-gen/SKILL.md", ".claude/skills/ext/SKILL.md",
    "CLAUDE.md", "AGENTS.md",
]
# upgrade 가 템플릿에서 가져오는 범위 (도구 · 스튜디오 스킬 · 관련 워크플로 · 외부 카탈로그 진입)
# 외부 카탈로그 미러(.agent/marketing · .agent/gamedev)는 크기가 커서 넣지 않는다 — 필요하면 sync-catalog.py --root.
# 비상업 번들(.agent/gamedesign)은 절대 넣지 않는다 (사용자가 직접 받음).
UPGRADE_TREES = [".agent/tools/studio", ".agent/tools/artgen",
                 ".claude/skills/studio-join", ".claude/skills/studio-status", ".claude/skills/studio-ticket",
                 ".claude/skills/studio-director",
                 ".claude/skills/ko-art-gen",
                 ".claude/skills/ext", ".agent/catalogs"]
UPGRADE_FILES = [".agent/workflows/studio-join.md", ".agent/workflows/ko-art-gen.md", ".agent/workflows/ext.md",
                 ".claude/statusline.sh", ".claude/hooks/studio-pause-notice.sh"]
UNION_LISTS = ("directorOwns",)  # 병합 시 프로젝트 값으로 덮지 않고 템플릿 항목을 더하는 목록
# 프로젝트 값이 우선하는 깊은 병합 대상 (디렉터 결정 보존)
MERGE_JSON = [".agent/tools/studio/studio.config.json", ".agent/tools/artgen/artgen.config.json"]
SKIP_NAMES = ("__pycache__", ".pytest_cache")


def _rel(path):
    return path.replace("\\", "/")


def _hash(path):
    with open(path, "rb") as f:
        data = f.read().replace(b"\r\n", b"\n")  # 줄바꿈 변환만으로 '변경' 이 되지 않게
    return hashlib.sha256(data).hexdigest()[:16]


# ---------------------------------------------------------------- 쓰기 영역 감사
def audit(st):
    """미커밋 변경을 영역별로 분류 — 주인 없는 파일(orphans)과 역할 간 겹침(overlaps)."""
    try:
        changed = st.all_changed_files()
    except StudioError as e:  # git 저장소가 아닌 곳(초기 셋업 등) — 감사 생략
        return {"changed": 0, "orphans": [], "overlaps": {}, "error": str(e)}
    owners = {r: set(st.changed_files(r)) for r in st.roles}
    owners[DIRECTOR] = set(st.changed_files(DIRECTOR))
    shared = set(st.changed_files_for(list(st.cfg.get("shared", []))))
    allowed = st.cfg.get("allowedOverlaps", [])
    orphans, overlaps = [], {}
    for f in changed:
        who = [o for o, files in owners.items() if f in files]
        if not who and f not in shared:
            orphans.append(f)
        # 공유 영역은 모든 역할 집합에 포함되므로 겹침 판정에서 제외
        exclusive = [o for o in who if f not in shared]
        if len(exclusive) > 1 and not any(f == a or f.startswith(a.rstrip("/") + "/") for a in allowed):
            overlaps[f] = exclusive
    return {"changed": len(changed), "orphans": orphans, "overlaps": overlaps}


# ---------------------------------------------------------------- 프로토콜 지문
def _protocol_paths(st):
    out = set()
    for pattern in st.cfg.get("protocolFiles", DEFAULT_PROTOCOL_FILES):
        for p in glob.glob(os.path.join(st.root, pattern)):
            if os.path.isfile(p) and not any(s in p for s in SKIP_NAMES):
                out.add(_rel(os.path.relpath(p, st.root)))
    return sorted(out)


def _snapshot(st):
    return {p: _hash(os.path.join(st.root, p)) for p in _protocol_paths(st)}


def protocol_state(st):
    path = os.path.join(st.dir, PROTOCOL_FILE)
    rec = read_json(path)
    cur = _snapshot(st)
    if rec is None:  # 첫 사용 — 현재 상태를 기준선으로 (설치 직후)
        rec = {"baseline": cur, "ackedAt": now(), "ackedBy": "init", "note": "최초 기준선"}
        write_json(path, rec)
    base = rec["baseline"]
    changed = sorted(p for p in cur if p in base and cur[p] != base[p])
    added = sorted(p for p in cur if p not in base)
    removed = sorted(p for p in base if p not in cur)
    return {"changed": changed, "added": added, "removed": removed,
            "dirty": bool(changed or added or removed),
            "ackedAt": rec.get("ackedAt"), "ackedBy": rec.get("ackedBy"), "note": rec.get("note", "")}


def protocol_ack(st, by, note=""):
    state = protocol_state(st)
    rec = {"baseline": _snapshot(st), "ackedAt": now(), "ackedBy": by, "note": note,
           "previous": {k: state[k] for k in ("changed", "added", "removed")}}
    write_json(os.path.join(st.dir, PROTOCOL_FILE), rec)
    st.log("protocol.ack", by=by, note=note, changed=len(state["changed"]), added=len(state["added"]),
           removed=len(state["removed"]))
    return dict(state, ackedBy=by, note=note)


# ---------------------------------------------------------------- 템플릿 업그레이드
def _template_files(template):
    files = []
    for tree in UPGRADE_TREES:
        base = os.path.join(template, tree)
        for dirpath, dirnames, filenames in os.walk(base):
            dirnames[:] = [d for d in dirnames if d not in SKIP_NAMES]
            for n in filenames:
                if fnmatch.fnmatch(n, "*.local.json"):
                    continue  # 머신별 설정은 템플릿에서 가져오지 않는다
                files.append(_rel(os.path.relpath(os.path.join(dirpath, n), template)))
    files += [f for f in UPGRADE_FILES if os.path.isfile(os.path.join(template, f))]
    return sorted(files)


def upgrade(st, template, by=DIRECTOR, dry_run=False):
    template = os.path.abspath(template)
    if not os.path.isfile(os.path.join(template, ".agent", "tools", "studio", "studio.py")):
        raise StudioError(f"템플릿 저장소가 아님 (.agent/tools/studio/studio.py 없음): {template}")
    if os.path.samefile(template, st.root):
        raise StudioError("템플릿과 대상이 같은 폴더")
    plan = {"replace": [], "add": [], "merge": [], "unchanged": 0}
    merged = {}
    for rel in _template_files(template):
        src, dst = os.path.join(template, rel), os.path.join(st.root, rel)
        if rel in MERGE_JSON and os.path.isfile(dst):
            tpl, mine = read_json(src), read_json(dst)
            result = deep_merge(tpl, mine)  # 템플릿 기반 + 프로젝트 값 우선 → 디렉터 결정 보존, 새 키만 추가
            # 디렉터 영역 목록은 합집합 — 템플릿이 새 도구 폴더를 추가하면 기존 프로젝트에서도 주인 없는 파일이 되지 않게
            for key in UNION_LISTS:
                if isinstance(tpl.get(key), list) and isinstance(mine.get(key), list):
                    result[key] = mine[key] + [x for x in tpl[key] if x not in mine[key]]
            new_keys = sorted(set(result) - set(mine))
            if result != mine:
                plan["merge"].append({"file": rel, "newTopLevelKeys": new_keys})
                merged[rel] = result
            else:
                plan["unchanged"] += 1
            continue
        if not os.path.isfile(dst):
            plan["add"].append(rel)
        elif _hash(src) != _hash(dst):
            plan["replace"].append(rel)
        else:
            plan["unchanged"] += 1
    head = subprocess.run(["git", "-C", template, "rev-parse", "--short", "HEAD"], capture_output=True, text=True)
    plan["templateRev"] = head.stdout.strip() or "unknown"
    dirty = subprocess.run(["git", "-C", template, "status", "--porcelain", "--", *UPGRADE_TREES, *UPGRADE_FILES],
                           capture_output=True, text=True)
    if dirty.stdout.strip():
        plan["templateRev"] += "+uncommitted"  # 커밋 전 템플릿에서 가져왔음을 기록 (출처 추적)
    plan["dryRun"] = dry_run
    touched = plan["replace"] + plan["add"] + [m["file"] for m in plan["merge"]]
    if dry_run or not touched:
        return plan

    for rel in plan["replace"] + plan["add"]:
        dst = os.path.join(st.root, rel)
        os.makedirs(os.path.dirname(dst), exist_ok=True)
        shutil.copyfile(os.path.join(template, rel), dst)
    for rel, data in merged.items():
        write_json(os.path.join(st.root, rel), data)

    note = f"템플릿 업그레이드 {plan['templateRev']} — 교체 {len(plan['replace'])} · 추가 {len(plan['add'])} · 병합 {len(plan['merge'])}"
    protocol_ack(st, by, note)
    body = (f"{note}\n\n바뀐 파일:\n" + "\n".join(f"- {f}" for f in touched)
            + "\n\n**할 일:** 역할 헌장 · README · 업무 루프 프롬프트를 다시 읽고 이어서 일한다. "
              "이 변경은 디렉터가 upgrade 로 적용한 것이다 (수상한 변경이 아님).")
    plan["tickets"] = [st.new_ticket(by, role, "info", f"프로토콜 갱신 ({plan['templateRev']})", body, priority="P2")["id"]
                       for role in st.roles]
    st.log("upgrade", template=template, rev=plan["templateRev"], files=len(touched))
    return plan


# ---------------------------------------------------------------- Claude 주간 사용량 가드
# 세 세션은 같은 계정의 한도를 함께 쓴다. statusLine(.claude/statusline.sh)이 받은 rate_limits 를
# 여기로 넘기면, 주간 사용량이 임계값을 넘는 순간 전체를 정지시키고 인계 기록을 남긴다.
USAGE_DEFAULTS = {"enabled": True, "weeklyPausePercent": 90}
HANDOFF_FILE = "HANDOFF.md"


def usage_settings(st):
    s = dict(USAGE_DEFAULTS)
    s.update(st.cfg.get("usageGuard", {}))
    return s


def _usage_path(st):
    return os.path.join(st.dir, "locks", "usage.json")  # 런타임 상태 (git 무시)


def usage_state(st):
    return read_json(_usage_path(st), {})


def _claim_trigger(st, window):
    """리셋 주기마다 한 번만 발동 — 여러 세션의 statusLine 이 동시에 90% 를 봐도 하나만 통과한다."""
    path = os.path.join(st.dir, "locks", "usage-trigger-" + (re.sub(r"[^0-9A-Za-z]", "_", window) or "none"))
    os.makedirs(os.path.dirname(path), exist_ok=True)
    try:
        os.close(os.open(path, os.O_CREAT | os.O_EXCL | os.O_WRONLY))
        return True
    except FileExistsError:
        return False


def fmt_epoch(epoch):
    try:
        return datetime.datetime.fromtimestamp(float(epoch), datetime.timezone.utc).astimezone().strftime("%Y-%m-%d %H:%M")
    except (TypeError, ValueError, OverflowError, OSError):
        return "알 수 없음"


def parse_statusline(data):
    """statusLine stdin JSON → (주간 %, 리셋 epoch). 구독 플랜이 아니거나 첫 응답 전이면 (None, None)."""
    week = ((data or {}).get("rate_limits") or {}).get("seven_day") or {}
    pct = week.get("used_percentage")
    return (float(pct) if pct is not None else None), week.get("resets_at")


def record_usage(st, percent, resets_at=None, source="statusline"):
    """사용량을 기록하고, 임계값 이상이면 리셋 주기당 한 번 정지 + 인계 기록 + 디렉터 티켓.
    디렉터가 일부러 재개한 뒤에는 같은 주기에서 다시 정지시키지 않는다."""
    if percent is None or not os.path.isdir(st.dir):
        return {"recorded": False, "triggered": False}
    cfg = usage_settings(st)
    state = usage_state(st)
    window = str(resets_at or "")
    out = {"recorded": True, "triggered": False, "percent": percent, "threshold": cfg["weeklyPausePercent"]}
    below = not (cfg["enabled"] and percent >= cfg["weeklyPausePercent"])
    if below and state.get("percent") == percent and state.get("resetsAt") == resets_at:
        # 값이 그대로면 쓰지 않는다 — statusLine 이 세션마다 1분 주기로 부르므로 느린 디스크(HDD)에서 쓰기가 쌓인다
        out["unchanged"] = True
        return out
    state.update(percent=percent, resetsAt=resets_at, at=now(), source=source)
    if cfg["enabled"] and percent >= cfg["weeklyPausePercent"] and state.get("pausedWindow") != window \
            and _claim_trigger(st, window):
        reason = (f"Claude 주간 사용량 {percent:.0f}% ≥ {cfg['weeklyPausePercent']}% — "
                  f"리셋 {fmt_epoch(resets_at)}. 인계: production/studio/{HANDOFF_FILE}")
        # statusLine 은 새 갱신이 오면 실행 중인 스크립트를 취소한다 — 정지부터 걸고 나머지를 한다
        if not st.paused():
            st.set_paused(True, reason)
        state["pausedWindow"] = window
        write_json(_usage_path(st), state)
        body = (f"{reason}\n\n전 세션 정지. 각 세션은 진행 중 티켓에 '인계:' note 를 남기고 멈춘다.\n"
                f"인계 기록: production/studio/{HANDOFF_FILE}\n\n"
                "디렉터 할 일: 사용자에게 알리고, 리셋 후 재개 시점을 정한다 (resume 은 사용자 합의).")
        t = st.new_ticket(SYSTEM, DIRECTOR, "info", f"Claude 주간 사용량 {percent:.0f}% — 전체 정지 · 인계", body,
                          priority="P0", refs=[f"production/studio/{HANDOFF_FILE}"])
        path = write_handoff(st, reason, percent, resets_at)  # 티켓 뒤에 — 디렉터 대기열에 이 티켓이 보이게
        st.log("usage.pause", percent=percent, resetsAt=resets_at, ticket=t["id"])
        out.update(triggered=True, reason=reason, handoff=path, ticket=t["id"],
                   notifySession=st.notify_session(DIRECTOR))
        return out
    write_json(_usage_path(st), state)
    return out


def write_handoff(st, reason, percent=None, resets_at=None):
    """정지 시점의 스냅샷 — 다음 세션이 이 파일 + 티켓 스레드의 '인계:' note 로 이어서 작업한다."""
    roster = st.roster()
    lines = ["# 스튜디오 인계 기록", "", f"- 정지: {now()}", f"- 사유: {reason}"]
    if percent is not None:
        lines.append(f"- Claude 주간 사용량: {percent:.0f}% (리셋 {fmt_epoch(resets_at)})")
    lines += ["", "## 이어서 하는 법", "",
              "1. 사용량이 리셋되면 각 터미널에서 `/studio-join <역할>` (디렉터는 `/studio-director`).",
              "2. 디렉터가 사용자와 합의해 `resume` 한다. 정지 중에는 새 티켓에 착수하지 않는다.",
              "3. 각 세션은 아래 진행 중 티켓부터 재개 절차로 이어 간다. 스레드의 마지막 `인계:` note 가 출발점이다.",
              "", "## 게이트", ""]
    lines += [f"- {g['id']} {g['status']} — {g['name']}" for g in st.gates()]
    lines += ["", "## 역할별 진행 상황", ""]
    try:
        shared = set(st.changed_files_for(list(st.cfg.get("shared", []))))
    except StudioError:  # git 저장소가 아님
        shared = None
    for role in st.roles:
        rows = st.inbox(role)
        lines.append(f"### {role} (세션 {roster.get(role, {}).get('session', '-')})")
        active = [r for r in rows if r["status"] in ("in-progress", "blocked")]
        waiting = [r for r in rows if r["status"] == "open"]
        for r in active:
            last = r["thread"][-1] if r["thread"] else "(note 없음)"
            lines.append(f"- {r['id']} {r['status']} {r['title']}")
            lines.append(f"  - 마지막 note: {last}")
        if waiting:
            lines.append(f"- 대기 {len(waiting)}건: " + ", ".join(r["id"] for r in waiting[:10]))
        mine = [] if shared is None else [f for f in st.changed_files(role) if f not in shared]
        if mine:
            lines.append(f"- 미커밋 변경 {len(mine)}개: " + ", ".join(mine[:15]) + (" …" if len(mine) > 15 else ""))
        if not (active or waiting or mine):
            lines.append("- 없음")
        lines.append("")
    queue = st.inbox(DIRECTOR)
    lines += ["## 디렉터 판단 대기", ""]
    lines += [f"- {t['id']} {t['type']} ({t['from']}) {t['title']}" for t in queue] or ["- 없음"]
    os.makedirs(st.dir, exist_ok=True)
    path = os.path.join(st.dir, HANDOFF_FILE)
    with open(path, "w", encoding="utf-8", newline="\n") as f:
        f.write("\n".join(lines) + "\n")
    st.log("handoff", reason=reason)
    return path
