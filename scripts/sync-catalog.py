#!/usr/bin/env python3
"""외부 스킬 카탈로그 동기화 — 업스트림 저장소를 .agent/<카탈로그>/ 로 미러하고 한국어 카탈로그(catalog.json)를 만든다.

카탈로그 (진입 스킬 /mk · /gd 가 필요할 때만 읽는다 — .claude/skills/ 에 넣지 않아 세션 상시 비용이 없다):
  marketing   coreyhaines31/marketingskills        MIT — 템플릿에 포함 (git 추적)
  gamedev     gamedev-skills/awesome-gamedev-agent-skills  Apache-2.0 — 템플릿에 포함 (Unity · 분야 · 장르 · 워크플로만,
              Godot · Unreal · Roblox · 웹 엔진 전용은 제외 — 이 템플릿은 Unity 전용)
  android     android/skills                       Apache-2.0 — 템플릿에 포함 (기기 프로파일링 · Play 정책 · ANR · R8 4개만,
              Compose · Wear · TV 등 네이티브 앱 전용은 제외)
  gamedesign  Stanestane/game-design-skills-bundle PolyForm Noncommercial 1.0.0 — 템플릿에 포함하지 않음 (git 무시).
              사용자가 라이선스를 확인하고 직접 받는다. 상업적 사용(게임 회사 안에서의 사용 포함)은 작성자의 상업 라이선스가 필요하다.

한국어 요약 · 그룹 · 게임 적합도는 .agent/catalogs/<카탈로그>.ko.json (로컬 작성, 업스트림 원문 아님) 에서 병합한다.

사용:
  python scripts/sync-catalog.py marketing --src <로컬 clone>          # 미러 + 카탈로그 (업스트림 갱신)
  python scripts/sync-catalog.py marketing --fetch                     # 임시 clone 후 미러
  python scripts/sync-catalog.py gamedesign --fetch --accept-license noncommercial|commercial
  python scripts/sync-catalog.py gamedesign --fetch --accept-license … --root <Unity 프로젝트>   # 설치된 프로젝트에 직접
  python scripts/sync-catalog.py <카탈로그> --index-only               # 미러는 그대로, catalog.json 만 다시 생성
  python scripts/sync-catalog.py <카탈로그> --status
업스트림 파일은 실행하지 않는다 (복사 · 읽기만).
"""
import argparse
import datetime
import fnmatch
import json
import os
import re
import shutil
import subprocess
import sys
import tempfile

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
OVERLAY_DIR = os.path.join(ROOT, ".agent", "catalogs")

CATALOGS = {
    "marketing": {
        "repo": "https://github.com/coreyhaines31/marketingskills.git",
        "dst": ".agent/marketing",
        "skillsDir": "skills",           # 업스트림 안에서 스킬 폴더들의 부모
        "license": "MIT",
        "vendored": True,
        # 업스트림 상대 경로 패턴 — 스킬 본문이 ../../tools/integrations/*.md 를 참조하므로 tools 문서도 같은 구조로 둔다
        "include": ["skills/*/**", "tools/*.md", "tools/integrations/*.md", "tools/composio/*.md", "tools/aisa/*.md",
                    "LICENSE"],
        "exclude": ["*/evals/*", "tools/clis/*"],  # 평가 데이터 · 외부 API CLI(JS) 제외
    },
    "gamedev": {
        "repo": "https://github.com/gamedev-skills/awesome-gamedev-agent-skills.git",
        "dst": ".agent/gamedev",
        "skillsDir": "skills",
        "license": "Apache-2.0",
        "vendored": True,
        "include": ["skills/disciplines/*/**", "skills/genres/*/**", "skills/unity/*/**", "skills/workflows/*/**",
                    "LICENSE", "NOTICE"],
        "exclude": ["*/agents/openai.yaml"],
    },
    "android": {
        "repo": "https://github.com/android/skills.git",
        "dst": ".agent/android",
        "skillsDir": "",
        "license": "Apache-2.0",
        "vendored": True,
        # 네이티브 Android(Compose · Wear · TV …) 스킬은 제외 — Unity Android 빌드에도 통하는 기기 · 스토어 단 스킬만
        "include": ["profilers/android-profiler/**", "play/play-policy-insights/**",
                    "performance/anr-audit-and-fix/**", "performance/r8-analyzer/**", "LICENSE.txt"],
        "exclude": [],
    },
    "gamedesign": {
        "repo": "https://github.com/Stanestane/game-design-skills-bundle.git",
        "dst": ".agent/gamedesign",
        "skillsDir": "",
        "license": "PolyForm-Noncommercial-1.0.0",
        "vendored": False,
        "include": ["*/SKILL.md", "*/references/*", "*/scripts/*", "*/assets/*",
                    "LICENSE", "COMMERCIAL-LICENSE.md", "CREDITS.md", "README.md", "game-design-skill-catalog.md"],
        "exclude": ["package-skills/*"],
    },
}

