"""design_graph 테스트 — 규칙마다 실제로 걸리는 문서를 만들어 확인한다."""
import datetime
import os
import sys

TOOL_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, TOOL_DIR)

import design_graph as G  # noqa: E402
from designlib import ParseError, parse_frontmatter  # noqa: E402

TODAY = datetime.date(2026, 10, 30)


def doc(root, rel, **meta):
    body = meta.pop("body", "")
    rels = meta.pop("relations", None)
    lines = ["---"]
    for k, v in meta.items():
        lines.append(f"{k}: [{', '.join(v)}]" if isinstance(v, list) else f"{k}: {v}")
    if rels:
        lines.append("relations:")
        for k, v in rels.items():
            lines.append(f"  {k}: [{', '.join(v)}]")
    lines.append("---")
    path = os.path.join(root, *rel.split("/"))
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        f.write("\n".join(lines) + "\n" + body + "\n")


def base(**kw):
    m = {"title": "제목", "type": "gdd", "status": "draft", "owner": "기획", "updated": "2026-10-01", "abstraction": "L1"}
    m.update(kw)
    return m


def rules(root):
    g = G.Graph(str(root), today=TODAY)
    return g, [(f["rule"], f["path"]) for f in g.check()]


def test_parser_reads_lists_maps_and_comments():
    meta, body, _ = parse_frontmatter("---\nid: SYS-a  # 주석\ntags:\n  - x\n  - \"y z\"\nrelations:\n  affects: [SYS-b, SYS-c]\n"
                                      "  requires:\n    - SYS-d\n---\n본문")
    assert meta["id"] == "SYS-a" and meta["tags"] == ["x", "y z"]
    assert meta["relations"] == {"affects": ["SYS-b", "SYS-c"], "requires": ["SYS-d"]}
    assert body.strip() == "본문"


def test_parser_rejects_unclosed_frontmatter():
    try:
        parse_frontmatter("---\nid: x\n본문", "a.md")
    except ParseError as e:
        assert "닫히지" in e.msg
    else:
        raise AssertionError("ParseError 가 나야 한다")


def test_clean_graph_has_no_errors(tmp_path):
    doc(tmp_path, "design/gdd/combat.md", id="SYS-combat", **base(), relations={"requires": ["SYS-input"]},
        body="입력 시스템(SYS-input)에 의존")
    doc(tmp_path, "design/gdd/input.md", id="SYS-input", **base(), body="전투(SYS-combat)가 이 시스템을 쓴다")
    g, found = rules(tmp_path)
    assert not [r for r in found if r[0] in ("DG002", "DG003", "DG004", "DG006", "DG008", "DG009", "DG015")]
    assert len(g.docs) == 2


def test_required_values_duplicates_and_broken_relation(tmp_path):
    doc(tmp_path, "design/a.md", id="SYS-a", **base(status="done", owner=""), relations={"requires": ["SYS-zzz"]})
    doc(tmp_path, "design/b.md", id="SYS-a", **base())
    _, found = rules(tmp_path)
    names = {r for r, _ in found}
    assert {"DG002", "DG003", "DG004", "DG006"} <= names


def test_cycle_conflict_supersedes_archived_link(tmp_path):
    doc(tmp_path, "design/a.md", id="SYS-a", **base(status="approved"),
        relations={"requires": ["SYS-b"], "conflicts_with": ["SYS-c"]})
    doc(tmp_path, "design/b.md", id="SYS-b", **base(), relations={"requires": ["SYS-a"]})
    doc(tmp_path, "design/c.md", id="SYS-c", **base(status="approved"))
    doc(tmp_path, "design/d.md", id="SYS-d", **base(), relations={"supersedes": ["SYS-c"], "affects": ["SYS-e"]})
    doc(tmp_path, "design/e.md", id="SYS-e", **base(status="archived"))
    doc(tmp_path, "design/f.md", id="SYS-f", **base(), relations={"affects": ["SYS-e"]})
    _, found = rules(tmp_path)
    names = [r for r, _ in found]
    assert "DG008" in names and "DG009" in names and "DG010" in names
    assert ("DG007", "design/f.md") in found


