# `.agent/skills/` — SkillForge 정적 미러

Unity-SkillForge (nlelouche/Unity-SkillForge) 의 C# 코드 패턴 카탈로그 102개를 오프라인 미러로 복제한 디렉토리입니다.

## 출처

- **Upstream**: https://github.com/nlelouche/Unity-SkillForge
- **로컬 클론**: 임의 위치 (sync 스크립트 기본값 = 이 패키지 저장소의 형제 폴더 `..\Unity3D-AntiGravitySkills\`)
- **복제 시점**: 2026-05-13
- **라이선스**: 상류 저장소 LICENSE 준수 (MIT 기반)

## 동기화 절차

> **권장**: 저장소 루트의 `scripts/sync-upstream.ps1` 을 사용하면 두 upstream 을 한 번에 갱신한다.
> 아래는 수동 절차. `<PACKAGE_ROOT>` 는 이 패키지 저장소 루트(clone 위치)로 치환한다.

```powershell
# 1. 로컬 클론 업데이트 (<SKILLFORGE_CLONE> = SkillForge upstream clone 경로)
git -C "<SKILLFORGE_CLONE>" pull

# 2. 이 패키지 저장소 미러 재복사
$src = "<SKILLFORGE_CLONE>"
$dst = "<PACKAGE_ROOT>\.agent\skills"
Copy-Item "$src\.agent\skills\*" $dst -Recurse -Force
Copy-Item "$src\skills-index.json" "$dst\skills-index.json" -Force

# 3. 변경 확인
git -C "<PACKAGE_ROOT>" diff .agent/skills
```

Bash (Git Bash) 등가:

```bash
SRC="<SKILLFORGE_CLONE>"           # SkillForge upstream clone 경로
DST="<PACKAGE_ROOT>/.agent/skills"
git -C "$SRC" pull
cp -R "$SRC/.agent/skills/." "$DST/"
cp "$SRC/skills-index.json" "$DST/skills-index.json"
git -C "<PACKAGE_ROOT>" diff .agent/skills
```

## 절대 수정 금지

이 디렉토리 하위 파일은 **업스트림 미러**입니다. 다음 규칙을 지킵니다:

- `.agent/skills/<카테고리>/<스킬>/SKILL.md` — 직접 수정 금지
- `.agent/skills/<카테고리>/<스킬>/templates/*` — 직접 수정 금지
- `skills-index.json` — 직접 수정 금지

한국어 커스터마이즈나 게임 특화 변형이 필요하면:
1. SkillForge skill을 **참조 자료**로 두고
2. `.claude/skills/ko-*/SKILL.md` 에 한국어 wrapper 작성
3. 실제 C# 코드는 `Assets/<Game>/Scripts/` 에 직접 (혹은 `/sf-add` 로 템플릿 주입 후 수정)

업스트림 수정 → 직접 push 가 아니라, upstream에 PR로 기여 → 다음 sync에서 가져오는 흐름.

## 인덱스 무결성 검증

`skills-index.json` 의 모든 `path` 가 실제 파일을 가리키는지 확인:

```bash
# 모든 path 추출 후 존재 여부 검증 (DST = 이 패키지 저장소 루트)
DST="<PACKAGE_ROOT>"
python3 -c "
import json, os, sys
idx = json.load(open('$DST/.agent/skills/skills-index.json'))
missing = [name for name, meta in idx.items() if not os.path.exists(os.path.join('$DST', meta['path']))]
print(f'TOTAL {len(idx)} / MISSING {len(missing)}')
[print(f'  - {n}') for n in missing[:20]]
"
```

## 사용 진입점

- `/sf-list [카테고리]` — 카테고리별 skill 목록
- `/sf-info <skill-name>` — 특정 skill 상세
- `/sf-add <skill-name>` — 템플릿 + SKILL.md를 사용자 지정 위치에 복사
- 마스터 진입: `/unity-fullstack code`

## 분기 정책

- **상류 push 가능한 개선**: upstream에 PR
- **프로젝트 고유 변형**: `.claude/skills/ko-*/` 에 별도 skill로 작성, `.agent/skills/`는 건드리지 않음
- **버그 픽스**: upstream 이슈 등록 + 임시 패치는 `.claude/skills/sf-patch-<이슈번호>/` 에 wrapper로
