"""studio 단위 테스트 — python -m pytest .agent/tools/studio/tests -q"""
import json
import os
import subprocess
import sys

import pytest

TOOL_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, TOOL_DIR)

import studio as S  # noqa: E402


@pytest.fixture
def st(tmp_path):
    return S.Studio(str(tmp_path), S.load_config())


def _touch(root, rel, text="x"):
    path = os.path.join(root, *rel.split("/"))
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        f.write(text)


# ---- 티켓 ----
def test_ticket_new_roundtrip_preserves_fields(st):
    t = st.new_ticket("planning", "art", "asset-request", "전투 VFX 4종", "본문: 콜론, 쉼표 포함",
                      refs=["design/assets/specs/combat-assets.md"])
    loaded = st.load_ticket(t["id"])
    assert loaded["id"] == "T-0001"
    assert loaded["title"] == "전투 VFX 4종"
    assert loaded["refs"] == ["design/assets/specs/combat-assets.md"]
    assert loaded["body"] == "본문: 콜론, 쉼표 포함"
    assert loaded["status"] == "open"


def test_ticket_ids_are_sequential_and_skip_reserved(st):
    st.new_ticket("planning", "art", "task", "a")
    os.makedirs(st.tickets_dir, exist_ok=True)
    open(os.path.join(st.tickets_dir, "T-0002.md"), "w").close()  # 다른 세션이 예약만 한 상태
    t = st.new_ticket("planning", "dev", "task", "b")
    assert t["id"] == "T-0003"
    assert [x["id"] for x in st.tickets()] == ["T-0001", "T-0003"]


@pytest.mark.parametrize("kwargs, needle", [
    (dict(sender="planning", to="planning", ttype="task", title="x"), "자기 자신"),
    (dict(sender="planning", to="qa", ttype="task", title="x"), "역할"),
    (dict(sender="planning", to="art", ttype="memo", title="x"), "type"),
    (dict(sender="planning", to="art", ttype="task", title="두\n줄"), "title"),
    (dict(sender="planning", to="art", ttype="task", title="x", gate="G9"), "게이트"),
    (dict(sender="planning", to="art", ttype="task", title="x", depends=["T-0099"]), "T-0099"),
])
def test_ticket_new_invalid_input_rejected(st, kwargs, needle):
    with pytest.raises(S.StudioError, match=needle):
        st.new_ticket(**kwargs)


def test_ticket_update_appends_thread_and_reassigns(st):
    t = st.new_ticket("dev", "planning", "question", "점프 높이 단위?")
    st.update_ticket(t["id"], "planning", note="미터 단위, GDD §3 갱신함", to="dev")
    loaded = st.load_ticket(t["id"])
    assert loaded["to"] == "dev"
    assert "담당 planning→dev" in loaded["thread"][0]
    assert "미터 단위" in loaded["thread"][0]


# ---- 착수 조건: 게이트 · 의존 ----
def test_ticket_gated_cannot_start_until_gate_approved(st, tmp_path):
    t = st.new_ticket("planning", "art", "asset-request", "양산", gate="G2")
    with pytest.raises(S.StudioError, match="G2"):
        st.update_ticket(t["id"], "art", status="in-progress")
    for a in st.gate("G2")["artifacts"]:
        _touch(str(tmp_path), a)
    st.set_gate("G2", "requested", "planning")
    st.set_gate("G2", "approved", "director")
    assert st.update_ticket(t["id"], "art", status="in-progress")["status"] == "in-progress"


def test_ticket_dependency_blocks_until_done(st):
    a = st.new_ticket("planning", "art", "asset-request", "에셋")
    b = st.new_ticket("planning", "dev", "story", "배치", depends=[a["id"]])
    assert st.readiness(st.load_ticket(b["id"]))[0] is False
    st.update_ticket(a["id"], "art", status="done")
    assert st.readiness(st.load_ticket(b["id"]))[0] is True


def test_inbox_orders_in_progress_then_ready_then_waiting(st):
    gated = st.new_ticket("planning", "dev", "story", "게이트 대기", gate="G3", priority="P0")
    low = st.new_ticket("planning", "dev", "task", "낮음", priority="P2")
    high = st.new_ticket("planning", "dev", "task", "높음", priority="P0")
    st.update_ticket(low["id"], "dev", status="in-progress")
    assert [r["id"] for r in st.inbox("dev")] == [low["id"], high["id"], gated["id"]]


