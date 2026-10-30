#!/usr/bin/env python3
"""design_graph — 기획 문서 프런트매터 · 관계 그래프 · 결정 카드 검사 (표준 라이브러리만).

기획 문서(design/ 아래 .md)의 프런트매터를 표준(standard.json)에 맞춰 읽고, 문서 사이 관계(relations)로 그래프를 만들어
구조 문제를 찾는다. 사람은 관계를 한쪽 문서에만 적는다 — 반대 방향(누가 나를 가리키나)은 이 도구가 계산한다.
판정(PASS/FAIL)은 스킬이 한다. 이 도구는 발견만 낸다.

    python .agent/tools/design/design_graph.py check  [--root R] [--dirs design ...] [--json]
    python .agent/tools/design/design_graph.py impact <id | 문서 경로> [--root R] [--json]
    python .agent/tools/design/design_graph.py map    [--root R] [--out design/graph.md]
    python .agent/tools/design/design_graph.py next-id [--root R] [--year 2026]

규칙
  문서     DG001 프런트매터 파싱 실패            DG002 필수 필드 누락            DG003 허용되지 않은 값(type · status · abstraction · 관계 종류)
           DG004 id 중복                          DG005 id 형식                   DG014 오래 갱신 안 됨(staleDays)
  그래프   DG006 없는 id 를 가리킴(깨진 관계)     DG007 archived 문서를 가리킴    DG008 순환(requires · derives_from · part_of)
           DG009 conflicts_with 인 두 문서가 모두 approved                        DG010 supersedes 대상이 archived 아님
           DG011 추상 역행 — 위(L 숫자 작음) 문서가 아래 문서에 기대어 성립       DG012 고아(관계 없음 — 폐기 후보)
           DG013 허브 과부하(들어오는 관계 hubInbound 초과)                       DG015 GDD 의존 한쪽만 언급(design-docs.md 양방향 규칙)
  결정     DG101 결정 id 형식(D<연도>-<번호>)      DG102 결정 필수 필드(impact · decided_by)
           DG103 결정 본문 절 누락                DG104 사후 확인 시기 지남       DG105 [MISSING] 표시가 남음
           DG106 템플릿 안내문(<…>)이 남음
프런트매터가 없는 문서는 그래프 밖이다 — 검사하지 않고 개수와 경로를 'notRun' 에 밝힌다 (점진 도입).
종료 코드: 0 = error 없음 · 1 = error 있음 · 2 = 사용법 오류.
"""
import argparse
import datetime
import os
import re
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from designlib import as_list, finding, iter_docs, load_standard, print_report  # noqa: E402

GRAPH_ORDER_RELATIONS = ("requires", "derives_from", "part_of")


def _date(s):
    try:
        return datetime.date.fromisoformat(str(s)[:10])
    except ValueError:
        return None


def _level(meta):
    m = re.match(r"^L(\d)$", str(meta.get("abstraction", "")))
    return int(m.group(1)) if m else None


