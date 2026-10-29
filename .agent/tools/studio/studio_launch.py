"""팀 정의 파일 하나로 스튜디오 세션들을 기동 — `studio.py launch`.

production/studio/team.json 에 역할마다 도구 · 모델을 적어 두면, 명령 하나로
  - 대화형 Claude Code 세션: `claude --name studio-<역할> ... "/studio-join <역할>"` (디렉터는 "/studio-director")
  - 그 외 도구: `studio.py dispatch <역할> --agent <도구>` 감독 루프
를 역할마다 터미널 하나씩 띄운다. 띄우는 곳(backend):
  - vscode  : .vscode/tasks.json 에 역할별 작업 + "studio: 전체 기동" 묶음 작업을 만든다 (실행은 VS Code 에서)
  - console : PowerShell 창을 역할마다 하나씩 연다
역할 사이에 stagger 초 간격을 둔다 — 느린 디스크(HDD)에서 세션 기동이 한꺼번에 몰리지 않게 (2026-10-23 포화 사고).
역할마다 만든 세션 ID 를 locks/launch.json 에 남겨 `--resume` 이 이전 대화 맥락을 그대로 잇는다.
"""
import json
import os
import shutil
import socket
import subprocess
import urllib.request
import uuid

from studio import DIRECTOR, StudioError, now, read_json, write_json

TEAM_FILE = "team.json"
BACKENDS = ("vscode", "console")
# Claude Code --permission-mode 값. 팀 전체에 하나만 쓴다 — 세션끼리 모드가 다르면 세션 간 메시지가 승인 대기로 묶인다
PERMISSION_MODES = ("default", "acceptEdits", "plan", "auto", "dontAsk", "bypassPermissions")
TEAM_DEFAULTS = {"permissionMode": "default", "backend": "vscode", "stagger": 20}
# Claude 세션 안에서 launch 를 실행하면 새 세션이 부모의 세션 전용 변수를 물려받아 "자식 세션"으로 뜬다
# (대화 기록 저장 꺼짐 · 세션 등록 안 됨 → SendMessage 대상이 되지 못함). 기동 전에 이것들만 지운다 —
# 사용자 설정 변수(CLAUDE_CODE_USE_BEDROCK 등)는 건드리지 않는다. (2026-10-23 실험에서 확인)
PARENT_SESSION_VARS = ("CLAUDECODE", "CLAUDE_CODE_CHILD_SESSION", "CLAUDE_CODE_ENTRYPOINT", "CLAUDE_CODE_EXECPATH",
                       "CLAUDE_CODE_MESSAGING_SOCKET", "CLAUDE_CODE_MESSAGING_TOKEN", "CLAUDE_CODE_SESSION_ATTENDED",
                       "CLAUDE_CODE_SESSION_ID", "CLAUDE_CODE_SSE_PORT", "CLAUDE_EFFORT", "CLAUDE_PID")
TASK_PREFIX = "studio: "
ALL_TASK = "studio: 전체 기동"


def _team_path(st):
    return os.path.join(st.dir, TEAM_FILE)


def default_team(st):
    """team init 이 쓰는 기본값 — 모든 역할 대화형 Claude, 판단이 많은 planning · director 는 상위 모델."""
    roles = {DIRECTOR: {"tool": "claude", "model": "opus"}}
    for r in st.roles:
        roles[r] = {"tool": "claude", "model": "opus" if r == "planning" else "sonnet"}
    return dict(TEAM_DEFAULTS, roles=roles)


