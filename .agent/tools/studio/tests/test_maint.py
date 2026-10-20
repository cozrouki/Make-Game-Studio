"""쓰기 영역 감사 · 프로토콜 변경 기록 · 템플릿 업그레이드 테스트."""
import json
import os
import shutil
import subprocess
import sys

import pytest

TOOL_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, TOOL_DIR)

import studio as S  # noqa: E402
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
    # 프로젝트에 설치된 스튜디오 도구(설정 포함)를 흉내 — protocolFiles 가 이 파일들을 본다
    shutil.copytree(TOOL_DIR, os.path.join(root, ".agent", "tools", "studio"),
                    ignore=shutil.ignore_patterns("__pycache__", "tests"))
    _touch(root, "CLAUDE.md", "# persona\n")
    _git(root, "add", "-A")
    _git(root, "commit", "-q", "-m", "base")
    return S.Studio(root, S.load_config(os.path.join(root, ".agent", "tools", "studio")))


# ---- A. 디렉터 영역 ----
def test_director_commit_takes_protocol_files_only(repo):
    _touch(repo.root, "CLAUDE.md", "# persona\n## Technology Stack\n- Unity 6\n")
    _touch(repo.root, "design/gdd/concept.md")
    r = repo.commit("director", "[studio:director] 지침", dry_run=True)
    assert "CLAUDE.md" in r["files"] and "design/gdd/concept.md" not in r["files"]


def test_dev_no_longer_owns_claude_md(repo):
    _touch(repo.root, "CLAUDE.md", "changed\n")
    assert "CLAUDE.md" not in repo.commit("dev", "x", dry_run=True).get("files", [])


def test_director_does_not_own_tech_preferences(repo):
    _touch(repo.root, ".claude/docs/technical-preferences.md")
    assert ".claude/docs/technical-preferences.md" in repo.changed_files("dev")
    assert ".claude/docs/technical-preferences.md" not in repo.changed_files("director")


# ---- B. 감사 ----
def test_audit_finds_orphan_files(repo):
    _touch(repo.root, "docs/random-notes.md")          # 어느 영역에도 없음
    _touch(repo.root, "design/gdd/concept.md")         # planning
    a = M.audit(repo)
    assert a["orphans"] == ["docs/random-notes.md"]


def test_audit_allows_designed_overlap(repo):
    _touch(repo.root, "production/epics/core/story-01.md")   # planning · dev 공동 (allowedOverlaps)
    assert M.audit(repo)["overlaps"] == {}


def test_audit_reports_unexpected_overlap(repo):
    repo.cfg["roles"]["art"]["owns"].append("design/gdd")     # 설정 실수로 planning 과 겹침
    _touch(repo.root, "design/gdd/concept.md")
    assert M.audit(repo)["overlaps"] == {"design/gdd/concept.md": ["planning", "art"]}


def test_shared_files_are_not_orphans_or_overlaps(repo):
    _touch(repo.root, "doc/work_log.md")
    a = M.audit(repo)
    assert a["orphans"] == [] and a["overlaps"] == {}


# ---- C. 프로토콜 지문 ----
def test_protocol_first_call_sets_baseline_then_detects_change(repo):
    assert M.protocol_state(repo)["dirty"] is False                 # 최초 = 기준선
    cfg = os.path.join(repo.root, ".agent", "tools", "studio", "studio.config.json")
    with open(cfg, "a", encoding="utf-8") as f:
        f.write("\n")
    st = M.protocol_state(repo)
    assert st["dirty"] and st["changed"] == [".agent/tools/studio/studio.config.json"]


def test_protocol_crlf_only_change_is_not_a_change(repo):
    M.protocol_state(repo)
    p = os.path.join(repo.root, "CLAUDE.md")
    with open(p, "wb") as f:
        f.write(b"# persona\r\n")
    assert M.protocol_state(repo)["dirty"] is False


def test_protocol_ack_records_who_and_clears(repo):
    M.protocol_state(repo)
    _touch(repo.root, "CLAUDE.md", "# changed\n")
    r = M.protocol_ack(repo, "director", "Tech Stack 갱신")
    assert r["changed"] == ["CLAUDE.md"] and r["ackedBy"] == "director"
    assert M.protocol_state(repo)["dirty"] is False


def test_inbox_cli_reports_protocol_change(repo, capsys):
    M.protocol_state(repo)
    _touch(repo.root, "AGENTS.md", "new\n")
    assert S.main(["--root", repo.root, "--json", "inbox", "dev"]) == 0
    out = json.loads(capsys.readouterr().out)
    assert out["protocolChanged"]["added"] == ["AGENTS.md"]


# ---- D. 업그레이드 ----
def test_upgrade_preserves_director_decisions_and_announces(repo, tmp_path):
    # 프로젝트: 디렉터가 dev 영역에서 docs/architecture 를 뺐다 (프로젝트 고유 결정)
    cfg_path = os.path.join(repo.root, ".agent", "tools", "studio", "studio.config.json")
    cfg = json.load(open(cfg_path, encoding="utf-8"))
    cfg["roles"]["dev"]["owns"].remove("docs/architecture")
    del cfg["allowedOverlaps"]                                       # 템플릿에만 있는 새 키로 만든다
    json.dump(cfg, open(cfg_path, "w", encoding="utf-8"), ensure_ascii=False, indent=2)
    M.protocol_state(repo)                                           # 기준선
    # 템플릿: 현재 도구 + README 한 줄 추가
    template = str(tmp_path / "template")
    shutil.copytree(TOOL_DIR, os.path.join(template, ".agent", "tools", "studio"),
                    ignore=shutil.ignore_patterns("__pycache__", "tests", "*.local.json"))
    with open(os.path.join(template, ".agent", "tools", "studio", "README.md"), "a", encoding="utf-8") as f:
        f.write("\n새 절\n")

    plan = M.upgrade(repo, template, dry_run=True)
    assert ".agent/tools/studio/README.md" in plan["replace"]
    assert not os.path.exists(os.path.join(repo.dir, "tickets"))     # dry-run 은 쓰지 않음

    plan = M.upgrade(repo, template)
    merged = json.load(open(cfg_path, encoding="utf-8"))
    assert "docs/architecture" not in merged["roles"]["dev"]["owns"]  # 디렉터 결정 보존
    assert merged["allowedOverlaps"] == ["production/epics"]          # 새 키는 추가
    assert len(plan["tickets"]) == len(repo.roles)
    t = repo.load_ticket(plan["tickets"][0])
    assert t["type"] == "info" and t["from"] == "director" and "upgrade" in t["body"]
    assert M.protocol_state(repo)["dirty"] is False                  # 업그레이드가 승인까지 기록


def test_upgrade_rejects_non_template(repo, tmp_path):
    with pytest.raises(S.StudioError, match="템플릿"):
        M.upgrade(repo, str(tmp_path))
