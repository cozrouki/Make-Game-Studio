<#
.SYNOPSIS
    Unity 풀스택 통합 스킬 — Upstream 동기화 스크립트

.DESCRIPTION
    두 upstream repo의 미러 영역을 갱신한다. fork 영역(로컬 수정분)은
    건드리지 않는다. 실행 후 git diff 로 변경 확인 → 수동 commit/push.

    Upstream:
      - Donchitos/Claude-Code-Game-Studios (L1 프로세스)
      - nlelouche/Unity-SkillForge          (L2 코드 패턴)
      - 외부 카탈로그 (scripts/sync-catalog.py — /ext):
          coreyhaines31/marketingskills               → .agent/marketing/ (MIT)
          gamedev-skills/awesome-gamedev-agent-skills → .agent/gamedev/   (Apache-2.0, Unity · 분야 · 장르 · 워크플로만)
          (Stanestane/game-design-skills-bundle 은 비상업 라이선스라 동기화 대상이 아니다 — 사용자가 직접 받음)

    미러 영역 (자동 갱신):
      - .agent/skills/                    (SkillForge 전체 미러 — Unity 전용 L2)
      - .claude/skills/<GS-skill>/        (GS skill 전부 — ko-/sf-/studio-/unity-fullstack/ext 보존)
      - .claude/agents/                   (GS agent 전부 — Unity · Godot · Unreal 엔진 전문가 포함)
      - .claude/docs/ · rules/ · hooks/ · scripts/   (상류 이름 그대로, 아래 fork 제외)
      - docs/engine-reference/ · docs/*.md · design/CLAUDE.md · src/CLAUDE.md · studio-tests/

    씨앗 (없을 때만 복사 — 프로젝트가 채우는 데이터):
      - project.yaml · docs/registry/ · docs/architecture/tr-registry.yaml · design/registry/

    Fork 영역 (자동 갱신 안 함, 수동 머지 필요):
      - .claude/hooks/session-start.sh · session-stop.sh  (한국어 출력 + STATUS 블록)
      - .claude/rules/gameplay-code.md                    (한국어 · 엔진별 규칙)
      - .claude/settings.json · .claude/statusline.sh
      - .claude/scripts/test-scaffold.sh                  (생성 CI 의 기본 브랜치 master)

.PARAMETER GameStudiosClone
    Claude-Code-Game-Studios 로컬 clone 경로

.PARAMETER SkillForgeClone
    Unity-SkillForge (Unity3D-AntiGravitySkills) 로컬 clone 경로

.PARAMETER MarketingClone
    marketingskills 로컬 clone 경로 (없으면 임시 clone)

.PARAMETER GamedevClone
    awesome-gamedev-agent-skills 로컬 clone 경로 (없으면 임시 clone)

.PARAMETER AndroidClone
    android/skills 로컬 clone 경로 (없으면 임시 clone)

.PARAMETER GameStudiosOnly
    Game-Studios 만 동기화 (SkillForge · 외부 카탈로그 단계 생략)

.PARAMETER DryRun
    변경 시도 표시만, 파일 쓰기 안 함

.PARAMETER SkipPull
    upstream git pull 생략 (이미 최신이면 사용)

.EXAMPLE
    .\scripts\sync-upstream.ps1
    .\scripts\sync-upstream.ps1 -DryRun
    .\scripts\sync-upstream.ps1 -SkipPull
#>

[CmdletBinding()]
param(
    # 기본값: upstream clone 이 이 패키지 저장소의 형제 폴더에 있다고 가정.
    # 다른 위치면 -GameStudiosClone / -SkillForgeClone 로 override.
    # (Windows PowerShell 5.1 은 -File 실행 때 param 기본값에서 $PSScriptRoot 가 비어 있어 본문에서 채운다)
    [string]$GameStudiosClone,
    [string]$SkillForgeClone,
    [string]$MarketingClone,
    [string]$GamedevClone,
    [string]$AndroidClone,
    [switch]$GameStudiosOnly,
    [switch]$DryRun,
    [switch]$SkipPull
)

$ErrorActionPreference = "Stop"
$scriptDir = if ($PSScriptRoot) { $PSScriptRoot } else { Split-Path -Parent $MyInvocation.MyCommand.Path }
if (-not $GameStudiosClone) { $GameStudiosClone = Join-Path $scriptDir "..\..\Claude-Code-Game-Studios" }
if (-not $SkillForgeClone)  { $SkillForgeClone  = Join-Path $scriptDir "..\..\Unity3D-AntiGravitySkills" }
if (-not $MarketingClone)   { $MarketingClone   = Join-Path $scriptDir "..\..\marketingskills" }
if (-not $GamedevClone)     { $GamedevClone     = Join-Path $scriptDir "..\..\awesome-gamedev-agent-skills" }
if (-not $AndroidClone)     { $AndroidClone     = Join-Path $scriptDir "..\..\android-skills" }
$pkg = Split-Path -Parent $scriptDir

# === 한국어 안내 재삽입 함수 ===
# 7개 11-game-design overlap skill (L1과 L2 양쪽 존재) 의 SKILL.md 본문 상단에
# 한국어 상세 안내 한 줄을 frontmatter 종료 직후에 삽입한다.
# 이미 안내가 있으면 skip (idempotent).
function Add-KoreanNoteIfMissing {
    param(
        [Parameter(Mandatory)] [string]$FilePath,
        [Parameter(Mandatory)] [string]$Slug,
        [Parameter(Mandatory)] [string]$Extra
    )
    if (-not (Test-Path $FilePath)) { return $false }
    $raw = Get-Content $FilePath -Raw
    if ($raw -match "한국어 상세 버전") { return $false }

    $lines = $raw -split "(?:\r\n|\r|\n)"
    $dashCount = 0
    $endIdx = -1
    for ($i = 0; $i -lt $lines.Count; $i++) {
        if ($lines[$i].Trim() -eq '---') {
            $dashCount++
            if ($dashCount -eq 2) { $endIdx = $i; break }
        }
    }
    if ($endIdx -lt 0) { return $false }

    $note = "> 📘 한국어 상세 버전 — ``/sf-info $Slug`` (SkillForge ``.agent/skills/11-game-design/$Slug/``)$Extra"

    $beforeEnd = $lines[0..$endIdx]
    $afterEnd = if ($endIdx + 1 -lt $lines.Count) { $lines[($endIdx + 1)..($lines.Count - 1)] } else { @() }

    # frontmatter 직후가 빈 줄이면 그 빈 줄 유지 + note + 빈 줄. 아니면 빈 줄 + note + 빈 줄.
    $newLines = if ($afterEnd.Count -gt 0 -and $afterEnd[0] -eq "") {
        $beforeEnd + @("") + @($note) + @("") + $afterEnd[1..($afterEnd.Count - 1)]
    } else {
        $beforeEnd + @("") + @($note) + @("") + $afterEnd
    }

    $newContent = ($newLines -join "`n")
    # UTF-8 no BOM (Windows PowerShell 5.1 호환)
    $utf8NoBom = New-Object System.Text.UTF8Encoding($false)
    [System.IO.File]::WriteAllText($FilePath, $newContent, $utf8NoBom)
    return $true
}

Write-Host ""
Write-Host "=== Unity 풀스택 — Upstream 동기화 ===" -ForegroundColor Cyan
Write-Host "패키지 루트:        $pkg"             -ForegroundColor Gray
Write-Host "Game-Studios 클론:  $GameStudiosClone" -ForegroundColor Gray
Write-Host "SkillForge 클론:    $SkillForgeClone"  -ForegroundColor Gray
Write-Host "DryRun=$DryRun, SkipPull=$SkipPull"    -ForegroundColor Gray

# === [1/6] upstream pull ===
if (-not $SkipPull) {
    Write-Host ""
    Write-Host "[1/6] upstream git pull..." -ForegroundColor Yellow
    foreach ($repo in @($GameStudiosClone, $SkillForgeClone, $MarketingClone, $GamedevClone)) {
        if (-not (Test-Path $repo)) {
            Write-Warning "  스킵: $repo 가 존재하지 않음"
            continue
        }
        Write-Host "  pulling: $repo"
        if (-not $DryRun) {
            git -C $repo pull --ff-only 2>&1 | ForEach-Object { Write-Host "    $_" }
        } else {
            Write-Host "    (DryRun 생략)" -ForegroundColor DarkGray
        }
    }
} else {
    Write-Host ""
    Write-Host "[1/6] upstream pull SKIPPED" -ForegroundColor DarkGray
}

# === [2/6] SkillForge → .agent/skills/ 미러 ===
Write-Host ""
Write-Host "[2/6] SkillForge → .agent/skills/ 미러..." -ForegroundColor Yellow
$skfSrc = Join-Path $SkillForgeClone ".agent\skills"
$skfDst = Join-Path $pkg ".agent\skills"
if ($GameStudiosOnly) {
    Write-Host "  생략 (-GameStudiosOnly)" -ForegroundColor DarkGray
} elseif (-not (Test-Path $skfSrc)) {
    Write-Warning "  스킵: $skfSrc 없음"
} else {
    if (-not $DryRun) {
        New-Item -ItemType Directory -Force -Path $skfDst | Out-Null
        Copy-Item -Path "$skfSrc\*" -Destination $skfDst -Recurse -Force
        Copy-Item -Path (Join-Path $SkillForgeClone "skills-index.json") `
                  -Destination (Join-Path $skfDst "skills-index.json") -Force
    }
    $cnt = (Get-ChildItem $skfSrc -Recurse -File).Count
    Write-Host "  완료: $cnt 파일 미러" -ForegroundColor Green
}

# === [3/6] Game-Studios skills/agents 미러 ===
Write-Host ""
Write-Host "[3/6] Game-Studios → .claude/ 미러 (skills + agents)..." -ForegroundColor Yellow

# 3a. skills — GS 72개 디렉토리를 패키지에 덮어쓰기
$gsSkillsSrc = Join-Path $GameStudiosClone ".claude\skills"
$gsSkillsDst = Join-Path $pkg ".claude\skills"
if (Test-Path $gsSkillsSrc) {
    if (-not $DryRun) {
        Get-ChildItem $gsSkillsSrc -Directory | ForEach-Object {
            Copy-Item -Path $_.FullName -Destination $gsSkillsDst -Recurse -Force
        }
    }
    $cnt = (Get-ChildItem $gsSkillsSrc -Directory).Count
    Write-Host "  skills: $cnt GS skill 미러 (ko-/sf-/unity-fullstack 보존)" -ForegroundColor Green

    # 3a-후처리: 7개 11-game-design overlap skill 의 한국어 안내 자동 재삽입
    if (-not $DryRun) {
        $koreanNotes = [ordered]@{
            'brainstorm'      = '. MDA/SDT/Bartle 프레임워크와 `game-concept.md`/`game-pillars.md` 산출물에 대한 한국어 가이드를 원하면 그쪽 사용.'
            'design-review'   = '. GDD 8섹션 체크리스트의 한국어 버전을 원하면 그쪽 사용.'
            'design-system'   = '. 단일 시스템 GDD를 Overview→Rules→Formulas→EdgeCases→Dependencies 순서로 한국어 작성하려면 그쪽 사용.'
            'map-systems'     = '. Foundation→Core→Content→Polish 계층별 systems-index 생성을 한국어로 원하면 그쪽 사용.'
            'playtest-report' = '. `new`/`analyze` 모드와 Pain Points/Delight/Bugs/Insights 분류 한국어 가이드는 그쪽 사용.'
            'balance-check'   = '. 전투/경제/진행/전리품 밸런스 분석과 Bloat Score 한국어 가이드는 그쪽 사용.'
            'scope-check'     = '. Bloat Score와 컷/연기/유지 권장 한국어 가이드는 그쪽 사용.'
        }
        $restored = 0
        foreach ($slug in $koreanNotes.Keys) {
            $skillFile = Join-Path $gsSkillsDst (Join-Path $slug "SKILL.md")
            if (Add-KoreanNoteIfMissing -FilePath $skillFile -Slug $slug -Extra $koreanNotes[$slug]) {
                $restored++
            }
        }
        Write-Host "  korean notes: $restored / 7 재삽입 (이미 있는 파일은 skip)" -ForegroundColor Green
    }
}

# 3b. agents — 엔진 전문가(Unity · Godot · Unreal) 포함 전부 미러 (엔진 중립 템플릿)
$gsAgentsSrc = Join-Path $GameStudiosClone ".claude\agents"
$gsAgentsDst = Join-Path $pkg ".claude\agents"
if (Test-Path $gsAgentsSrc) {
    if (-not $DryRun) {
        New-Item -ItemType Directory -Force -Path $gsAgentsDst | Out-Null
        Copy-Item -Path "$gsAgentsSrc\*.md" -Destination $gsAgentsDst -Force
    }
    $cnt = (Get-ChildItem $gsAgentsSrc -Filter "*.md" -File).Count
    Write-Host "  agents: $cnt agent 미러 (엔진 전문가 포함)" -ForegroundColor Green
}

# === [4/6] Game-Studios docs/rules/hooks/scripts + 루트 자산 미러 ===
Write-Host ""
Write-Host "[4/6] Game-Studios → .claude/ docs · rules · hooks · scripts + 루트 자산..." -ForegroundColor Yellow

# 이 템플릿이 고친 파일 (fork) — 자동 갱신하지 않는다. 상류 변경은 수동 머지
$forkFiles = @(
    '.claude\hooks\session-start.sh', '.claude\hooks\session-stop.sh',
    '.claude\rules\gameplay-code.md', '.claude\settings.json', '.claude\statusline.sh',
    '.claude\scripts\test-scaffold.sh'   # 생성 CI 의 기본 브랜치 main → master
)
function Copy-GsTree {
    param([string]$Rel, [switch]$SeedOnly)
    $root = (Get-Item -LiteralPath $GameStudiosClone).FullName.TrimEnd('\', '/')
    $src = Join-Path $root $Rel
    if (-not (Test-Path $src)) { Write-Warning "  스킵: $Rel 없음"; return 0 }
    $n = 0
    $files = if ((Get-Item $src).PSIsContainer) { Get-ChildItem $src -Recurse -File -Force } else { @(Get-Item $src) }
    foreach ($f in $files) {
        $relFile = $f.FullName.Substring($root.Length + 1)
        if ($forkFiles -contains $relFile) { continue }
        $dst = Join-Path $pkg $relFile
        if ($SeedOnly -and (Test-Path $dst)) { continue }   # 프로젝트 데이터 — 없을 때만 씨앗으로
        if (-not $DryRun) {
            New-Item -ItemType Directory -Force -Path (Split-Path $dst) | Out-Null
            Copy-Item $f.FullName $dst -Force
        }
        $n++
    }
    return $n
}

# 4a. 예전 gs-* 접두사 문서 정리 (v1.2.0 부터 상류 이름 그대로 — 스킬 참조 경로와 맞춘다)
if (-not $DryRun) {
    Get-ChildItem (Join-Path $pkg ".claude\docs") -Filter "gs-*" -File -ErrorAction SilentlyContinue | Remove-Item -Force
}
# 4b. 미러 (상류가 정본)
foreach ($rel in @('.claude\docs', '.claude\rules', '.claude\hooks', '.claude\scripts',
                   'docs\engine-reference', 'docs\CLAUDE.md', 'docs\COLLABORATIVE-DESIGN-PRINCIPLE.md',
                   'docs\WORKFLOW-GUIDE.md', 'docs\skill-flow-diagrams.md',
                   'design\CLAUDE.md', 'src\CLAUDE.md', 'studio-tests', 'production\.gdignore')) {
    $n = Copy-GsTree -Rel $rel
    Write-Host ("  {0,-42} {1} 파일" -f $rel, $n) -ForegroundColor Green
}
# 4c. 씨앗 (프로젝트가 채우는 데이터 — 없을 때만 복사)
foreach ($rel in @('project.yaml', 'docs\registry', 'docs\architecture\tr-registry.yaml', 'design\registry',
                   'production\session-state')) {
    $n = Copy-GsTree -Rel $rel -SeedOnly
    Write-Host ("  {0,-42} {1} 파일 (씨앗)" -f $rel, $n) -ForegroundColor Green
}
# 4d. 상류에서 사라진 훅 — 남아 있으면 알린다 (settings.json 등록도 함께 지울 것)
$gsHookNames = Get-ChildItem (Join-Path $GameStudiosClone ".claude\hooks") -File | ForEach-Object Name
$ownHooks = @('studio-pause-notice.sh', 'studio-write-guard.sh', 'validate-lint.sh')
Get-ChildItem (Join-Path $pkg ".claude\hooks") -File | Where-Object { $gsHookNames -notcontains $_.Name -and $ownHooks -notcontains $_.Name } |
    ForEach-Object { Write-Warning "  상류에 없는 훅: $($_.Name) — 쓰지 않으면 settings.json 등록과 함께 지운다" }
Write-Host "  fork (수동 머지): $($forkFiles -join ', ')" -ForegroundColor DarkGray

# === [5/6] 외부 카탈로그 (marketing · gamedev · android) ===
Write-Host ""
Write-Host "[5/6] 외부 카탈로그 → .agent/marketing · .agent/gamedev · .agent/android (scripts/sync-catalog.py)" -ForegroundColor Yellow
$catScript = Join-Path $scriptDir "sync-catalog.py"
$catalogs = if ($GameStudiosOnly) { Write-Host "  생략 (-GameStudiosOnly)" -ForegroundColor DarkGray; @() } else {
    @(@{ Name = "marketing"; Clone = $MarketingClone }, @{ Name = "gamedev"; Clone = $GamedevClone },
      @{ Name = "android"; Clone = $AndroidClone }) }
foreach ($cat in $catalogs) {
    $catArgs = @($catScript, $cat.Name)
    if (Test-Path $cat.Clone) { $catArgs += @("--src", $cat.Clone) } else { $catArgs += "--fetch" }
    if ($DryRun) { $catArgs += "--dry-run" }
    & python @catArgs 2>&1 | ForEach-Object { Write-Host "  $_" }
    if ($LASTEXITCODE -ne 0) { Write-Warning "  $($cat.Name) 동기화 실패 (exit $LASTEXITCODE)" }
}
Write-Host "  새 스킬에 '한국어 요약 없음' 이 뜨면 .agent/catalogs/<카탈로그>.ko.json 에 추가 후 --index-only" -ForegroundColor DarkGray

# === [6/6] git status 요약 ===
Write-Host ""
Write-Host "[6/6] git status 요약" -ForegroundColor Yellow
Push-Location $pkg
try {
    if (Test-Path (Join-Path $pkg ".git")) {
        $changes = git status --short
        if ($changes) {
            $changes | ForEach-Object { Write-Host "  $_" }
            $count = ($changes | Measure-Object).Count
            Write-Host "  변경 라인: $count" -ForegroundColor Cyan
        } else {
            Write-Host "  변경 없음 (이미 최신)" -ForegroundColor Green
        }
    } else {
        Write-Host "  (git repo 아님 — git status 생략)" -ForegroundColor DarkGray
    }
}
finally {
    Pop-Location
}

Write-Host ""
Write-Host "=== 완료 ===" -ForegroundColor Cyan
Write-Host ""
Write-Host "다음 단계 권장:" -ForegroundColor Yellow
Write-Host "  1. 변경 확인:    git -C `"$pkg`" diff"
Write-Host "  2. fork 영역 점검: gameplay-code.md, session-*.sh, settings.json 잘 살아있는지"
Write-Host "  3. 커밋:        git -C `"$pkg`" add -A; git -C `"$pkg`" commit -m 'chore: sync upstream'"
Write-Host "  4. 푸시:        git -C `"$pkg`" push"
Write-Host ""
if ($DryRun) {
    Write-Host "(DryRun 모드 — 파일 실제 변경 없음)" -ForegroundColor DarkGray
}
