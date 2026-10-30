"""artgen CLI. 모든 명령은 --json 으로 기계 판독 출력 (스킬이 파싱)."""
import argparse
import json
import os
import sys

from . import ArtgenError
from . import providers as registry
from .config import load_config
from .request import compile_prompt, load_request, validate_request
from .store import Store


def _print(args, data, text):
    if args.json:
        print(json.dumps(data, ensure_ascii=False, indent=2))
    else:
        print(text)


def cmd_providers(args, cfg):
    rows = []
    for name, cls in sorted(registry.discover().items()):
        p = registry.create(name, cfg)
        ok, msg = p.check()
        rows.append({"name": name, "active": name == cfg["provider"], "ready": ok, "message": msg,
                     "description": cls.description, "capabilities": p.capabilities,
                     "placeholder": getattr(p, "placeholder", False)})
    text = "\n".join(f"{'*' if r['active'] else ' '} {r['name']:<10} {'OK ' if r['ready'] else 'N/A'}  {r['description']}"
                     f"\n{'':14}{r['message']}" for r in rows)
    _print(args, {"active": cfg["provider"], "providers": rows}, text + "\n(* = 현재 provider)")
    return 0


def cmd_validate(args, cfg):
    results, bad = [], 0
    for path in args.requests:
        try:
            with open(path, encoding="utf-8") as f:
                req = json.load(f)
            errors = validate_request(req)
        except (OSError, json.JSONDecodeError) as e:
            errors = [str(e)]
        bad += bool(errors)
        results.append({"file": path, "ok": not errors, "errors": errors})
    text = "\n".join(f"{'OK  ' if r['ok'] else 'FAIL'} {r['file']}" + "".join(f"\n     - {e}" for e in r["errors"]) for r in results)
    _print(args, {"results": results}, text)
    return 1 if bad else 0


def cmd_prompt(args, cfg):
    req = load_request(args.request)
    p = compile_prompt(req)
    _print(args, p, f"[positive]\n{p['positive']}\n\n[negative]\n{p['negative']}")
    return 0


def cmd_generate(args, cfg):
    req = load_request(args.request)
    run = Store(args.root, cfg).generate(req, args.request, provider_name=args.provider, variants=args.variants,
                                         seed=args.seed, dry_run=args.dry_run)
    if run.get("dryRun"):
        text = (f"[dry-run] {run['assetId']} {run['version']} · provider={run['provider']} · 변형 {run['variants']}"
                f" · seeds {run['seeds']}\n→ {run['outDir']}\n[positive] {run['prompt']['positive']}"
                f"\n[negative] {run['prompt']['negative']}")
    else:
        files = "\n".join(f"  {run['outDir']}/{o['file']}  " + (
            f"{o['durationSec']}s {o['sampleRate']}Hz ch={o['channels']} peak={o.get('peakDbfs')}dBFS"
            if run.get("kind") == "audio" else f"{o['width']}x{o['height']} alpha={o['alpha']}") + f" seed={o['seed']}"
            for o in run["outputs"])
        warn = "".join(f"\n  ⚠ {w}" for w in run["warnings"])
        note = "\n  (placeholder 결과 — 시각 검수 생략, 기술 검사만)" if run["placeholder"] else ""
        text = f"{run['assetId']} {run['version']} · provider={run['provider']}\n{files}{warn}{note}"
    _print(args, run, text)
    return 0


def cmd_select(args, cfg):
    s = Store(args.root, cfg).select(args.asset_id, args.version, args.file)
    _print(args, s, f"{args.asset_id}: 선택 {args.version}/{args.file}")
    return 0


def cmd_reject(args, cfg):
    s = Store(args.root, cfg).reject(args.asset_id, args.reason)
    _print(args, s, f"{args.asset_id}: 반려 — {args.reason}")
    return 0


def cmd_promote(args, cfg):
    req = load_request(args.request)
    s = Store(args.root, cfg).promote(req, dest=args.dest, force=args.force)
    p = s["promoted"]
    extra = f"\n  기존 파일 백업: {p['backup']}" if p["backup"] else ""
    _print(args, s, f"{req['assetId']}: {p['version']}/{p['file']} → {p['dest']}\n  임포트 맵: {cfg['importMap']}{extra}")
    return 0


def cmd_status(args, cfg):
    states = Store(args.root, cfg).list_states()
    if args.asset_id:
        states = [s for s in states if s["assetId"] == args.asset_id]
    lines = [f"{s['assetId']:<10} {s['status']:<9} v{len(s['versions']):<3} {s.get('name', '')}"
             + (f"  → {s['promoted']['dest']}" if s.get("promoted") else "") for s in states]
    _print(args, {"assets": states}, "\n".join(lines) or "(생성 기록 없음)")
    return 0


