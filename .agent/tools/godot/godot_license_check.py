#!/usr/bin/env python3
"""godot_license_check — Godot 게임이 출시물에 엔진 라이선스 고지를 넣었는지 찾는다 (표준 라이브러리만).

`/ko-godot-license` 스킬이 쓰는 결정적 검사다. 기준은 Godot 4.7 문서 "Complying with licenses"
(docs.godotengine.org/en/4.7/about/complying_with_licenses.html — 2026-11-04 확인):
- Godot(MIT) 라이선스 문구를 사용자가 볼 수 있게 어딘가에 넣는다. 크레딧 화면 · 라이선스 화면 · 출력 로그(iOS 제외) ·
  함께 배포하는 파일 · 인쇄 설명서 · godotengine.org/license 링크 중 **하나**면 된다.
- 엔진에 든 제3자 구성 요소도 고지가 필요하다 — Engine.get_license_info · get_copyright_info, 또는 에디터의
  COPYRIGHT.txt 를 (예: GODOT_COPYRIGHT.txt 로) 함께 배포.
코드 · 데이터에서 그 흔적을 찾을 뿐이다. 화면에 실제로 뜨는지, 배포 꾸러미에 파일이 들어가는지는 사람이 확인한다.

    python .agent/tools/godot/godot_license_check.py [프로젝트 루트]   # 기본: 현재 폴더
    python .agent/tools/godot/godot_license_check.py --json .

규칙
    GL001  Godot 라이선스 고지 경로가 하나도 없다                         → FAIL
    GL002  제3자 구성 요소 고지 경로가 없다                               → FAIL
    GL003  고지가 출력 로그(print)뿐인데 iOS 내보내기 프리셋이 있다       → CONCERNS (iOS 는 로그로 안 된다)
    GL004  addons/<이름> 에 라이선스 파일이 없다 — 출처 · 조건 확인 필요   → CONCERNS
    GL005  고지가 '함께 배포하는 파일' 뿐이다 — 배포 꾸러미에 들어가는지 이 도구로 알 수 없다 → NOT ASSESSED
판정 순서: FAIL > CONCERNS > NOT ASSESSED > PASS. project.godot 이 없으면 NOT ASSESSED. 종료 코드는 0 (인수 오류만 2).
"""
import argparse
import json
import os
import re
import sys

SCAN_EXT = (".gd", ".cs", ".tscn", ".tres", ".txt", ".md", ".json", ".csv", ".cfg", ".translation", ".po")
GODOT_TEXT_RE = re.compile(r"Engine\s*\.\s*(?:get_license_text|GetLicenseText)\s*\(")
THIRD_RE = re.compile(r"Engine\s*\.\s*(?:get_license_info|get_copyright_info|GetLicenseInfo|GetCopyrightInfo)\s*\(")
LITERAL_RE = re.compile(r"This game uses Godot Engine|Copyright \(c\) 2014-present Godot Engine contributors", re.I)
LINK_RE = re.compile(r"godotengine\.org/license", re.I)
PRINT_RE = re.compile(r"\b(?:print|prints|print_rich|printt|GD\.Print\w*)\s*\(")
GODOT_FILE_RE = re.compile(r"^(?:GODOT_LICEN[SC]E|LICENSE[_.-]?GODOT|GODOT[_.-]?MIT)\w*(?:\.\w+)?$", re.I)
THIRD_FILE_RE = re.compile(r"^(?:GODOT_COPYRIGHT|COPYRIGHT)(?:\.\w+)?$", re.I)
ADDON_LICENSE_RE = re.compile(r"^(?:LICEN[SC]E|COPYING|NOTICE)", re.I)

RULES = {
    "GL001": "Godot 라이선스 고지 경로가 없다 — 크레딧 · 라이선스 화면에 Engine.get_license_text() 를 띄우거나 godotengine.org/license 링크를 넣는다",
    "GL002": "제3자 구성 요소 고지 경로가 없다 — Engine.get_license_info() · get_copyright_info() 를 화면에 띄우거나 "
             "에디터의 COPYRIGHT.txt 를 GODOT_COPYRIGHT.txt 로 함께 배포한다",
    "GL003": "고지가 출력 로그(print)뿐인데 iOS 프리셋이 있다 — iOS 는 로그로 고지가 안 된다. 화면 · 링크 경로를 더한다",
    "GL004": "애드온에 라이선스 파일이 없다 — 출처 저장소에서 조건을 확인하고, 고지가 필요하면 크레딧에 넣는다",
    "GL005": "고지가 함께 배포하는 파일뿐이다 — 내보낸 빌드 폴더 · 설치 꾸러미에 그 파일이 들어가는지 직접 확인한다",
}


def _walk(root):
    for dp, dns, fns in os.walk(root):
        dns[:] = [d for d in dns if not d.startswith(".") and d != "addons"]
        for fn in fns:
            yield dp, fn


