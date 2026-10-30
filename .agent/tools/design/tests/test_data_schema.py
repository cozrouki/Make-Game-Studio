"""data_schema.py 테스트 — 각 규칙은 그 규칙이 실제로 실패하는 데이터로 확인한다."""
import copy
import json
import os
import sys

TOOL_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, TOOL_DIR)

import data_schema as ds  # noqa: E402

BASE_SCHEMA = {
    "enums": {"Element": ["NONE", "FIRE", "ICE"]},
    "tables": {
        "Monster": {
            "source": "design/data/monster.csv",
            "key": "id",
            "fields": {
                "id": {"type": "string", "pattern": "^MON_[0-9]{3}$"},
                "name": {"type": "string"},
                "hp": {"type": "int", "min": 1, "max": 99999},
                "speed": {"type": "float", "min": 0},
                "element": {"type": "enum", "enum": "Element"},
                "drop": {"type": "ref", "table": "Item", "optional": True},
                "tags": {"type": "list", "item": "string", "optional": True},
            },
        },
        "Item": {"source": "design/data/item.json", "key": "id", "fields": {"id": {"type": "string"}}},
    },
}
HEADER = "id,name,hp,speed,element,drop,tags"
GOOD_ROWS = [
    "MON_001,슬라임,10,1.5,FIRE,ITEM_A,small;green",
    "MON_002,골렘,500,0.5,ICE,,",
]
ITEMS = [{"id": "ITEM_A"}, {"id": "ITEM_B"}]


def setup(tmp_path, schema=None, csv_rows=None, header=HEADER, items=ITEMS, csv_text=None):
    schema = copy.deepcopy(BASE_SCHEMA) if schema is None else schema
    d = tmp_path / "design" / "data"
    d.mkdir(parents=True, exist_ok=True)
    (d / "schema.json").write_text(json.dumps(schema, ensure_ascii=False), encoding="utf-8")
    if csv_text is not None:
        (d / "monster.csv").write_text(csv_text, encoding="utf-8")
    elif csv_rows is not None:
        (d / "monster.csv").write_text("\n".join([header] + csv_rows) + "\n", encoding="utf-8")
    if items is not None:
        (d / "item.json").write_text(json.dumps(items), encoding="utf-8")
    return schema


def run_check(tmp_path, schema):
    findings, not_run, _ = ds.check(schema, "design/data/schema.json", str(tmp_path))
    return findings, not_run


def by_rule(findings, rule, severity=None):
    return [f for f in findings if f["rule"] == rule and (severity is None or f["severity"] == severity)]


def errors(findings):
    return [f for f in findings if f["severity"] == "error"]


# ---------------------------------------------------------------- 깨끗한 데이터

def test_clean_data_has_no_error_or_warn(tmp_path):
    schema = setup(tmp_path, csv_rows=GOOD_ROWS)
    findings, not_run = run_check(tmp_path, schema)
    assert findings == []
    assert not_run == []


def test_csv_with_bom_is_accepted(tmp_path):
    schema = setup(tmp_path, csv_rows=[])
    p = tmp_path / "design" / "data" / "monster.csv"
    p.write_bytes(b"\xef\xbb\xbf" + ("\n".join([HEADER] + GOOD_ROWS) + "\n").encode("utf-8"))
    findings, _ = run_check(tmp_path, schema)
    assert findings == []


def test_cli_exit_codes(tmp_path, capsys):
    setup(tmp_path, csv_rows=GOOD_ROWS)
    assert ds.main(["check", "design/data/schema.json", "--root", str(tmp_path)]) == 0
    setup(tmp_path, csv_rows=["MON_001,슬라임,10,1.5,FIRE,ITEM_ZZZ,"])
    assert ds.main(["check", "design/data/schema.json", "--root", str(tmp_path), "--json"]) == 1
    (tmp_path / "bad.json").write_text("{ not json", encoding="utf-8")
    assert ds.main(["check", "bad.json", "--root", str(tmp_path)]) == 2
    assert ds.main(["check", "missing.json", "--root", str(tmp_path)]) == 2
    assert ds.main(["nope"]) == 2


