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
    ".agent/tools/artgen/artgen_lib/providers/*.py", ".agent/tools/setup/*.py",
    ".claude/skills/studio-*/SKILL.md", ".claude/skills/ko-art-gen/SKILL.md", ".claude/skills/ext/SKILL.md",
    ".claude/skills/ko-prereq/SKILL.md",
    "CLAUDE.md", "AGENTS.md",
]
# upgrade 가 템플릿에서 가져오는 범위 (도구 · 스튜디오 스킬 · 관련 워크플로 · 외부 카탈로그 진입)
# 외부 카탈로그 미러(.agent/marketing · .agent/gamedev)는 크기가 커서 넣지 않는다 — 필요하면 sync-catalog.py --root.
# 비상업 번들(.agent/gamedesign · .agent/gdpractice)은 절대 넣지 않는다 (사용자가 직접 받음).
# .agent/android 는 작아서(약 0.5MB) 넣는다 — prereq 의 Android 점검과 dev 스킬 맵이 이 미러를 본다
UPGRADE_TREES = [".agent/tools/studio", ".agent/tools/artgen", ".agent/tools/setup", ".agent/tools/lint", ".agent/tools/design",
                 ".agent/android",
                 ".claude/skills/studio-join", ".claude/skills/studio-status", ".claude/skills/studio-ticket",
                 ".claude/skills/studio-director",
                 ".claude/skills/ko-art-gen", ".claude/skills/ko-prereq", ".claude/skills/ko-code-review",
                 ".claude/skills/ko-diagnose", ".claude/skills/ko-tdd", ".claude/skills/ko-grill",
                 ".claude/skills/ko-agent-retro", ".claude/skills/ko-setup-engine",
                 ".claude/skills/ko-design-decision", ".claude/skills/ko-design-graph", ".claude/skills/ko-balance-sim",
                 ".claude/skills/ko-narrative-lint", ".claude/skills/ko-data-schema", ".claude/skills/ko-content-pattern",
                 ".claude/skills/ext", ".agent/catalogs"]
UPGRADE_FILES = [".agent/workflows/studio-join.md", ".agent/workflows/ko-art-gen.md", ".agent/workflows/ext.md",
                 ".agent/workflows/ko-prereq.md",
                 ".claude/statusline.sh", ".claude/hooks/studio-pause-notice.sh", ".claude/hooks/studio-write-guard.sh",
                 ".claude/hooks/validate-commit.sh", ".claude/hooks/validate-lint.sh", ".claude/hooks/yaml-helper.sh",
                 ".claude/docs/engine-layers.md"]
# 프레임워크 범위 — 상류 Game-Studios(v1.2.0~) · 템플릿 공용 자산. 템플릿의 git 추적 파일만 가져온다 (로컬 잔재 제외).
# 이것이 없으면 새 ko-* 스킬이 의존하는 .claude/scripts · 엔진 레퍼런스 · GS 스킬이 빠진 채 반쯤 깨진다.
FRAMEWORK_TREES = [".claude/skills", ".claude/agents", ".claude/scripts", ".claude/rules", ".claude/docs",
                   ".claude/hooks", ".agent/workflows", "docs/engine-reference"]
FRAMEWORK_FILES = [".agent/VERSION", "docs/CLAUDE.md", "design/CLAUDE.md", "src/CLAUDE.md",
                   "docs/COLLABORATIVE-DESIGN-PRINCIPLE.md", "docs/WORKFLOW-GUIDE.md", "docs/skill-flow-diagrams.md",
                   "production/.gdignore"]
# 프로젝트가 채우는 데이터 — 없을 때만 씨앗으로 넣는다
SEED_FILES = ["project.yaml", "docs/registry/architecture.yaml", "docs/architecture/tr-registry.yaml",
              "design/registry/entities.yaml"]
# 프로젝트가 고쳐 쓴 파일 — 덮어쓰지 않는다. kept: 프로젝트 값이 정본 / manual: 템플릿과 다르면 직접 병합하라고 알린다
PROJECT_OWNED = {".claude/docs/technical-preferences.md": "kept",
                 ".claude/rules/gameplay-code.md": "manual", ".claude/rules/doc-writing.md": "manual"}