# ---- 게이트 ----
def test_gate_request_requires_artifacts(st):
    with pytest.raises(S.StudioError, match="산출물 누락"):
        st.set_gate("G1", "requested", "planning")


def test_gate_only_director_can_approve(st, tmp_path):
    for a in st.gate("G1")["artifacts"]:
        _touch(str(tmp_path), a)
    st.set_gate("G1", "requested", "planning")
    with pytest.raises(S.StudioError, match="director"):
        st.set_gate("G1", "approved", "planning")
    g = st.set_gate("G1", "approved", "director", "좋음")
    assert g["status"] == "approved" and g["history"][-1]["note"] == "좋음"


def test_gate_g2_artifacts_follow_art_mode(tmp_path):
    cfg = S.load_config()
    assert "design/assets/requests/_style-tokens.json" in S.Studio(str(tmp_path), cfg).gate("G2")["artifacts"]
    cfg["artMode"] = "human"
    human = S.Studio(str(tmp_path), cfg).gate("G2")["artifacts"]
    assert "design/art/art-direction-brief.md" in human
    assert "design/assets/requests/_style-tokens.json" not in human


def test_art_mode_invalid_value_rejected(tmp_path):
    cfg = S.load_config()
    cfg["artMode"] = "robot"
    with pytest.raises(S.StudioError, match="artMode"):
        S.Studio(str(tmp_path), cfg).status()


def test_gate_add_custom_milestone(st):
    g = st.add_gate("M1", "버티컬 슬라이스", "planning", [], "M2 착수")
    assert g["status"] == "pending"
    with pytest.raises(S.StudioError, match="이미"):
        st.add_gate("M1", "중복", "planning", [], "")


# ---- 현황 · 로스터 ----
def test_status_counts_director_queue_and_roster(st):
    st.join("art", "unitygame-a1")
    st.new_ticket("art", "director", "question", "픽셀아트 vs 셀셰이딩?")
    s = st.status()
    assert s["roster"]["art"]["session"] == "unitygame-a1"
    assert s["directorQueue"][0]["title"] == "픽셀아트 vs 셀셰이딩?"
    assert s["roles"]["director"]["open"] == 1


def test_pause_resume_reflected_in_status(st):
    st.set_paused(True, "방향 재검토")
    assert "방향 재검토" in st.status()["paused"]
    st.set_paused(False)
    assert st.status()["paused"] is None


# ---- 커밋: 역할 쓰기 영역만 ----
@pytest.fixture
def repo(tmp_path):
    root = str(tmp_path)
    for args in (["init", "-q"], ["config", "user.email", "t@t"], ["config", "user.name", "t"],
                 ["config", "core.autocrlf", "false"]):
        subprocess.run(["git", "-C", root, *args], check=True)
    for rel in ("Assets/MyGame/Art/vfx.png", "Assets/MyGame/Art/vfx.png.meta", "Assets/MyGame/Scripts/Player.cs",
                "design/gdd/game-concept.md", "design/assets/requests/ASSET-001.json", "production/studio/roster.json",
                ".claude/docs/technical-preferences.md", "docs/architecture/adr-0001.md", "production/studio/PAUSED"):
        _touch(root, rel)
    return S.Studio(root, S.load_config())


def test_commit_art_includes_only_art_and_shared_paths(repo):
    r = repo.commit("art", "[studio:art] 에셋")
    assert r["committed"]
    assert r["files"] == ["Assets/MyGame/Art/vfx.png", "Assets/MyGame/Art/vfx.png.meta",
                          "design/assets/requests/ASSET-001.json", "production/studio/roster.json"]
    left = subprocess.run(["git", "-C", repo.root, "status", "--porcelain", "-uall"], capture_output=True, text=True).stdout
    assert "Player.cs" in left and "game-concept.md" in left


def test_commit_dev_excludes_art_folder(repo):
    files = repo.commit("dev", "x", dry_run=True)["files"]
    assert "Assets/MyGame/Scripts/Player.cs" in files
    assert not any("/Art/" in f for f in files)


