#!/usr/bin/env python3
"""data_schema — 스키마 우선 데이터 설계 검사 · 문서 생성 (표준 라이브러리만).

게임 데이터는 순서대로 만든다: **스키마 → enum → 데이터 행**. 이 도구는 스키마 JSON 을 정본으로 삼아
데이터 파일(CSV · JSON)을 검사하고, 사람이 베껴 쓰지 않도록 스키마 설명 마크다운을 생성한다.

    python .agent/tools/design/data_schema.py check <schema.json> [--root <프로젝트>] [--json]
    python .agent/tools/design/data_schema.py doc   <schema.json> [--root <프로젝트>] [--out <md 경로>]

경로(스키마 · 데이터 source · --out)는 절대 경로가 아니면 --root(기본 현재 디렉터리) 기준이다.
종료 코드: 0 = error 없음 · 1 = error 있음 · 2 = 사용법 오류 · 스키마 파일을 읽거나 파싱하지 못함.

스키마 형식
    {
      "enums":  {"Element": ["NONE", "FIRE", "ICE"]},          # 0번은 '미지정' 자리 (NONE · UNSPECIFIED 등)
      "tables": {
        "Monster": {
          "source": "design/data/monster.csv",                # .csv (헤더 + 행) 또는 .json (객체 배열)
          "key": "id",                                         # fields 안의 필드
          "desc": "선택 — 문서에 들어갈 설명",
          "fields": {
            "id":      {"type": "string", "pattern": "^MON_[0-9]{3}$"},
            "hp":      {"type": "int", "min": 1, "max": 99999},
            "speed":   {"type": "float", "min": 0},
            "boss":    {"type": "bool"},                        # true/false · 1/0 · yes/no
            "element": {"type": "enum", "enum": "Element"},
            "drop":    {"type": "ref", "table": "Item", "optional": true},
            "tags":    {"type": "list", "item": "string", "optional": true},   # CSV 에서는 a;b;c
            "elems":   {"type": "list", "item": "enum", "enum": "Element"},    # item 이 enum/ref 면 enum/table 도 적는다
            "note":    {"type": "string", "optional": true, "desc": "선택 — 문서용 설명"}
          }
        }
      }
    }

규칙 (severity: error 는 종료 코드 1, warn · info 는 보고만)
    DS001  스키마 자체 오류 — 모르는 타입 · 없는 enum/테이블 참조 · key 필드 없음 · 잘못된 pattern 등 (error)
    DS002  enum 0번이 미지정 이름(NONE · UNSPECIFIED · UNSET · UNKNOWN · INVALID · UNDEFINED · NULL · EMPTY)이 아님 (warn)
    DS003  데이터 파일 없음 (warn) · 읽지 못함 (error) — 그 테이블 데이터 검사와 그 테이블을 가리키는 참조 검사는 not_run 에 이름을 남긴다
    DS004  스키마에 없는 열 · 스키마 필드가 데이터에 없음 (warn)
    DS005  타입 위반 (error) · 범위(min/max) · pattern 위반 (warn)
    DS006  enum 값이 목록에 없음 (warn) · optional 아닌 필드에 0번(미지정) 값을 씀 (warn)
    DS007  참조(ref) 대상 키가 없음 — 깨진 참조 (error)
    DS008  키 중복 · 빈 키 (error)
    DS009  필수(optional 아님) 값이 빔 (error)
    DS010  `_ignore` 형식 오류 — 규칙 ID 나 이유가 없어 무시하지 않음 (warn)

의도된 예외
    데이터 행의 `_ignore` 열(CSV) 또는 `_ignore` 필드(JSON)에 규칙 ID 와 이유를 적으면 그 행의 그 규칙을 건너뛰고
    보고에 info 로 "무시됨 — 이유" 를 남긴다.
        CSV  : _ignore 열 값  "DS007 DS005: 다음 패치에서 Item 추가"
        JSON : "_ignore": "DS007: 이유"  또는  {"rules": ["DS007"], "reason": "이유"}
    행 단위 규칙(DS005~DS009)만 무시할 수 있다.
"""
import argparse
import csv
import datetime
import json
import math
import os
import re
import sys