def test_cli_json_output(tmp_path, capsys):
    setup(tmp_path, csv_rows=["MON_001,슬라임,10,1.5,FIRE,ITEM_ZZZ,"])
    rc = ds.main(["check", "design/data/schema.json", "--root", str(tmp_path), "--json"])
    data = json.loads(capsys.readouterr().out)
    assert rc == 1
    assert any(f["rule"] == "DS007" for f in data["findings"])
    assert data["notRun"] == []


# ---------------------------------------------------------------- DS001 · DS002 스키마

def test_ds001_unknown_type_missing_enum_table_key(tmp_path):
    schema = copy.deepcopy(BASE_SCHEMA)
    f = schema["tables"]["Monster"]["fields"]
    f["hp"]["type"] = "integer"                       # 모르는 타입
    f["element"]["enum"] = "Elem"                     # 없는 enum
    f["drop"]["table"] = "Weapon"                     # 없는 테이블
    schema["tables"]["Item"]["key"] = "code"          # key 필드 없음
    setup(tmp_path, schema=schema, csv_rows=GOOD_ROWS)
    findings, not_run = run_check(tmp_path, schema)
    msgs = " ".join(x["message"] for x in by_rule(findings, "DS001", "error"))
    assert "integer" in msgs and "Elem" in msgs and "Weapon" in msgs and "code" in msgs
    assert any("Item 데이터 검사" in n for n in not_run)
    assert any("Monster.hp" in n for n in not_run)


def test_ds001_bad_pattern_and_list_item(tmp_path):
    schema = copy.deepcopy(BASE_SCHEMA)
    schema["tables"]["Monster"]["fields"]["id"]["pattern"] = "^(MON"
    schema["tables"]["Monster"]["fields"]["tags"]["item"] = "vector"
    setup(tmp_path, schema=schema, csv_rows=GOOD_ROWS)
    findings, not_run = run_check(tmp_path, schema)
    assert len(by_rule(findings, "DS001", "error")) == 2
    assert any("Monster 데이터 검사" in n for n in not_run)   # key 필드 정의 오류 → 테이블 건너뜀


def test_ds002_enum_zero_not_unspecified(tmp_path):
    schema = copy.deepcopy(BASE_SCHEMA)
    schema["enums"]["Element"] = ["FIRE", "ICE"]
    setup(tmp_path, schema=schema, csv_rows=["MON_001,슬라임,10,1.5,ICE,,"])
    findings, _ = run_check(tmp_path, schema)
    hit = by_rule(findings, "DS002")
    assert len(hit) == 1 and hit[0]["severity"] == "warn" and "FIRE" in hit[0]["message"]


def test_ds002_not_raised_for_unspecified_names(tmp_path):
    schema = copy.deepcopy(BASE_SCHEMA)
    schema["enums"]["Element"] = ["Unspecified", "FIRE"]
    setup(tmp_path, schema=schema, csv_rows=["MON_001,슬라임,10,1.5,FIRE,,"])
    findings, _ = run_check(tmp_path, schema)
    assert by_rule(findings, "DS002") == []


# ---------------------------------------------------------------- DS003 데이터 파일

def test_ds003_missing_file_goes_to_not_run(tmp_path):
    schema = setup(tmp_path, csv_rows=None)        # monster.csv 를 만들지 않음
    findings, not_run = run_check(tmp_path, schema)
    hit = by_rule(findings, "DS003")
    assert len(hit) == 1 and hit[0]["severity"] == "warn" and hit[0]["path"] == "design/data/monster.csv"
    assert any(n.startswith("Monster 데이터 검사") and "monster.csv" in n for n in not_run)
    assert errors(findings) == []


def test_ds003_missing_ref_target_data_reports_ref_not_run(tmp_path):
    schema = setup(tmp_path, csv_rows=GOOD_ROWS, items=None)   # item.json 없음
    findings, not_run = run_check(tmp_path, schema)
    assert any("Item 데이터 검사" in n for n in not_run)
    assert any("Monster.drop 참조 검사" in n for n in not_run)
    assert by_rule(findings, "DS007") == []


