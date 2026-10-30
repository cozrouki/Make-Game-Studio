"""content_pattern 테스트 — 각 규칙이 실패 입력에서 잡히는지, 깨끗한 입력은 error 0 인지 확인한다."""
import datetime
import json
import os
import sys

TOOL_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, TOOL_DIR)

import content_pattern as cp  # noqa: E402

TAGS = {"maxPerRoom": 2, "categories": {"분위기": ["dark", "bright"], "구조": ["narrow", "open"], "위험": ["trap"]}}


def write(path, data):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, ensure_ascii=False), encoding="utf-8")
    return str(path)


def room(rid, conns, **kw):
    d = {"id": rid, "type": "combat", "size": "M", "tags": [], "connections": conns}
    d.update(kw)
    return d


def clean_level(tags="design/levels/tags.json"):
    # R01-R02-R03-R01 삼각형 + R03-R04(목표)
    return {"id": "DUN-ok", "start": "R01", "goal": "R04", "tags": tags, "rooms": [
        room("R01", ["R02", "R03"], tags=["dark"]),
        room("R02", ["R01", "R03"], tags=["narrow", "trap"]),
        room("R03", ["R01", "R02", "R04"]),
        room("R04", ["R03"]),
    ]}


def rules(fs, sev=None):
    return [f["rule"] for f in fs if sev is None or f["severity"] == sev]


def run_level(tmp_path, level, with_tags=True):
    if with_tags:
        write(tmp_path / "design/levels/tags.json", TAGS)
    p = write(tmp_path / "design/levels/lv.json", level)
    return cp.check_level(level, p, str(tmp_path))


# ---------------------------------------------------------------- levels

def test_clean_level_no_errors(tmp_path):
    fs, nr, st = run_level(tmp_path, clean_level())
    assert rules(fs, "error") == []
    assert rules(fs, "warn") == []
    assert nr == []
    assert st["triangles"] == 1
    assert st["branching"] == {"1": 1, "2": 2, "3": 1}
    assert "CP108" in rules(fs, "info")
    assert "CP103" not in rules(fs)  # R04 는 목표라 막다른 길 아님


def test_cp101_goal_unreachable(tmp_path):
    lv = clean_level()
    lv["rooms"][2]["connections"] = ["R01", "R02"]  # R03 → R04 끊음
    lv["rooms"][3]["connections"] = ["R03"]          # R04 → R03 만 남음
    lv["rooms"][3]["oneWay"] = ["R03"]
    fs, _, _ = run_level(tmp_path, lv)
    assert "CP101" in rules(fs, "error")
    assert any(f["rule"] == "CP102" and f.get("room") == "R04" for f in fs)


def test_cp102_isolated_room(tmp_path):
    lv = clean_level()
    lv["rooms"].append(room("R05", []))
    fs, _, _ = run_level(tmp_path, lv)
    assert [f["room"] for f in fs if f["rule"] == "CP102"] == ["R05"]
    assert "CP101" not in rules(fs)


def test_cp103_dead_end_counted(tmp_path):
    lv = clean_level()
    lv["rooms"][1]["connections"].append("R05")
    lv["rooms"].append(room("R05", ["R02"]))
    lv["rooms"].append(room("R06", ["R03"]))
    lv["rooms"][2]["connections"].append("R06")
    fs, _, st = run_level(tmp_path, lv)
    f = next(f for f in fs if f["rule"] == "CP103")
    assert f["severity"] == "info" and f["count"] == 2 and f["rooms"] == ["R05", "R06"]
    assert st["deadEnds"] == 2


def test_cp104_one_way_mismatch_and_intended(tmp_path):
    lv = clean_level()
    lv["rooms"][1]["connections"] = ["R01"]  # R02 → R03 없음, R03 → R02 있음
    fs, _, _ = run_level(tmp_path, lv)
    hits = [f for f in fs if f["rule"] == "CP104"]
    assert [(f["room"], f["target"]) for f in hits] == [("R03", "R02")]
    assert hits[0]["severity"] == "warn"
    # 의도된 일방이면 경고 없음
    lv["rooms"][2]["oneWay"] = ["R02"]
    fs, _, _ = run_level(tmp_path, lv)
    assert "CP104" not in rules(fs)


def test_cp105_missing_target(tmp_path):
    lv = clean_level()
    lv["rooms"][0]["connections"].append("R99")
    fs, _, _ = run_level(tmp_path, lv)
    assert any(f["rule"] == "CP105" and f["target"] == "R99" and f["severity"] == "error" for f in fs)


def test_cp106_unknown_tag_and_cp107_too_many(tmp_path):
    lv = clean_level()
    lv["rooms"][0]["tags"] = ["dark", "spooky"]
    lv["rooms"][1]["tags"] = ["narrow", "trap", "dark"]
    fs, _, _ = run_level(tmp_path, lv)
    assert [f["tag"] for f in fs if f["rule"] == "CP106"] == ["spooky"]
    assert [f["room"] for f in fs if f["rule"] == "CP107"] == ["R02"]


