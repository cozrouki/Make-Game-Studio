<#
.SYNOPSIS
    Unity 풀스택 통합 스킬 — Upstream 동기화 스크립트

.DESCRIPTION
    두 upstream repo의 미러 영역을 갱신한다. fork 영역(로컬 수정분)은
    건드리지 않는다. 실행 후 git diff 로 변경 확인 → 수동 commit/push.

    Upstream:
      - Donchitos/Claude-Code-Game-Studios (L1 프로세스)
      - nlelouche/Unity-SkillForge          (L2 코드 패턴)

    미러 영역 (자동 갱신):
      - .agent/skills/                    (SkillForge 전체 미러)
      - .claude/skills/<GS-skill>/        (72 GS skill — ko-/sf-/unity-fullstack 보존)
      - .claude/agents/                   (39 agents, Godot/UE 자동 제외)
      - .claude/docs/gs-*                 (6 GS docs)
      - .claude/rules/<10 GS rules>       (gameplay-code.md 보존)
      - .claude/hooks/<10 GS hooks>       (session-*.sh 보존)

    Fork 영역 (자동 갱신 안 함, 수동 머지 필요):
      - .claude/hooks/session-start.sh    (한국어 톤 머지)
      - .claude/hooks/session-stop.sh
      - .claude/rules/gameplay-code.md
      - .claude/settings.json

.PARAMETER GameStudiosClone
    Claude-Code-Game-Studios 로컬 clone 경로

.PARAMETER SkillForgeClone
    Unity-SkillForge (Unity3D-AntiGravitySkills) 로컬 clone 경로

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
    [string]$GameStudiosClone = "D:\works\projects\github\Claude-Code-Game-Studios",
    [string]$SkillForgeClone  = "D:\works\projects\github\Unity3D-AntiGravitySkills",
    [switch]$DryRun,
    [switch]$SkipPull
)

$ErrorActionPreference = "Stop"
$pkg = Split-Path -Parent $PSScriptRoot

Write-Host ""
Write-Host "=== Unity 풀스택 — Upstream 동기화 ===" -ForegroundColor Cyan
Write-Host "패키지 루트:        $pkg"             -ForegroundColor Gray
Write-Host "Game-Studios 클론:  $GameStudiosClone" -ForegroundColor Gray
Write-Host "SkillForge 클론:    $SkillForgeClone"  -ForegroundColor Gray
Write-Host "DryRun=$DryRun, SkipPull=$SkipPull"    -ForegroundColor Gray