def test_commit_dev_includes_tech_setup_outputs(repo):
    # 리허설 T-0006 회귀: /setup-engine · /create-architecture 산출물이 어느 역할에도 없어 커밋되지 않았음
    files = repo.commit("dev", "x", dry_run=True)["files"]
    assert ".claude/docs/technical-preferences.md" in files
    assert "docs/architecture/adr-0001.md" in files


def test_commit_excludes_pause_marker(repo):
    for role in ("planning", "art", "dev"):
        assert "production/studio/PAUSED" not in repo.commit(role, "x", dry_run=True)["files"]


def test_commit_planning_excludes_asset_requests(repo):
    files = repo.commit("planning", "x", dry_run=True)["files"]
    assert "design/gdd/game-concept.md" in files
    assert "design/assets/requests/ASSET-001.json" not in files


def test_commit_warns_on_missing_meta(repo):
    _touch(repo.root, "Assets/MyGame/Art/new.png")
    r = repo.commit("art", "x", dry_run=True)
    assert any("new.png" in w for w in r["warnings"])


def test_changes_cli_lists_own_area_and_in_progress(repo, capsys):
    t = repo.new_ticket("planning", "dev", "task", "중단된 작업")
    repo.update_ticket(t["id"], "dev", status="in-progress")
    assert S.main(["--root", repo.root, "--json", "changes", "dev"]) == 0
    out = json.loads(capsys.readouterr().out)
    assert "Assets/MyGame/Scripts/Player.cs" in out["files"]
    assert not any("/Art/" in f for f in out["files"])
    assert out["inProgress"] == [t["id"]]


def test_commit_only_limits_role_files_but_keeps_shared(repo):
    _touch(repo.root, "Assets/MyGame/Scripts/Enemy.cs")
    _touch(repo.root, "Assets/MyGame/Scripts/Enemy.cs.meta")
    _touch(repo.root, "ProjectSettings/EditorSettings.asset")     # Unity 가 만든 무관한 변경
    r = repo.commit("dev", "x", dry_run=True, only=["Assets/MyGame/Scripts"])
    assert "Assets/MyGame/Scripts/Player.cs" in r["files"]
    assert "ProjectSettings/EditorSettings.asset" not in r["files"]
    assert "production/studio/roster.json" in r["files"]           # 공유 영역은 항상


def test_commit_only_supports_glob(repo):
    _touch(repo.root, "Assets/MyGame/Scripts/Enemy.cs.meta")
    files = repo.commit("dev", "x", dry_run=True, only=["Assets/MyGame/Scripts/*.cs"])["files"]
    assert "Assets/MyGame/Scripts/Player.cs" in files and "Assets/MyGame/Scripts/Enemy.cs.meta" not in files


def test_commit_only_rejects_paths_outside_role(repo):
    with pytest.raises(S.StudioError, match="영역 밖"):
        repo.commit("dev", "x", dry_run=True, only=["design/gdd"])


def test_commit_only_warns_unmatched_path(repo):
    r = repo.commit("dev", "x", dry_run=True, only=["Assets/MyGame/Scripts", "Assets/Nope"])
    assert any("Assets/Nope" in w for w in r["warnings"])


def test_commit_only_really_commits_subset(repo):
    _touch(repo.root, "ProjectSettings/EditorSettings.asset")
    r = repo.commit("dev", "[studio:dev] 스크립트만", only=["Assets/MyGame/Scripts"])
    assert r["committed"]
    left = subprocess.run(["git", "-C", repo.root, "status", "--porcelain", "-uall"], capture_output=True, text=True).stdout
    assert "ProjectSettings/EditorSettings.asset" in left and "Player.cs" not in left


def test_commit_nothing_to_commit(repo):
    repo.commit("planning", "first")
    assert repo.commit("planning", "again")["committed"] is False


# ---- CLI ----
def test_cli_new_reports_notify_session(tmp_path, capsys):
    S.main(["--root", str(tmp_path), "join", "dev", "unitygame-d4"])
    capsys.readouterr()
    assert S.main(["--root", str(tmp_path), "--json", "new", "--from", "art", "--to", "dev",
                   "--type", "assets-ready", "--title", "VFX 승격 완료"]) == 0
    out = json.loads(capsys.readouterr().out)
    assert out["notifySession"] == "unitygame-d4" and out["ready"] is True
