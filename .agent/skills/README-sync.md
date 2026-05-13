# `.agent/skills/` — SkillForge 정적 미러

Unity-SkillForge (nlelouche/Unity-SkillForge) 의 C# 코드 패턴 카탈로그 102개를 오프라인 미러로 복제한 디렉토리입니다.

## 출처

- **Upstream**: https://github.com/nlelouche/Unity-SkillForge
- **로컬 클론**: `D:\works\projects\github\Unity3D-AntiGravitySkills\`
- **복제 시점**: 2026-05-13
- **라이선스**: 상류 저장소 LICENSE 준수 (MIT 기반)

## 동기화 절차

업스트림 업데이트를 가져오는 표준 절차:

```powershell
# 1. 로컬 클론 업데이트
git -C "D:\works\projects\github\Unity3D-AntiGravitySkills" pull

# 2. TikiProject 미러 재복사
$src = "D:\works\projects\github\Unity3D-AntiGravitySkills"
$dst = "D:\works\projects\github\TikiProject\.agent\skills"
Copy-Item "$src\.agent\skills\*" $dst -Recurse -Force
Copy-Item "$src\skills-index.json" "$dst\skills-index.json" -Force

# 3. 변경 확인
git -C "D:\works\projects\github\TikiProject" diff .agent/skills
```

Bash (Git Bash) 등가:

```bash
SRC="/d/works/projects/github/Unity3D-AntiGravitySkills"
DST="/d/works/projects/github/TikiProject/.agent/skills"
git -C "$SRC" pull
cp -R "$SRC/.agent/skills/." "$DST/"
cp "$SRC/skills-index.json" "$DST/skills-index.json"
git -C "/d/works/projects/github/TikiProject" diff .agent/skills
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
# 모든 path 추출 후 존재 여부 검증
DST="/d/works/projects/github/TikiProject"
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
- **TikiProject 고유 변형**: `.claude/skills/ko-*/` 에 별도 skill로 작성, `.agent/skills/`는 건드리지 않음
- **버그 픽스**: upstream 이슈 등록 + 임시 패치는 `.claude/skills/sf-patch-<이슈번호>/` 에 wrapper로