TOOL_DIR = os.path.dirname(os.path.abspath(__file__))
if TOOL_DIR not in sys.path:
    sys.path.insert(0, TOOL_DIR)

from designlib import finding, print_report  # noqa: E402

SCALAR_TYPES = ("string", "int", "float", "bool")
ALL_TYPES = SCALAR_TYPES + ("enum", "ref", "list")
LIST_ITEM_TYPES = SCALAR_TYPES + ("enum", "ref")
KEY_TYPES = ("string", "int")
UNSPECIFIED_NAMES = {"NONE", "UNSPECIFIED", "UNSET", "UNKNOWN", "INVALID", "UNDEFINED", "NULL", "EMPTY"}
IGNORABLE = {"DS005", "DS006", "DS007", "DS008", "DS009"}
IGNORE_COL = "_ignore"
LIST_SEP = ";"
TRUE_WORDS = {"true", "1", "yes", "y"}
FALSE_WORDS = {"false", "0", "no", "n"}
INT_RE = re.compile(r"^[+-]?\d+$")
RULE_ID_RE = re.compile(r"\bDS\d{3}\b")


class SchemaLoadError(Exception):
    """스키마 파일을 읽거나 파싱하지 못함 — 종료 코드 2."""


# ---------------------------------------------------------------- 스키마

def load_schema(path):
    try:
        with open(path, encoding="utf-8-sig") as f:
            data = json.load(f)
    except FileNotFoundError:
        raise SchemaLoadError(f"스키마 파일 없음: {path}")
    except (json.JSONDecodeError, UnicodeDecodeError) as e:
        raise SchemaLoadError(f"스키마 JSON 파싱 실패: {path}: {e}")
    if not isinstance(data, dict):
        raise SchemaLoadError(f"스키마 최상위가 객체가 아님: {path}")
    return data


def _is_num(v):
    return isinstance(v, (int, float)) and not isinstance(v, bool)


