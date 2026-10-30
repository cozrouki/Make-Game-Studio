"""하네스 테스트 — 래칫(lesson) · 지표(metrics) · 쓰기 가드(guard) · 업그레이드 훅/절 병합 · 커밋 검사(unity_lint)."""
import json
import os
import shutil
import subprocess
import sys

import pytest

TOOL_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
TOOLS = os.path.dirname(TOOL_DIR)
TEMPLATE = os.path.dirname(os.path.dirname(TOOLS))
sys.path.insert(0, TOOL_DIR)

import studio as S  # noqa: E402
import studio_harness as H  # noqa: E402
import studio_maint as M  # noqa: E402


def _touch(root, rel, text="x"):
    path = os.path.join(root, *rel.split("/"))
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        f.write(text)


def _git(root, *args):
    subprocess.run(["git", "-C", root, *args], check=True, capture_output=True)


@pytest.fixture
def repo(tmp_path):
    root = str(tmp_path / "proj")
    os.makedirs(root)
    for args in (["init", "-q"], ["config", "user.email", "t@t"], ["config", "user.name", "t"],
                 ["config", "core.autocrlf", "false"]):
        _git(root, *args)
    shutil.copytree(TOOL_DIR, os.path.join(root, ".agent", "tools", "studio"),
                    ignore=shutil.ignore_patterns("__pycache__", "tests"))
    _touch(root, ".gitignore", "production/session-state/\n*.local.json\n")
    _touch(root, "CLAUDE.md", "# persona\n")
    _git(root, "add", "-A")
    _git(root, "commit", "-q", "-m", "base")
    return S.Studio(root, S.load_config(os.path.join(root, ".agent", "tools", "studio")))


# ---- 래칫 ----
def test_harness_lesson_second_occurrence_opens_director_ticket(repo):
    # Arrange · Act
    first = H.add_lesson(repo, "planning", "missing-evidence", "T-0012 증거 폴더 없음", "T-0012")
    second = H.add_lesson(repo, "planning", "Missing-Evidence", "T-0015 스크린샷 빠짐", "T-0015")
    third = H.add_lesson(repo, "dev", "missing-evidence", "또", "T-0016")
    # Assert
    assert first["ticket"] is None and second["ticket"]
    t = repo.load_ticket(second["ticket"])
    assert (t["to"], t["type"], t["title"]) == ("director", "task", "하네스 개선: missing-evidence")
    assert "T-0012" in t["body"] and "T-0015" in t["body"]
    assert third["ticket"] is None                                   # 열린 하네스 티켓이 있으면 또 내지 않는다


def test_harness_lesson_recurrence_after_resolve_reopens_with_threshold_one(repo):
    for i in range(2):
        H.add_lesson(repo, "dev", "update-alloc", f"리뷰 지적 {i}")
    first_ticket = H.load_lessons(repo)["kinds"]["update-alloc"]["ticket"]
    repo.update_ticket(first_ticket, "director", status="done", note="lint blocking UL002")
    H.resolve_lesson(repo, "update-alloc", "lint.config.json blocking UL002")
    r = H.add_lesson(repo, "dev", "update-alloc", "막았는데 다시")
    assert r["status"] == "recurred" and r["ticket"] and r["ticket"] != first_ticket


def test_harness_lesson_validation(repo):
    with pytest.raises(S.StudioError, match="kind"):
        H.add_lesson(repo, "dev", "Bad Kind!", "x")
    with pytest.raises(S.StudioError, match="note"):
        H.add_lesson(repo, "dev", "ok-kind", "  ")
    with pytest.raises(S.StudioError, match="director"):
        H.resolve_lesson(repo, "ok-kind", "x", by="dev")


# ---- 지표 ----
def test_harness_metrics_reject_rate_reopen_and_cycle(repo):
    s = repo.new_ticket("planning", "dev", "story", "점프")
    repo.update_ticket(s["id"], "dev", status="in-progress")
    repo.update_ticket(s["id"], "dev", status="done")
    rv = repo.new_ticket("dev", "planning", "review", "검수: 점프")
    repo.update_ticket(rv["id"], "planning", status="done")
    repo.new_ticket("planning", "dev", "bug", "점프 높이 미달")
    repo.update_ticket(s["id"], "dev", status="in-progress", note="다시 연다")
    m = H.metrics(repo)
    assert m["review"] == {"requested": 1, "done": 1, "rejects": 1, "rejectRate": 1.0}
    assert m["reopened"] == 1 and m["stories"]["total"] == 1
    assert "반려율 100%" in H.format_metrics(m)