# === [1/5] upstream pull ===
if (-not $SkipPull) {
    Write-Host ""
    Write-Host "[1/5] upstream git pull..." -ForegroundColor Yellow
    foreach ($repo in @($GameStudiosClone, $SkillForgeClone)) {
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
    Write-Host "[1/5] upstream pull SKIPPED" -ForegroundColor DarkGray
}

# === [2/5] SkillForge → .agent/skills/ 미러 ===
Write-Host ""
Write-Host "[2/5] SkillForge → .agent/skills/ 미러..." -ForegroundColor Yellow
$skfSrc = Join-Path $SkillForgeClone ".agent\skills"
$skfDst = Join-Path $pkg ".agent\skills"
if (-not (Test-Path $skfSrc)) {
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

# === [3/5] Game-Studios skills/agents 미러 ===
Write-Host ""
Write-Host "[3/5] Game-Studios → .claude/ 미러 (skills + agents)..." -ForegroundColor Yellow

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
}

# 3b. agents — 다 복사 후 Godot/UE 제거
$gsAgentsSrc = Join-Path $GameStudiosClone ".claude\agents"
$gsAgentsDst = Join-Path $pkg ".claude\agents"
if (Test-Path $gsAgentsSrc) {
    if (-not $DryRun) {
        New-Item -ItemType Directory -Force -Path $gsAgentsDst | Out-Null
        Copy-Item -Path "$gsAgentsSrc\*.md" -Destination $gsAgentsDst -Force
        Get-ChildItem $gsAgentsDst -Filter "godot-*.md"  -ErrorAction SilentlyContinue | Remove-Item -Force
        Get-ChildItem $gsAgentsDst -Filter "ue-*.md"     -ErrorAction SilentlyContinue | Remove-Item -Force
        Get-ChildItem $gsAgentsDst -Filter "unreal*.md"  -ErrorAction SilentlyContinue | Remove-Item -Force
    }
    $cnt = (Get-ChildItem $gsAgentsDst -File -ErrorAction SilentlyContinue).Count
    Write-Host "  agents: $cnt agent 유지 (Godot/UE 자동 제외)" -ForegroundColor Green
}

# === [4/5] Game-Studios docs/rules/hooks 미러 ===
Write-Host ""
Write-Host "[4/5] Game-Studios → .claude/ 미러 (docs + rules + hooks)..." -ForegroundColor Yellow

# 4a. docs (gs- prefix)
$gsDocsSrc = Join-Path $GameStudiosClone ".claude\docs"
$gsDocsDst = Join-Path $pkg ".claude\docs"
$gsDocFiles = @(
    'coding-standards.md',
    'coordination-rules.md',
    'agent-roster.md',
    'workflow-catalog.yaml',
    'skills-reference.md',
    'hooks-reference.md'
)
if (Test-Path $gsDocsSrc) {
    $n = 0
    foreach ($f in $gsDocFiles) {
        $src = Join-Path $gsDocsSrc $f
        $dst = Join-Path $gsDocsDst ("gs-$f")
        if (Test-Path $src) {
            if (-not $DryRun) {
                New-Item -ItemType Directory -Force -Path $gsDocsDst | Out-Null
                Copy-Item $src $dst -Force
            }
            $n++
        }
    }
    Write-Host "  docs: $n gs-* docs 미러" -ForegroundColor Green
}

# 4b. rules (gameplay-code.md 제외)
$gsRulesSrc = Join-Path $GameStudiosClone ".claude\rules"
$gsRulesDst = Join-Path $pkg ".claude\rules"
$gsRuleFiles = @(
    'ai-code.md','data-files.md','design-docs.md','engine-code.md',
    'narrative.md','network-code.md','prototype-code.md','shader-code.md',
    'test-standards.md','ui-code.md'
)
if (Test-Path $gsRulesSrc) {
    $n = 0
    foreach ($f in $gsRuleFiles) {
        $src = Join-Path $gsRulesSrc $f
        $dst = Join-Path $gsRulesDst $f
        if (Test-Path $src) {
            if (-not $DryRun) {
                New-Item -ItemType Directory -Force -Path $gsRulesDst | Out-Null
                Copy-Item $src $dst -Force
            }
            $n++
        }
    }
    Write-Host "  rules: $n GS rules 미러 (gameplay-code.md 보존)" -ForegroundColor Green
}

# 4c. hooks (session-start/stop 제외)
$gsHooksSrc = Join-Path $GameStudiosClone ".claude\hooks"
$gsHooksDst = Join-Path $pkg ".claude\hooks"
$gsHookFiles = @(
    'detect-gaps.sh','notify.sh','pre-compact.sh','post-compact.sh',
    'log-agent.sh','log-agent-stop.sh',
    'validate-commit.sh','validate-push.sh',
    'validate-assets.sh','validate-skill-change.sh'
)
if (Test-Path $gsHooksSrc) {
    $n = 0
    foreach ($f in $gsHookFiles) {
        $src = Join-Path $gsHooksSrc $f
        $dst = Join-Path $gsHooksDst $f
        if (Test-Path $src) {
            if (-not $DryRun) {
                New-Item -ItemType Directory -Force -Path $gsHooksDst | Out-Null
                Copy-Item $src $dst -Force
            }
            $n++
        }
    }
    Write-Host "  hooks: $n GS hooks 미러 (session-*.sh 보존)" -ForegroundColor Green
}

# === [5/5] git status 요약 ===
Write-Host ""
Write-Host "[5/5] git status 요약" -ForegroundColor Yellow
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