def validate_schema(schema, spath):
    """스키마를 검사한다. (findings, bad) — bad = {"tables": {이름: 이유}, "fields": {(테이블, 필드): 이유}}.

    bad 에 든 테이블 · 필드는 데이터 검사에서 빼고 not_run 으로 알린다."""
    out = []
    bad = {"tables": {}, "fields": {}}

    def err(msg, **kw):
        out.append(finding("DS001", "error", spath, msg, **kw))

    enums = schema.get("enums", {})
    if not isinstance(enums, dict):
        err("enums 가 객체가 아님")
        enums = {}
    for name, values in enums.items():
        if not isinstance(values, list) or not values or not all(isinstance(v, str) and v for v in values):
            err(f"enum {name}: 비어 있지 않은 문자열 목록이어야 함", enum=name)
            continue
        dup = sorted({v for v in values if values.count(v) > 1})
        if dup:
            err(f"enum {name}: 중복 값 {', '.join(dup)}", enum=name)
        if values[0].upper() not in UNSPECIFIED_NAMES:
            out.append(finding("DS002", "warn", spath,
                               f"enum {name}: 0번 '{values[0]}' 이 미지정 이름이 아님 — 0번은 NONE · UNSPECIFIED 등으로 비워 두고 "
                               f"의미 있는 값은 1번부터 둔다", enum=name))

    tables = schema.get("tables")
    if not isinstance(tables, dict) or not tables:
        err("tables 가 없거나 비어 있음")
        return out, bad

    def check_target(tname, fname, spec, kind, where):
        """enum/ref 대상이 있는지. 문제가 있으면 이유 문자열."""
        if kind == "enum":
            en = spec.get("enum")
            if not isinstance(en, str) or not en:
                return f"{where}: enum 이름(\"enum\")이 없음"
            if en not in enums:
                return f"{where}: 없는 enum '{en}'"
        elif kind == "ref":
            tt = spec.get("table")
            if not isinstance(tt, str) or not tt:
                return f"{where}: 참조 테이블(\"table\")이 없음"
            if tt not in tables:
                return f"{where}: 없는 테이블 '{tt}' 참조"
        return None

    for tname, t in tables.items():
        if not isinstance(t, dict):
            err(f"테이블 {tname}: 객체가 아님", table=tname)
            bad["tables"][tname] = "테이블 정의가 객체가 아님"
            continue
        src = t.get("source")
        if not isinstance(src, str) or not src:
            err(f"테이블 {tname}: source 가 없음", table=tname)
            bad["tables"][tname] = "source 없음"
        elif os.path.splitext(src)[1].lower() not in (".csv", ".json"):
            err(f"테이블 {tname}: source 확장자는 .csv 또는 .json 이어야 함 ({src})", table=tname)
            bad["tables"][tname] = "지원하지 않는 source 형식"
        fields = t.get("fields")
        if not isinstance(fields, dict) or not fields:
            err(f"테이블 {tname}: fields 가 없거나 비어 있음", table=tname)
            bad["tables"][tname] = "fields 없음"
            continue
        if IGNORE_COL in fields:
            err(f"테이블 {tname}: '{IGNORE_COL}' 은 예약된 열 이름이라 필드로 쓸 수 없음", table=tname)
        key = t.get("key")
        if not isinstance(key, str) or not key:
            err(f"테이블 {tname}: key 가 없음", table=tname)
            bad["tables"][tname] = "key 없음"
        elif key not in fields:
            err(f"테이블 {tname}: key 필드 '{key}' 가 fields 에 없음", table=tname)
            bad["tables"][tname] = "key 필드 없음"
        else:
            kt = fields[key].get("type") if isinstance(fields[key], dict) else None
            if kt not in KEY_TYPES:
                err(f"테이블 {tname}: key 필드 '{key}' 의 타입은 string 또는 int 여야 함 ({kt})", table=tname, field=key)
                bad["tables"][tname] = "key 타입 오류"
            elif fields[key].get("optional"):
                err(f"테이블 {tname}: key 필드 '{key}' 는 optional 일 수 없음", table=tname, field=key)

        for fname, spec in fields.items():
            where = f"{tname}.{fname}"
            reason = None
            if not isinstance(spec, dict):
                reason = f"{where}: 필드 정의가 객체가 아님"
            else:
                ftype = spec.get("type")
                if ftype not in ALL_TYPES:
                    reason = f"{where}: 모르는 타입 '{ftype}' (허용: {', '.join(ALL_TYPES)})"
                elif ftype in ("enum", "ref"):
                    reason = check_target(tname, fname, spec, ftype, where)
                elif ftype == "list":
                    item = spec.get("item")
                    if item not in LIST_ITEM_TYPES:
                        reason = f"{where}: list 의 item 타입 '{item}' 을 모름 (허용: {', '.join(LIST_ITEM_TYPES)})"
                    else:
                        reason = check_target(tname, fname, spec, item, where)
                if reason is None:
                    base = spec.get("item") if ftype == "list" else ftype
                    for b in ("min", "max"):
                        if b in spec:
                            if base not in ("int", "float"):
                                reason = f"{where}: {b} 는 int · float 에만 쓸 수 있음"
                            elif not _is_num(spec[b]):
                                reason = f"{where}: {b} 가 숫자가 아님"
                    if reason is None and _is_num(spec.get("min")) and _is_num(spec.get("max")) and spec["min"] > spec["max"]:
                        reason = f"{where}: min({spec['min']}) 이 max({spec['max']}) 보다 큼"
                    if reason is None and "pattern" in spec:
                        if base != "string":
                            reason = f"{where}: pattern 은 string 에만 쓸 수 있음"
                        else:
                            try:
                                re.compile(spec["pattern"])
                            except (re.error, TypeError) as e:
                                reason = f"{where}: pattern 정규식 오류 — {e}"
            if reason:
                err(reason, table=tname, field=fname)
                bad["fields"][(tname, fname)] = reason
                if fname == key:
                    bad["tables"].setdefault(tname, "key 필드 정의 오류")
    return out, bad


# ---------------------------------------------------------------- 데이터 읽기

class DataLoadError(Exception):
    pass