# ---- 가드 ----
@pytest.mark.parametrize("path, spec, hit", [
    ("Assets/G/Art/a.png", ":(glob)Assets/*/Art/**", True),
    ("Assets/G/Scripts/a.cs", ":(glob)Assets/*/Art/**", False),
    ("Assets/G/Art", ":(glob)Assets/*/Art/**", True),
    ("design/gdd/x.md", "design", True),
    ("designer.md", "design", False),
    ("production/qa/qa-plan-s1-2026.md", ":(glob)production/qa/qa-plan-*.md", True),
    ("production/qa/sub/qa-plan-x.md", ":(glob)production/qa/qa-plan-*.md", False),
])
def test_harness_pathspec_matching(path, spec, hit):
    assert H.spec_matches(path, spec)[1] is hit


def test_harness_guard_blocks_other_roles_area_and_names_owner(repo):
    ok, _ = H.guard(repo, "Assets/Game/Scripts/Player.cs", "dev")
    assert ok
    ok, why = H.guard(repo, "Assets/Game/Scripts/Player.cs", "art")
    assert not ok and "주인: dev" in why and "--to dev" in why
    ok, _ = H.guard(repo, os.path.join(repo.root, "design", "gdd", "x.md"), "planning")   # 절대경로
    assert ok


def test_harness_guard_allows_ignored_shared_outside_and_unknown(repo, tmp_path):
    assert H.guard(repo, "production/session-state/active.md", "art")[0]       # git 무시
    assert H.guard(repo, "doc/work_log.md", "art")[0]                          # 공유 영역
    assert H.guard(repo, str(tmp_path / "elsewhere.txt"), "art")[0]            # 프로젝트 밖
    assert H.guard(repo, "Assets/X.cs", None)[0]                               # 역할 미상


def test_harness_guard_hook_resolves_role_from_launch_session(repo):
    os.makedirs(os.path.join(repo.dir, "locks"), exist_ok=True)
    with open(os.path.join(repo.dir, "locks", "launch.json"), "w", encoding="utf-8") as f:
        json.dump({"roles": {"art": {"sessionId": "sid-art"}}}, f)
    payload = {"session_id": "sid-art", "tool_input": {"file_path": "design/gdd/x.md"}}
    assert H.guard_hook(repo, payload, env={})[0] is False
    assert H.guard_hook(repo, dict(payload, session_id="other"), env={})[0] is True
    assert H.guard_hook(repo, payload, env={"STUDIO_ROLE": "planning"})[0] is True


def test_harness_guard_cli_exit_code(repo):
    script = os.path.join(repo.root, ".agent", "tools", "studio", "studio.py")
    blocked = subprocess.run([sys.executable, script, "--root", repo.root, "guard", "--role", "art",
                              "--file", "Assets/G/Scripts/A.cs"], capture_output=True, text=True, encoding="utf-8")
    hook = subprocess.run([sys.executable, script, "--root", repo.root, "guard", "--hook"], input="not json",
                          capture_output=True, text=True, encoding="utf-8")
    assert blocked.returncode == 2 and "쓰기 영역 밖" in blocked.stderr
    assert hook.returncode == 0                                       # 고장 난 입력은 막지 않는다


# ---- 커밋 검사 ----
def test_harness_commit_runs_unity_lint_and_blocks_on_blocking_rule(repo):
    shutil.copytree(os.path.join(TOOLS, "lint"), os.path.join(repo.root, ".agent", "tools", "lint"),
                    ignore=shutil.ignore_patterns("__pycache__", "tests"))
    _touch(repo.root, "Assets/Game/Scripts/P.cs",
           "public class P : MonoBehaviour\n{\n    void Update()\n    {\n        var rb = GetComponent<Rigidbody>();\n    }\n}\n")
    r = repo.commit("dev", "[studio:dev] P", dry_run=True)
    assert any("UL004" in w for w in r["warnings"])                  # 기본은 경고
    cfg_path = os.path.join(repo.root, ".agent", "tools", "lint", "lint.config.json")
    cfg = json.load(open(cfg_path, encoding="utf-8"))
    cfg["blocking"] = ["UL004"]
    json.dump(cfg, open(cfg_path, "w", encoding="utf-8"))
    with pytest.raises(S.StudioError, match="UL004"):
        repo.commit("dev", "[studio:dev] P", dry_run=True)