class Graph:
    def __init__(self, root, dirs=("design",), standard=None, today=None):
        self.root = os.path.abspath(root)
        self.std = standard or load_standard()
        self.today = today or datetime.date.today()
        self.raw = iter_docs(self.root, dirs)
        self.docs = {}            # id → doc
        self.no_front = []        # 프런트매터 없는 문서 경로
        self.findings = []
        self._index()

    # ------------------------------------------------------------------ 수집
    def _index(self):
        seen = {}
        for d in self.raw:
            if "error" in d:
                self.findings.append(finding("DG001", "error", d["path"], f"프런트매터 파싱 실패 — {d['error']}"))
                continue
            if not d["meta"]:
                self.no_front.append(d["path"])
                continue
            did = str(d["meta"].get("id", "")).strip()
            if not did:
                continue  # DG002 에서 보고
            if did in seen:
                self.findings.append(finding("DG004", "error", d["path"], f"id 중복 '{did}' — {seen[did]} 와 같다"))
                continue
            seen[did] = d["path"]
            self.docs[did] = d

    def relations(self, doc):
        rel = doc["meta"].get("relations") or {}
        return rel if isinstance(rel, dict) else {}

    def inbound(self):
        inc = {i: [] for i in self.docs}
        for sid, d in self.docs.items():
            for kind, targets in self.relations(d).items():
                for t in as_list(targets):
                    if t in inc:
                        inc[t].append((sid, kind))
        return inc

    # ------------------------------------------------------------------ 검사
    def check(self):
        std, f = self.std, self.findings
        all_with_meta = [d for d in self.raw if "error" not in d and d["meta"]]
        for d in all_with_meta:
            m, p = d["meta"], d["path"]
            for k in std["required"]:
                if not str(m.get(k) or "").strip():
                    f.append(finding("DG002", "error", p, f"필수 필드 '{k}' 없음"))
            if m.get("type") and m["type"] not in std["types"]:
                f.append(finding("DG003", "error", p, f"type '{m['type']}' 는 표준에 없음 ({', '.join(std['types'])})"))
            if m.get("status") and m["status"] not in std["status"]:
                f.append(finding("DG003", "error", p, f"status '{m['status']}' 는 표준에 없음 ({', '.join(std['status'])})"))
            if m.get("abstraction") and m["abstraction"] not in std["abstraction"]:
                f.append(finding("DG003", "error", p, f"abstraction '{m['abstraction']}' 는 L0~L4 가 아님"))
            for kind in self.relations(d):
                if kind not in std["relations"]:
                    f.append(finding("DG003", "error", p, f"관계 종류 '{kind}' 는 표준에 없음 ({', '.join(std['relations'])})"))
            did = str(m.get("id", ""))
            if did and m.get("type") != "decision" and not re.match(std["idPattern"], did):
                f.append(finding("DG005", "warn", p, f"id '{did}' 가 형식({std['idPattern']})과 다름 — 예: SYS-combat"))
            up = _date(m.get("updated", ""))
            if m.get("updated") and not up:
                f.append(finding("DG003", "error", p, f"updated '{m['updated']}' 는 YYYY-MM-DD 가 아님"))
            elif up and m.get("status") != "archived" and (self.today - up).days > std["staleDays"]:
                f.append(finding("DG014", "info", p, f"{(self.today - up).days}일 동안 갱신 없음 — 아직 맞는지 확인"))
            if m.get("type") == "decision":
                self._check_decision(d)
        self._check_graph()
        return f

    def _check_graph(self):
        std, f, inc = self.std, self.findings, self.inbound()
        for sid, d in self.docs.items():
            p, m = d["path"], d["meta"]
            for kind, targets in self.relations(d).items():
                for t in as_list(targets):
                    if t not in self.docs:
                        f.append(finding("DG006", "error", p, f"{kind} → '{t}' 가 없음 (깨진 관계)"))
                        continue
                    tm = self.docs[t]["meta"]
                    if kind == "supersedes":
                        if tm.get("status") != "archived":
                            f.append(finding("DG010", "warn", p, f"supersedes '{t}' 인데 대상이 archived 가 아님"))
                    elif tm.get("status") == "archived" and m.get("status") != "archived":
                        f.append(finding("DG007", "warn", p, f"{kind} → '{t}' 는 archived 문서다 — 대체 문서로 고친다"))
                    if kind == "conflicts_with" and m.get("status") == "approved" and tm.get("status") == "approved" \
                            and sid < t:
                        f.append(finding("DG009", "error", p, f"'{t}' 와 conflicts_with 인데 둘 다 approved"))
                    if kind in std["abstractionCheckedRelations"]:
                        a, b = _level(m), _level(tm)
                        if a is not None and b is not None and a < b:
                            f.append(finding("DG011", "warn", p,
                                             f"추상 역행 — L{a} 문서가 L{b} 문서 '{t}' 에 {kind} (위가 아래에 기대면 아래 변경에 위가 흔들린다)"))
            n_in, n_out = len(inc[sid]), sum(len(as_list(v)) for v in self.relations(d).values())
            if n_in == 0 and n_out == 0 and m.get("status") != "archived" and m.get("abstraction") != "L0":
                f.append(finding("DG012", "info", p, "관계가 하나도 없음 — 다른 문서와 연결하거나 폐기 후보로 본다"))
            if n_in > std["hubInbound"]:
                f.append(finding("DG013", "info", p, f"들어오는 관계 {n_in}개 (> {std['hubInbound']}) — 나눌 수 있는지 본다"))
            if m.get("type") == "gdd":
                for t in as_list(self.relations(d).get("requires")):
                    td = self.docs.get(t)
                    if not td or td["meta"].get("type") != "gdd":
                        continue
                    back = [x for x in inc[sid] if x[0] == t] or [
                        k for k, v in self.relations(td).items() if sid in as_list(v)]
                    mentioned = sid in td["body"] or str(m.get("title", "")) in td["body"]
                    if not back and not mentioned:
                        f.append(finding("DG015", "warn", p,
                                         f"'{t}' 에 의존하는데 '{t}' 쪽 문서는 이 문서를 언급하지 않는다 (design-docs.md 양방향 규칙)"))
        self._check_cycles()

    def _check_cycles(self):
        adj = {i: [t for k in GRAPH_ORDER_RELATIONS for t in as_list(self.relations(d).get(k)) if t in self.docs]
               for i, d in self.docs.items()}
        color, stack, reported = {i: 0 for i in adj}, [], set()

        def visit(u):
            color[u] = 1
            stack.append(u)
            for v in adj[u]:
                if color[v] == 0:
                    visit(v)
                elif color[v] == 1:
                    cyc = stack[stack.index(v):] + [v]
                    key = frozenset(cyc)
                    if key not in reported:
                        reported.add(key)
                        self.findings.append(finding("DG008", "error", self.docs[v]["path"],
                                                     "순환 — " + " → ".join(cyc), cycle=cyc))
            stack.pop()
            color[u] = 2

        sys.setrecursionlimit(max(1000, len(adj) * 2 + 100))
        for i in sorted(adj):
            if color[i] == 0:
                visit(i)

    def _check_decision(self, d):
        std, f, m, p = self.std["decision"], self.findings, d["meta"], d["path"]
        did = str(m.get("id", ""))
        if did and not re.match(std["idPattern"], did):
            f.append(finding("DG101", "warn", p, f"결정 id '{did}' 가 D<연도>-<번호 3자리> 형식이 아님 (next-id 로 받는다)"))
        for k in std["required"]:
            if not str(m.get(k) or "").strip():
                f.append(finding("DG102", "error", p, f"결정 필수 필드 '{k}' 없음"))
        if m.get("impact") and m["impact"] not in std["impact"]:
            f.append(finding("DG102", "error", p, f"impact '{m['impact']}' 는 T0~T4 가 아님"))
        heads = set(re.findall(r"^##\s+(.+?)\s*$", d["body"], re.M))
        missing = [s for s in std["bodySections"] if not any(h.startswith(s) for h in heads)]
        if missing:
            f.append(finding("DG103", "warn", p, f"본문 절 없음: {', '.join(missing)}"))
        for k, v in m.items():
            # 따옴표 없이 쓴 [MISSING] 은 YAML 목록 ["MISSING"] 으로 읽힌다 — 두 형태 모두 잡는다
            if "[MISSING]" in str(v) or v == ["MISSING"]:
                f.append(finding("DG105", "error", p, f"'{k}' 가 [MISSING] — 담당 · 근거가 정해지기 전에는 승인하지 않는다"))
        if "[MISSING]" in d["body"]:
            f.append(finding("DG105", "error", p, "본문에 [MISSING] 이 남아 있음"))
        # 템플릿 안내문(<…>)이 남은 줄 — 표 칸 안의 <A> 같은 것도 포함
        left = [ln.strip() for ln in d["body"].split("\n") if re.search(r"<[^<>\n]{1,200}>", ln) and "<!--" not in ln]
        if left:
            f.append(finding("DG106", "warn", p, f"템플릿 안내문이 {len(left)}줄 남아 있음 — 예: {left[0][:60]}"))
        ra = _date(m.get("review_after", ""))
        if m.get("status") == "approved" and ra and ra < self.today:
            sec = re.search(r"^##\s+사후 확인.*?$(.*?)(?=^##\s|\Z)", d["body"], re.M | re.S)
            body = (sec.group(1) if sec else "").strip()
            if not body or "미측정" in body or "TODO" in body:
                f.append(finding("DG104", "info", p, f"사후 확인 시기({ra}) 지남 — 실측을 '사후 확인' 절에 적는다"))

    # ------------------------------------------------------------------ 영향 범위
    def impact(self, target):
        doc = self.docs.get(target) or next((d for d in self.docs.values() if d["path"] == target.replace("\\", "/")), None)
        if not doc:
            raise SystemExit(f"오류: '{target}' 를 id 나 경로로 찾지 못함 (프런트매터 있는 design/ 문서만)")
        tid, title, path = doc["meta"]["id"], str(doc["meta"].get("title", "")), doc["path"]
        rows, seen = [], set()

        def add(kind, ref, why, strength):
            if (ref, why) in seen or ref == path:
                return
            seen.add((ref, why))
            rows.append({"kind": kind, "ref": ref, "why": why, "strength": strength})

        inc = self.inbound()
        for sid, kind in inc[tid]:
            add("문서", self.docs[sid]["path"], f"{sid} --{kind}--> {tid}",
                "직접" if kind in ("requires", "derives_from", "part_of", "conflicts_with") else "간접")
        for t in as_list(self.relations(doc).get("affects")):
            if t in self.docs:
                add("문서", self.docs[t]["path"], f"{tid} --affects--> {t}", "직접")
        # 2단계 — 직접 영향 문서를 다시 requires 하는 문서
        direct = [r["ref"] for r in rows if r["strength"] == "직접"]
        for sid, d in self.docs.items():
            for t in as_list(self.relations(d).get("requires")):
                if t in self.docs and self.docs[t]["path"] in direct and d["path"] not in direct:
                    add("문서", d["path"], f"{sid} --requires--> {t} (2단계)", "간접")
        # 본문 언급 · 링크 — 프런트매터 없는 문서와 ADR 까지
        needles = [tid] + ([title] if len(title) >= 3 else [])
        link = os.path.basename(path)
        for d in iter_docs(self.root, ("design", "docs/architecture")):
            if "error" in d or d["path"] == path:
                continue
            text = d.get("body", "")
            hit = next((n for n in needles if n and n in text), None)
            if hit:
                add("언급", d["path"], f"본문에 '{hit}'", "약")
            elif link in text:
                add("링크", d["path"], f"{link} 로 링크", "약")
        # 데이터 · 코드 언급 (id 만 — 제목은 오탐이 많다)
        for base in ("design/data", "assets/data"):
            b = os.path.join(self.root, *base.split("/"))
            for dirpath, _, files in os.walk(b):
                for n in files:
                    fp = os.path.join(dirpath, n)
                    try:
                        with open(fp, encoding="utf-8") as fh:
                            if tid in fh.read():
                                add("데이터", os.path.relpath(fp, self.root).replace("\\", "/"), f"'{tid}' 언급", "약")
                    except (UnicodeDecodeError, OSError):
                        pass
        order = {"직접": 0, "간접": 1, "약": 2}
        rows.sort(key=lambda r: (order[r["strength"]], r["ref"]))
        return doc, rows

    # ------------------------------------------------------------------ 지도
    def mermaid(self):
        out = ["```mermaid", "flowchart TD"]
        cls = {f"L{i}": c for i, c in enumerate(("#f6d365", "#a1c4fd", "#c2e9fb", "#d4fc79", "#e0e0e0"))}
        ids = {i: f"n{k}" for k, i in enumerate(sorted(self.docs))}
        for i in sorted(self.docs):
            m = self.docs[i]["meta"]
            label = f"{i}<br/>{m.get('title', '')}".replace('"', "'")
            out.append(f'  {ids[i]}["{label}"]')
            if m.get("abstraction") in cls:
                out.append(f"  style {ids[i]} fill:{cls[m['abstraction']]}")
        for i in sorted(self.docs):
            for kind, targets in sorted(self.relations(self.docs[i]).items()):
                for t in as_list(targets):
                    if t in ids:
                        arrow = "-.->" if kind in ("affects", "conflicts_with") else "-->"
                        out.append(f"  {ids[i]} {arrow}|{kind}| {ids[t]}")
        out.append("```")
        return "\n".join(out)

    def next_decision_id(self, year):
        nums = [int(i.split("-")[1]) for i in self.docs if re.match(rf"^D{year}-\d{{3}}$", i)]
        archive = os.path.join(self.root, "design", "decisions")
        if os.path.isdir(archive):  # 프런트매터가 깨진 카드도 번호를 쓴 것으로 본다 — 재사용 금지
            for n in os.listdir(archive):
                m = re.match(rf"^D{year}-(\d{{3}})", n)
                if m:
                    nums.append(int(m.group(1)))
        return f"D{year}-{(max(nums) + 1 if nums else 1):03d}"


