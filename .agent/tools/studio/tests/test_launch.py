"""studio launch — 팀 정의 · 명령 생성 · 사전 점검 · backend (창은 실제로 열지 않는다)."""
import json
import os
import sys

import pytest

TOOL_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, TOOL_DIR)

import studio as S  # noqa: E402
import studio_launch as L  # noqa: E402


@pytest.fixture
def st(tmp_path):
    s = S.Studio(str(tmp_path), S.load_config())
    os.makedirs(s.dir)
    return s


def _team(st, **kw):
    team = L.default_team(st)
    team.update(kw)
    json.dump(team, open(os.path.join(st.dir, "team.json"), "w", encoding="utf-8"))
    return team


def test_launch_team_init_writes_defaults_and_refuses_overwrite(st):
    L.team_init(st)
    team = L.load_team(st)
    assert set(team["roles"]) == {"director", *st.roles}
    assert team["roles"]["planning"]["model"] == "opus" and team["permissionMode"] == "default"
    with pytest.raises(S.StudioError, match="이미 있음"):
        L.team_init(st)


@pytest.mark.parametrize("patch, needle", [
    ({"permissionMode": "yolo"}, "permissionMode"),
    ({"backend": "tmux"}, "backend"),
    ({"stagger": -1}, "stagger"),
    ({"roles": {"qa": {"tool": "claude"}}}, "역할"),
    ({"roles": {"dev": {"tool": "unknown-cli"}}}, "unknown-cli"),
    ({"roles": {"director": {"tool": "codex"}}}, "director"),
    ({"roles": {"art": {"tool": "antigravity"}}}, "헤드리스"),
])
def test_launch_team_invalid_rejected(st, patch, needle):
    _team(st, **patch)
    with pytest.raises(S.StudioError, match=needle):
        L.load_team(st)


def test_launch_commands_claude_and_dispatch(st):
    team = _team(st, permissionMode="acceptEdits")
    team["roles"]["dev"] = {"tool": "codex"}
    json.dump(team, open(os.path.join(st.dir, "team.json"), "w", encoding="utf-8"))
    team = L.load_team(st)
    cmds = {c["role"]: c for c in L.build_commands(st, team, L.selected_roles(team))}
    p = cmds["planning"]["argv"]
    assert p[:5] == ["claude", "--name", "studio-planning", "--permission-mode", "acceptEdits"]
    assert p[p.index("--model") + 1] == "opus" and p[-1] == "/studio-join planning"
    assert p[p.index("--session-id") + 1] == cmds["planning"]["sessionId"]
    assert cmds["director"]["argv"][-1] == "/studio-director"
    assert cmds["dev"]["argv"][-4:] == ["dispatch", "dev", "--agent", "codex"] and cmds["dev"]["kind"] == "dispatch"
    assert list(cmds) == ["director", "planning", "art", "dev"]   # 디렉터 먼저


def test_launch_resume_uses_previous_session_id(st):
    _team(st)
    team = L.load_team(st)
    with pytest.raises(S.StudioError, match="재개할 세션 ID 없음"):
        L.build_commands(st, team, ["art"], resume=True)
    S.write_json(os.path.join(st.dir, "locks", "launch.json"), {"roles": {"art": {"sessionId": "abc-123"}}})
    argv = L.build_commands(st, team, ["art"], resume=True)[0]["argv"]
    assert argv[argv.index("--resume") + 1] == "abc-123" and "--session-id" not in argv


def test_launch_ps1_quotes_arguments_and_staggers(st):
    cmd = {"title": "studio-it's", "argv": ["claude", "--name", "a'b", "/studio-join planning"]}
    s = L.ps1_script("D:\\Proj O'Neil", cmd, delay=40)
    assert "Set-Location -LiteralPath 'D:\\Proj O''Neil'" in s
    assert "Start-Sleep -Seconds 40" in s
    assert s.rstrip().endswith("& 'claude' '--name' 'a''b' '/studio-join planning'")
    # 회귀: Claude 세션 안에서 띄우면 CLAUDE_CODE_CHILD_SESSION 등을 물려받아 기록 · 세션 등록이 꺼졌다 (2026-10-23)
    assert "'CLAUDE_CODE_CHILD_SESSION'" in s and "'CLAUDE_CODE_MESSAGING_TOKEN'" in s and "Remove-Item" in s
    assert s.index("Remove-Item") < s.index("& 'claude'")


