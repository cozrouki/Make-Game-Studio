"""스튜디오 유지보수 — 쓰기 영역 감사(audit) · 프로토콜 변경 기록(protocol) · 템플릿 업그레이드(upgrade).

리허설에서 확인된 문제:
  - 프로토콜 · 지침 파일(설정 · 도구 · 헌장 · CLAUDE.md)은 어느 역할에도 없어서, 바뀌어도 기록 · 커밋할 주체가 없었다.
  - 영역 밖 쓰기를 커밋 시점에야 발견해 미커밋 파일이 쌓였다.
  - 템플릿 갱신을 실행 중인 프로젝트에 직접 덮어써 디렉터 결정이 되돌려졌다.
그래서 디렉터 영역(directorOwns)을 두고, 변경을 지문으로 감지해 기록하며, 갱신은 upgrade 로만 한다.
"""
import fnmatch
import glob
import hashlib
import json
import os
import shutil
import subprocess

from studio import DIRECTOR, StudioError, deep_merge, now, read_json, write_json

PROTOCOL_FILE = "protocol.json"
DEFAULT_PROTOCOL_FILES = [
    ".agent/tools/studio/*.py", ".agent/tools/studio/studio.config.json", ".agent/tools/studio/README.md",
    ".agent/tools/studio/roles/*.md", ".agent/tools/studio/prompts/*.md",
    ".agent/tools/artgen/artgen.config.json", ".agent/tools/artgen/artgen_lib/*.py",
    ".agent/tools/artgen/artgen_lib/providers/*.py",
    ".claude/skills/studio-*/SKILL.md", ".claude/skills/ko-art-gen/SKILL.md",
    "CLAUDE.md", "AGENTS.md",
]
# upgrade 가 템플릿에서 가져오는 범위 (도구 · 스튜디오 스킬 · 관련 워크플로)
UPGRADE_TREES = [".agent/tools/studio", ".agent/tools/artgen",
                 ".claude/skills/studio-join", ".claude/skills/studio-status", ".claude/skills/studio-ticket",
                 ".claude/skills/ko-art-gen"]
UPGRADE_FILES = [".agent/workflows/studio-join.md", ".agent/workflows/ko-art-gen.md"]
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
        allp = st._git("status", "--porcelain", "-z", "-uall", "--no-renames")
    except StudioError as e:  # git 저장소가 아닌 곳(초기 셋업 등) — 감사 생략
        return {"changed": 0, "orphans": [], "overlaps": {}, "error": str(e)}
    changed = sorted({e[3:] for e in allp.stdout.split("\0") if len(e) > 3})
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