def cmd_library(args, cfg):
    from . import library as lib
    from .providers.library import library_dir

    root = library_dir(cfg.get("providers", {}).get("library", {}), args.root)
    store = Store(args.root, cfg)
    if args.action == "add":
        if not args.target or not args.name:
            raise ArtgenError("library add <zip|폴더> --name <팩> --license <SPDX> [--url ..] [--attribution ..]")
        meta = lib.add_pack(root, args.target, args.name, args.license, args.url or "", args.attribution or "")
        index = lib.build_index(root, _optional_audio_python(store))
        n = sum(1 for e in index["entries"] if e["pack"] == args.name)
        _print(args, {"pack": meta, "files": n}, f"{args.name} 등록 ({meta['license']}) — 오디오 {n}개 · 색인 갱신")
    elif args.action == "index":
        index = lib.build_index(root, _optional_audio_python(store))
        missing = sum(1 for e in index["entries"] if "durationSec" not in e)
        note = f"\n  ⚠ 길이 미측정 {missing}개 — audio.python(PyAV) 설정 후 다시 index" if missing else ""
        _print(args, {"packs": index["packs"], "files": len(index["entries"]), "missingDuration": missing},
               f"팩 {len(index['packs'])}개 · 오디오 {len(index['entries'])}개 색인{note}")
    elif args.action == "search":
        hits = lib.search(lib.load_index(root), args.target or "", args.max_duration, args.limit)
        text = "\n".join(f"{h['score']:>4} {h.get('durationSec', '?'):>6}s  {h['file']}" for h in hits)
        _print(args, {"query": args.target, "hits": hits}, text or "(결과 없음 — 다른 단어로)")
    return 0


def _optional_audio_python(store):
    try:
        return store._audio_python()
    except ArtgenError:
        return None  # WAV 만 길이를 잰다 — 색인 결과에 미측정 수를 알린다


def build_parser():
    ap = argparse.ArgumentParser(prog="artgen", description="백엔드 중립 게임 그래픽 생성 파이프라인")
    ap.add_argument("--root", default=os.getcwd(), help="게임 프로젝트 루트 — Unity · Godot · Unreal (기본: 현재 디렉터리)")
    ap.add_argument("--json", action="store_true", help="JSON 출력")
    sub = ap.add_subparsers(dest="cmd", required=True)

    sub.add_parser("providers", help="등록된 백엔드 어댑터와 준비 상태")

    p = sub.add_parser("validate", help="요청 파일 검증")
    p.add_argument("requests", nargs="+")

    p = sub.add_parser("prompt", help="요청을 백엔드 중립 텍스트 프롬프트로 컴파일 (미리보기)")
    p.add_argument("request")

    p = sub.add_parser("generate", help="새 버전 생성")
    p.add_argument("request")
    p.add_argument("--provider")
    p.add_argument("--variants", type=int)
    p.add_argument("--seed", type=int)
    p.add_argument("--dry-run", action="store_true")

    p = sub.add_parser("select", help="승격할 변형 선택")
    p.add_argument("asset_id")
    p.add_argument("version")
    p.add_argument("file")

    p = sub.add_parser("reject", help="에셋 반려 기록")
    p.add_argument("asset_id")
    p.add_argument("--reason", required=True)

    p = sub.add_parser("promote", help="선택 변형을 프로젝트로 복사 (Unity: Assets/ + 임포트 맵 · Godot/Unreal: 파일만, 임포트는 엔진에서)")
    p.add_argument("request")
    p.add_argument("--dest", help="unity.dest 대신 사용할 프로젝트 상대경로 (Unity 는 Assets/...)")
    p.add_argument("--force", action="store_true", help="기존 파일 교체 (저장소에 백업)")

    p = sub.add_parser("status", help="저장소 상태")
    p.add_argument("asset_id", nargs="?")

    p = sub.add_parser("library", help="사운드 라이브러리 — add <zip|폴더> · index · search <질의>")
    p.add_argument("action", choices=("add", "index", "search"))
    p.add_argument("target", nargs="?", help="add: zip · 폴더 / search: 질의")
    p.add_argument("--name", help="add: 팩 이름 (소문자 · 숫자 · - )")
    p.add_argument("--license", help="add: 라이선스 SPDX (예: CC0-1.0) — 필수")
    p.add_argument("--url", help="add: 출처 URL")
    p.add_argument("--attribution", help="add: 표기 문구 (필요한 라이선스만)")
    p.add_argument("--max-duration", type=float, help="search: 길이 상한(초)")
    p.add_argument("--limit", type=int, default=20)
    return ap


COMMANDS = {"providers": cmd_providers, "validate": cmd_validate, "prompt": cmd_prompt, "generate": cmd_generate,
            "select": cmd_select, "reject": cmd_reject, "promote": cmd_promote, "status": cmd_status,
            "library": cmd_library}


def main(argv=None):
    for stream in (sys.stdout, sys.stderr):
        try:
            stream.reconfigure(encoding="utf-8")  # Windows 콘솔 cp949 에서 한글·기호 깨짐 방지
        except (AttributeError, ValueError):
            pass
    args = build_parser().parse_args(argv)
    try:
        return COMMANDS[args.cmd](args, load_config())
    except ArtgenError as e:
        if args.json:
            print(json.dumps({"error": str(e)}, ensure_ascii=False))
        else:
            print(f"오류: {e}", file=sys.stderr)
        return 1