LICENSE_TEXT = {
    "gamedesign": """\
game-design-skills-bundle 은 PolyForm Noncommercial License 1.0.0 이다 (작성자: Stanislav Stankovic).
  - 무료: 개인 · 취미 · 학습, 학생 · 학술, 교육기관 · 비영리 · 공공 연구 · 정부 기관
  - 상업 라이선스 필요: 게임을 개발 · 퍼블리싱 · 운영하는 회사 안에서의 사용, 외주 · 컨설팅, 유료 교육,
    일부라도 재배포 · 재판매 · 스킬 묶음으로 재패키징
  - 상업 라이선스: https://www.stane-island.net/ (구매해도 재배포 권리는 없다)
  - 원문: https://github.com/Stanestane/game-design-skills-bundle/blob/main/LICENSE · COMMERCIAL-LICENSE.md
이 템플릿은 번들을 재배포하지 않는다. 받은 파일은 .agent/gamedesign/ 에만 두고 git 에 커밋하지 않는다.""",
}


def now():
    return datetime.datetime.now().astimezone().isoformat(timespec="seconds")


def rel(p):
    return p.replace("\\", "/")


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


def selected_files(src, cat):
    out = []
    for dirpath, dirnames, filenames in os.walk(src):
        dirnames[:] = [d for d in dirnames if d not in (".git", "__pycache__", "node_modules")]
        for n in filenames:
            r = rel(os.path.relpath(os.path.join(dirpath, n), src))
            if any(fnmatch.fnmatch(r, p) for p in cat["exclude"]):
                continue
            if any(fnmatch.fnmatch(r, p) for p in cat["include"]):
                out.append(r)
    return sorted(out)


def git_rev(src):
    p = subprocess.run(["git", "-C", src, "rev-parse", "--short", "HEAD"], capture_output=True, text=True)
    return p.stdout.strip() or "unknown"


def mirror(name, src, dry_run=False, license_mode=""):
    cat = CATALOGS[name]
    dst = os.path.join(ROOT, *cat["dst"].split("/"))
    files = selected_files(src, cat)
    if not any(f.endswith("SKILL.md") for f in files):
        raise SystemExit(f"오류: {src} 에 SKILL.md 가 없음 — 업스트림 구조가 바뀌었는지 확인")
    print(f"{name}: 업스트림 {git_rev(src)} · 파일 {len(files)}개 → {cat['dst']}" + (" [dry-run]" if dry_run else ""))
    if dry_run:
        return
    # 미러 영역 전체를 새로 쓴다 — 업스트림에서 지워진 스킬이 남지 않게. 카탈로그 폴더는 업스트림 전용이다.
    if os.path.isdir(dst):
        shutil.rmtree(dst)
    for f in files:
        target = os.path.join(dst, *f.split("/"))
        os.makedirs(os.path.dirname(target), exist_ok=True)
        shutil.copyfile(os.path.join(src, *f.split("/")), target)
    upstream = {"repo": cat["repo"], "commit": git_rev(src), "syncedAt": now(), "license": cat["license"],
                "vendored": cat["vendored"]}
    if license_mode:
        upstream["licenseAccepted"] = {"mode": license_mode, "at": now()}
    write_json(os.path.join(dst, "UPSTREAM.json"), upstream)
    build_index(name)


def _frontmatter(text):
    m = re.match(r"^---\s*\n(.*?)\n---", text, re.S)
    if not m:
        return {}
    # 최상위 키 · 블록 스칼라(> |) · metadata.version 만 읽는 최소 파서 (PyYAML 의존 없음)
    meta, key, block = {}, None, None
    for line in m.group(1).splitlines():
        km = re.match(r"^([A-Za-z_-]+):\s*(.*)$", line)
        if km:
            key, val = km.group(1), km.group(2).strip()
            block = key if val in (">", "|", ">-", "|-", ">+", "|+") else None
            meta[key] = "" if block else val.strip("\"'")
        elif block and line.strip():
            meta[block] = (meta[block] + " " + line.strip()).strip()
        elif key == "metadata":
            vm = re.match(r"^\s+version:\s*(.+)$", line)
            if vm:
                meta["version"] = vm.group(1).strip().strip("\"'")
    return meta