def load_team(st):
    team = read_json(_team_path(st))
    if team is None:
        raise StudioError(f"팀 정의 없음: {os.path.relpath(_team_path(st), st.root)} — `studio.py team init` 으로 만든다")
    team = dict(TEAM_DEFAULTS, **team)
    if team["permissionMode"] not in PERMISSION_MODES:
        raise StudioError(f"permissionMode 는 {', '.join(PERMISSION_MODES)} 중 하나 (현재: {team['permissionMode']})")
    if team["backend"] not in BACKENDS:
        raise StudioError(f"backend 는 {', '.join(BACKENDS)} 중 하나 (현재: {team['backend']})")
    if not isinstance(team["stagger"], (int, float)) or team["stagger"] < 0:
        raise StudioError("stagger 는 0 이상 숫자 (초)")
    roles = team.get("roles") or {}
    if not roles:
        raise StudioError("team.json 에 roles 가 비어 있음")
    presets = st.cfg.get("agents", {})
    for role, spec in roles.items():
        st.check_role(role, allow_director=True)
        tool = spec.get("tool", "claude")
        if tool != "claude" and tool not in presets:
            raise StudioError(f"{role}.tool '{tool}' — claude 또는 agents 프리셋({', '.join(sorted(presets))}) 중 하나")
        if role == DIRECTOR and tool != "claude":
            raise StudioError("director 는 사용자와 대화해야 하므로 tool=claude 만 가능")
        if tool != "claude" and not presets[tool].get("argv"):
            raise StudioError(f"{role}.tool '{tool}' 은 헤드리스 실행이 없는 도구 — 그 도구 안에서 직접 참여")
    team["roles"] = roles
    return team


def selected_roles(team, only=None):
    order = [DIRECTOR] + [r for r in team["roles"] if r != DIRECTOR]
    rows = [r for r in order if r in team["roles"] and team["roles"][r].get("enabled", True)]
    if only:
        unknown = [r for r in only if r not in team["roles"]]
        if unknown:
            raise StudioError(f"team.json 에 없는 역할: {', '.join(unknown)}")
        rows = [r for r in rows if r in only]
    if not rows:
        raise StudioError("기동할 역할 없음 (enabled · --only 확인)")
    return rows


def _state_path(st):
    return os.path.join(st.dir, "locks", "launch.json")


def launch_state(st):
    return read_json(_state_path(st), {"roles": {}})


# ---------------------------------------------------------------- 명령
def build_commands(st, team, roles, resume=False):
    """역할마다 {role, kind, argv, sessionId, title} — 실제 실행은 backend 가 한다."""
    prev = launch_state(st).get("roles", {})
    out = []
    for role in roles:
        spec = team["roles"][role]
        tool = spec.get("tool", "claude")
        title = f"studio-{role}"
        if tool == "claude":
            argv = ["claude", "--name", title, "--permission-mode", team["permissionMode"]]
            if spec.get("model"):
                argv += ["--model", spec["model"]]
            sid = None
            if resume:
                sid = prev.get(role, {}).get("sessionId")
                if not sid:
                    raise StudioError(f"{role}: 재개할 세션 ID 없음 (locks/launch.json) — --resume 없이 새로 기동")
                argv += ["--resume", sid]
            else:
                sid = str(uuid.uuid4())
                argv += ["--session-id", sid]
            prompt = spec.get("prompt") or ("/studio-director" if role == DIRECTOR else f"/studio-join {role}")
            argv.append(prompt)
            out.append({"role": role, "kind": "claude", "argv": argv, "sessionId": sid, "title": title})
        else:
            argv = ["python", ".agent/tools/studio/studio.py", "dispatch", role, "--agent", tool]
            out.append({"role": role, "kind": "dispatch", "argv": argv, "sessionId": None, "title": title})
    return out


def _ps_quote(s):
    return "'" + str(s).replace("'", "''") + "'"


def ps1_script(root, cmd, delay=0):
    """역할 하나를 띄우는 PowerShell 스크립트 — 인자는 작은따옴표로 감싸 해석되지 않게 한다."""
    lines = ["# studio.py launch 가 생성 — 직접 고치지 말 것",
             f"$Host.UI.RawUI.WindowTitle = {_ps_quote(cmd['title'])}",
             f"Set-Location -LiteralPath {_ps_quote(root)}",
             "# 부모 Claude 세션의 세션 전용 변수 제거 — 남아 있으면 자식 세션으로 떠서 기록 · 등록이 꺼진다",
             "foreach ($v in @(" + ", ".join(_ps_quote(v) for v in PARENT_SESSION_VARS) + ")) "
             "{ Remove-Item -LiteralPath \"Env:$v\" -ErrorAction SilentlyContinue }"]
    if delay:
        lines.append(f"Start-Sleep -Seconds {int(delay)}  # 느린 디스크에서 기동이 한꺼번에 몰리지 않게")
    exe, args = cmd["argv"][0], cmd["argv"][1:]
    lines.append("& " + _ps_quote(exe) + "".join(" " + _ps_quote(a) for a in args))
    return "\n".join(lines) + "\n"