def test_ds003_unreadable_json_is_error(tmp_path):
    schema = setup(tmp_path, csv_rows=GOOD_ROWS)
    (tmp_path / "design" / "data" / "item.json").write_text('{"id": "x"}', encoding="utf-8")   # 배열 아님
    findings, not_run = run_check(tmp_path, schema)
    assert by_rule(findings, "DS003", "error")
    assert any("Item 데이터 검사" in n for n in not_run)


# ---------------------------------------------------------------- DS004 열

def test_ds004_unknown_and_missing_columns(tmp_path):
    header = "id,name,hp,speed,element,drop,weight"   # tags 없음, weight 추가
    rows = ["MON_001,슬라임,10,1.5,FIRE,ITEM_A,3"]
    schema = setup(tmp_path, csv_rows=rows, header=header)
    findings, _ = run_check(tmp_path, schema)
    msgs = [f["message"] for f in by_rule(findings, "DS004", "warn")]
    assert any("weight" in m for m in msgs) and any("tags" in m for m in msgs)


def test_ds004_missing_required_column_skips_row_ds009(tmp_path):
    header = "id,name,hp,speed,drop,tags"   # 필수 element 열 없음
    schema = setup(tmp_path, csv_rows=["MON_001,슬라임,10,1.5,,"], header=header)
    findings, not_run = run_check(tmp_path, schema)
    assert any("element" in f["message"] for f in by_rule(findings, "DS004"))
    assert by_rule(findings, "DS009") == []
    assert any("Monster.element 필수 값 검사" in n for n in not_run)


# ---------------------------------------------------------------- DS005 타입 · 범위 · pattern

def test_ds005_type_error(tmp_path):
    schema = setup(tmp_path, csv_rows=["MON_001,슬라임,ten,fast,FIRE,,"])
    findings, _ = run_check(tmp_path, schema)
    hit = by_rule(findings, "DS005", "error")
    assert {f["field"] for f in hit} == {"hp", "speed"}
    assert hit[0]["line"] == 2


def test_ds005_range_and_pattern_warn(tmp_path):
    schema = setup(tmp_path, csv_rows=["MONSTER_1,슬라임,0,-1,FIRE,,"])
    findings, _ = run_check(tmp_path, schema)
    hit = by_rule(findings, "DS005", "warn")
    assert {f["field"] for f in hit} == {"id", "hp", "speed"}
    assert by_rule(findings, "DS005", "error") == []


def test_ds005_json_types(tmp_path):
    schema = copy.deepcopy(BASE_SCHEMA)
    schema["tables"]["Item"]["fields"].update({"price": {"type": "int"}, "rare": {"type": "bool"}})
    items = [{"id": "ITEM_A", "price": 1.5, "rare": "maybe"}, {"id": "ITEM_B", "price": 3, "rare": True}]
    setup(tmp_path, schema=schema, csv_rows=GOOD_ROWS, items=items)
    findings, _ = run_check(tmp_path, schema)
    hit = by_rule(findings, "DS005", "error")
    assert {f["field"] for f in hit} == {"price", "rare"} and all(f["index"] == 0 for f in hit)


# ---------------------------------------------------------------- DS006 enum

def test_ds006_enum_not_in_list(tmp_path):
    schema = setup(tmp_path, csv_rows=["MON_001,슬라임,10,1.5,WATER,,"])
    findings, _ = run_check(tmp_path, schema)
    hit = by_rule(findings, "DS006")
    assert len(hit) == 1 and hit[0]["severity"] == "warn" and "WATER" in hit[0]["message"]


def test_ds006_zero_value_on_required_field(tmp_path):
    schema = setup(tmp_path, csv_rows=["MON_001,슬라임,10,1.5,NONE,,"])
    findings, _ = run_check(tmp_path, schema)
    hit = by_rule(findings, "DS006", "warn")
    assert len(hit) == 1 and "미지정" in hit[0]["message"]


