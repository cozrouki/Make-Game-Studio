#!/usr/bin/env python3
"""studio — 기획 · 아트 · 개발 세션 협업 프로토콜의 결정적 부분 (티켓 · 게이트 · 로스터 · 역할별 커밋).

세션 간 알림(SendMessage)은 스킬이 하고, 이 도구는 파일 상태만 다룬다.
여러 AI 도구 혼합(감시 · 헤드리스 디스패치)은 studio_dispatch.py,
쓰기 영역 감사 · 프로토콜 변경 기록 · 템플릿 업그레이드는 studio_maint.py.
Unity 프로젝트 루트에서 실행:
    python .agent/tools/studio/studio.py status
상세: .agent/tools/studio/README.md
"""
import argparse
import datetime
import json
import os
import re
import subprocess
import sys
import time

TOOL_DIR = os.path.dirname(os.path.abspath(__file__))
STATUSES = ("open", "in-progress", "blocked", "done", "cancelled")
ACTIVE = ("open", "in-progress", "blocked")
TYPES = ("task", "question", "asset-request", "assets-ready", "story", "review", "bug", "gate", "info")
PRIORITIES = ("P0", "P1", "P2")
GATE_STATUSES = ("pending", "requested", "approved", "rejected")
DIRECTOR = "director"
ART_MODES = ("ai", "human")
TICKET_RE = re.compile(r"^T-(\d{4,})\.md$")
FIELDS = ("id", "title", "from", "to", "type", "status", "priority", "gate", "depends", "refs", "created", "updated")
LIST_FIELDS = ("depends", "refs")
ROSTER_KINDS = ("claude", "dispatch", "manual")  # claude = 대화형 Claude Code(SendMessage 가능)


class StudioError(Exception):
    pass


# ---------------------------------------------------------------- 공통
def now():
    return datetime.datetime.now().astimezone().isoformat(timespec="seconds")


def parse_time(s):
    try:
        return datetime.datetime.fromisoformat(s)
    except (TypeError, ValueError):
        return None


def read_json(path, default=None):
    if not os.path.isfile(path):
        return default
    with open(path, encoding="utf-8") as f:
        return json.load(f)


def write_json(path, data):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    tmp = path + ".tmp"
    with open(tmp, "w", encoding="utf-8", newline="\n") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)
        f.write("\n")
    os.replace(tmp, path)


def deep_merge(base, over):
    out = dict(base)
    for k, v in over.items():
        out[k] = deep_merge(out[k], v) if isinstance(v, dict) and isinstance(out.get(k), dict) else v
    return out


def load_config(tool_dir=TOOL_DIR):
    cfg = read_json(os.path.join(tool_dir, "studio.config.json"))
    local = read_json(os.path.join(tool_dir, "studio.config.local.json"), {})
    return deep_merge(cfg, local)


