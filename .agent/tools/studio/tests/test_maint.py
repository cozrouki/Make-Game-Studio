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


def test_upgrade_unions_director_owns(repo, tmp_path):
    # 프로젝트: 예전 템플릿의 directorOwns + 디렉터가 직접 넣은 항목
    cfg_path = os.path.join(repo.root, ".agent", "tools", "studio", "studio.config.json")
    cfg = json.load(open(cfg_path, encoding="utf-8"))
    cfg["directorOwns"] = [x for x in cfg["directorOwns"] if x != ".agent/catalogs"] + ["docs/director-notes"]
    json.dump(cfg, open(cfg_path, "w", encoding="utf-8"), ensure_ascii=False, indent=2)
    template = str(tmp_path / "template")
    shutil.copytree(TOOL_DIR, os.path.join(template, ".agent", "tools", "studio"),
                    ignore=shutil.ignore_patterns("__pycache__", "tests", "*.local.json"))

    M.upgrade(repo, template)
    owns = json.load(open(cfg_path, encoding="utf-8"))["directorOwns"]
    assert ".agent/catalogs" in owns          # 템플릿의 새 도구 폴더가 들어온다
    assert "docs/director-notes" in owns      # 프로젝트 항목은 유지
    assert len(owns) == len(set(owns))


def test_upgrade_rejects_non_template(repo, tmp_path):
    with pytest.raises(S.StudioError, match="템플릿"):
        M.upgrade(repo, str(tmp_path))


# ---- Claude 주간 사용량 가드 ----
HOOK = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(TOOL_DIR))), ".claude", "hooks",
                    "studio-pause-notice.sh")


def _bash():
    """Claude Code 훅과 같은 Git Bash — Windows 의 PATH 에서는 WSL bash.exe 가 먼저 잡힐 수 있다."""
    if os.name == "nt":
        p = subprocess.run(["git", "--exec-path"], capture_output=True, text=True, encoding="utf-8").stdout.strip()
        cand = os.path.normpath(os.path.join(p, "..", "..", "..", "bin", "bash.exe")) if p else ""
        if os.path.isfile(cand):
            return cand
    return shutil.which("bash")


@pytest.fixture
def st(tmp_path):
    s = S.Studio(str(tmp_path), S.load_config())
    os.makedirs(s.dir)
    return s


def test_usage_parse_statusline_reads_seven_day():
    data = {"rate_limits": {"five_hour": {"used_percentage": 99}, "seven_day": {"used_percentage": 91.5, "resets_at": 1800000000}}}
    assert M.parse_statusline(data) == (91.5, 1800000000)
    assert M.parse_statusline({"model": {}}) == (None, None)  # API 키 사용자 · 첫 응답 전


def test_usage_below_threshold_only_records(st):
    r = M.record_usage(st, 72, 1800000000)
    assert r["recorded"] and not r["triggered"]
    assert st.paused() is None and M.usage_state(st)["percent"] == 72


def test_usage_over_threshold_pauses_once_per_window(st):
    st.new_ticket("planning", "dev", "task", "진행 중 작업")
    st.update_ticket("T-0001", "dev", "in-progress", "§1 완료")
    r = M.record_usage(st, 90, 1800000000)
    assert r["triggered"] and "90%" in st.paused()
    handoff = open(os.path.join(st.dir, "HANDOFF.md"), encoding="utf-8").read()
    assert "T-0001" in handoff and "§1 완료" in handoff and "/studio-join" in handoff
    assert f"- {r['ticket']} info (studio)" in handoff  # 디렉터 대기열에 정지 티켓
    t = st.load_ticket(r["ticket"])
    assert (t["from"], t["to"], t["priority"]) == ("studio", "director", "P0")
    # 같은 주기: 디렉터가 일부러 재개한 뒤에도 다시 정지하지 않는다
    st.set_paused(False)
    assert M.record_usage(st, 95, 1800000000)["triggered"] is False and st.paused() is None
    # 다음 주기에는 다시 발동
    assert M.record_usage(st, 92, 1800604800)["triggered"] is True