def test_missing_tag_dictionary_is_not_run(tmp_path):
    fs, nr, _ = run_level(tmp_path, clean_level(), with_tags=False)
    assert any("CP106" in n and "CP107" in n for n in nr)
    assert "CP106" not in rules(fs) and "CP107" not in rules(fs)
    # 경로 자체가 없을 때도
    lv = clean_level()
    del lv["tags"]
    fs, nr, _ = run_level(tmp_path, lv, with_tags=False)
    assert any("CP106" in n for n in nr)


def test_tags_resolved_relative_to_level_file(tmp_path):
    write(tmp_path / "design/levels/tags.json", TAGS)
    lv = clean_level(tags="tags.json")
    p = write(tmp_path / "design/levels/lv.json", lv)
    _, nr, _ = cp.check_level(lv, p, str(tmp_path / "elsewhere"))
    assert nr == []


def test_cp100_duplicate_and_missing_start(tmp_path):
    lv = clean_level()
    lv["rooms"].append(room("R01", []))
    lv["start"] = "R77"
    fs, nr, _ = run_level(tmp_path, lv)
    msgs = [f["message"] for f in fs if f["rule"] == "CP100"]
    assert any("중복" in m for m in msgs) and any("R77" in m for m in msgs)
    assert any("CP101" in n for n in nr)


def test_levels_cli_exit_codes(tmp_path, capsys):
    write(tmp_path / "design/levels/tags.json", TAGS)
    good = write(tmp_path / "design/levels/good.json", clean_level())
    bad_lv = clean_level()
    bad_lv["rooms"].append(room("R05", []))
    bad = write(tmp_path / "design/levels/bad.json", bad_lv)
    assert cp.main(["levels", good, "--root", str(tmp_path)]) == 0
    assert cp.main(["levels", bad, "--root", str(tmp_path), "--json"]) == 1
    broken = tmp_path / "broken.json"
    broken.write_text("{nope", encoding="utf-8")
    assert cp.main(["levels", str(broken)]) == 2
    assert cp.main(["levels", str(tmp_path / "none.json")]) == 2
    assert cp.main([]) == 2
    assert cp.main(["levels"]) == 2


def test_levels_cli_json_output(tmp_path, capsys):
    p = write(tmp_path / "lv.json", clean_level(tags="no/such.json"))
    capsys.readouterr()
    assert cp.main(["levels", p, "--root", str(tmp_path), "--json"]) == 0
    out = json.loads(capsys.readouterr().out)
    assert out["levels"][0]["id"] == "DUN-ok"
    assert any("CP106" in n for n in out["notRun"])


# ---------------------------------------------------------------- patterns

TODAY = datetime.date(2026, 10, 30)


def setup_patterns(tmp_path, n_levels=2):
    pdir = tmp_path / "design/patterns"
    write(pdir / "ambush.json", {"id": "PAT-ambush", "status": "active", "kind": "event", "created": "2026-09-01"})
    write(pdir / "old.json", {"id": "PAT-old", "status": "deprecated", "kind": "space", "created": "2025-01-01"})
    write(pdir / "unused.json", {"id": "PAT-unused", "status": "active", "kind": "npc", "created": "2025-01-01"})
    write(pdir / "fresh.json", {"id": "PAT-fresh", "status": "active", "kind": "npc", "created": "2026-10-01"})
    ldir = tmp_path / "design/levels"
    write(ldir / "tags.json", TAGS)  # 레벨이 아닌 JSON — 건너뛴다
    for i in range(n_levels):
        write(ldir / f"lv{i}.json", {"id": f"L{i}", "start": "R01", "goal": "R01", "rooms": [
            room("R01", [], patterns=["PAT-ambush"]),
            room("R02", [], patterns=["PAT-ambush", "PAT-old"] if i == 0 else []),
        ]})
    return str(pdir), str(ldir)


def test_patterns_usage_and_rules(tmp_path):
    pdir, ldir = setup_patterns(tmp_path)
    write(tmp_path / "design/levels/lv_bad.json", {"rooms": [room("R01", [], patterns=["PAT-ghost"])]})
    fs, nr, extra = cp.run_patterns(pdir, [ldir], str(tmp_path), today=TODAY)
    assert extra["usage"] == {"PAT-ambush": 3, "PAT-fresh": 0, "PAT-old": 1, "PAT-unused": 0}
    assert len(extra["levelFiles"]) == 3  # tags.json 제외
    assert [f["pattern"] for f in fs if f["rule"] == "CP201"] == ["PAT-ghost"]
    assert [f["pattern"] for f in fs if f["rule"] == "CP202"] == ["PAT-old"]
    assert [f["pattern"] for f in fs if f["rule"] == "CP203"] == ["PAT-unused"]  # fresh 는 아직 새것
    assert "CP204" in rules(fs, "info")
    assert nr == []