# 엔진 전용 — 프로젝트 엔진이 다르면 가져오지 않는다 (install.ps1 의 제외 규칙과 같다)
ENGINE_ONLY = {
    "unity": [".claude/skills/sf-*", ".agent/skills/*", ".agent/tools/lint/*", ".claude/docs/mcp-unity-guide.md",
              ".claude/docs/editor-automation-decision.md", "docs/engine-reference/unity/*"],
    "godot": ["src/CLAUDE.md", "src/.gitkeep", "production/.gdignore", "docs/engine-reference/godot/*"],
    "unreal": ["docs/engine-reference/unreal/*"],
}
# 템플릿에서 사라진 파일 — 프로젝트에 남아 있으면 지우고, 그 훅의 settings.json 등록도 지운다
OBSOLETE = [".claude/docs/gs-agent-roster.md", ".claude/docs/gs-coding-standards.md", ".claude/docs/gs-coordination-rules.md",
            ".claude/docs/gs-hooks-reference.md", ".claude/docs/gs-skills-reference.md", ".claude/docs/gs-workflow-catalog.yaml",
            ".claude/hooks/post-compact.sh"]
# 스튜디오 훅 등록 — settings.json 은 프로젝트 것을 덮지 않고, 빠진 등록만 더한다 (이벤트, matcher, command)
STUDIO_HOOKS = [("PreToolUse", "Write|Edit|MultiEdit|NotebookEdit", "bash .claude/hooks/studio-write-guard.sh"),
                ("PostToolUse", "", "bash .claude/hooks/studio-pause-notice.sh"),
                # 엔진별 정적 검사 — 상류 validate-commit.sh 에서 unity_lint 연동이 빠져 별도 훅으로 옮겼다
                ("PreToolUse", "Bash", "bash .claude/hooks/validate-lint.sh")]
# 프로젝트마다 치환된 정본 문서는 통째로 바꾸지 않고, 템플릿에 새로 생긴 절만 끼워 넣는다 (파일, 절 머리, 앞에 둘 절 머리)
SECTION_INSERTS = [("AGENTS.md", "## §3-1.", "## §4."),
                   ("CLAUDE.md", "## Engine Version Reference", "## §7."),
                   ("CLAUDE.md", "## 상류 GS 기준 문서", "## §7.")]
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
def _engine_of(st):
    """업그레이드 대상 엔진. 표지 파일이 없으면 Unity 로 본다 (엔진 중립 이전 템플릿은 Unity 전용이었다)."""
    return st.engine or "unity", st.engine is None


def _engine_skip(rel, engine):
    return any(fnmatch.fnmatch(rel, pat) for eng, pats in ENGINE_ONLY.items() if eng != engine for pat in pats)


def _template_tracked(template, paths):
    """템플릿의 git 추적 파일 (paths 아래). git 저장소가 아니면 None."""
    p = subprocess.run(["git", "-C", template, "ls-files", "-z", "--", *paths], capture_output=True, text=True,
                       encoding="utf-8")
    if p.returncode != 0:
        return None
    return sorted({_rel(f) for f in p.stdout.split("\0") if f})


def _template_files(template):
    trees = UPGRADE_TREES + FRAMEWORK_TREES
    tracked = _template_tracked(template, trees + UPGRADE_FILES + FRAMEWORK_FILES)
    if tracked is not None:
        return [f for f in tracked if not fnmatch.fnmatch(os.path.basename(f), "*.local.json")
                and not any(s in f.split("/") for s in SKIP_NAMES)]
    files = []
    for tree in trees:
        base = os.path.join(template, tree)
        for dirpath, dirnames, filenames in os.walk(base):
            dirnames[:] = [d for d in dirnames if d not in SKIP_NAMES]
            for n in filenames:
                if fnmatch.fnmatch(n, "*.local.json"):
                    continue  # 머신별 설정은 템플릿에서 가져오지 않는다
                files.append(_rel(os.path.relpath(os.path.join(dirpath, n), template)))
    files += [f for f in UPGRADE_FILES + FRAMEWORK_FILES if os.path.isfile(os.path.join(template, f))]
    return sorted(set(files))


def _hook_key(cmd):
    """등록 비교 키 — 훅 스크립트 파일 이름. 'bash .claude/hooks/x.sh' 와 'bash "$CLAUDE_PROJECT_DIR/.claude/hooks/x.sh"' 는 같다."""
    m = re.findall(r"[\w.-]+\.(?:sh|py)", cmd or "")
    return m[-1] if m else (cmd or "")


def _template_hooks(template):
    s = read_json(os.path.join(template, ".claude", "settings.json"), {}) or {}
    out = [(ev, e.get("matcher", ""), h.get("command"), h.get("timeout", 15))
           for ev, entries in (s.get("hooks") or {}).items() for e in entries for h in e.get("hooks", [])]
    return out + [(ev, m, cmd, 15) for ev, m, cmd in STUDIO_HOOKS]


