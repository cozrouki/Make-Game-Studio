"""여러 AI 도구 혼합 — 파일 감시(watch)와 헤드리스 감독 루프(dispatch).

알림을 "누가 보냈나"(SendMessage)가 아니라 "티켓 파일이 바뀌었나"로 판단한다.
그래서 티켓을 Claude · Codex · Gemini · 사람 중 누가 만들었든 같은 방식으로 깨어난다.

- watch    : 역할에 처리할 티켓이 생길 때까지 파일만 보며 대기 (AI 토큰 소모 없음).
             대화형 Claude 세션은 이것을 백그라운드로 걸어 두면 종료 시 자동으로 깨어난다.
- dispatch : Claude 외 도구(Codex CLI · Gemini CLI · Cursor CLI · Copilot CLI · OpenCode …)를
             처리할 티켓이 생길 때마다 헤드리스로 실행하는 감독 루프.
             진전이 없으면 백오프하고, 역할당 1개만 돌도록 잠근다.
"""
import datetime
import hashlib
import json
import os
import shutil
import subprocess
import time

from studio import DIRECTOR, StudioError, TOOL_DIR, now, read_json, write_json

DISPATCH_DEFAULTS = {
    "pollSec": 3,
    "runTimeoutSec": 3600,
    "backoffSec": [60, 300, 900],
    "maxNoProgress": 3,
    "logDir": "production/studio/logs",
    "prompt": "You are the {role} agent of a game studio pipeline. Read {prompt_file} and follow it with ROLE={role}. "
              "Process actionable tickets, then exit.",
}
PROMPT_FILE = os.path.join(TOOL_DIR, "prompts", "agent-loop.md")
# Windows 의 .cmd/.bat 실행 파일(npm 전역 설치 CLI)은 cmd.exe 를 거친다 — 인자에 이 문자가 있으면 해석될 수 있다
CMD_METACHARS = set('&|<>^%"!')


def settings(st):
    s = dict(DISPATCH_DEFAULTS)
    s.update(st.cfg.get("dispatch", {}))
    return s


# ---------------------------------------------------------------- 감시
def actionable(st, role):
    """(처리할 것이 있는가, 해당 티켓 목록). 정지 중이면 항상 False."""
    if st.paused():
        return False, []
    rows = st.inbox(role)
    todo = [r for r in rows if r["status"] == "in-progress" or (r["status"] == "open" and r["ready"])]
    return bool(todo), todo


def fingerprint(st):
    """스튜디오 상태 지문 — 에이전트 실행 전후로 비교해 진전 여부를 판단."""
    h = hashlib.sha256()
    paths = []
    if os.path.isdir(st.tickets_dir):
        paths += [os.path.join(st.tickets_dir, n) for n in sorted(os.listdir(st.tickets_dir))]
    paths += [st.gates_path(), st.pause_path()]
    for p in paths:
        if os.path.isfile(p):
            stat = os.stat(p)
            h.update(f"{p}|{stat.st_size}|{stat.st_mtime_ns}\n".encode("utf-8"))
    head = subprocess.run(["git", "-C", st.root, "rev-parse", "HEAD"], capture_output=True, text=True)
    h.update(head.stdout.strip().encode("ascii", "ignore"))
    return h.hexdigest()


def watch(st, role, timeout=0, interval=0, heartbeat=None):
    st.check_role(role)
    interval = interval or settings(st)["pollSec"]
    start = time.monotonic()
    while True:
        ok, todo = actionable(st, role)
        if ok:
            ids = ", ".join(f"{t['id']}({t['status']})" for t in todo)
            return {"actionable": True, "role": role, "tickets": [t["id"] for t in todo],
                    "text": f"{role}: 처리할 티켓 {len(todo)}건 — {ids}"}
        if timeout and time.monotonic() - start >= timeout:
            paused = st.paused()
            return {"actionable": False, "role": role, "tickets": [], "paused": paused,
                    "text": f"{role}: 시간 초과 — 처리할 티켓 없음" + (f" (정지 중: {paused})" if paused else "")}
        if heartbeat:
            heartbeat()
        time.sleep(interval)


# ---------------------------------------------------------------- 에이전트 프리셋
def agents(st):
    presets = st.cfg.get("agents", {})
    if not presets:
        raise StudioError("studio.config.json 에 agents 프리셋이 없음")
    return presets


