"""balance_sim 테스트 — 결정론 · 목표 판정 · 명세 차이 분해 · 경제 게이트."""
import json
import os
import sys

TOOL_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, TOOL_DIR)

import balance_sim as B  # noqa: E402

MODEL = '''
def simulate(params, rng):
    # 공격력 atk 로 HP 1000 을 깎는 데 걸리는 타격 수 — 치명타 확률 crit 로 2배
    hp, hits = 1000.0, 0
    while hp > 0:
        dmg = params["atk"] * (2 if rng.random() < params["crit"] else 1)
        hp -= dmg
        hits += 1
    return {"hits": hits}
'''

BROKEN_MODEL = '''
import random
def simulate(params, rng):
    return {"hits": random.random()}   # 전역 random — 재현 불가
'''


def setup(tmp_path, model=MODEL, **spec):
    (tmp_path / "design" / "balance").mkdir(parents=True)
    (tmp_path / "design" / "balance" / "m.py").write_text(model, encoding="utf-8")
    s = {"model": "design/balance/m.py", "runs": 300, "seed": 7, "baseline": {"atk": 50, "crit": 0.1}}
    s.update(spec)
    (tmp_path / "design" / "balance" / "spec.json").write_text(json.dumps(s), encoding="utf-8")
    return "design/balance/spec.json"


def rules(tmp_path, spec, cmd="run"):
    code = B.main(["--root", str(tmp_path), cmd, spec, "--json"])
    return code


def test_same_seed_same_result(tmp_path):
    setup(tmp_path)
    spec = json.loads((tmp_path / "design" / "balance" / "spec.json").read_text(encoding="utf-8"))
    a = B.run_combat(spec, str(tmp_path))[1]
    b = B.run_combat(spec, str(tmp_path))[1]
    assert a == b


def test_targets_and_candidates(tmp_path, capsys):
    spec = setup(tmp_path, targets={"hits": {"min": 15, "max": 20}}, candidates={"strong": {"atk": 100}})
    code = rules(tmp_path, spec)
    out = json.loads(capsys.readouterr().out)
    bad = [f for f in out["findings"] if f["rule"] == "BS003"]
    assert code == 1 and [f["path"] for f in bad] == ["strong"]   # baseline ~18타 통과 · strong ~9타 미달
    assert set(out["result"]["variants"]) == {"baseline", "strong"}


def test_expected_structural_vs_statistical(tmp_path):
    spec_path = setup(tmp_path, expected={"hits": 30})
    spec = json.loads((tmp_path / spec_path).read_text(encoding="utf-8"))
    f, _ = B.run_combat(spec, str(tmp_path))
    assert [x["severity"] for x in f if x["rule"] == "BS004"] == ["warn"]
    spec["expected"] = {"hits": B.run_combat(spec, str(tmp_path))[1]["variants"]["baseline"]["metrics"]["hits"]["mean"]}
    f, _ = B.run_combat(spec, str(tmp_path))
    assert [x["severity"] for x in f if x["rule"] == "BS004"] == ["info"]


def test_nondeterministic_model_is_caught(tmp_path):
    spec_path = setup(tmp_path, model=BROKEN_MODEL)
    spec = json.loads((tmp_path / spec_path).read_text(encoding="utf-8"))
    f, _ = B.run_combat(spec, str(tmp_path))
    assert any(x["rule"] == "BS002" for x in f)


def test_missing_model_is_named_not_run(tmp_path, capsys):
    spec = setup(tmp_path)
    (tmp_path / "design" / "balance" / "m.py").unlink()
    assert rules(tmp_path, spec) == 2
    out = json.loads(capsys.readouterr().out)
    assert out["notRun"] and out["findings"][0]["rule"] == "BS001"


def test_out_writes_report(tmp_path):
    spec = setup(tmp_path)
    assert B.main(["--root", str(tmp_path), "run", spec, "--out", "design/balance/reports"]) == 0
    assert list((tmp_path / "design" / "balance" / "reports").glob("spec-run-*.json"))


ECON = {"days": 30, "runs": 50, "seed": 3,
        "segments": {"casual": {"share": 0.7, "hoursPerDay": 1}, "core": {"share": 0.3, "hoursPerDay": 4}},
        "resources": {"gold": {"sources": [{"id": "quest", "perHour": 100, "jitter": 0.2}],
                               "sinks": [{"id": "repair", "perHour": 40, "jitter": 0.1}],
                               "netPerDay": {"min": 0, "max": 150}},
                      "gem": {"sources": [{"id": "daily", "perHour": 1}]}}}


def test_economy_gate(tmp_path):
    f, payload = B.run_economy(json.loads(json.dumps(ECON)))
    rules_by = {(x["rule"], x["path"]) for x in f}
    assert ("EC002", "gold/core") in rules_by          # 4시간 × 60 = 240 > 150
    assert ("EC002", "gold/casual") not in rules_by    # 60
    assert ("EC005", "gem") in rules_by
    assert ("EC004", "gold") in rules_by               # 240 / 60 = 4배
    g = payload["resources"]["gold"]["casual"]
    assert abs(g["cumulative"]["mean"] - g["plannedCumulative"]) / g["plannedCumulative"] < 0.10


def test_economy_drift_beyond_tolerance(tmp_path):
    spec = json.loads(json.dumps(ECON))
    spec["resources"]["gold"]["sinks"][0]["jitter"] = 0.0
    spec["resources"]["gold"]["tolerance"] = 0.0001       # 지터 때문에 계획과 조금은 어긋난다 → 아주 좁은 허용치면 걸린다
    f, _ = B.run_economy(spec)
    assert any(x["rule"] == "EC003" for x in f)