def write_scripts(st, team, cmds, staggered):
    """locks/launch/<역할>.ps1 — staggered 면 순번 × stagger 초 대기 (VS Code 병렬 작업용)."""
    d = os.path.join(st.dir, "locks", "launch")
    os.makedirs(d, exist_ok=True)
    paths = {}
    for i, c in enumerate(cmds):
        p = os.path.join(d, f"{c['role']}.ps1")
        with open(p, "w", encoding="utf-8-sig", newline="\r\n") as f:  # Windows PowerShell 5 는 BOM 이 있어야 UTF-8 로 읽는다
            f.write(ps1_script(st.root, c, i * team["stagger"] if staggered else 0))
        paths[c["role"]] = p
    return paths


# ---------------------------------------------------------------- 사전 점검
def _port_open(port, host="127.0.0.1", timeout=1.0):
    try:
        with socket.create_connection((host, port), timeout=timeout):
            return True
    except OSError:
        return False


def _unity_mcp_port(st):
    cfg = read_json(os.path.join(st.root, ".mcp.json"), {}) or {}
    for server in (cfg.get("mcpServers") or {}).values():
        args = server.get("args") or []
        if "--port" in args and args.index("--port") + 1 < len(args):
            try:
                return int(args[args.index("--port") + 1])
            except ValueError:
                pass
    return 6400


def _pid_alive(pid):
    if not pid:
        return False
    if os.name == "nt":
        p = subprocess.run(["tasklist", "/FI", f"PID eq {int(pid)}", "/NH"], capture_output=True, text=True)
        return str(int(pid)) in p.stdout
    try:
        os.kill(int(pid), 0)
        return True
    except OSError:
        return False


def preflight(st, team, roles, probe=True):
    """[{level: error|warn, msg}] — error 가 있으면 --force 없이 기동하지 않는다."""
    import studio_maint
    issues = []
    if st.paused():
        issues.append({"level": "error", "msg": f"정지 중 — {st.paused()} (resume 후 기동)"})
    usage = studio_maint.usage_state(st)
    limit = studio_maint.usage_settings(st)["weeklyPausePercent"]
    if usage.get("percent") is not None:
        if usage["percent"] >= limit:
            issues.append({"level": "error", "msg": f"Claude 주간 사용량 {usage['percent']:.0f}% ≥ 임계 {limit}%"})
        elif usage["percent"] >= limit - 10:
            issues.append({"level": "warn", "msg": f"Claude 주간 사용량 {usage['percent']:.0f}% — 임계 {limit}% 근처"})
    if os.path.exists(os.path.join(st.root, ".git", "index.lock")):
        issues.append({"level": "error", "msg": ".git/index.lock 이 남아 있음 — git 작업이 끝났는지 확인 후 정리"})
    prev = launch_state(st).get("roles", {})
    for r in roles:
        if _pid_alive(prev.get(r, {}).get("pid")):
            issues.append({"level": "error", "msg": f"{r}: 이전에 띄운 창(PID {prev[r]['pid']})이 아직 살아 있음 — 중복 기동"})
    kinds = {team["roles"][r].get("tool", "claude") for r in roles}
    if "claude" in kinds and not shutil.which("claude"):
        issues.append({"level": "error", "msg": "claude 실행 파일을 PATH 에서 찾지 못함"})
    for r in roles:
        tool = team["roles"][r].get("tool", "claude")
        if tool != "claude":
            exe = st.cfg["agents"][tool]["argv"][0]
            if not shutil.which(exe):
                issues.append({"level": "error", "msg": f"{r}: {tool} 실행 파일({exe})을 PATH 에서 찾지 못함"})
    if probe and "dev" in roles:
        port = _unity_mcp_port(st)
        if not _port_open(port):
            issues.append({"level": "warn", "msg": f"dev: Unity MCP 포트 {port} 응답 없음 — Unity 에디터 · Window > MCP for Unity 확인"})
    if probe and "art" in roles:
        art = read_json(os.path.join(st.root, ".agent", "tools", "artgen", "artgen.config.local.json"), {}) or {}
        if art.get("provider") == "comfyui":
            url = (read_json(os.path.join(st.root, ".agent", "tools", "artgen", "artgen.config.json"), {}) or {}) \
                .get("providers", {}).get("comfyui", {}).get("url", "http://127.0.0.1:8188")
            try:
                urllib.request.urlopen(url.rstrip("/") + "/system_stats", timeout=2).close()
            except OSError:
                issues.append({"level": "warn", "msg": f"art: ComfyUI({url}) 응답 없음 — run_nvidia_gpu.bat 실행"})
    if probe:
        issues += prereq_issues(st, roles)
    return issues