def list_agents(st):
    rows = []
    for name, p in sorted(agents(st).items()):
        exe = shutil.which(p["argv"][0]) if p.get("argv") else None
        rows.append({"name": name, "installed": bool(exe), "executable": exe, "note": p.get("note", ""),
                     "headless": bool(p.get("argv"))})
    return rows


def build_command(st, role, agent_name):
    preset = agents(st).get(agent_name)
    if not preset:
        raise StudioError(f"알 수 없는 에이전트 '{agent_name}' (프리셋: {', '.join(sorted(agents(st)))})")
    if not preset.get("argv"):
        raise StudioError(f"'{agent_name}' 은 헤드리스 실행이 없는 도구 — 그 도구 안에서 studio.py watch 로 참여 (README §여러 AI 도구)")
    s = settings(st)
    try:
        prompt_file = os.path.relpath(PROMPT_FILE, st.root).replace("\\", "/")
    except ValueError:  # Windows 에서 도구와 프로젝트가 다른 드라이브
        prompt_file = PROMPT_FILE.replace("\\", "/")
    values = {"role": role, "prompt_file": prompt_file, "root": st.root}
    prompt = preset.get("prompt", s["prompt"])
    for k, v in values.items():
        prompt = prompt.replace("{" + k + "}", v)
    values["prompt"] = prompt
    argv = []
    for a in preset["argv"]:
        for k, v in values.items():
            a = a.replace("{" + k + "}", v)
        argv.append(a)
    exe = shutil.which(argv[0])
    if exe and os.path.splitext(exe)[1].lower() in (".cmd", ".bat"):
        bad = [a for a in argv[1:] if CMD_METACHARS & set(a)]
        if bad:
            raise StudioError(f"{exe} 는 cmd.exe 를 거치는 실행 파일 — 인자에 특수문자({''.join(sorted(CMD_METACHARS))}) 금지: {bad[0][:60]}")
    env = dict(os.environ)
    env.update({k: str(v) for k, v in preset.get("env", {}).items()})
    env["STUDIO_ROLE"] = role
    return argv, exe, env, preset


# ---------------------------------------------------------------- 잠금
class RoleLock:
    """역할당 디스패처 1개. 하트비트가 오래되면(프로세스가 죽었으면) 다른 디스패처가 가져갈 수 있다."""

    def __init__(self, st, role, agent_name, stale_sec):
        self.path = os.path.join(st.dir, "locks", f"{role}.json")
        self.info = {"pid": os.getpid(), "agent": agent_name, "role": role}
        self.stale_sec = stale_sec

    def acquire(self, force=False):
        cur = read_json(self.path)
        if cur and not force:
            age = time.time() - cur.get("heartbeatEpoch", 0)
            if age < self.stale_sec:
                raise StudioError(f"{self.info['role']} 디스패처가 이미 실행 중 (pid {cur.get('pid')}, {cur.get('agent')}, "
                                  f"{int(age)}초 전 응답) — 중복이 아니라면 --force-lock")
        self.beat()

    def beat(self):
        write_json(self.path, dict(self.info, heartbeat=now(), heartbeatEpoch=time.time()))

    def release(self):
        cur = read_json(self.path)
        if cur and cur.get("pid") == self.info["pid"] and os.path.isfile(self.path):
            os.remove(self.path)


# ---------------------------------------------------------------- 감독 루프
def _run_agent(argv_exec, env, cwd, log_path, timeout, poll, beat):
    os.makedirs(os.path.dirname(log_path), exist_ok=True)
    with open(log_path, "wb") as log:
        log.write(f"$ {argv_exec!r}\n[start {now()}]\n".encode("utf-8"))
        log.flush()
        proc = subprocess.Popen(argv_exec, cwd=cwd, env=env, stdin=subprocess.DEVNULL, stdout=log,
                                stderr=subprocess.STDOUT)
        start = time.monotonic()
        while proc.poll() is None:
            if time.monotonic() - start > timeout:
                proc.terminate()
                try:
                    proc.wait(10)
                except subprocess.TimeoutExpired:
                    proc.kill()
                log.write(f"\n[timeout {timeout}s — 종료]\n".encode("utf-8"))
                return -1
            beat()
            time.sleep(poll)
        log.write(f"\n[exit {proc.returncode} {now()}]\n".encode("utf-8"))
        return proc.returncode