class Studio:
    def __init__(self, root, config):
        self.root = os.path.abspath(root)
        self.cfg = config
        self.dir = os.path.join(self.root, config["dataDir"])
        self.tickets_dir = os.path.join(self.dir, "tickets")

    @property
    def art_mode(self):
        mode = self.cfg.get("artMode", "ai")
        if mode not in ART_MODES:
            raise StudioError(f"artMode 는 {ART_MODES} 중 하나 (현재: {mode})")
        return mode

    @property
    def roles(self):
        return list(self.cfg["roles"])

    def check_role(self, role, allow_director=False):
        valid = self.roles + ([DIRECTOR] if allow_director else [])
        if role not in valid:
            raise StudioError(f"알 수 없는 역할 '{role}' (허용: {', '.join(valid)})")

    def log(self, event, **data):
        os.makedirs(self.dir, exist_ok=True)
        with open(os.path.join(self.dir, "events.jsonl"), "a", encoding="utf-8", newline="\n") as f:
            f.write(json.dumps(dict(at=now(), event=event, **data), ensure_ascii=False) + "\n")

    # ------------------------------------------------------------ 로스터
    def roster_path(self):
        return os.path.join(self.dir, "roster.json")

    def roster(self):
        return read_json(self.roster_path(), {})

    def join(self, role, session, kind="claude", agent=""):
        self.check_role(role)
        if kind not in ROSTER_KINDS:
            raise StudioError(f"kind 는 {ROSTER_KINDS} 중 하나")
        roster = self.roster()
        prev = roster.get(role, {}).get("session")
        roster[role] = {"session": session, "kind": kind, "agent": agent or ("claude" if kind == "claude" else ""),
                        "joinedAt": now()}
        write_json(self.roster_path(), roster)
        self.log("join", role=role, session=session, kind=kind, previous=prev)
        return roster

    def notify_session(self, role):
        """SendMessage 로 깨울 수 있는 세션 이름 — 대화형 Claude Code 만. 나머지는 dispatch/watch 가 파일 변화로 깨어난다."""
        entry = self.roster().get(role, {})
        return entry.get("session") if entry.get("kind", "claude") == "claude" else None

    # ------------------------------------------------------------ 티켓
    def _ticket_path(self, tid):
        if not re.match(r"^T-\d{4,}$", tid or ""):
            raise StudioError(f"티켓 ID 형식 오류: {tid} (T-0001)")
        return os.path.join(self.tickets_dir, f"{tid}.md")

    def _allocate_id(self):
        """O_EXCL 생성으로 번호 예약 — 여러 세션이 동시에 발행해도 충돌 없음."""
        os.makedirs(self.tickets_dir, exist_ok=True)
        nums = [int(m.group(1)) for n in os.listdir(self.tickets_dir) if (m := TICKET_RE.match(n))]
        n = max(nums) + 1 if nums else 1
        while True:
            tid = f"T-{n:04d}"
            try:
                fd = os.open(self._ticket_path(tid), os.O_CREAT | os.O_EXCL | os.O_WRONLY)
                os.close(fd)
                return tid
            except FileExistsError:
                n += 1

    def new_ticket(self, sender, to, ttype, title, body="", priority="P1", gate="", depends=(), refs=()):
        self.check_role(sender, allow_director=True)
        self.check_role(to, allow_director=True)
        if sender == to:
            raise StudioError("자기 자신에게 티켓을 보낼 수 없음")
        if ttype not in TYPES:
            raise StudioError(f"type 은 {TYPES} 중 하나")
        if priority not in PRIORITIES:
            raise StudioError(f"priority 는 {PRIORITIES} 중 하나")
        if not title.strip() or "\n" in title:
            raise StudioError("title 은 한 줄 필수")
        if gate:
            self.gate(gate)  # 존재 확인
        for d in depends:
            self.load_ticket(d)
        tid = self._allocate_id()
        t = {"id": tid, "title": title.strip(), "from": sender, "to": to, "type": ttype, "status": "open",
             "priority": priority, "gate": gate, "depends": list(depends), "refs": list(refs),
             "created": now(), "updated": now(),
             "body": body.strip() or "(본문 없음)", "thread": []}
        self._save_ticket(t)
        self.log("ticket.new", id=tid, sender=sender, to=to, type=ttype)
        return t

    def load_ticket(self, tid):
        path = self._ticket_path(tid)
        if not os.path.isfile(path):
            raise StudioError(f"티켓 없음: {tid}")
        with open(path, encoding="utf-8") as f:
            text = f.read()
        m = re.match(r"^---\n(.*?)\n---\n(.*)$", text, re.S)
        if not m:
            raise StudioError(f"{tid}: 프론트매터 손상")
        t = {}
        for line in m.group(1).splitlines():
            key, _, val = line.partition(":")
            key, val = key.strip(), val.strip()
            t[key] = [v.strip() for v in val.split(",") if v.strip()] if key in LIST_FIELDS else val
        rest = m.group(2)
        body, _, thread = rest.partition("\n## 스레드\n")
        t["body"] = body.replace("## 요청\n", "", 1).strip()
        t["thread"] = [ln[2:] for ln in thread.splitlines() if ln.startswith("- ")]
        return t

    def _save_ticket(self, t):
        head = "\n".join(f"{k}: {', '.join(t[k]) if k in LIST_FIELDS else t[k]}" for k in FIELDS)
        thread = "\n".join(f"- {e}" for e in t["thread"])
        text = f"---\n{head}\n---\n\n## 요청\n\n{t['body']}\n\n## 스레드\n{thread}\n"
        with open(self._ticket_path(t["id"]), "w", encoding="utf-8", newline="\n") as f:
            f.write(text)

    def update_ticket(self, tid, by, status=None, note="", to=None):
        self.check_role(by, allow_director=True)
        t = self.load_ticket(tid)
        changes = []
        if status:
            if status not in STATUSES:
                raise StudioError(f"status 는 {STATUSES} 중 하나")
            if status == "in-progress":
                ready, why = self.readiness(t)
                if not ready:
                    raise StudioError(f"{tid} 착수 불가 — {why}")
            if status != t["status"]:
                changes.append(f"status {t['status']}→{status}")
                t["status"] = status
        if to and to != t["to"]:
            self.check_role(to, allow_director=True)
            changes.append(f"담당 {t['to']}→{to}")
            t["to"] = to
        if not changes and not note:
            raise StudioError("변경 없음 — --status / --to / --note 중 하나 필요")
        entry = f"{now()} [{by}] " + "; ".join(changes) + (": " if changes and note else "") + note.replace("\n", " ")
        t["thread"].append(entry)
        t["updated"] = now()
        self._save_ticket(t)
        self.log("ticket.update", id=tid, by=by, changes=changes)
        return t

    def tickets(self):
        if not os.path.isdir(self.tickets_dir):
            return []
        ids = sorted(n[:-3] for n in os.listdir(self.tickets_dir) if TICKET_RE.match(n))
        out = []
        for tid in ids:
            try:
                out.append(self.load_ticket(tid))
            except StudioError:
                continue  # 번호만 예약되고 아직 비어 있는 파일
        return out

    def readiness(self, t):
        if t.get("gate"):
            g = self.gate(t["gate"])
            if g["status"] != "approved":
                return False, f"게이트 {g['id']}({g['name']}) {g['status']}"
        for d in t.get("depends", []):
            try:
                dt = self.load_ticket(d)
            except StudioError:
                return False, f"의존 티켓 {d} 없음"
            if dt["status"] != "done":
                return False, f"의존 {d} {dt['status']}"
        return True, "ready"

    def inbox(self, role, include_done=False):
        self.check_role(role, allow_director=True)
        prio = {p: i for i, p in enumerate(PRIORITIES)}
        rows = []
        for t in self.tickets():
            if t["to"] != role or (not include_done and t["status"] not in ACTIVE):
                continue
            ready, why = self.readiness(t)
            rows.append(dict(t, ready=ready, readyReason=why))
        # 진행 중 → 착수 가능 → 대기, 그 안에서 우선순위 · 번호
        rows.sort(key=lambda r: (r["status"] != "in-progress", not r["ready"], prio.get(r["priority"], 9), r["id"]))
        return rows

    # ------------------------------------------------------------ 게이트
    def gates_path(self):
        return os.path.join(self.dir, "gates.json")

    def gates(self):
        state = read_json(self.gates_path(), {})
        defs = list(self.cfg["gates"]) + state.get("_custom", [])
        out = []
        for g in defs:
            s = state.get(g["id"], {})
            g = dict(g)
            # 아트 모드별 산출물 — 사람 아티스트면 스타일 토큰 대신 디렉션 브리프 · 시안 선택이 게이트 조건
            by_mode = g.pop("artifactsByArtMode", {})
            if self.art_mode in by_mode:
                g["artifacts"] = by_mode[self.art_mode]
            out.append(dict(g, status=s.get("status", "pending"), history=s.get("history", [])))
        return out

    def gate(self, gid):
        for g in self.gates():
            if g["id"] == gid:
                return g
        raise StudioError(f"게이트 없음: {gid}")

    def add_gate(self, gid, name, owner, artifacts, unlocks):
        self.check_role(owner)
        if any(g["id"] == gid for g in self.gates()):
            raise StudioError(f"이미 존재하는 게이트: {gid}")
        state = read_json(self.gates_path(), {})
        state.setdefault("_custom", []).append(
            {"id": gid, "name": name, "owner": owner, "artifacts": artifacts, "unlocks": unlocks})
        write_json(self.gates_path(), state)
        self.log("gate.add", id=gid)
        return self.gate(gid)

    def set_gate(self, gid, status, by, note=""):
        g = self.gate(gid)
        if status == "requested":
            if g["status"] == "approved":
                raise StudioError(f"{gid} 는 이미 승인됨")
            missing = [a for a in g["artifacts"] if not os.path.exists(os.path.join(self.root, a))]
            if missing:
                raise StudioError(f"{gid} 산출물 누락 — {', '.join(missing)}")
        elif status in ("approved", "rejected"):
            if by != DIRECTOR:
                raise StudioError("게이트 승인·반려는 director 만 가능 (--by director)")
            if g["status"] != "requested":
                raise StudioError(f"{gid} 는 요청 상태가 아님 ({g['status']})")
        state = read_json(self.gates_path(), {})
        s = state.setdefault(gid, {"history": []})
        s["status"] = status
        s["history"].append({"at": now(), "by": by, "status": status, "note": note})
        write_json(self.gates_path(), state)
        self.log("gate." + status, id=gid, by=by)
        return self.gate(gid)

    # ------------------------------------------------------------ 일시정지 (디렉터 비상 정지)
    def pause_path(self):
        return os.path.join(self.dir, "PAUSED")

    def paused(self):
        path = self.pause_path()
        if not os.path.isfile(path):
            return None
        with open(path, encoding="utf-8") as f:
            return f.read().strip() or "사유 없음"

    def set_paused(self, on, reason=""):
        if on:
            os.makedirs(self.dir, exist_ok=True)
            with open(self.pause_path(), "w", encoding="utf-8", newline="\n") as f:
                f.write(f"{now()} {reason}\n")
        elif os.path.isfile(self.pause_path()):
            os.remove(self.pause_path())
        self.log("pause" if on else "resume", reason=reason)

    # ------------------------------------------------------------ 현황
    def status(self):
        tickets = self.tickets()
        stale_after = datetime.timedelta(hours=self.cfg.get("staleHours", 24))
        current = datetime.datetime.now().astimezone()
        per_role = {}
        for r in self.roles + [DIRECTOR]:
            mine = [t for t in tickets if t["to"] == r]
            per_role[r] = {s: sum(1 for t in mine if t["status"] == s) for s in ACTIVE}
            per_role[r]["ready"] = sum(1 for t in mine if t["status"] == "open" and self.readiness(t)[0])
        stale = [t["id"] for t in tickets if t["status"] == "in-progress"
                 and (u := parse_time(t["updated"])) and current - u > stale_after]
        director_queue = [{"id": t["id"], "title": t["title"], "from": t["from"], "type": t["type"]}
                          for t in tickets if t["to"] == DIRECTOR and t["status"] in ACTIVE]
        gates = [{"id": g["id"], "name": g["name"], "status": g["status"], "unlocks": g["unlocks"]} for g in self.gates()]
        maint = _maint()
        return {"artMode": self.art_mode, "paused": self.paused(), "roster": self.roster(), "gates": gates, "roles": per_role,
                "directorQueue": director_queue, "stale": stale, "total": len(tickets),
                "audit": maint.audit(self), "protocol": maint.protocol_state(self)}

    # ------------------------------------------------------------ 커밋
    def pathspecs(self, role):
        """역할(또는 director) 쓰기 영역 + 공유 영역. director 는 프로토콜 · 지침 · 도구 미러 (directorOwns)."""
        if role == DIRECTOR:
            return list(self.cfg.get("directorOwns", [])) + list(self.cfg.get("shared", []))
        self.check_role(role)
        return list(self.cfg["roles"][role]["owns"]) + list(self.cfg.get("shared", []))

    def _git(self, *args, check=True, stdin=None):
        for attempt in range(6):
            p = subprocess.run(["git", "-C", self.root, *args], input=stdin, capture_output=True, text=True,
                               encoding="utf-8")
            if p.returncode == 0 or "index.lock" not in (p.stderr or ""):
                break
            time.sleep(1 + attempt)  # 다른 세션이 git 작업 중 — 잠시 후 재시도
        if check and p.returncode != 0:
            raise StudioError(f"git {' '.join(args[:2])} 실패: {(p.stderr or p.stdout).strip()}")
        return p

    def changed_files(self, role):
        """역할 쓰기 영역 + 공유 영역의 변경 파일."""
        return self.changed_files_for(self.pathspecs(role))

    def changed_files_for(self, specs):
        """pathspec 목록에 해당하는 미커밋 변경. status 는 매칭 없는 pathspec 에도 실패하지 않는다."""
        if not specs:
            return []
        p = self._git("status", "--porcelain", "-z", "-uall", "--no-renames", "--", *specs)
        return sorted({e[3:] for e in p.stdout.split("\0") if len(e) > 3})

    def commit(self, role, message, dry_run=False):
        files = self.changed_files(role)
        if not files:
            return {"committed": False, "files": [], "warnings": [], "reason": "변경 없음"}
        # 생성된 .meta 없이 커밋하면 팀원 쪽에서 GUID 가 새로 생겨 참조가 깨진다
        warnings = [f"{f}: .meta 없음 — Unity 임포트 후 커밋 권장" for f in files
                    if f.startswith("Assets/") and not f.endswith(".meta")
                    and os.path.isfile(os.path.join(self.root, f)) and not os.path.exists(os.path.join(self.root, f + ".meta"))]
        if dry_run:
            return {"committed": False, "dryRun": True, "files": files, "warnings": warnings}
        # 파일을 명시해 커밋 — 다른 세션이 스테이징해 둔 파일이 섞이지 않는다
        # 파일 목록은 stdin 으로 — Windows 명령줄 길이 제한 회피
        nul_list = "".join(f + chr(0) for f in files)
        self._git("add", "-A", "--pathspec-from-file=-", "--pathspec-file-nul", stdin=nul_list)
        self._git("commit", "-m", message, "--pathspec-from-file=-", "--pathspec-file-nul", stdin=nul_list)
        names = files
        sha = self._git("rev-parse", "--short", "HEAD").stdout.strip()
        self.log("commit", role=role, sha=sha, files=len(names))
        return {"committed": True, "sha": sha, "files": names, "warnings": warnings}


