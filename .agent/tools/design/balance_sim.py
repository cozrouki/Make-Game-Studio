#!/usr/bin/env python3
"""balance_sim — 결정론 밸런스 시뮬레이션 · 후보 비교 · 경제 흐름 게이트 (표준 라이브러리만).

같은 시드면 같은 결과가 나와야 한다. 그래야 후보 A · B 의 차이가 값 변경 때문인지 운 때문인지 가를 수 있다.
계산은 코드가 하고, AI 는 결과 해석 · 이상치 설명 · 다음 후보 제안에만 쓴다 (/ko-balance-sim).

    python .agent/tools/design/balance_sim.py run     <spec.json> [--root R] [--out <폴더>] [--json]
    python .agent/tools/design/balance_sim.py economy <spec.json> [--root R] [--out <폴더>] [--json]

run — 모델 파일(파이썬)에 `simulate(params: dict, rng: random.Random) -> dict[str, float]` 하나를 둔다.
      전역 random · time 을 쓰지 말고 넘겨받은 rng 만 쓴다 (재현성 검사가 잡는다).
  spec: {"model": "design/balance/combat_model.py", "runs": 1000, "seed": 20261030,
         "baseline": {...}, "candidates": {"A": {...변경분}}, "targets": {"지표": {"min": x, "max": y}},
         "expected": {"지표": 명세값}}
  규칙  BS001 모델 · spec 오류              BS002 결정론 깨짐(같은 시드 다른 결과)
        BS003 목표 범위 밖(평균)            BS004 명세값과 구조적 차이(95% 신뢰구간 밖) — 안이면 통계적 분산(info)
        BS005 이상치 run(|z| > 4) 개수      BS006 목표가 없는 지표(판정 안 함)

economy — 코드 없이 자원 흐름(source · sink)을 플레이어층별로 일 단위 시뮬레이션한다.
  spec: {"days": 90, "runs": 200, "seed": 1,
         "segments": {"casual": {"share": 0.7, "hoursPerDay": 1.0}, "core": {"share": 0.3, "hoursPerDay": 3.0}},
         "resources": {"gold": {"sources": [{"id": "quest", "perHour": 120, "jitter": 0.2}],
                                "sinks": [{"id": "repair", "perHour": 60, "jitter": 0.1}],
                                "netPerDay": {"min": 0, "max": 400}, "tolerance": 0.10}}}
  규칙  EC001 spec 오류    EC002 하루 순증가(평균)가 목표 밖    EC003 누적량이 계획(지터 없는 기대값)과 tolerance 넘게 벌어짐
        EC004 플레이어층 간 하루 순증가 격차(최대/최소 > 3배 — info)    EC005 sink 없는 자원(무한 누적 — warn)
판정(PASS/FAIL)은 스킬이 낸다. 이 도구는 error(목표 위반 · 결정론 깨짐) · warn · info 와 수치 표만 낸다.
종료 코드: 0 = error 없음 · 1 = error 있음 · 2 = 사용법 · spec · 모델 로드 실패.
"""
import argparse
import datetime
import importlib.util
import json
import math
import os
import random
import statistics
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from designlib import finding, print_report  # noqa: E402

REPRO_RUNS = 30
Z_OUTLIER = 4.0


class SpecError(Exception):
    pass


def _load_json(path):
    try:
        with open(path, encoding="utf-8") as f:
            return json.load(f)
    except (OSError, json.JSONDecodeError) as e:
        raise SpecError(f"spec 읽기 실패: {path} — {e}")


def _load_model(path):
    if not os.path.isfile(path):
        raise SpecError(f"모델 파일 없음: {path}")
    spec = importlib.util.spec_from_file_location("balance_model", path)
    mod = importlib.util.module_from_spec(spec)
    try:
        spec.loader.exec_module(mod)
    except Exception as e:  # 사용자 모델의 오류를 그대로 알린다
        raise SpecError(f"모델 로드 실패: {path} — {type(e).__name__}: {e}")
    if not callable(getattr(mod, "simulate", None)):
        raise SpecError(f"모델에 simulate(params, rng) 함수가 없음: {path}")
    return mod.simulate


def _summary(values):
    vs = sorted(values)
    n = len(vs)
    mean = statistics.fmean(vs)
    sd = statistics.pstdev(vs) if n > 1 else 0.0

    def q(p):
        return vs[min(n - 1, max(0, int(round(p * (n - 1)))))]
    return {"mean": mean, "sd": sd, "p5": q(0.05), "p50": q(0.5), "p95": q(0.95), "n": n}


def _run_many(simulate, params, runs, seed):
    out = []
    for i in range(runs):
        res = simulate(dict(params), random.Random(seed + i))
        if not isinstance(res, dict):
            raise SpecError(f"simulate 가 dict 를 돌려주지 않음 (run {i}: {type(res).__name__})")
        out.append({k: float(v) for k, v in res.items()})
    return out