def load_rows(path):
    """(열 목록, [(위치 표기, 위치 extra, row dict)]). CSV 값은 문자열, JSON 값은 원래 타입."""
    ext = os.path.splitext(path)[1].lower()
    try:
        if ext == ".csv":
            with open(path, encoding="utf-8-sig", newline="") as f:
                reader = csv.reader(f)
                try:
                    header = next(reader)
                except StopIteration:
                    raise DataLoadError("헤더 행이 없음")
                header = [h.strip() for h in header]
                if len(set(header)) != len(header):
                    dup = sorted({h for h in header if header.count(h) > 1})
                    raise DataLoadError(f"헤더에 중복 열 {', '.join(dup)}")
                rows = []
                for rec in reader:
                    if not rec or all(not c.strip() for c in rec):
                        continue
                    line = reader.line_num
                    if len(rec) > len(header):
                        raise DataLoadError(f"{line}행: 열 개수({len(rec)})가 헤더({len(header)})보다 많음")
                    rec = rec + [""] * (len(header) - len(rec))
                    rows.append((f"{line}행", {"line": line}, dict(zip(header, rec))))
                return header, rows
        with open(path, encoding="utf-8-sig") as f:
            data = json.load(f)
    except UnicodeDecodeError:
        raise DataLoadError("UTF-8 이 아님")
    except json.JSONDecodeError as e:
        raise DataLoadError(f"JSON 파싱 실패 — {e}")
    except csv.Error as e:
        raise DataLoadError(f"CSV 파싱 실패 — {e}")
    if not isinstance(data, list):
        raise DataLoadError("JSON 데이터는 객체 배열이어야 함")
    header, rows = [], []
    for i, obj in enumerate(data):
        if not isinstance(obj, dict):
            raise DataLoadError(f"#{i}: 객체가 아님")
        for k in obj:
            if k not in header:
                header.append(k)
        rows.append((f"#{i}", {"index": i}, obj))
    return header, rows


def _is_empty(v):
    return v is None or (isinstance(v, str) and not v.strip()) or (isinstance(v, list) and not v)


def parse_ignore(v):
    """(규칙 집합, 이유) — 형식이 틀리면 (None, 문제)."""
    if _is_empty(v):
        return set(), ""
    if isinstance(v, dict):
        rules = v.get("rules")
        rules = [rules] if isinstance(rules, str) else rules
        reason = v.get("reason") if isinstance(v.get("reason"), str) else ""
        rules = {r for r in (rules or []) if isinstance(r, str) and RULE_ID_RE.fullmatch(r.strip())}
    elif isinstance(v, str):
        rules = set(RULE_ID_RE.findall(v))
        reason = RULE_ID_RE.sub("", v)
    else:
        return None, "문자열 또는 {rules, reason} 객체가 아님"
    reason = reason.strip(" \t,;:—-–|/").strip()
    if not rules:
        return None, "규칙 ID(DS0xx)가 없음"
    if not reason:
        return None, "이유가 없음 — 의도된 예외는 이유를 함께 적는다"
    return rules, reason


# ---------------------------------------------------------------- 값 검사

def parse_scalar(raw, typ):
    """(값, 오류 메시지). raw 는 CSV 문자열 또는 JSON 원래 값."""
    if typ in ("string", "enum", "ref"):
        if isinstance(raw, (dict, list)) or isinstance(raw, bool):
            return None, f"{typ} 자리에 {type(raw).__name__} 값"
        if typ == "string" and not isinstance(raw, str):
            return None, f"string 자리에 {type(raw).__name__} 값"
        return str(raw).strip() if isinstance(raw, str) else str(raw), None
    if typ == "int":
        if isinstance(raw, bool):
            return None, "int 자리에 bool 값"
        if isinstance(raw, int):
            return raw, None
        if isinstance(raw, str) and INT_RE.match(raw.strip()):
            return int(raw.strip()), None
        return None, f"int 가 아님: {raw!r}"
    if typ == "float":
        if isinstance(raw, bool):
            return None, "float 자리에 bool 값"
        if _is_num(raw):
            v = float(raw)
        elif isinstance(raw, str):
            try:
                v = float(raw.strip())
            except ValueError:
                return None, f"float 가 아님: {raw!r}"
        else:
            return None, f"float 가 아님: {raw!r}"
        if math.isnan(v) or math.isinf(v):
            return None, f"float 가 유한한 수가 아님: {raw!r}"
        return v, None
    if typ == "bool":
        if isinstance(raw, bool):
            return raw, None
        if isinstance(raw, str):
            s = raw.strip().lower()
            if s in TRUE_WORDS:
                return True, None
            if s in FALSE_WORDS:
                return False, None
        if isinstance(raw, int) and raw in (0, 1):
            return bool(raw), None
        return None, f"bool 이 아님: {raw!r} (true/false · 1/0 · yes/no)"
    return None, f"모르는 타입 {typ}"