def test_abstraction_reversal_orphan_stale_and_gdd_bidirectional(tmp_path):
    doc(tmp_path, "design/pillar.md", id="PIL-core", **base(type="pillar", abstraction="L0"),
        relations={"requires": ["DAT-curve"]})
    doc(tmp_path, "design/curve.md", id="DAT-curve", **base(abstraction="L3", type="spec"))
    doc(tmp_path, "design/lonely.md", id="SYS-lonely", **base(updated="2026-01-01"))
    doc(tmp_path, "design/gdd/a.md", id="SYS-gdda", **base(), relations={"requires": ["SYS-gddb"]})
    doc(tmp_path, "design/gdd/b.md", id="SYS-gddb", **base(), body="다른 이야기")
    _, found = rules(tmp_path)
    assert ("DG011", "design/pillar.md") in found
    assert ("DG012", "design/lonely.md") in found
    assert ("DG014", "design/lonely.md") in found
    assert ("DG015", "design/gdd/a.md") in found


def test_decision_card_rules(tmp_path):
    good = "## 결정\nx\n## 이유\ny\n## 검토한 대안\nz\n## 영향\nw\n## 사후 확인\n미측정\n"
    doc(tmp_path, "design/decisions/D2026-001.md", id="D2026-001", **base(type="decision", status="approved"),
        impact="T2", decided_by="리드", review_after="2026-10-01", body=good)
    doc(tmp_path, "design/decisions/D2026-002.md", id="D2026-002", **base(type="decision", owner="[MISSING]"),
        impact="T9", body="## 결정\nx\n")
    doc(tmp_path, "design/decisions/bad.md", id="DEC-1", **base(type="decision"), impact="T3", decided_by="a", body=good)
    g, found = rules(tmp_path)
    assert ("DG104", "design/decisions/D2026-001.md") in found
    two = [r for r, p in found if p.endswith("D2026-002.md")]
    assert "DG102" in two and "DG103" in two and "DG105" in two
    assert ("DG101", "design/decisions/bad.md") in found
    assert g.next_decision_id(2026) == "D2026-003"


def test_documents_without_frontmatter_are_named_not_checked(tmp_path, capsys):
    os.makedirs(tmp_path / "design" / "gdd")
    (tmp_path / "design" / "gdd" / "old.md").write_text("# 예전 GDD\n", encoding="utf-8")
    code = G.main(["--root", str(tmp_path), "check"])
    out = capsys.readouterr().out
    assert code == 0 and "검사 안 함" in out and "old.md" in out


def test_impact_finds_inbound_affects_two_hop_and_mentions(tmp_path):
    doc(tmp_path, "design/gdd/economy.md", id="SYS-economy", **base(title="경제 시스템"), relations={"affects": ["SYS-shop"]})
    doc(tmp_path, "design/gdd/craft.md", id="SYS-craft", **base(), relations={"requires": ["SYS-economy"]})
    doc(tmp_path, "design/gdd/shop.md", id="SYS-shop", **base())
    doc(tmp_path, "design/gdd/quest.md", id="SYS-quest", **base(), relations={"requires": ["SYS-craft"]})
    os.makedirs(tmp_path / "docs" / "architecture")
    (tmp_path / "docs" / "architecture" / "adr-0001.md").write_text("경제 시스템 저장 구조\n", encoding="utf-8")
    g = G.Graph(str(tmp_path), today=TODAY)
    _, rows = g.impact("SYS-economy")
    got = {(r["ref"], r["strength"]) for r in rows}
    assert ("design/gdd/craft.md", "직접") in got
    assert ("design/gdd/shop.md", "직접") in got
    assert ("design/gdd/quest.md", "간접") in got
    assert ("docs/architecture/adr-0001.md", "약") in got


def test_map_writes_mermaid(tmp_path):
    doc(tmp_path, "design/a.md", id="SYS-a", **base(), relations={"affects": ["SYS-b"]})
    doc(tmp_path, "design/b.md", id="SYS-b", **base())
    assert G.main(["--root", str(tmp_path), "map", "--out", "design/graph.md"]) == 0
    text = (tmp_path / "design" / "graph.md").read_text(encoding="utf-8")
    assert "flowchart TD" in text and "|affects|" in text


def test_unfilled_template_placeholders_are_flagged(tmp_path):
    body = "## 결정\n<무엇을 하기로 했나>\n## 이유\n플레이테스트 3회 관찰\n## 검토한 대안\n| <A> | <결과> |\n## 영향\nx\n## 사후 확인\n미측정\n"
    doc(tmp_path, "design/decisions/D2026-001.md", id="D2026-001", **base(type="decision"), impact="T3", decided_by="a",
        body=body)
    _, found = rules(tmp_path)
    assert ("DG106", "design/decisions/D2026-001.md") in found