def test_usage_unchanged_value_skips_write(st):
    # 회귀: statusLine 이 1분마다 같은 값을 넘길 때 매번 쓰면 느린 HDD 에서 프로세스가 쌓였다 (2026-10-23)
    M.record_usage(st, 57, 1800000000)
    path = os.path.join(st.dir, "locks", "usage.json")
    before = os.path.getmtime(path)
    os.utime(path, (before - 100, before - 100))
    r = M.record_usage(st, 57, 1800000000)
    assert r["unchanged"] is True and os.path.getmtime(path) == before - 100
    assert M.record_usage(st, 58, 1800000000).get("unchanged") is None   # 값이 바뀌면 기록


def test_usage_guard_disabled_or_custom_threshold(tmp_path):
    cfg = S.load_config()
    cfg["usageGuard"] = {"enabled": False}
    s = S.Studio(str(tmp_path), cfg)
    os.makedirs(s.dir)
    assert M.record_usage(s, 99, 1800000000)["triggered"] is False
    cfg["usageGuard"] = {"weeklyPausePercent": 80}
    assert M.record_usage(S.Studio(str(tmp_path), cfg), 81, 1800000000)["triggered"] is True


def test_usage_fmt_epoch_handles_bad_values():
    assert M.fmt_epoch(None) == "알 수 없음" and M.fmt_epoch("x") == "알 수 없음"
    assert M.fmt_epoch(1800000000).startswith("2027-01-15")


def test_usage_ignored_without_studio_dir(tmp_path):
    s = S.Studio(str(tmp_path), S.load_config())
    assert M.record_usage(s, 99, 1) == {"recorded": False, "triggered": False}
    assert not os.path.exists(s.dir)


def test_usage_cli_stdin_from_statusline(st, capsys, monkeypatch):
    import io
    monkeypatch.setattr(sys, "stdin", io.StringIO(json.dumps({"rate_limits": {"seven_day": {"used_percentage": 93, "resets_at": 1800000000}}})))
    assert S.main(["--root", st.root, "usage", "--stdin"]) == 0
    assert "정지 발동" in capsys.readouterr().out
    monkeypatch.setattr(sys, "stdin", io.StringIO("not json"))
    assert S.main(["--root", st.root, "usage", "--stdin"]) == 0
    assert capsys.readouterr().out.strip() == "기록 안 함"


def test_watch_director_wakes_while_paused(st):
    import studio_dispatch as D
    M.record_usage(st, 90, 1800000000)
    assert D.watch(st, "director", timeout=1, interval=0.1)["actionable"] is True
    st.new_ticket("planning", "dev", "task", "x")
    assert D.watch(st, "dev", timeout=0.3, interval=0.1)["actionable"] is False


@pytest.mark.skipif(_bash() is None, reason="bash 없음")
def test_pause_notice_hook_injects_once_per_session(tmp_path):
    root = str(tmp_path)
    env = dict(os.environ, CLAUDE_PROJECT_DIR=root)

    def run(sid):
        return subprocess.run([_bash(), HOOK], input=json.dumps({"session_id": sid}), capture_output=True,
                              text=True, encoding="utf-8", env=env).stdout.strip()

    assert run("a") == ""  # 정지 없음
    _touch(root, "production/studio/PAUSED", "2026-10-23 Claude 주간 사용량 91%\n")
    out = json.loads(run("a"))["hookSpecificOutput"]
    assert out["hookEventName"] == "PostToolUse" and "91%" in out["additionalContext"]
    assert run("a") == "" and run("b") != ""  # 세션마다 한 번
    _touch(root, "production/studio/PAUSED", "2026-10-24 디렉터 정지\n")
    assert "디렉터 정지" in run("a")  # 새 정지는 다시 알림