def _sleep_until_change(st, seconds, before, poll, beat):
    """백오프 대기 — 그 사이 상태가 바뀌면(새 티켓 · 디렉터 조치) 바로 깨어난다."""
    end = time.monotonic() + seconds
    while time.monotonic() < end:
        if fingerprint(st) != before:
            return True
        beat()
        time.sleep(min(poll, max(0.0, end - time.monotonic())))
    return False


def dispatch(st, role, agent_name, max_runs=0, once=False, dry_run=False, force_lock=False, emit=print):
    st.check_role(role)
    argv, exe, env, preset = build_command(st, role, agent_name)
    s = settings(st)
    if dry_run:
        emit(f"[dry-run] {role} ← {agent_name}: {argv!r}" + ("" if exe else "  (실행 파일 미설치)"))
        return 0
    if not exe:
        raise StudioError(f"'{argv[0]}' 실행 파일을 찾을 수 없음 — {agent_name} 설치 또는 agents 프리셋 수정")
    argv_exec = [exe] + argv[1:]
    poll = s["pollSec"]
    lock = RoleLock(st, role, agent_name, stale_sec=max(60, poll * 10))
    lock.acquire(force_lock)
    st.join(role, f"dispatch:{agent_name}", kind="dispatch", agent=agent_name)
    st.log("dispatch.start", role=role, agent=agent_name)
    runs, no_progress = 0, 0
    try:
        while True:
            ok, todo = actionable(st, role)
            if not ok:
                if once:
                    emit(f"{role}: 처리할 티켓 없음 — 종료 (--once)")
                    return 0
                emit(f"{role}: 대기 중 (티켓 · 게이트 · 정지 해제를 감시)")
                watch(st, role, heartbeat=lock.beat)
                ok, todo = actionable(st, role)
            ids = ", ".join(t["id"] for t in todo)
            before = fingerprint(st)
            stamp = datetime.datetime.now().strftime("%Y%m%d-%H%M%S")
            log_path = os.path.join(st.root, s["logDir"], f"{role}-{stamp}-{agent_name}.log")
            emit(f"{role}: {agent_name} 실행 — {ids}  (로그 {os.path.relpath(log_path, st.root)})")
            st.log("dispatch.run", role=role, agent=agent_name, tickets=[t["id"] for t in todo])
            rc = _run_agent(argv_exec, env, st.root, log_path, s["runTimeoutSec"], poll, lock.beat)
            runs += 1
            progressed = fingerprint(st) != before
            st.log("dispatch.exit", role=role, agent=agent_name, rc=rc, progressed=progressed)
            if progressed:
                no_progress = 0
                emit(f"{role}: 종료 (exit {rc}) — 진전 있음")
            else:
                no_progress += 1
                wait = s["backoffSec"][min(no_progress - 1, len(s["backoffSec"]) - 1)]
                emit(f"{role}: 종료 (exit {rc}) — 진전 없음 {no_progress}회, {wait}초 대기 (상태 변화 시 즉시 재개)")
                if no_progress == s["maxNoProgress"]:
                    # 사용량 한도 · 인증 만료 · 프롬프트 문제 등 사람이 봐야 할 상황 — 같은 연속 구간에 1회만 보고
                    st.new_ticket(role, DIRECTOR, "bug", f"{agent_name} 디스패치 {no_progress}회 연속 진전 없음 ({role})",
                                  f"대상 티켓: {ids}\n마지막 로그: {os.path.relpath(log_path, st.root)}\n"
                                  f"확인할 것: 사용량 한도 · 인증 · CLI 옵션(agents 프리셋) · 권한 승인 대기.\n"
                                  f"디스패처는 백오프하며 계속 대기한다.", priority="P0")
                if not (once or (max_runs and runs >= max_runs)):
                    _sleep_until_change(st, wait, fingerprint(st), poll, lock.beat)
            if once or (max_runs and runs >= max_runs):
                return 0
    except KeyboardInterrupt:
        emit(f"{role}: 중단됨")
        return 130
    finally:
        st.log("dispatch.stop", role=role, agent=agent_name, runs=runs)
        lock.release()