# ---- 업그레이드: 훅 등록 · 절 삽입 ----
def test_harness_upgrade_adds_missing_hooks_and_agents_section(repo, tmp_path):
    # Arrange — 프로젝트: 훅 하나만 등록돼 있고 AGENTS.md 에 §3-1 이 없다 (게임 매핑이 치환된 상태)
    _touch(repo.root, ".claude/settings.json", json.dumps({"hooks": {"PostToolUse": [
        {"matcher": "", "hooks": [{"type": "command", "command": "bash .claude/hooks/studio-pause-notice.sh"}]}]}}))
    _touch(repo.root, "AGENTS.md", "# A\n\n## §3. 표준\n- x\n\n---\n\n## §4. 실행\n| [RH2] | Rehearsal2 |\n")
    _git(repo.root, "add", "-A")
    _git(repo.root, "commit", "-q", "-m", "proj")
    # Act
    plan = M.upgrade(repo, TEMPLATE, dry_run=False)
    # Assert
    files = [m["file"] for m in plan["merge"]]
    assert ".claude/settings.json" in files and "AGENTS.md" in files
    hooks = json.load(open(os.path.join(repo.root, ".claude", "settings.json"), encoding="utf-8"))["hooks"]
    cmds = [h["command"] for es in hooks.values() for e in es for h in e["hooks"]]
    assert cmds.count("bash .claude/hooks/studio-pause-notice.sh") == 1
    assert "bash .claude/hooks/studio-write-guard.sh" in cmds
    agents = open(os.path.join(repo.root, "AGENTS.md"), encoding="utf-8").read()
    assert agents.index("## §3-1.") < agents.index("## §4.") and "| [RH2] | Rehearsal2 |" in agents
    again = M.upgrade(repo, TEMPLATE, dry_run=True)                    # 두 번째는 할 일 없음
    assert not [m for m in again["merge"] if m["file"] in (".claude/settings.json", "AGENTS.md")]


# ---- 엔진별 쓰기 영역 (studio.config.json roles.<역할>.ownsByEngine) ----
def _with_engine(repo, marker, text=""):
    _touch(repo.root, marker, text)
    return S.Studio(repo.root, repo.cfg)


def test_harness_godot_project_uses_godot_areas(repo):
    st = _with_engine(repo, "project.godot", "config_version=5\n")
    assert st.engine == "godot"
    assert H.guard(st, "src/player/player.gd", "dev")[0]
    assert H.guard(st, "project.godot", "dev")[0]
    assert H.guard(st, "assets/game/art/vfx/hit.png", "art")[0]
    ok, why = H.guard(st, "assets/game/art/vfx/hit.png", "dev")
    assert not ok and "주인: art" in why


def test_harness_unreal_project_uses_unreal_areas(repo):
    st = _with_engine(repo, "Game.uproject", "{}")
    assert st.engine == "unreal"
    assert H.guard(st, "Source/Game/Private/Hero.cpp", "dev")[0]
    assert H.guard(st, "Config/DefaultEngine.ini", "dev")[0]
    assert H.guard(st, "Content/Import/Game/VFX/hit.png", "art")[0]
    assert not H.guard(st, "Source/Game/Private/Hero.cpp", "art")[0]


def test_harness_unity_or_unknown_engine_keeps_default_areas(repo):
    assert repo.engine is None
    assert H.guard(repo, "Assets/Game/Scripts/Player.cs", "dev")[0]
    st = _with_engine(repo, "ProjectSettings/ProjectVersion.txt", "m_EditorVersion: 6000.3.1f1\n")
    assert st.engine == "unity"
    assert H.guard(st, "Assets/Game/Scripts/Player.cs", "dev")[0]


def test_harness_project_yaml_belongs_to_dev(repo):
    assert H.guard(repo, "project.yaml", "dev")[0]
    assert not H.guard(repo, "project.yaml", "planning")[0]