def main(argv=None):
    for s in (sys.stdout, sys.stderr):
        try:
            s.reconfigure(encoding="utf-8")
        except (AttributeError, ValueError):
            pass
    ap = argparse.ArgumentParser(prog="design_graph", description="기획 문서 그래프 · 결정 카드 검사")
    ap.add_argument("--root", default=os.getcwd())
    sub = ap.add_subparsers(dest="cmd", required=True)
    p = sub.add_parser("check")
    p.add_argument("--dirs", nargs="+", default=["design"])
    p.add_argument("--json", action="store_true")
    p = sub.add_parser("impact")
    p.add_argument("target")
    p.add_argument("--json", action="store_true")
    p = sub.add_parser("map")
    p.add_argument("--out")
    p = sub.add_parser("next-id")
    p.add_argument("--year", type=int, default=datetime.date.today().year)
    args = ap.parse_args(argv)

    g = Graph(args.root, getattr(args, "dirs", ("design",)))
    if args.cmd == "check":
        f = g.check()
        not_run = [f"프런트매터 없는 문서 {len(g.no_front)}개 — 그래프 밖 ({', '.join(g.no_front[:5])}"
                   + (" …" if len(g.no_front) > 5 else "") + ")"] if g.no_front else []
        if not g.docs:
            not_run.append("그래프 검사 전체 — 프런트매터 있는 문서가 없음")
        print_report(f"기획 문서 그래프 검사 — 문서 {len(g.docs)}개", f, not_run, args.json,
                     {"documents": len(g.docs), "withoutFrontmatter": g.no_front})
        return 1 if any(x["severity"] == "error" for x in f) else 0
    if args.cmd == "impact":
        doc, rows = g.impact(args.target)
        if args.json:
            import json
            print(json.dumps({"target": doc["meta"]["id"], "path": doc["path"], "rows": rows}, ensure_ascii=False, indent=1))
        else:
            print(f"# 영향 범위 — {doc['meta']['id']} ({doc['path']})\n")
            print("| 강도 | 종류 | 대상 | 근거 |\n|---|---|---|---|")
            for r in rows:
                print(f"| {r['strength']} | {r['kind']} | {r['ref']} | {r['why']} |")
            if not rows:
                print("| - | - | 영향받는 문서 없음 | - |")
            print("\n누락보다 과잉을 택한다 — '약' 은 사람이 걸러 낸다. 우선순위 · 작업 지시는 하지 않는다.")
        return 0
    if args.cmd == "map":
        text = "# 기획 문서 관계도 (design_graph.py map — 직접 고치지 않는다)\n\n" + g.mermaid() + "\n"
        if args.out:
            out = os.path.join(g.root, *args.out.split("/"))
            os.makedirs(os.path.dirname(out), exist_ok=True)
            with open(out, "w", encoding="utf-8", newline="\n") as fh:
                fh.write(text)
            print(f"관계도: {args.out} (문서 {len(g.docs)}개)")
        else:
            print(text)
        return 0
    if args.cmd == "next-id":
        print(g.next_decision_id(args.year))
        return 0
    return 2


if __name__ == "__main__":
    sys.exit(main())