def check_value(raw, spec, ctx, enums, ref_keys):
    """한 칸을 검사해 [(rule, severity, msg)] 를 돌려준다. 비어 있음은 호출자가 처리한다."""
    out = []
    ftype = spec["type"]
    if ftype == "list":
        if isinstance(raw, list):
            items = raw
        elif isinstance(raw, str):
            items = [s.strip() for s in raw.split(LIST_SEP) if s.strip()]
        else:
            return [("DS005", "error", f"list 가 아님: {raw!r}")]
        itype = spec["item"]
        for i, it in enumerate(items):
            for r, sev, msg in _check_one(it, itype, spec, enums, ref_keys, ctx):
                out.append((r, sev, f"[{i}] {msg}"))
        return out
    return _check_one(raw, ftype, spec, enums, ref_keys, ctx)


def _check_one(raw, typ, spec, enums, ref_keys, ctx):
    v, e = parse_scalar(raw, typ)
    if e:
        return [("DS005", "error", e)]
    out = []
    if typ in ("int", "float"):
        if _is_num(spec.get("min")) and v < spec["min"]:
            out.append(("DS005", "warn", f"{v} 이 min {spec['min']} 보다 작음"))
        if _is_num(spec.get("max")) and v > spec["max"]:
            out.append(("DS005", "warn", f"{v} 이 max {spec['max']} 보다 큼"))
    elif typ == "string":
        if "pattern" in spec and not re.search(spec["pattern"], v):
            out.append(("DS005", "warn", f"'{v}' 이 pattern {spec['pattern']} 에 맞지 않음"))
    elif typ == "enum":
        values = enums[spec["enum"]]
        if v not in values:
            out.append(("DS006", "warn", f"'{v}' 은 enum {spec['enum']} 에 없음 (허용: {', '.join(values)})"))
        elif v == values[0] and not spec.get("optional"):
            out.append(("DS006", "warn", f"필수 필드에 enum {spec['enum']} 0번(미지정 자리) 값 '{v}' 을 씀 —실제 값을 정하거나 optional 로 둔다"))
    elif typ == "ref":
        keys = ref_keys.get(spec["table"])
        if keys is not None and v not in keys:
            out.append(("DS007", "error", f"깨진 참조 — {spec['table']} 에 키 '{v}' 가 없음"))
    return out


# ---------------------------------------------------------------- 검사 실행

def _rel(p, root):
    """root 아래면 / 구분 상대 경로, 아니면 그대로 (Windows 다른 드라이브 포함)."""
    try:
        r = os.path.relpath(p, root)
    except ValueError:
        return p
    return p if r.startswith("..") else r.replace(os.sep, "/")


def _resolve(root, p):
    return p if os.path.isabs(p) else os.path.join(root, *p.replace("\\", "/").split("/"))