# 위에서 이미 보는 항목(실행 파일 · 서버 응답)은 prereq 결과에서 뺀다
_PREREQ_DUP = {"claude", "comfyui-server"}


def prereq_issues(st, roles):
    """사전 설치 점검(.agent/tools/setup/prereq.py)의 필수 누락을 경고로. 도구가 없는 구버전 프로젝트면 건너뛴다."""
    path = os.path.join(st.root, ".agent", "tools", "setup", "prereq.py")
    if not os.path.isfile(path):
        return []
    import importlib.util
    spec = importlib.util.spec_from_file_location("prereq", path)
    prereq = importlib.util.module_from_spec(spec)
    try:
        spec.loader.exec_module(prereq)
        rows = prereq.run_checks(prereq.Ctx(st.root, [r for r in roles if r in prereq.ROLES]))
    except Exception as e:  # 점검 도구의 고장이 기동을 막지 않게
        return [{"level": "warn", "msg": f"사전 설치 점검 실패: {e}"}]
    return [{"level": "warn", "msg": f"사전 설치 누락: {r['title']} — {r['detail']} (prereq.py install"
                                     f"{' 로 자동 설치' if r['auto'] else ' · 안내 참고'})"}
            for r in rows if r["status"] == "missing" and r["id"] not in prereq.REQUIRED_SKIP | _PREREQ_DUP]


# ---------------------------------------------------------------- backend
def vscode_tasks(st, cmds, scripts):
    """.vscode/tasks.json 의 studio 작업 — 다른 작업은 보존한다."""
    path = os.path.join(st.root, ".vscode", "tasks.json")
    try:
        data = read_json(path, None)
    except ValueError:
        raise StudioError(f"{path} 를 JSON 으로 읽지 못함 (주석이 있는 tasks.json 은 수정하지 않는다)")
    data = data or {"version": "2.0.0", "tasks": []}
    keep = [t for t in data.get("tasks", []) if not str(t.get("label", "")).startswith(TASK_PREFIX)]
    ours = []
    for c in cmds:
        rel = os.path.relpath(scripts[c["role"]], st.root).replace("\\", "/")
        ours.append({"label": TASK_PREFIX + c["role"], "type": "process", "command": "powershell",
                     "args": ["-NoProfile", "-ExecutionPolicy", "Bypass", "-NoExit", "-File", rel],
                     "options": {"cwd": "${workspaceFolder}"}, "isBackground": True, "problemMatcher": [],
                     "presentation": {"panel": "dedicated", "reveal": "always", "focus": False, "group": "studio"}})
    ours.append({"label": ALL_TASK, "dependsOn": [TASK_PREFIX + c["role"] for c in cmds], "dependsOrder": "parallel",
                 "problemMatcher": []})
    data["tasks"] = keep + ours
    write_json(path, data)
    return path