def test_ds006_zero_value_allowed_when_optional(tmp_path):
    schema = copy.deepcopy(BASE_SCHEMA)
    schema["tables"]["Monster"]["fields"]["element"]["optional"] = True
    setup(tmp_path, schema=schema, csv_rows=["MON_001,슬라임,10,1.5,NONE,,"])
    findings, _ = run_check(tmp_path, schema)
    assert by_rule(findings, "DS006") == []


def test_ds006_enum_list_items(tmp_path):
    schema = copy.deepcopy(BASE_SCHEMA)
    schema["tables"]["Monster"]["fields"]["tags"] = {"type": "list", "item": "enum", "enum": "Element", "optional": True}
    setup(tmp_path, schema=schema, csv_rows=["MON_001,슬라임,10,1.5,FIRE,,FIRE;LAVA"])
    findings, _ = run_check(tmp_path, schema)
    hit = by_rule(findings, "DS006")
    assert len(hit) == 1 and "LAVA" in hit[0]["message"]


# ---------------------------------------------------------------- DS007 참조

def test_ds007_broken_ref(tmp_path):
    schema = setup(tmp_path, csv_rows=["MON_001,슬라임,10,1.5,FIRE,ITEM_ZZZ,"])
    findings, _ = run_check(tmp_path, schema)
    hit = by_rule(findings, "DS007", "error")
    assert len(hit) == 1 and "ITEM_ZZZ" in hit[0]["message"]


def test_ds007_ref_list_items(tmp_path):
    schema = copy.deepcopy(BASE_SCHEMA)
    schema["tables"]["Monster"]["fields"]["tags"] = {"type": "list", "item": "ref", "table": "Item", "optional": True}
    setup(tmp_path, schema=schema, csv_rows=["MON_001,슬라임,10,1.5,FIRE,,ITEM_A;ITEM_X"])
    findings, _ = run_check(tmp_path, schema)
    hit = by_rule(findings, "DS007", "error")
    assert len(hit) == 1 and "ITEM_X" in hit[0]["message"]


# ---------------------------------------------------------------- DS008 키

def test_ds008_duplicate_and_empty_key(tmp_path):
    schema = setup(tmp_path, csv_rows=GOOD_ROWS + ["MON_001,복제,10,1.5,FIRE,,", ",무명,10,1.5,FIRE,,"])
    findings, _ = run_check(tmp_path, schema)
    hit = by_rule(findings, "DS008", "error")
    assert len(hit) == 2
    assert any("중복" in f["message"] for f in hit) and any("비어" in f["message"] for f in hit)


def test_ds008_duplicate_key_json(tmp_path):
    schema = setup(tmp_path, csv_rows=GOOD_ROWS, items=[{"id": "ITEM_A"}, {"id": "ITEM_A"}])
    findings, _ = run_check(tmp_path, schema)
    assert len(by_rule(findings, "DS008", "error")) == 1


# ---------------------------------------------------------------- DS009 필수

def test_ds009_required_empty(tmp_path):
    schema = setup(tmp_path, csv_rows=["MON_001,,10,,FIRE,,"])
    findings, _ = run_check(tmp_path, schema)
    hit = by_rule(findings, "DS009", "error")
    assert {f["field"] for f in hit} == {"name", "speed"}


def test_ds009_json_missing_key_in_row(tmp_path):
    schema = copy.deepcopy(BASE_SCHEMA)
    schema["tables"]["Item"]["fields"]["name"] = {"type": "string"}
    setup(tmp_path, schema=schema, csv_rows=GOOD_ROWS, items=[{"id": "ITEM_A", "name": "검"}, {"id": "ITEM_B"}])
    findings, _ = run_check(tmp_path, schema)
    hit = by_rule(findings, "DS009", "error")
    assert len(hit) == 1 and hit[0]["index"] == 1


# ---------------------------------------------------------------- _ignore