def check(schema, spath, root):
    """(findings, not_run, summary)."""
    findings, bad = validate_schema(schema, spath)
    not_run = []
    tables = schema.get("tables") if isinstance(schema.get("tables"), dict) else {}
    enums = schema.get("enums") if isinstance(schema.get("enums"), dict) else {}
    if not tables:
        not_run.append("데이터 검사 전체 (tables 정의 오류)")
        return findings, not_run, {"tables": 0, "rows": 0}

    # 1) 데이터 읽기
    loaded = {}
    for tname, t in tables.items():
        if tname in bad["tables"]:
            not_run.append(f"{tname} 데이터 검사 (스키마 오류 — {bad['tables'][tname]})")
            continue
        src = t["source"]
        path = _resolve(root, src)
        if not os.path.isfile(path):
            findings.append(finding("DS003", "warn", src, f"테이블 {tname} 의 데이터 파일이 없음", table=tname))
            not_run.append(f"{tname} 데이터 검사 ({src} 없음)")
            continue
        try:
            loaded[tname] = load_rows(path)
        except DataLoadError as e:
            findings.append(finding("DS003", "error", src, f"테이블 {tname} 의 데이터 파일을 읽지 못함 — {e}", table=tname))
            not_run.append(f"{tname} 데이터 검사 ({src} 읽기 실패)")

    # 2) 참조용 키 집합 (키 필드를 문자열로 정규화)
    ref_keys = {}
    for tname, (header, rows) in loaded.items():
        key = tables[tname]["key"]
        ks = set()
        for _, _, row in rows:
            v = row.get(key)
            if not _is_empty(v) and not isinstance(v, (dict, list, bool)):
                ks.add(v.strip() if isinstance(v, str) else str(v))
        ref_keys[tname] = ks

    # 3) 테이블별 검사
    total_rows = 0
    for tname, (header, rows) in loaded.items():
        t = tables[tname]
        src, key, fields = t["source"], t["key"], t["fields"]
        total_rows += len(rows)
        for fname in fields:
            if (tname, fname) in bad["fields"]:
                not_run.append(f"{tname}.{fname} 값 검사 (필드 정의 오류)")
        unknown = [c for c in header if c not in fields and c != IGNORE_COL]
        for c in unknown:
            findings.append(finding("DS004", "warn", src, f"{tname}: 스키마에 없는 열 '{c}'", table=tname, field=c))
        # JSON 은 행마다 키가 빠질 수 있다 — 어느 행에도 없는 필드만 '열 없음' 으로 본다
        missing = [f for f in fields if f not in header]
        for f in missing:
            findings.append(finding("DS004", "warn", src, f"{tname}: 스키마 필드 '{f}' 가 데이터에 없음 (행별 필수 검사는 생략)",
                                    table=tname, field=f))
            if not fields[f].get("optional"):
                not_run.append(f"{tname}.{f} 필수 값 검사 (데이터에 열 없음)")
        for fname, spec in fields.items():
            if spec.get("type") == "ref" or (spec.get("type") == "list" and spec.get("item") == "ref"):
                tt = spec.get("table")
                if (tname, fname) not in bad["fields"] and tt not in ref_keys and fname not in missing:
                    not_run.append(f"{tname}.{fname} 참조 검사 ({tt} 데이터 없음)")

        seen = {}
        for label, loc, row in rows:
            rowf = []
            ign, ign_note = parse_ignore(row.get(IGNORE_COL))  # 성공이면 ign_note = 이유, 실패면 문제
            if ign is None:
                findings.append(finding("DS010", "warn", src, f"{tname} {label}: _ignore 를 적용하지 않음 — {ign_note}",
                                        table=tname, **loc))
                ign = set()
            else:
                for r in sorted(ign - IGNORABLE):
                    findings.append(finding("DS010", "warn", src, f"{tname} {label}: _ignore 의 {r} 는 행 단위 규칙이 아니라 무시할 수 없음",
                                            table=tname, **loc))
            ign_reason = ign_note if ign else ""
            kv = row.get(key)
            kshow = "" if _is_empty(kv) else f" (키 {kv})"
            # 키
            if (tname, key) not in bad["fields"]:
                if _is_empty(kv):
                    rowf.append(("DS008", "error", key, "키가 비어 있음"))
                else:
                    ks = kv.strip() if isinstance(kv, str) else str(kv)
                    if ks in seen:
                        rowf.append(("DS008", "error", key, f"키 '{ks}' 중복 — 처음 나온 곳 {seen[ks]}"))
                    else:
                        seen[ks] = label
            # 필드
            for fname, spec in fields.items():
                if (tname, fname) in bad["fields"] or fname in missing:
                    continue
                v = row.get(fname)
                if _is_empty(v):
                    if fname != key and not spec.get("optional"):
                        rowf.append(("DS009", "error", fname, "필수 값이 비어 있음"))
                    continue
                for r, sev, msg in check_value(v, spec, (tname, fname), enums, ref_keys):
                    rowf.append((r, sev, fname, msg))
            for r, sev, fname, msg in rowf:
                text = f"{tname} {label}{kshow} {fname}: {msg}"
                if r in ign & IGNORABLE:
                    findings.append(finding(r, "info", src, f"무시됨 — {ign_reason} ({text})", table=tname, field=fname,
                                            ignored=True, **loc))
                else:
                    findings.append(finding(r, sev, src, text, table=tname, field=fname, **loc))
    return findings, not_run, {"tables": len(tables), "checkedTables": len(loaded), "rows": total_rows}