def run_combat(spec, root):
    for k in ("model", "baseline"):
        if k not in spec:
            raise SpecError(f"spec 에 '{k}' 없음")
    runs, seed = int(spec.get("runs", 1000)), int(spec.get("seed", 1))
    simulate = _load_model(os.path.join(root, *spec["model"].split("/")))
    targets, expected = spec.get("targets", {}), spec.get("expected", {})
    variants = {"baseline": dict(spec["baseline"])}
    for name, delta in (spec.get("candidates") or {}).items():
        variants[name] = dict(spec["baseline"], **delta)

    findings, table = [], {}
    # 재현성 — 같은 시드로 두 번 돌려 결과가 같아야 한다
    first = _run_many(simulate, variants["baseline"], REPRO_RUNS, seed)
    again = _run_many(simulate, variants["baseline"], REPRO_RUNS, seed)
    if first != again:
        findings.append(finding("BS002", "error", spec["model"],
                                "같은 시드에서 결과가 다르다 — 전역 random · time · 딕셔너리 순서 등 비결정 요소를 쓰는지 본다"))
    for name, params in variants.items():
        results = _run_many(simulate, params, runs, seed)
        metrics = sorted({k for r in results for k in r})
        table[name] = {"params": params, "metrics": {}}
        for m in metrics:
            vals = [r[m] for r in results if m in r]
            s = _summary(vals)
            table[name]["metrics"][m] = s
            t = targets.get(m)
            if t is None:
                if name == "baseline":
                    findings.append(finding("BS006", "info", name, f"'{m}' 은 목표 범위가 없어 판정하지 않는다"))
            elif not (t.get("min", -math.inf) <= s["mean"] <= t.get("max", math.inf)):
                findings.append(finding("BS003", "error", name,
                                        f"'{m}' 평균 {s['mean']:.4g} 가 목표 [{t.get('min', '-∞')}, {t.get('max', '∞')}] 밖",
                                        metric=m, value=s["mean"]))
            if m in expected and name == "baseline":
                half = 1.96 * s["sd"] / math.sqrt(s["n"]) if s["n"] > 1 else 0.0
                diff = s["mean"] - float(expected[m])
                if abs(diff) > half:
                    findings.append(finding("BS004", "warn", name,
                                            f"'{m}' 시뮬 평균 {s['mean']:.4g} vs 명세 {expected[m]} — 차이 {diff:+.4g} 가 "
                                            f"95% 구간(±{half:.3g}) 밖: 공식 · 명세 · 모델 중 하나가 다르다(구조적 차이)",
                                            metric=m))
                else:
                    findings.append(finding("BS004", "info", name,
                                            f"'{m}' 명세 {expected[m]} 와의 차이 {diff:+.4g} 는 95% 구간 안 — 통계적 분산", metric=m))
            if s["sd"] > 0:
                n_out = sum(1 for v in vals if abs(v - s["mean"]) / s["sd"] > Z_OUTLIER)
                if n_out:
                    findings.append(finding("BS005", "info", name, f"'{m}' 이상치 run {n_out}개 (|z| > {Z_OUTLIER:g}) — 원인 설명 필요",
                                            metric=m))
    return findings, {"runs": runs, "seed": seed, "variants": table}


def run_economy(spec):
    try:
        days, runs, seed = int(spec["days"]), int(spec.get("runs", 200)), int(spec.get("seed", 1))
        segments, resources = spec["segments"], spec["resources"]
    except (KeyError, ValueError, TypeError) as e:
        raise SpecError(f"economy spec 형식 오류: {e}")
    share = sum(float(s.get("share", 0)) for s in segments.values())
    findings, table = [], {}
    if abs(share - 1.0) > 1e-6:
        findings.append(finding("EC001", "warn", "segments", f"share 합이 {share:g} (1 이어야 가중 평균이 맞다)"))
    for rname, r in resources.items():
        if not r.get("sinks"):
            findings.append(finding("EC005", "warn", rname, "sink 가 없다 — 쓸 곳 없이 계속 쌓인다 (의도면 이유를 기록)"))
        tol = float(r.get("tolerance", 0.10))
        table[rname] = {}
        per_day_means = {}
        for sname, seg in segments.items():
            hours = float(seg.get("hoursPerDay", 1.0))
            planned_day = hours * (sum(float(s["perHour"]) for s in r.get("sources", []))
                                   - sum(float(s["perHour"]) for s in r.get("sinks", [])))
            finals, daily = [], []
            for i in range(runs):
                rng = random.Random(f"{seed}:{rname}:{sname}:{i}")
                total = 0.0
                for _ in range(days):
                    day = 0.0
                    for s in r.get("sources", []):
                        day += hours * float(s["perHour"]) * (1 + rng.uniform(-1, 1) * float(s.get("jitter", 0)))
                    for s in r.get("sinks", []):
                        day -= hours * float(s["perHour"]) * (1 + rng.uniform(-1, 1) * float(s.get("jitter", 0)))
                    total += day
                    daily.append(day)
                finals.append(total)
            fin, dsum = _summary(finals), _summary(daily)
            planned = planned_day * days
            table[rname][sname] = {"plannedPerDay": planned_day, "perDay": dsum, "cumulative": fin, "plannedCumulative": planned}
            per_day_means[sname] = dsum["mean"]
            band = r.get("netPerDay")
            if band and not (band.get("min", -math.inf) <= dsum["mean"] <= band.get("max", math.inf)):
                findings.append(finding("EC002", "error", f"{rname}/{sname}",
                                        f"하루 순증가 평균 {dsum['mean']:.4g} 가 목표 [{band.get('min', '-∞')}, {band.get('max', '∞')}] 밖"))
            if planned != 0 and abs(fin["mean"] - planned) / abs(planned) > tol:
                findings.append(finding("EC003", "error", f"{rname}/{sname}",
                                        f"{days}일 누적 평균 {fin['mean']:.4g} 가 계획 {planned:.4g} 와 {tol:.0%} 넘게 다르다"))
        pos = [v for v in per_day_means.values() if v > 0]
        if len(pos) >= 2 and max(pos) / min(pos) > 3:
            findings.append(finding("EC004", "info", rname,
                                    "플레이어층 간 하루 순증가 격차 " + ", ".join(f"{k} {v:.4g}" for k, v in per_day_means.items())))
    return findings, {"days": days, "runs": runs, "seed": seed, "resources": table}