def _settings_patch(st, template=None):
    """프로젝트 settings.json 에 빠진 훅 등록 · deny 권한, 사라진 훅의 등록 — 프로젝트 값은 지우지 않는다."""
    settings = read_json(os.path.join(st.root, ".claude", "settings.json"), {}) or {}
    hooks = settings.get("hooks") or {}
    have = {(ev, _hook_key(h.get("command"))) for ev, entries in hooks.items() for e in entries for h in e.get("hooks", [])}
    obsolete = {os.path.basename(f) for f in OBSOLETE if f.startswith(".claude/hooks/")}
    add, seen = [], set()
    for ev, m, cmd, timeout in (_template_hooks(template) if template else
                                [(ev, m, cmd, 15) for ev, m, cmd in STUDIO_HOOKS]):
        key = (ev, _hook_key(cmd))
        if key not in have and key not in seen and key[1] not in obsolete:
            seen.add(key)
            add.append((ev, m, cmd, timeout))
    remove = sorted({f"{ev} {h.get('command')}" for ev, entries in hooks.items() for e in entries
                     for h in e.get("hooks", []) if _hook_key(h.get("command")) in obsolete})
    deny_add = []
    if template:
        tpl_deny = ((read_json(os.path.join(template, ".claude", "settings.json"), {}) or {}).get("permissions") or {}).get("deny", [])
        mine = set((settings.get("permissions") or {}).get("deny", []))
        deny_add = [d for d in tpl_deny if d not in mine]
    return {"add": add, "remove": remove, "denyAdd": deny_add}


def _missing_hooks(st):
    """(호환) 스튜디오 훅만 — 예전 호출부용."""
    return [(ev, m, cmd) for ev, m, cmd, _t in _settings_patch(st)["add"]]


def _apply_settings_patch(st, patch):
    path = os.path.join(st.root, ".claude", "settings.json")
    settings = read_json(path, {}) or {}
    hooks = settings.setdefault("hooks", {})
    obsolete = {os.path.basename(f) for f in OBSOLETE if f.startswith(".claude/hooks/")}
    for ev in list(hooks):
        kept = []
        for e in hooks[ev]:
            e = dict(e, hooks=[h for h in e.get("hooks", []) if _hook_key(h.get("command")) not in obsolete])
            if e["hooks"]:
                kept.append(e)
        if kept:
            hooks[ev] = kept
        else:
            del hooks[ev]
    for ev, matcher, cmd, timeout in patch["add"]:
        hooks.setdefault(ev, []).append({"matcher": matcher, "hooks": [{"type": "command", "command": cmd, "timeout": timeout}]})
    if patch["denyAdd"]:
        perms = settings.setdefault("permissions", {})
        perms["deny"] = list(perms.get("deny", [])) + patch["denyAdd"]
    write_json(path, settings)


def _add_hooks(st, missing):
    """(호환) 예전 호출부용."""
    _apply_settings_patch(st, {"add": [(ev, m, cmd, 15) for ev, m, cmd in missing], "remove": [], "denyAdd": []})


def _section(text, head):
    """'## §3-1.' 로 시작하는 절 — 다음 '## ' 머리 직전까지 (끝의 구분선 포함)."""
    start = text.find("\n" + head)
    if start < 0:
        return None
    end = text.find("\n## ", start + 1)
    return text[start + 1:end + 1 if end >= 0 else len(text)]


def _missing_sections(st, template):
    out = []
    for rel, head, before in SECTION_INSERTS:
        try:
            with open(os.path.join(template, rel), encoding="utf-8") as f:
                tpl = f.read()
            with open(os.path.join(st.root, rel), encoding="utf-8") as f:
                mine = f.read()
        except OSError:
            continue
        block = _section(tpl, head)
        if block and ("\n" + head) not in mine and ("\n" + before) in mine:
            out.append((rel, block, head))
    return out


def _insert_section(st, rel, block, engine=None):
    path = os.path.join(st.root, rel)
    with open(path, encoding="utf-8") as f:
        mine = f.read()
    for _rel, head, before in SECTION_INSERTS:
        if _rel == rel and ("\n" + before) in mine:
            i = mine.find("\n" + before) + 1
            mine = mine[:i] + block + mine[i:]
            break
    if engine and "@docs/engine-reference/" in block:
        mine = re.sub(r"(?m)^@docs/engine-reference/[a-z]+/VERSION\.md", f"@docs/engine-reference/{engine}/VERSION.md", mine)
    with open(path, "w", encoding="utf-8", newline="\n") as f:
        f.write(mine)