def test_patterns_stale_days_option(tmp_path):
    pdir, ldir = setup_patterns(tmp_path)
    fs, _, _ = cp.run_patterns(pdir, [ldir], str(tmp_path), stale_days=10, today=TODAY)
    assert sorted(f["pattern"] for f in fs if f["rule"] == "CP203") == ["PAT-fresh", "PAT-unused"]


def test_patterns_no_cp204_when_enough_levels(tmp_path):
    pdir, ldir = setup_patterns(tmp_path, n_levels=5)
    fs, _, _ = cp.run_patterns(pdir, [ldir], str(tmp_path), today=TODAY)
    assert "CP204" not in rules(fs)
    assert rules(fs, "error") == []


def test_patterns_bad_created_is_not_run(tmp_path):
    pdir, ldir = setup_patterns(tmp_path)
    write(tmp_path / "design/patterns/nodate.json", {"id": "PAT-nodate", "status": "active", "kind": "npc"})
    fs, nr, _ = cp.run_patterns(pdir, [ldir], str(tmp_path), today=TODAY)
    assert any("CP203" in n and "PAT-nodate" in n for n in nr)


def test_patterns_cli(tmp_path, capsys):
    pdir, ldir = setup_patterns(tmp_path)
    assert cp.main(["patterns", pdir, ldir, "--today", "2026-10-30"]) == 0
    out = capsys.readouterr().out
    assert "| PAT-ambush | active | 3 |" in out
    write(tmp_path / "design/levels/lv_bad.json", {"rooms": [room("R01", [], patterns=["PAT-ghost"])]})
    assert cp.main(["patterns", pdir, ldir, "--json"]) == 1
    assert cp.main(["patterns", str(tmp_path / "nope"), ldir]) == 2


# ---------------------------------------------------------------- tiers

def item(iid, tier, **kw):
    d = {"id": iid, "tier": tier, "volume": 10, "consistency": "mid", "nondeterminism_ok": False,
         "review_cost": "mid", "incident_cost": "mid", "reason": "근거"}
    d.update(kw)
    return d


def test_tiers_recommendations(tmp_path):
    items = [
        item("CNT-legal", "manual", incident_cost="high"),                                     # 보수, 맞음
        item("CNT-quest", "ai-first", consistency="high"),                                     # 보수 권장인데 AI → warn
        item("CNT-bark", "ai-first", volume=200, review_cost="low", nondeterminism_ok=True),   # AI, 맞음
        item("CNT-flavor", "manual", volume=500, review_cost="low", nondeterminism_ok=True),   # AI 권장인데 manual → warn
        item("CNT-mix", "manual", volume=500, review_cost="low", nondeterminism_ok=True, incident_cost="high"),  # 애매
        item("CNT-plain", "rulebook"),                                                         # 어느 쪽도 아님
        item("CNT-noreason", "rulebook", reason=" "),
    ]
    p = write(tmp_path / "tiers.json", {"items": items})
    fs, nr, extra = cp.run_tiers(p, str(tmp_path))
    warn301 = sorted(f["item"] for f in fs if f["rule"] == "CP301" and f["severity"] == "warn")
    info301 = sorted(f["item"] for f in fs if f["rule"] == "CP301" and f["severity"] == "info")
    assert warn301 == ["CNT-flavor", "CNT-quest"]
    assert info301 == ["CNT-mix", "CNT-noreason", "CNT-plain"]
    assert [f["item"] for f in fs if f["rule"] == "CP302"] == ["CNT-noreason"]
    assert rules(fs, "error") == []
    rec = {r["id"]: r["recommended"] for r in extra["recommendations"]}
    assert rec["CNT-legal"] == ["manual", "rulebook"] and rec["CNT-bark"] == ["rulebook+ai", "ai-first"]
    assert "검수 비용 low" in next(f["message"] for f in fs if f.get("item") == "CNT-flavor")
    assert "일관성 high" in next(f["message"] for f in fs if f.get("item") == "CNT-quest")


def test_tiers_ai_volume_threshold(tmp_path):
    p = write(tmp_path / "tiers.json", {"items": [
        item("CNT-a", "manual", volume=99, review_cost="low", nondeterminism_ok=True)]})
    fs, _, _ = cp.run_tiers(p, str(tmp_path))
    assert [f["severity"] for f in fs if f["rule"] == "CP301"] == ["info"]
    fs, _, _ = cp.run_tiers(p, str(tmp_path), ai_volume=50)
    assert [f["severity"] for f in fs if f["rule"] == "CP301"] == ["warn"]


def test_tiers_invalid_values_and_cli(tmp_path):
    p = write(tmp_path / "tiers.json", {"items": [item("CNT-x", "magic", consistency="huge"), {"tier": "manual"}]})
    fs, _, _ = cp.run_tiers(p, str(tmp_path))
    assert rules(fs, "error") == ["CP300", "CP300"]
    assert cp.main(["tiers", p]) == 1
    ok = write(tmp_path / "ok.json", {"items": [item("CNT-legal", "manual", incident_cost="high")]})
    assert cp.main(["tiers", ok]) == 0
    assert cp.main(["tiers", write(tmp_path / "nope.json", {"x": 1})]) == 2