def test_launch_dry_run_has_no_side_effects(st):
    _team(st)
    r = L.launch(st, dry_run=True, probe=False)
    assert r["dryRun"] and not r["launched"] and len(r["roles"]) == 4
    assert not os.path.exists(os.path.join(st.dir, "locks", "launch.json"))
    assert not os.path.exists(os.path.join(st.root, ".vscode"))


def test_launch_blocked_by_pause_and_index_lock_unless_forced(st):
    _team(st)
    st.set_paused(True, "점검")
    os.makedirs(os.path.join(st.root, ".git"))
    open(os.path.join(st.root, ".git", "index.lock"), "w").close()
    r = L.launch(st, probe=False, starter=lambda *a: 1, sleep=lambda s: None, backend="console")
    msgs = " ".join(i["msg"] for i in r["issues"])
    assert r["blocked"] and not r["launched"] and "정지 중" in msgs and "index.lock" in msgs
    r = L.launch(st, probe=False, force=True, starter=lambda *a: 1, sleep=lambda s: None, backend="console")
    assert r["launched"]


def test_launch_usage_near_and_over_threshold(st):
    import studio_maint as M
    _team(st)
    M.record_usage(st, 82, 1800000000)
    assert [i["level"] for i in L.launch(st, dry_run=True, probe=False)["issues"]] == ["warn"]


def test_launch_console_staggers_and_records_session_ids(st):
    _team(st, stagger=7)
    started, slept = [], []
    r = L.launch(st, backend="console", only=["planning", "art"], probe=False,
                 starter=lambda script, root: started.append(script) or 1000 + len(started), sleep=slept.append)
    assert r["launched"] and slept == [7]
    assert [os.path.basename(p) for p in started] == ["planning.ps1", "art.ps1"]
    state = L.launch_state(st)["roles"]
    assert state["art"]["pid"] == 1002 and state["planning"]["sessionId"] == r["roles"][0]["sessionId"]
    raw = open(started[0], "rb").read()
    assert raw.startswith(b"\xef\xbb\xbf") and b"\r\n" in raw   # PowerShell 5 용 BOM · CRLF


def test_launch_vscode_tasks_preserve_foreign_tasks(st):
    _team(st, stagger=10)
    os.makedirs(os.path.join(st.root, ".vscode"))
    S.write_json(os.path.join(st.root, ".vscode", "tasks.json"),
                 {"version": "2.0.0", "tasks": [{"label": "build game", "type": "shell", "command": "x"},
                                                 {"label": "studio: old", "type": "shell", "command": "y"}]})
    r = L.launch(st, probe=False)
    tasks = json.load(open(os.path.join(st.root, ".vscode", "tasks.json"), encoding="utf-8"))["tasks"]
    labels = [t["label"] for t in tasks]
    assert labels[0] == "build game" and "studio: old" not in labels
    assert labels[-1] == L.ALL_TASK and tasks[-1]["dependsOrder"] == "parallel"
    assert "Start-Sleep -Seconds 30" in open(os.path.join(st.dir, "locks", "launch", "dev.ps1"), encoding="utf-8-sig").read()
    assert r["launched"] and L.launch_state(st)["roles"]["dev"]["pid"] is None


def test_launch_duplicate_window_detected(st, monkeypatch):
    _team(st)
    S.write_json(os.path.join(st.dir, "locks", "launch.json"), {"roles": {"art": {"pid": 4242}}})
    monkeypatch.setattr(L, "_pid_alive", lambda pid: pid == 4242)
    r = L.launch(st, dry_run=True, probe=False)
    assert any("art" in i["msg"] and "중복" in i["msg"] for i in r["issues"])


def test_launch_cli_dry_run(st, capsys):
    _team(st)
    assert S.main(["--root", st.root, "launch", "--dry-run", "--only", "planning"]) == 0
    out = capsys.readouterr().out
    assert "[dry-run]" in out and "/studio-join planning" in out