def _start_console(script, root):
    """PowerShell 창 하나 — 새 창의 PID 를 돌려준다."""
    p = subprocess.run(["powershell", "-NoProfile", "-Command",
                        "(Start-Process powershell -WorkingDirectory " + _ps_quote(root) +
                        " -ArgumentList '-NoProfile','-ExecutionPolicy','Bypass','-NoExit','-File'," + _ps_quote(script) +
                        " -PassThru).Id"], capture_output=True, text=True, timeout=60)
    if p.returncode != 0:
        raise StudioError(f"창 열기 실패: {(p.stderr or p.stdout).strip()[:300]}")
    try:
        return int(p.stdout.strip().splitlines()[-1])
    except (ValueError, IndexError):
        return None


def launch(st, only=None, backend=None, resume=False, dry_run=False, force=False, probe=True,
           starter=_start_console, sleep=None):
    team = load_team(st)
    backend = backend or team["backend"]
    if backend not in BACKENDS:
        raise StudioError(f"backend 는 {', '.join(BACKENDS)} 중 하나")
    roles = selected_roles(team, only)
    issues = preflight(st, team, roles, probe=probe)
    cmds = build_commands(st, team, roles, resume)
    result = {"backend": backend, "permissionMode": team["permissionMode"], "stagger": team["stagger"],
              "roles": cmds, "issues": issues, "dryRun": dry_run, "launched": False}
    errors = [i for i in issues if i["level"] == "error"]
    if dry_run or (errors and not force):
        result["blocked"] = bool(errors) and not dry_run
        return result
    scripts = write_scripts(st, team, cmds, staggered=(backend == "vscode"))
    state = {"launchedAt": now(), "backend": backend, "permissionMode": team["permissionMode"],
             "roles": dict(launch_state(st).get("roles", {}))}
    if backend == "vscode":
        result["tasksFile"] = vscode_tasks(st, cmds, scripts)
        for c in cmds:
            state["roles"][c["role"]] = {"sessionId": c["sessionId"], "kind": c["kind"], "pid": None, "at": now()}
    else:
        import time
        sleep = sleep or time.sleep
        for i, c in enumerate(cmds):
            if i and team["stagger"]:
                sleep(team["stagger"])
            pid = starter(scripts[c["role"]], st.root)
            c["pid"] = pid
            state["roles"][c["role"]] = {"sessionId": c["sessionId"], "kind": c["kind"], "pid": pid, "at": now()}
    write_json(_state_path(st), state)
    st.log("launch", backend=backend, roles=roles, resume=resume)
    result["launched"] = True
    return result


def team_init(st, force=False):
    path = _team_path(st)
    if os.path.exists(path) and not force:
        raise StudioError(f"이미 있음: {os.path.relpath(path, st.root)} (덮어쓰려면 --force)")
    write_json(path, default_team(st))
    return path


def format_result(r):
    head = (f"[dry-run] " if r["dryRun"] else "") + \
        f"backend={r['backend']} · permissionMode={r['permissionMode']} · stagger={r['stagger']}s"
    lines = [head]
    for c in r["roles"]:
        lines.append(f"  {c['role']:<9} {c['kind']:<8} " + " ".join(c["argv"]) + (f"   (PID {c['pid']})" if c.get("pid") else ""))
    for i in r["issues"]:
        lines.append(("  ✗ " if i["level"] == "error" else "  ⚠ ") + i["msg"])
    if r.get("blocked"):
        lines.append("중단: 위 오류를 해결하거나 --force")
    elif r["launched"] and r["backend"] == "vscode":
        lines.append(f"VS Code: 명령 팔레트 → Tasks: Run Task → '{ALL_TASK}' (작업 파일 {r['tasksFile']})")
    elif r["launched"]:
        lines.append("창을 열었다 — 세션 ID 는 production/studio/locks/launch.json (다음 번 --resume)")
    return "\n".join(lines)