def test_ignore_csv_suppresses_rule_with_info(tmp_path):
    header = HEADER + ",_ignore"
    rows = ['MON_001,슬라임,10,1.5,FIRE,ITEM_NEW,,"DS007: 다음 패치에서 ITEM_NEW 추가"']
    schema = setup(tmp_path, csv_rows=rows, header=header)
    findings, _ = run_check(tmp_path, schema)
    assert errors(findings) == []
    info = by_rule(findings, "DS007", "info")
    assert len(info) == 1 and info[0]["message"].startswith("무시됨 — 다음 패치에서 ITEM_NEW 추가")
    assert by_rule(findings, "DS004") == []   # _ignore 열은 '모르는 열' 이 아니다


def test_ignore_only_named_rule(tmp_path):
    header = HEADER + ",_ignore"
    rows = ['MON_001,,10,1.5,FIRE,ITEM_NEW,,"DS007: 다음 패치"']   # DS009(name 빔)는 무시 대상 아님
    schema = setup(tmp_path, csv_rows=rows, header=header)
    findings, _ = run_check(tmp_path, schema)
    assert len(by_rule(findings, "DS009", "error")) == 1
    assert len(by_rule(findings, "DS007", "info")) == 1


def test_ignore_without_reason_is_not_applied(tmp_path):
    header = HEADER + ",_ignore"
    schema = setup(tmp_path, csv_rows=["MON_001,슬라임,10,1.5,FIRE,ITEM_NEW,,DS007"], header=header)
    findings, _ = run_check(tmp_path, schema)
    assert len(by_rule(findings, "DS007", "error")) == 1
    assert len(by_rule(findings, "DS010", "warn")) == 1


def test_ignore_json_object_form(tmp_path):
    schema = copy.deepcopy(BASE_SCHEMA)
    schema["tables"]["Item"]["fields"]["price"] = {"type": "int", "min": 0}
    items = [{"id": "ITEM_A", "price": -5, "_ignore": {"rules": ["DS005"], "reason": "디버그 아이템"}}, {"id": "ITEM_B", "price": 1}]
    setup(tmp_path, schema=schema, csv_rows=GOOD_ROWS, items=items)
    findings, _ = run_check(tmp_path, schema)
    assert by_rule(findings, "DS005", "warn") == []
    info = by_rule(findings, "DS005", "info")
    assert len(info) == 1 and "디버그 아이템" in info[0]["message"] and info[0]["ignored"] is True


# ---------------------------------------------------------------- doc

def test_doc_contains_tables_enums_relations(tmp_path):
    md = ds.render_doc(BASE_SCHEMA, "design/data/schema.json", today="2026-10-30")
    assert "type: schema" in md and "updated: 2026-10-30" in md
    assert "### Monster" in md and "### Item" in md
    assert "### Element" in md and "| 0 | `NONE` |" in md and "미지정" in md
    assert "| `hp` | int | 필수 | min 1 · max 99999 |" in md
    assert "| `drop` | ref → `Item` | 선택 |" in md
    assert "`Monster.drop` → 테이블 `Item`" in md
    assert "`Monster.element` → enum `Element`" in md
    assert "```mermaid" in md and "flowchart LR" in md and "n_Monster -->|drop| n_Item" in md
    assert "-.->|element| n_enum_Element" in md


def test_doc_cli_writes_file(tmp_path):
    setup(tmp_path, csv_rows=None, items=None)
    rc = ds.main(["doc", "design/data/schema.json", "--root", str(tmp_path), "--out", "design/data/schema.md"])
    assert rc == 0
    text = (tmp_path / "design" / "data" / "schema.md").read_text(encoding="utf-8")
    assert "### Monster" in text and "```mermaid" in text


def test_doc_refuses_broken_schema(tmp_path):
    schema = copy.deepcopy(BASE_SCHEMA)
    schema["tables"]["Monster"]["fields"]["hp"]["type"] = "integer"
    setup(tmp_path, schema=schema)
    out = tmp_path / "out.md"
    rc = ds.main(["doc", "design/data/schema.json", "--root", str(tmp_path), "--out", str(out)])
    assert rc == 1 and not out.exists()