def scan(root):
    routes = {"godot": set(), "third": set()}
    evidence = []
    log_only_candidates = []
    for dp, fn in _walk(root):
        full = os.path.join(dp, fn)
        rel = os.path.relpath(full, root).replace("\\", "/")
        if GODOT_FILE_RE.match(fn):
            routes["godot"].add("file")
            evidence.append({"route": "godot:file", "path": rel, "line": 0})
        if THIRD_FILE_RE.match(fn):
            routes["third"].add("file")
            evidence.append({"route": "third:file", "path": rel, "line": 0})
        if not fn.lower().endswith(SCAN_EXT):
            continue
        try:
            with open(full, encoding="utf-8", errors="replace") as f:
                lines = f.read().splitlines()
        except OSError:
            continue
        for i, line in enumerate(lines, 1):
            code = line.split("#", 1)[0] if fn.endswith(".gd") else line
            if GODOT_TEXT_RE.search(code):
                kind = "log" if PRINT_RE.search(code) else "screen"
                routes["godot"].add(kind)
                evidence.append({"route": f"godot:{kind}", "path": rel, "line": i})
            if THIRD_RE.search(code):
                kind = "log" if PRINT_RE.search(code) else "screen"
                routes["third"].add(kind)
                evidence.append({"route": f"third:{kind}", "path": rel, "line": i})
            if LITERAL_RE.search(line):
                routes["godot"].add("screen")
                evidence.append({"route": "godot:text", "path": rel, "line": i})
            if LINK_RE.search(line):
                routes["godot"].add("link")
                evidence.append({"route": "godot:link", "path": rel, "line": i})
    return routes, evidence


def ios_preset(root):
    try:
        with open(os.path.join(root, "export_presets.cfg"), encoding="utf-8", errors="replace") as f:
            return bool(re.search(r'^platform\s*=\s*"iOS"', f.read(), re.M))
    except OSError:
        return False


def addons_without_license(root):
    base = os.path.join(root, "addons")
    out, ok = [], []
    if not os.path.isdir(base):
        return out, ok
    for name in sorted(os.listdir(base)):
        d = os.path.join(base, name)
        if not os.path.isdir(d):
            continue
        has = any(ADDON_LICENSE_RE.match(fn) for fn in os.listdir(d))
        (ok if has else out).append(name)
    return out, ok


def run(root):
    if not os.path.isfile(os.path.join(root, "project.godot")):
        return {"verdict": "NOT ASSESSED", "reason": "project.godot 없음 — Godot 프로젝트 루트가 아니다", "findings": [],
                "routes": {}, "evidence": [], "addons_licensed": []}
    routes, evidence = scan(root)
    findings = []
    shown = lambda kinds: bool(kinds & {"screen", "link"})  # noqa: E731 — 화면에 보이는 경로
    if not routes["godot"]:
        findings.append({"rule": "GL001", "severity": "FAIL", "msg": RULES["GL001"]})
    if not routes["third"]:
        findings.append({"rule": "GL002", "severity": "FAIL", "msg": RULES["GL002"]})
    if ios_preset(root):
        for key in ("godot", "third"):
            if routes[key] and not shown(routes[key]) and "file" not in routes[key]:
                findings.append({"rule": "GL003", "severity": "CONCERNS", "msg": f"{RULES['GL003']} ({key})"})
    for key in ("godot", "third"):
        if routes[key] == {"file"}:
            findings.append({"rule": "GL005", "severity": "NOT ASSESSED", "msg": f"{RULES['GL005']} ({key})"})
    missing, licensed = addons_without_license(root)
    for name in missing:
        findings.append({"rule": "GL004", "severity": "CONCERNS", "msg": f"{RULES['GL004']} — addons/{name}"})
    order = ["FAIL", "CONCERNS", "NOT ASSESSED"]
    verdict = next((v for v in order if any(f["severity"] == v for f in findings)), "PASS")
    return {"verdict": verdict, "reason": "", "findings": findings,
            "routes": {k: sorted(v) for k, v in routes.items()}, "evidence": evidence, "addons_licensed": licensed}


def main(argv=None):
    ap = argparse.ArgumentParser(description="Godot 게임 라이선스 고지 점검")
    ap.add_argument("root", nargs="?", default=".")
    ap.add_argument("--json", action="store_true")
    a = ap.parse_args(argv)
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")
    if not os.path.isdir(a.root):
        print(f"폴더 없음: {a.root}", file=sys.stderr)
        return 2
    r = run(os.path.abspath(a.root))
    if a.json:
        print(json.dumps(r, ensure_ascii=False, indent=2))
        return 0
    for e in r["evidence"]:
        print(f"  근거 {e['route']:<13} {e['path']}" + (f":{e['line']}" if e["line"] else ""))
    for f in r["findings"]:
        print(f"{f['rule']} [{f['severity']}] {f['msg']}")
    if r["addons_licensed"]:
        print("라이선스 파일이 있는 애드온 (조건대로 크레딧에 넣었는지 확인): " + ", ".join(r["addons_licensed"]))
    print("사람이 확인할 것: 고지가 실제 화면에 뜨는지 · 폰트 · 음악 · 텍스처 등 제3자 에셋의 저작자 표시")
    print(f"판정: {r['verdict']}" + (f" — {r['reason']}" if r["reason"] else ""))
    return 0


if __name__ == "__main__":
    sys.exit(main())