def upgrade(st, template, by=DIRECTOR, dry_run=False):
    template = os.path.abspath(template)
    if not os.path.isfile(os.path.join(template, ".agent", "tools", "studio", "studio.py")):
        raise StudioError(f"템플릿 저장소가 아님 (.agent/tools/studio/studio.py 없음): {template}")
    if os.path.samefile(template, st.root):
        raise StudioError("템플릿과 대상이 같은 폴더")
    engine, guessed = _engine_of(st)
    version = ""
    try:
        with open(os.path.join(template, ".agent", "VERSION"), encoding="utf-8") as f:
            version = f.read().strip()
    except OSError:
        pass
    plan = {"replace": [], "add": [], "merge": [], "unchanged": 0, "seed": [], "manual": [], "kept": [],
            "obsolete": [], "skippedByEngine": [], "engine": engine, "templateVersion": version or "unknown"}
    if guessed:
        plan["engineNote"] = "엔진 표지 파일 · project.yaml engine.name 이 없어 Unity 로 보고 진행"
    merged = {}
    for rel in _template_files(template):
        src, dst = os.path.join(template, rel), os.path.join(st.root, rel)
        if _engine_skip(rel, engine):
            plan["skippedByEngine"].append(rel)
            continue
        if rel in PROJECT_OWNED and os.path.isfile(dst):
            if PROJECT_OWNED[rel] == "kept":
                plan["kept"].append(rel)
            elif _hash(src) != _hash(dst):
                plan["manual"].append(rel)
            else:
                plan["unchanged"] += 1
            continue
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
    seeds_tracked = _template_tracked(template, SEED_FILES)
    for rel in (seeds_tracked if seeds_tracked is not None else
                [f for f in SEED_FILES if os.path.isfile(os.path.join(template, f))]):
        if not os.path.exists(os.path.join(st.root, rel)):
            plan["seed"].append(rel)
    tpl_files = set(_template_files(template))
    plan["obsolete"] = [f for f in OBSOLETE if f not in tpl_files and os.path.isfile(os.path.join(st.root, f))]
    settings_patch = _settings_patch(st, template)
    if settings_patch["add"] or settings_patch["remove"] or settings_patch["denyAdd"]:
        plan["merge"].append({"file": ".claude/settings.json", "newTopLevelKeys": [],
                              "hooks": [f"{ev} {cmd}" for ev, _m, cmd, _t in settings_patch["add"]],
                              "hooksRemoved": settings_patch["remove"], "denyAdded": settings_patch["denyAdd"]})
    sections = _missing_sections(st, template)
    for rel, _text, head_line in sections:
        plan["merge"].append({"file": rel, "newTopLevelKeys": [], "section": head_line})
    head = subprocess.run(["git", "-C", template, "rev-parse", "--short", "HEAD"], capture_output=True, text=True,
                          encoding="utf-8")
    plan["templateRev"] = head.stdout.strip() or "unknown"
    dirty = subprocess.run(["git", "-C", template, "status", "--porcelain", "--", *UPGRADE_TREES, *UPGRADE_FILES,
                            *FRAMEWORK_TREES, *FRAMEWORK_FILES], capture_output=True, text=True, encoding="utf-8")
    if dirty.stdout.strip():
        plan["templateRev"] += "+uncommitted"  # 커밋 전 템플릿에서 가져왔음을 기록 (출처 추적)
    plan["dryRun"] = dry_run
    touched = plan["replace"] + plan["add"] + plan["seed"] + plan["obsolete"] + [m["file"] for m in plan["merge"]]
    if dry_run or not touched:
        return plan

    for rel in plan["replace"] + plan["add"] + plan["seed"]:
        dst = os.path.join(st.root, rel)
        os.makedirs(os.path.dirname(dst), exist_ok=True)
        shutil.copyfile(os.path.join(template, rel), dst)
    for rel in plan["obsolete"]:
        os.remove(os.path.join(st.root, rel))
    for rel, data in merged.items():
        write_json(os.path.join(st.root, rel), data)
    if settings_patch["add"] or settings_patch["remove"] or settings_patch["denyAdd"]:
        _apply_settings_patch(st, settings_patch)
    for rel, text, _head in sections:
        _insert_section(st, rel, text, engine)

    note = (f"템플릿 업그레이드 {plan['templateVersion']} ({plan['templateRev']}) — 교체 {len(plan['replace'])} · "
            f"추가 {len(plan['add'])} · 씨앗 {len(plan['seed'])} · 병합 {len(plan['merge'])} · 정리 {len(plan['obsolete'])}")
    protocol_ack(st, by, note)
    body = (f"{note}\n\n바뀐 파일:\n" + "\n".join(f"- {f}" for f in touched)
            + ("\n\n**직접 병합 필요 (덮어쓰지 않음):** " + ", ".join(plan["manual"]) if plan["manual"] else "")
            + "\n\n**할 일:** 역할 헌장 · README · 업무 루프 프롬프트를 다시 읽고 이어서 일한다. 훅 등록이 바뀌었으면 "
              "세션을 다시 띄워야 적용된다. 이 변경은 디렉터가 upgrade 로 적용한 것이다 (수상한 변경이 아님).")
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