# ---------------------------------------------------------------- 문서 생성

def _md(s):
    return str(s).replace("|", "\\|").replace("\n", " ")


def _node(name):
    return "n_" + re.sub(r"\W", "_", name, flags=re.ASCII)


def _type_label(spec):
    t = spec.get("type")
    if t == "enum":
        return f"enum `{spec.get('enum')}`"
    if t == "ref":
        return f"ref → `{spec.get('table')}`"
    if t == "list":
        item = spec.get("item")
        inner = f"enum `{spec.get('enum')}`" if item == "enum" else f"ref → `{spec.get('table')}`" if item == "ref" else item
        return f"list<{inner}>"
    return str(t)


def _constraints(spec):
    parts = []
    if "min" in spec:
        parts.append(f"min {spec['min']}")
    if "max" in spec:
        parts.append(f"max {spec['max']}")
    if "pattern" in spec:
        parts.append(f"pattern `{_md(spec['pattern'])}`")
    if spec.get("type") == "list":
        parts.append(f"CSV 는 `{LIST_SEP}` 구분")
    return " · ".join(parts)


def relations(schema):
    """[(출발 테이블, 필드, 종류 'ref'|'enum', 대상)]"""
    rel = []
    for tname, t in (schema.get("tables") or {}).items():
        for fname, spec in (t.get("fields") or {}).items():
            if not isinstance(spec, dict):
                continue
            kind = spec.get("item") if spec.get("type") == "list" else spec.get("type")
            if kind == "ref":
                rel.append((tname, fname, "ref", spec.get("table")))
            elif kind == "enum":
                rel.append((tname, fname, "enum", spec.get("enum")))
    return rel


def render_doc(schema, schema_rel, today=None):
    today = today or datetime.date.today().isoformat()
    stem = re.sub(r"[^A-Za-z0-9_.-]", "_", os.path.splitext(os.path.basename(schema_rel))[0]) or "schema"
    enums = schema.get("enums") or {}
    tables = schema.get("tables") or {}
    owner = schema.get("owner") if isinstance(schema.get("owner"), str) else "TBD"
    L = [
        "---",
        f"id: SCHEMA-{stem}",
        f"title: \"데이터 스키마 — {stem}\"",
        "type: schema",
        "status: draft",
        f"owner: {owner}",
        f"updated: {today}",
        "abstraction: L3",
        "---",
        "",
        f"# 데이터 스키마 — {stem}",
        "",
        f"> 자동 생성 문서 — `data_schema.py doc {schema_rel}`. 직접 고치지 말고 스키마를 고친 뒤 다시 생성한다.",
        "> 데이터는 **스키마 → enum → 데이터 행** 순서로 만든다.",
        "",
        "## Enum",
        "",
    ]
    if not enums:
        L += ["- (없음)", ""]
    for en, values in enums.items():
        L += [f"### {en}", "", "| 번호 | 값 | 비고 |", "|---|---|---|"]
        for i, v in enumerate(values if isinstance(values, list) else []):
            note = "미지정 자리 (데이터에서 필수 필드 값으로 쓰지 않는다)" if i == 0 else ""
            L.append(f"| {i} | `{_md(v)}` | {note} |")
        L.append("")
    L += ["## 테이블", ""]
    for tname, t in tables.items():
        if not isinstance(t, dict):
            continue
        L += [f"### {tname}", ""]
        if t.get("desc"):
            L += [_md(t["desc"]), ""]
        L += [f"- 원본: `{t.get('source')}`", f"- 키: `{t.get('key')}`", "",
              "| 필드 | 타입 | 필수 | 제약 | 설명 |", "|---|---|---|---|---|"]
        for fname, spec in (t.get("fields") or {}).items():
            if not isinstance(spec, dict):
                continue
            req = "키" if fname == t.get("key") else ("선택" if spec.get("optional") else "필수")
            L.append(f"| `{fname}` | {_type_label(spec)} | {req} | {_constraints(spec)} | {_md(spec.get('desc', ''))} |")
        L.append("")
    rel = relations(schema)
    L += ["## 참조 관계", ""]
    if not rel:
        L += ["- (없음)", ""]
    else:
        for src, f, kind, dst in rel:
            L.append(f"- `{src}.{f}` → {'테이블' if kind == 'ref' else 'enum'} `{dst}`")
        L += ["", "```mermaid", "flowchart LR"]
        for tname in tables:
            L.append(f"  {_node(tname)}[\"{tname}\"]")
        for en in sorted({d for _, _, k, d in rel if k == "enum"}):
            L.append(f"  {_node('enum_' + str(en))}([\"enum {en}\"])")
        for src, f, kind, dst in rel:
            if kind == "ref":
                L.append(f"  {_node(src)} -->|{f}| {_node(str(dst))}")
            else:
                L.append(f"  {_node(src)} -.->|{f}| {_node('enum_' + str(dst))}")
        L += ["```", ""]
    return "\n".join(L)


