"""여러 AI 도구 혼합 — watch · dispatch 테스트. python -m pytest .agent/tools/studio/tests -q"""
import json
import os
import sys
import threading
import time

import pytest

TOOL_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, TOOL_DIR)

import studio as S  # noqa: E402
import studio_dispatch as D  # noqa: E402

# 가짜 에이전트: 자기 역할의 착수 가능한 티켓을 모두 done 처리 (실제 CLI 에이전트가 하는 일의 최소 모형)
FAKE_AGENT = """
import os, sys
sys.path.insert(0, {tool_dir!r})
import studio as S
st = S.Studio(os.getcwd(), S.load_config())
role = os.environ["STUDIO_ROLE"]
for t in st.inbox(role):
    if t["ready"] and t["status"] in ("open", "in-progress"):
        st.update_ticket(t["id"], role, status="done", note="fake agent")
"""


@pytest.fixture
def st(tmp_path):
    cfg = S.load_config()
    cfg["dispatch"] = dict(cfg.get("dispatch", {}), pollSec=0.05, backoffSec=[0.1], maxNoProgress=2,
                           runTimeoutSec=30)
    fake = tmp_path / "fake_agent.py"
    fake.write_text(FAKE_AGENT.format(tool_dir=TOOL_DIR), encoding="utf-8")
    cfg["agents"] = dict(cfg["agents"],
                         fake={"argv": [sys.executable, str(fake)], "note": "test"},
                         idle={"argv": [sys.executable, "-c", "pass"], "note": "아무것도 안 함"},
                         ide={"argv": [], "note": "headless 없음"})
    return S.Studio(str(tmp_path), cfg)


# ---- watch ----
def test_watch_returns_immediately_when_ready_ticket_exists(st):
    t = st.new_ticket("planning", "dev", "task", "셋업")
    r = D.watch(st, "dev", timeout=1)
    assert r["actionable"] and r["tickets"] == [t["id"]]


def test_watch_times_out_when_only_gated_tickets(st):
    st.new_ticket("planning", "dev", "story", "구현", gate="G3")
    r = D.watch(st, "dev", timeout=0.2, interval=0.05)
    assert r["actionable"] is False


def test_watch_wakes_when_another_agent_creates_ticket(st):
    # 다른 도구(예: Codex 가 맡은 planning)가 나중에 티켓을 만들어도 파일 감시로 깨어난다
    threading.Timer(0.2, lambda: st.new_ticket("planning", "art", "asset-request", "VFX")).start()
    start = time.monotonic()
    r = D.watch(st, "art", timeout=5, interval=0.05)
    assert r["actionable"] and time.monotonic() - start < 4


def test_watch_ignores_work_while_paused(st):
    st.new_ticket("planning", "dev", "task", "셋업")
    st.set_paused(True, "점검")
    assert D.watch(st, "dev", timeout=0.2, interval=0.05)["actionable"] is False


# ---- 명령 조립 ----
def test_build_command_substitutes_role_and_prompt_file(st):
    argv, _, env, _ = D.build_command(st, "dev", "codex")
    assert argv[:4] == ["codex", "exec", "--sandbox", "workspace-write"]
    assert "ROLE=dev" in argv[-1] and "agent-loop.md" in argv[-1]
    assert env["STUDIO_ROLE"] == "dev"


def test_default_prompt_is_safe_for_cmd_shims(st):
    # npm 전역 CLI(.cmd)는 cmd.exe 를 거친다 — 기본 프롬프트에 해석될 문자가 없어야 한다
    argv, _, _, _ = D.build_command(st, "planning", "gemini")
    assert not (D.CMD_METACHARS & set(argv[2]))


def test_build_command_rejects_ide_agent_without_headless(st):
    with pytest.raises(S.StudioError, match="헤드리스"):
        D.build_command(st, "dev", "ide")


def test_build_command_unknown_agent(st):
    with pytest.raises(S.StudioError, match="알 수 없는 에이전트"):
        D.build_command(st, "dev", "nope")


# ---- dispatch ----
def test_dispatch_once_runs_agent_and_records_roster(st):
    t = st.new_ticket("planning", "dev", "task", "셋업")
    assert D.dispatch(st, "dev", "fake", once=True, emit=lambda m: None) == 0
    assert st.load_ticket(t["id"])["status"] == "done"
    entry = st.roster()["dev"]
    assert entry["kind"] == "dispatch" and entry["agent"] == "fake"
    assert not os.path.exists(os.path.join(st.dir, "locks", "dev.json"))   # 잠금 해제
    logs = os.listdir(os.path.join(st.root, "production", "studio", "logs"))
    assert len(logs) == 1 and logs[0].startswith("dev-")


def test_dispatch_once_without_work_exits_without_running(st):
    assert D.dispatch(st, "dev", "fake", once=True, emit=lambda m: None) == 0
    assert not os.path.isdir(os.path.join(st.root, "production", "studio", "logs"))


def test_dispatch_no_progress_escalates_to_director_once(st):
    st.new_ticket("planning", "dev", "task", "셋업")
    msgs = []
    D.dispatch(st, "dev", "idle", max_runs=3, emit=msgs.append)
    bugs = [t for t in st.tickets() if t["to"] == "director" and t["type"] == "bug"]
    assert len(bugs) == 1                               # maxNoProgress=2 에 도달한 시점 1회
    assert any("진전 없음" in m for m in msgs)


def test_dispatch_lock_blocks_second_dispatcher(st):
    lock = D.RoleLock(st, "dev", "other", stale_sec=60)
    lock.acquire()
    st.new_ticket("planning", "dev", "task", "셋업")
    with pytest.raises(S.StudioError, match="이미 실행 중"):
        D.dispatch(st, "dev", "fake", once=True, emit=lambda m: None)
    assert D.dispatch(st, "dev", "fake", once=True, force_lock=True, emit=lambda m: None) == 0


def test_dispatch_dry_run_does_not_touch_state(st):
    out = []
    assert D.dispatch(st, "planning", "codex", dry_run=True, emit=out.append) == 0
    assert "codex" in out[0] and not os.path.exists(st.roster_path())


# ---- 로스터 kind · 알림 ----
def test_notify_session_only_for_interactive_claude(st):
    st.join("planning", "unitygame-p1")                                   # 대화형 Claude
    st.join("dev", "dispatch:codex", kind="dispatch", agent="codex")
    assert st.notify_session("planning") == "unitygame-p1"
    assert st.notify_session("dev") is None                                # 파일 감시로 깨어남


def test_cli_new_skips_notify_for_dispatch_role(st, capsys):
    st.join("dev", "dispatch:gemini", kind="dispatch", agent="gemini")
    with open(os.path.join(TOOL_DIR, "studio.config.json"), encoding="utf-8") as f:
        assert "agents" in json.load(f)                                    # 프리셋은 정본 설정에 있음
    assert S.main(["--root", st.root, "--json", "new", "--from", "planning", "--to", "dev",
                   "--title", "셋업"]) == 0
    assert json.loads(capsys.readouterr().out)["notifySession"] is None


def test_list_agents_reports_presets(st):
    names = {r["name"] for r in D.list_agents(st)}
    assert {"claude", "codex", "gemini", "cursor", "copilot", "opencode", "antigravity"} <= names