def _write_out(root, out_dir, kind, spec_path, payload, findings):
    if not out_dir:
        return None
    d = os.path.join(root, *out_dir.split("/"))
    os.makedirs(d, exist_ok=True)
    name = f"{os.path.splitext(os.path.basename(spec_path))[0]}-{kind}-{datetime.date.today().isoformat()}.json"
    path = os.path.join(d, name)
    with open(path, "w", encoding="utf-8", newline="\n") as f:
        json.dump({"spec": spec_path, "kind": kind, "result": payload, "findings": findings}, f, ensure_ascii=False, indent=1)
    return os.path.relpath(path, root).replace("\\", "/")


def _print_table(kind, payload):
    if kind == "run":
        for name, v in payload["variants"].items():
            print(f"\n## {name}  {json.dumps(v['params'], ensure_ascii=False)}")
            print("| 지표 | 평균 | 표준편차 | p5 | p50 | p95 |\n|---|---|---|---|---|---|")
            for m, s in v["metrics"].items():
                print(f"| {m} | {s['mean']:.4g} | {s['sd']:.3g} | {s['p5']:.4g} | {s['p50']:.4g} | {s['p95']:.4g} |")
    else:
        for rname, segs in payload["resources"].items():
            print(f"\n## {rname} ({payload['days']}일 · {payload['runs']}회)")
            print("| 층 | 계획/일 | 시뮬/일(평균) | 누적 평균 | 계획 누적 | p5~p95 누적 |\n|---|---|---|---|---|---|")
            for s, v in segs.items():
                c = v["cumulative"]
                print(f"| {s} | {v['plannedPerDay']:.4g} | {v['perDay']['mean']:.4g} | {c['mean']:.4g} | "
                      f"{v['plannedCumulative']:.4g} | {c['p5']:.4g}~{c['p95']:.4g} |")


def main(argv=None):
    for s in (sys.stdout, sys.stderr):
        try:
            s.reconfigure(encoding="utf-8")
        except (AttributeError, ValueError):
            pass
    ap = argparse.ArgumentParser(prog="balance_sim", description="결정론 밸런스 시뮬레이션")
    ap.add_argument("--root", default=os.getcwd())
    sub = ap.add_subparsers(dest="cmd", required=True)
    for c in ("run", "economy"):
        p = sub.add_parser(c)
        p.add_argument("spec")
        p.add_argument("--out", help="결과 JSON 을 남길 폴더 (예: design/balance/reports) — 결정 카드에 링크한다")
        p.add_argument("--json", action="store_true")
    args = ap.parse_args(argv)
    root = os.path.abspath(args.root)
    spec_path = args.spec.replace("\\", "/")
    try:
        spec = _load_json(os.path.join(root, *spec_path.split("/")) if not os.path.isabs(spec_path) else spec_path)
        findings, payload = run_combat(spec, root) if args.cmd == "run" else run_economy(spec)
    except SpecError as e:
        rule = "BS001" if args.cmd == "run" else "EC001"
        print_report("밸런스 시뮬레이션 — 실행 못 함", [finding(rule, "error", spec_path, str(e))],
                     [f"{args.cmd} 전체 — spec · 모델 오류로 시뮬레이션을 돌리지 않았다"], args.json)
        return 2
    saved = _write_out(root, args.out, args.cmd, spec_path, payload, findings)
    if args.json:
        print_report(f"밸런스 시뮬레이션 ({args.cmd})", findings, (), True, {"result": payload, "saved": saved})
    else:
        print_report(f"밸런스 시뮬레이션 ({args.cmd}) — {spec_path}", findings)
        _print_table(args.cmd, payload)
        if saved:
            print(f"\n결과: {saved}")
    return 1 if any(f["severity"] == "error" for f in findings) else 0


if __name__ == "__main__":
    sys.exit(main())