# ---------------------------------------------------------------- CLI

def main(argv=None):
    for stream in (sys.stdout, sys.stderr):
        try:
            stream.reconfigure(encoding="utf-8")
        except (AttributeError, ValueError):
            pass
    ap = argparse.ArgumentParser(description="스키마 우선 데이터 검사 · 스키마 문서 생성")
    sub = ap.add_subparsers(dest="cmd")
    pc = sub.add_parser("check", help="스키마 기준으로 데이터(CSV · JSON) 검사")
    pc.add_argument("schema")
    pc.add_argument("--root", default=os.getcwd())
    pc.add_argument("--json", action="store_true")
    pd = sub.add_parser("doc", help="스키마 설명 마크다운 생성")
    pd.add_argument("schema")
    pd.add_argument("--root", default=os.getcwd())
    pd.add_argument("--out", help="출력 md 경로 (없으면 표준 출력)")
    try:
        a = ap.parse_args(argv)
    except SystemExit as e:
        return 0 if e.code == 0 else 2
    if not a.cmd:
        ap.print_help(sys.stderr)
        return 2
    root = os.path.abspath(a.root)
    spath = _resolve(root, a.schema)
    srel = _rel(spath, root)
    try:
        schema = load_schema(spath)
    except SchemaLoadError as e:
        print(f"data_schema: {e}", file=sys.stderr)
        return 2

    if a.cmd == "check":
        findings, not_run, summary = check(schema, srel, root)
        print_report(f"데이터 스키마 검사 — {srel}", findings, not_run, a.json, {"summary": summary} if a.json else None)
        errors = sum(1 for f in findings if f["severity"] == "error")
        if not a.json:
            warns = sum(1 for f in findings if f["severity"] == "warn")
            print(f"data-schema: 테이블 {summary.get('checkedTables', 0)}/{summary['tables']} · 행 {summary['rows']} · "
                  f"error {errors} · warn {warns} · 검사 안 함 {len(not_run)}")
        return 1 if errors else 0

    findings, _ = validate_schema(schema, srel)
    errors = [f for f in findings if f["severity"] == "error"]
    if errors:
        print_report(f"스키마 오류 — 문서를 만들지 않음 ({srel})", errors)
        return 1
    text = render_doc(schema, srel)
    if a.out:
        out = _resolve(root, a.out)
        os.makedirs(os.path.dirname(out) or ".", exist_ok=True)
        with open(out, "w", encoding="utf-8", newline="\n") as f:
            f.write(text)
        print(f"data_schema: 문서 생성 — {_rel(out, root)}")
    else:
        print(text)
    return 0


if __name__ == "__main__":
    sys.exit(main())