def _maint():
    # 스크립트로 실행되면 이 모듈은 __main__ — 'studio' 로 다시 import 되어 클래스가 두 벌 생기지 않게 한다
    sys.modules.setdefault("studio", sys.modules[__name__])
    import studio_maint  # noqa: E402 — 같은 디렉터리
    return studio_maint


# ---------------------------------------------------------------- CLI
def _split(v):
    return [x.strip() for x in (v or "").split(",") if x.strip()]


def _fmt_ticket_row(t):
    flag = "▶" if t["status"] == "in-progress" else ("●" if t.get("ready") else "◌")
    why = "" if t.get("ready", True) or t["status"] == "in-progress" else f"  ({t['readyReason']})"
    return f"{flag} {t['id']} {t['priority']} {t['type']:<13} {t['from']:>8}→{t['to']:<8} {t['status']:<11} {t['title']}{why}"


def main(argv=None):
    for stream in (sys.stdout, sys.stderr):
        try:
            stream.reconfigure(encoding="utf-8")
        except (AttributeError, ValueError):
            pass
    ap = argparse.ArgumentParser(prog="studio", description="기획·아트·개발 세션 협업 프로토콜")
    ap.add_argument("--root", default=os.getcwd())
    ap.add_argument("--json", action="store_true")
    sub = ap.add_subparsers(dest="cmd", required=True)

    p = sub.add_parser("join", help="역할 ↔ 세션 이름 등록")
    p.add_argument("role")
    p.add_argument("session")
    p.add_argument("--kind", default="claude", choices=ROSTER_KINDS)
    p.add_argument("--agent", default="", help="도구 이름 (codex, gemini, cursor …)")
    sub.add_parser("roster")

    p = sub.add_parser("watch", help="역할에 처리할 티켓이 생길 때까지 대기 (파일 감시, 토큰 소모 없음)")
    p.add_argument("role")
    p.add_argument("--timeout", type=float, default=0, help="초. 0 = 무기한")
    p.add_argument("--interval", type=float, default=0, help="감시 주기 초 (기본: config dispatch.pollSec)")

    p = sub.add_parser("dispatch", help="Claude 외 도구를 헤드리스로 실행하는 감독 루프")
    p.add_argument("role")
    p.add_argument("--agent", required=True, help="config agents 의 프리셋 이름")
    p.add_argument("--max-runs", type=int, default=0, help="0 = 무한")
    p.add_argument("--once", action="store_true", help="처리할 티켓이 있을 때 1회만 실행하고 종료")
    p.add_argument("--dry-run", action="store_true", help="실행할 명령만 출력")
    p.add_argument("--force-lock", action="store_true", help="남아 있는 잠금을 무시")

    sub.add_parser("agents", help="에이전트 프리셋과 설치 여부")

    p = sub.add_parser("new", help="티켓 발행")
    p.add_argument("--from", dest="sender", required=True)
    p.add_argument("--to", required=True)
    p.add_argument("--type", default="task")
    p.add_argument("--title", required=True)
    p.add_argument("--body", default="")
    p.add_argument("--body-file")
    p.add_argument("--priority", default="P1")
    p.add_argument("--gate", default="")
    p.add_argument("--depends", default="")
    p.add_argument("--refs", default="")

    p = sub.add_parser("inbox", help="역할의 받은 티켓")
    p.add_argument("role")
    p.add_argument("--all", action="store_true")

    p = sub.add_parser("show")
    p.add_argument("id")

    p = sub.add_parser("update", help="상태 변경 · 메모 · 재배정")
    p.add_argument("id")
    p.add_argument("--by", required=True)
    p.add_argument("--status")
    p.add_argument("--to")
    p.add_argument("--note", default="")

    p = sub.add_parser("gate", help="게이트 조회·요청·승인·반려·추가")
    p.add_argument("action", choices=("list", "request", "approve", "reject", "add"))
    p.add_argument("id", nargs="?")
    p.add_argument("--by", default="")
    p.add_argument("--note", default="")
    p.add_argument("--name", default="")
    p.add_argument("--owner", default="planning")
    p.add_argument("--artifacts", default="")
    p.add_argument("--unlocks", default="")

    sub.add_parser("status", help="디렉터 현황판")

    p = sub.add_parser("pause", help="전 세션 정지 (진행 중 티켓만 마무리)")
    p.add_argument("--reason", default="")
    sub.add_parser("resume", help="정지 해제")

    p = sub.add_parser("changes", help="역할 쓰기 영역 + 공유 영역의 미커밋 변경 (중단 후 재개 점검용)")
    p.add_argument("role")

    sub.add_parser("audit", help="미커밋 변경 중 주인 없는 파일 · 역할 간 겹침")

    p = sub.add_parser("protocol", help="프로토콜(설정 · 도구 · 헌장 · 지침) 변경 확인 / 승인")
    p.add_argument("action", nargs="?", default="status", choices=("status", "ack"))
    p.add_argument("--by", default="director")
    p.add_argument("--note", default="")

    p = sub.add_parser("upgrade", help="템플릿 저장소에서 스튜디오 · artgen 도구 갱신 (프로젝트 설정 보존 · 공지 티켓)")
    p.add_argument("--from", dest="template", required=True, help="템플릿 저장소 경로")
    p.add_argument("--dry-run", action="store_true")

    p = sub.add_parser("commit", help="역할(또는 director) 쓰기 영역 + 공유 영역만 커밋")
    p.add_argument("role")
    p.add_argument("-m", "--message", required=True)
    p.add_argument("--dry-run", action="store_true")

    args = ap.parse_args(argv)
    st = Studio(args.root, load_config())

    def out(data, text):
        print(json.dumps(data, ensure_ascii=False, indent=2) if args.json else text)

    try:
        if args.cmd == "join":
            r = st.join(args.role, args.session, args.kind, args.agent)
            out(r, f"{args.role} = {args.session} ({args.kind})")
        elif args.cmd == "roster":
            r = st.roster()
            out(r, "\n".join(f"{k:<9} {v['session']}  [{v.get('kind', 'claude')}/{v.get('agent') or 'claude'}]"
                             f"  (등록 {v['joinedAt']})" for k, v in r.items()) or "(등록 없음)")
        elif args.cmd in ("watch", "dispatch", "agents"):
            # 스크립트로 실행되면 이 모듈은 __main__ — 'studio' 로 다시 import 되어 클래스가 두 벌 생기지 않게 한다
            sys.modules.setdefault("studio", sys.modules[__name__])
            import studio_dispatch as D  # noqa: E402 — 같은 디렉터리
            if args.cmd == "watch":
                r = D.watch(st, args.role, args.timeout, args.interval)
                out(r, r["text"])
                return 0 if r["actionable"] else 3
            if args.cmd == "agents":
                rows = D.list_agents(st)
                out(rows, "\n".join(f"{'OK ' if r['installed'] else '-- '} {r['name']:<9} {r['executable'] or ''}  {r['note']}"
                                    for r in rows))
                return 0
            return D.dispatch(st, args.role, args.agent, max_runs=args.max_runs, once=args.once,
                              dry_run=args.dry_run, force_lock=args.force_lock, emit=lambda m: print(m, flush=True))
        elif args.cmd == "new":
            body = args.body
            if args.body_file:
                with open(args.body_file, encoding="utf-8") as f:
                    body = f.read()
            t = st.new_ticket(args.sender, args.to, args.type, args.title, body, args.priority, args.gate,
                              _split(args.depends), _split(args.refs))
            ready, why = st.readiness(t)
            session = st.notify_session(t["to"]) if t["to"] != DIRECTOR else None
            out(dict(t, ready=ready, readyReason=why, notifySession=session),
                f"{t['id']} 발행 → {t['to']} ({'착수 가능' if ready else why})"
                + (f"\n알림 대상 세션: {session}" if session else "\n알림 없음 — 대상은 파일 감시(watch/dispatch)로 깨어남"))
        elif args.cmd == "inbox":
            rows = st.inbox(args.role, args.all)
            paused = st.paused()
            proto = _maint().protocol_state(st)
            text = "\n".join(_fmt_ticket_row(r) for r in rows) or "(받은 티켓 없음)"
            note = ""
            if proto["dirty"]:
                n = len(proto["changed"]) + len(proto["added"]) + len(proto["removed"])
                note = f"ⓘ 프로토콜 미승인 변경 {n}건 — 헌장 · README 를 다시 읽고 진행 (디렉터 확인 대기, 보고 불필요)\n"
            out({"paused": paused, "tickets": rows, "protocolChanged": proto["dirty"] and
                 {k: proto[k] for k in ("changed", "added", "removed")}},
                (f"⏸ 정지 중 — {paused}\n" if paused else "") + note + text)
        elif args.cmd == "show":
            t = st.load_ticket(args.id)
            ready, why = st.readiness(t)
            text = "\n".join(f"{k}: {t[k]}" for k in FIELDS) + f"\n착수: {why}\n\n{t['body']}\n\n" + "\n".join(t["thread"])
            out(dict(t, ready=ready, readyReason=why), text)
        elif args.cmd == "update":
            t = st.update_ticket(args.id, args.by, args.status, args.note, args.to)
            session = st.notify_session(t["from"]) if t["from"] != DIRECTOR else None
            out(dict(t, notifySession=session), f"{t['id']} {t['status']} — {t['thread'][-1]}")
        elif args.cmd == "gate":
            if args.action == "list":
                gs = st.gates()
                out(gs, "\n".join(f"{g['id']:<4} {g['status']:<10} {g['name']}  → {g['unlocks']}" for g in gs))
            elif args.action == "add":
                g = st.add_gate(args.id, args.name, args.owner, _split(args.artifacts), args.unlocks)
                out(g, f"{g['id']} 추가")
            else:
                if not args.id or not args.by:
                    raise StudioError("gate request/approve/reject 는 <id> 와 --by 필요")
                status = {"request": "requested", "approve": "approved", "reject": "rejected"}[args.action]
                g = st.set_gate(args.id, status, args.by, args.note)
                out(dict(g, roster=st.roster()), f"{g['id']} {g['status']}")
        elif args.cmd == "status":
            s = st.status()
            lines = ([f"⏸ 정지 중 — {s['paused']}"] if s["paused"] else []) + [f"아트 모드: {s['artMode']}", "[게이트]"] +[f"  {g['id']:<4} {g['status']:<10} {g['name']}" for g in s["gates"]]
            lines += ["[역할]          진행 착수가능 대기(open) 차단  세션"]
            for r, c in s["roles"].items():
                sess = s["roster"].get(r, {}).get("session", "-" if r != DIRECTOR else "(사용자)")
                lines.append(f"  {r:<12} {c['in-progress']:>4} {c['ready']:>8} {c['open']:>10} {c['blocked']:>4}  {sess}")
            lines += ["[디렉터 판단 대기]"] + ([f"  {d['id']} {d['type']} ({d['from']}) {d['title']}" for d in s["directorQueue"]] or ["  없음"])
            if s["stale"]:
                lines.append(f"[정체 — {st.cfg.get('staleHours', 24)}h 이상 갱신 없음] {', '.join(s['stale'])}")
            a, pr = s["audit"], s["protocol"]
            if a["orphans"] or a["overlaps"]:
                lines.append(f"[쓰기 영역] 주인 없는 변경 {len(a['orphans'])}건 · 역할 겹침 {len(a['overlaps'])}건 — studio.py audit")
            if pr["dirty"]:
                lines.append(f"[프로토콜] 미승인 변경 — 수정 {len(pr['changed'])} · 추가 {len(pr['added'])} · 삭제 {len(pr['removed'])}"
                             f" (마지막 승인 {pr['ackedAt']} {pr['ackedBy']}) — studio.py protocol")
            out(s, "\n".join(lines))
        elif args.cmd in ("pause", "resume"):
            st.set_paused(args.cmd == "pause", getattr(args, "reason", ""))
            out({"paused": st.paused(), "roster": st.roster()}, "정지됨" if args.cmd == "pause" else "재개됨")
        elif args.cmd == "changes":
            files = st.changed_files(args.role)
            active = [t["id"] for t in st.inbox(args.role) if t["status"] == "in-progress"]
            out({"role": args.role, "files": files, "inProgress": active},
                ("\n".join(files) or "(미커밋 변경 없음)") + (f"\n진행 중 티켓: {', '.join(active)}" if active else ""))
        elif args.cmd == "audit":
            a = _maint().audit(st)
            lines = [f"미커밋 변경 {a['changed']}건"]
            lines += ["[주인 없음 — 어느 역할 · 디렉터 · 공유 영역에도 없음]"] + ([f"  {f}" for f in a["orphans"]] or ["  없음"])
            lines += ["[역할 겹침]"] + ([f"  {f}  ← {', '.join(o)}" for f, o in a["overlaps"].items()] or ["  없음"])
            out(a, "\n".join(lines))
        elif args.cmd == "protocol":
            m = _maint()
            r = m.protocol_ack(st, args.by, args.note) if args.action == "ack" else m.protocol_state(st)
            body = [f"  수정 {f}" for f in r["changed"]] + [f"  추가 {f}" for f in r["added"]] + [f"  삭제 {f}" for f in r["removed"]]
            head = "승인함" if args.action == "ack" else ("미승인 변경 있음" if r["dirty"] else "변경 없음")
            out(r, f"프로토콜: {head} (마지막 승인 {r['ackedAt']} · {r['ackedBy']})" + ("\n" + "\n".join(body) if body else ""))
        elif args.cmd == "upgrade":
            r = _maint().upgrade(st, args.template, dry_run=args.dry_run)
            lines = [f"템플릿 {r['templateRev']}" + (" [dry-run]" if r["dryRun"] else "")]
            lines += [f"  교체 {f}" for f in r["replace"]] + [f"  추가 {f}" for f in r["add"]]
            lines += [f"  병합 {m['file']}" + (f" (새 키: {', '.join(m['newTopLevelKeys'])})" if m["newTopLevelKeys"] else "")
                      for m in r["merge"]]
            lines.append(f"  변경 없음 {r['unchanged']}개")
            if r.get("tickets"):
                lines.append(f"공지 티켓: {', '.join(r['tickets'])}")
            out(r, "\n".join(lines))
        elif args.cmd == "commit":
            r = st.commit(args.role, args.message, args.dry_run)
            text = (f"커밋 {r['sha']} — {len(r['files'])}개 파일" if r["committed"]
                    else ("[dry-run] 대상:\n  " + "\n  ".join(r["files"]) if r.get("dryRun") else r["reason"]))
            out(r, text + "".join(f"\n  ⚠ {w}" for w in r["warnings"]))
        return 0
    except StudioError as e:
        if args.json:
            print(json.dumps({"error": str(e)}, ensure_ascii=False))
        else:
            print(f"오류: {e}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    sys.exit(main())