def build_index(name):
    cat = CATALOGS[name]
    dst = os.path.join(ROOT, *cat["dst"].split("/"))
    base = os.path.join(dst, *cat["skillsDir"].split("/")) if cat["skillsDir"] else dst
    if not os.path.isdir(base):
        raise SystemExit(f"오류: 미러 없음 — {cat['dst']} (먼저 --src 또는 --fetch)")
    overlay = read_json(os.path.join(OVERLAY_DIR, f"{name}.ko.json"), {})
    groups = overlay.get("_groups", {})
    skills, missing_ko = {}, []
    found = []
    for dirpath, dirnames, filenames in os.walk(base):  # gamedev 는 skills/<분류>/<스킬>/ 2단계
        dirnames.sort()
        if "SKILL.md" in filenames and dirpath != base:
            found.append(os.path.join(dirpath, "SKILL.md"))
    for path in sorted(found):
        n = os.path.basename(os.path.dirname(path))
        parent = os.path.basename(os.path.dirname(os.path.dirname(path)))
        with open(path, encoding="utf-8") as f:
            meta = _frontmatter(f.read())
        ko = overlay.get("skills", {}).get(n, {})
        if not ko:
            missing_ko.append(n)
        skills[n] = {"description": meta.get("description", ""), "version": meta.get("version", ""),
                     "path": rel(os.path.relpath(path, ROOT)),
                     "ko": ko.get("ko", ""),
                     "group": ko.get("group", parent if os.path.dirname(os.path.dirname(path)) != base else "기타"),
                     "fit": ko.get("fit", ""),
                     "overlap": ko.get("overlap", "")}
    upstream = read_json(os.path.join(dst, "UPSTREAM.json"), {})
    data = {"catalog": name, "upstream": upstream, "builtAt": now(), "count": len(skills), "groups": groups,
            "skills": skills}
    write_json(os.path.join(dst, "catalog.json"), data)
    stale = sorted(set(overlay.get("skills", {})) - set(skills))
    print(f"{name}: catalog.json — 스킬 {len(skills)}개"
          + (f" · 한국어 요약 없음 {len(missing_ko)}개: {', '.join(missing_ko)}" if missing_ko else "")
          + (f" · 업스트림에서 사라진 요약 {len(stale)}개: {', '.join(stale)}" if stale else ""))


def status(name):
    cat = CATALOGS[name]
    dst = os.path.join(ROOT, *cat["dst"].split("/"))
    up = read_json(os.path.join(dst, "UPSTREAM.json"))
    if not up:
        print(f"{name}: 설치 안 됨 ({cat['dst']})")
        return 1
    idx = read_json(os.path.join(dst, "catalog.json"), {})
    print(f"{name}: {up['repo']} @ {up['commit']} · {up['license']} · 동기화 {up['syncedAt']} · 스킬 {idx.get('count', '?')}개"
          + (f" · 라이선스 동의 {up['licenseAccepted']['mode']} ({up['licenseAccepted']['at']})" if up.get("licenseAccepted") else ""))
    return 0


def main(argv=None):
    for stream in (sys.stdout, sys.stderr):
        try:
            stream.reconfigure(encoding="utf-8")
        except (AttributeError, ValueError):
            pass
    ap = argparse.ArgumentParser(description="외부 스킬 카탈로그 동기화")
    ap.add_argument("catalog", choices=sorted(CATALOGS))
    src = ap.add_mutually_exclusive_group()
    src.add_argument("--src", help="업스트림 로컬 clone 경로")
    src.add_argument("--fetch", action="store_true", help="업스트림을 임시 폴더에 clone 해서 미러")
    src.add_argument("--index-only", action="store_true", help="catalog.json 만 다시 생성")
    src.add_argument("--status", action="store_true")
    ap.add_argument("--accept-license", choices=("noncommercial", "commercial"),
                    help="비상업 라이선스 카탈로그(gamedesign)에 필요 — noncommercial: 비상업 용도 확인 / commercial: 상업 라이선스 보유")
    ap.add_argument("--root", help="대상 프로젝트 루트 (기본: 이 템플릿 저장소). 설치된 Unity 프로젝트에 직접 받을 때")
    ap.add_argument("--dry-run", action="store_true")
    args = ap.parse_args(argv)
    cat = CATALOGS[args.catalog]
    if args.root:
        global ROOT, OVERLAY_DIR
        ROOT = os.path.abspath(args.root)
        own = os.path.join(ROOT, ".agent", "catalogs")
        if os.path.isdir(own):  # 대상 프로젝트에 설치된 오버레이가 있으면 그것을, 없으면 템플릿 것을 쓴다
            OVERLAY_DIR = own

    if args.status:
        return status(args.catalog)
    if args.index_only:
        build_index(args.catalog)
        return 0
    if not (args.src or args.fetch):
        ap.error("--src / --fetch / --index-only / --status 중 하나 필요")
    if args.catalog in LICENSE_TEXT:
        print(LICENSE_TEXT[args.catalog])
        if not args.accept_license:
            print("\n중단: 라이선스를 확인했으면 --accept-license noncommercial (비상업 용도) 또는 commercial (상업 라이선스 보유) 를 붙인다.")
            return 2
    if args.src:
        mirror(args.catalog, os.path.abspath(args.src), args.dry_run, args.accept_license or "")
        return 0
    tmp = tempfile.mkdtemp(prefix=f"catalog-{args.catalog}-")
    try:
        clone = os.path.join(tmp, "repo")
        # core.autocrlf=false — 시스템 설정(true)이면 CRLF 로 풀려 미러에 섞인다 (shebang 스크립트가 bash 에서 깨짐)
        p = subprocess.run(["git", "-c", "core.autocrlf=false", "clone", "-q", "--depth", "1", cat["repo"], clone],
                           env=dict(os.environ, GIT_TERMINAL_PROMPT="0"))
        if p.returncode != 0:
            print("오류: git clone 실패", file=sys.stderr)
            return 1
        mirror(args.catalog, clone, args.dry_run, args.accept_license or "")
    finally:
        shutil.rmtree(tmp, ignore_errors=True)
    return 0


if __name__ == "__main__":
    sys.exit(main())
