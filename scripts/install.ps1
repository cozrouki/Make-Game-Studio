<#
.SYNOPSIS
    게임 개발 통합 스킬 — 대상 게임 프로젝트(Unity · Godot · Unreal)에 설치

.DESCRIPTION
    README "다른 프로젝트에 적용하는 방법" 1~4단계를 한 번에 수행한다.

      1. 자산 복사       — 이 저장소의 git 추적 파일만, 선택한 도구 · 엔진 기준
                           (Unity 전용 계층 SkillForge · unity_lint · MCP 가이드는 Unity 일 때만,
                            엔진 레퍼런스는 그 엔진 것만, project.yaml · 레지스트리는 없을 때만)
      2. 자리표시자 치환 — AGENTS.md 게임 폴더 매핑 표 · <SharedModule> · 네임스페이스 예시
                           + CLAUDE.md 엔진 레퍼런스 import 줄을 대상 엔진으로
      3. settings.local.json — MCP 권한 생성 또는 병합 (Unity)
      4. MCPForUnity     — Packages/manifest.json 의존성 + .mcp.json (Unity)
      +  .gitignore 항목 추가, production/session-state 생성

    기존 .claude / CLAUDE.md / AGENTS.md 등이 있으면 -Force 없이는 중단한다.
    -Force 면 덮어쓸 대상을 .claude.backup-<시각>/ 에 먼저 백업한다.

    설치 후 엔진 설정은 Claude Code 세션에서 /ko-setup-engine (실측 기반) 으로 한다.

.PARAMETER Target
    대상 게임 프로젝트 루트 — Unity(ProjectSettings/ProjectVersion.txt) · Godot(project.godot) · Unreal(*.uproject)

.PARAMETER Engine
    Auto(기본 — 표지 파일로 판정) | Unity | Godot | Unreal

.PARAMETER Tools
    설치할 도구 계층. 기본 Claude. 공통 자산(AGENTS.md, .agent/)은 항상 설치.
    Claude | Cursor | Antigravity | Gemini | Codex | Copilot | OpenCode | Windsurf | All
    (도구별 파일은 scripts/gen-rule-mirrors.py 가 만든 미러 — README §크로스툴 호환)

.PARAMETER Games
    게임 폴더 매핑. "TAG=폴더" 목록. 예: -Games "RPG=MyRpg","PZL=MyPuzzle"
    생략하면 Assets/ 하위 후보를 보여 주고 입력받는다 (비대화형이면 자리표시자 유지).

.PARAMETER SharedModule
    게임 간 공유 모듈 폴더명 (Assets/<이름>). 없으면 생략 — <SharedModule> 자리표시자 유지.

.PARAMETER McpPort
    MCPForUnity 브리지 포트 (기본 6401)

.PARAMETER SkipMcp
    manifest.json · .mcp.json 을 건드리지 않음

.PARAMETER Force
    기존 설치를 백업 후 덮어씀

.PARAMETER DryRun
    수행할 작업만 출력, 파일 쓰기 없음

.EXAMPLE
    .\scripts\install.ps1 -Target D:\Projects\MyGame -Games "MG=MyGame"
    .\scripts\install.ps1 -Target D:\Projects\Multi -Games "A=GameA","B=GameB" -SharedModule SharedCore -Tools Claude,Cursor
    .\scripts\install.ps1 -Target D:\Projects\MyGame -DryRun
#>

[CmdletBinding()]
param(
    [Parameter(Mandatory = $true)][string]$Target,
    [ValidateSet("Auto", "Unity", "Godot", "Unreal")][string]$Engine = "Auto",
    [string[]]$Tools = @("Claude"),
    [string[]]$Games = @(),
    [string]$SharedModule = "",
    [int]$McpPort = 6401,
    [switch]$SkipMcp,
    [switch]$Force,
    [switch]$DryRun
)

$ErrorActionPreference = "Stop"
$scriptDir = if ($PSScriptRoot) { $PSScriptRoot } else { Split-Path -Parent $MyInvocation.MyCommand.Path }
$pkg = Split-Path -Parent $scriptDir

# powershell -File 로 호출하면 "A,B" 가 배열이 아닌 문자열 하나로 들어온다 — 쉼표로 다시 나눈다
function Split-List($items) { @($items | ForEach-Object { $_ -split "," } | ForEach-Object { $_.Trim() } | Where-Object { $_ }) }
$Tools = Split-List $Tools
$Games = Split-List $Games
$validTools = @("Claude", "Cursor", "Antigravity", "Gemini", "Codex", "Copilot", "OpenCode", "Windsurf")
if ($Tools -contains "All") { $Tools = $validTools }
foreach ($t in $Tools) { if ($validTools -notcontains $t) { throw "Tools 값 오류: '$t' (허용: $($validTools -join ', '), All)" } }
$utf8NoBom = New-Object System.Text.UTF8Encoding($false)

function Write-Step($msg) { Write-Host ""; Write-Host $msg -ForegroundColor Yellow }
function Write-Ok($msg)   { Write-Host "  $msg" -ForegroundColor Green }
function Write-Info($msg) { Write-Host "  $msg" -ForegroundColor Gray }

# 줄바꿈·BOM 없이 UTF-8 로 쓴다 (훅 .sh 는 LF 여야 하고, PS 5.1 Set-Content 는 BOM 을 붙인다)
function Write-TextFile($path, $text) {
    if ($DryRun) { return }
    [System.IO.File]::WriteAllText($path, $text, $utf8NoBom)
}
function Read-TextFile($path) { [System.IO.File]::ReadAllText($path, $utf8NoBom) }
# PS 5.1 ConvertTo-Json 은 < > & ' 를 \u00XX 로 이스케이프한다 — 유효하지만 읽기 어려워 되돌린다
function ConvertTo-PlainJson($obj) {
    $s = $obj | ConvertTo-Json -Depth 10
    foreach ($hex in @("3c", "3e", "26", "27")) { $s = $s.Replace(("\u00" + $hex), [string][char][Convert]::ToInt32($hex, 16)) }
    $s
}

# === [0/6] 검증 ===
Write-Step "[0/6] 대상 확인"
$Target = (Resolve-Path $Target).Path
if ($Target -eq $pkg) { throw "대상이 이 템플릿 저장소 자신입니다." }
# 엔진 판정 — 표지 파일 (.claude/docs/engine-layers.md 의 '판정' 행과 같은 기준)
$markers = [ordered]@{
    Unity  = (Test-Path (Join-Path $Target "ProjectSettings\ProjectVersion.txt"))
    Godot  = (Test-Path (Join-Path $Target "project.godot"))
    Unreal = [bool](Get-ChildItem $Target -Filter "*.uproject" -File -ErrorAction SilentlyContinue)
}
$found = @($markers.Keys | Where-Object { $markers[$_] })
if ($Engine -eq "Auto") {
    if ($found.Count -eq 1) { $Engine = $found[0] }
    elseif ($found.Count -eq 0) { throw "엔진을 판정하지 못했습니다 (ProjectSettings/ProjectVersion.txt · project.godot · *.uproject 없음): $Target — 새 프로젝트면 엔진 에디터로 먼저 만들거나 -Engine 을 지정하세요" }
    else { throw "엔진 표지가 여럿입니다 ($($found -join ', ')) — -Engine 으로 지정하세요" }
} elseif (-not $markers[$Engine]) {
    Write-Host "  경고: -Engine $Engine 인데 표지 파일이 없습니다 (새 프로젝트로 보고 계속)" -ForegroundColor DarkYellow
}
$ver = switch ($Engine) {
    "Unity"  { $vf = Join-Path $Target "ProjectSettings\ProjectVersion.txt"
               if (Test-Path $vf) { (Select-String -Path $vf -Pattern "m_EditorVersion:\s*(\S+)").Matches[0].Groups[1].Value } }
    "Godot"  { $gf = Join-Path $Target "project.godot"
               if (Test-Path $gf) { $m = Select-String -Path $gf -Pattern 'config/features=PackedStringArray\("([0-9.]+)"'; if ($m) { $m.Matches[0].Groups[1].Value } } }
    "Unreal" { $uf = Get-ChildItem $Target -Filter "*.uproject" -File -ErrorAction SilentlyContinue | Select-Object -First 1
               if ($uf) { $m = Select-String -Path $uf.FullName -Pattern '"EngineAssociation"\s*:\s*"([^"]+)"'; if ($m) { $m.Matches[0].Groups[1].Value } } }
}
$codeRoot = @{ Unity = "Assets"; Godot = "src"; Unreal = "Source" }[$Engine]
$isUnity = ($Engine -eq "Unity")
Write-Ok "$Engine $ver — $Target"
Write-Info "도구: 공통(AGENTS.md, .agent) + $($Tools -join ', ')"
if ($DryRun) { Write-Info "DryRun — 파일을 쓰지 않습니다" }

# === [1/6] 복사 목록 ===
Write-Step "[1/6] 자산 복사"

# 저장소 운영 전용 파일은 대상에 복사하지 않는다
$excludeExact = @("README.md", "LICENSE", "THIRD_PARTY_LICENSES.md", ".gitattributes", ".gitignore",
                  "skills-index.json", ".mcp.json.template", "production/session-state/.gitkeep")
# studio-tests/ 는 상류 스킬 · 에이전트 자체 시험(템플릿 유지보수용)이라 게임 프로젝트에 넣지 않는다
$excludePrefix = @("i18n/", "scripts/", "studio-tests/")
# 다른 엔진의 레퍼런스
foreach ($e in @("unity", "godot", "unreal")) { if ($e -ne $Engine.ToLower()) { $excludePrefix += "docs/engine-reference/$e/" } }
# Unity 전용 계층 — SkillForge(L2) · unity_lint · MCP for Unity 가이드 · sf-* 스킬
if (-not $isUnity) {
    $excludePrefix += @(".agent/skills/", ".agent/tools/lint/", ".claude/skills/sf-add/", ".claude/skills/sf-info/", ".claude/skills/sf-list/")
    $excludeExact += @(".claude/docs/mcp-unity-guide.md", ".claude/docs/editor-automation-decision.md")
}
# Godot 전용 — src/ 가 Godot 코드 루트다 (다른 엔진에 src/ 를 만들면 코드 루트 판정이 모호해진다)
if ($Engine -ne "Godot") { $excludeExact += @("src/CLAUDE.md", "src/.gitkeep", "production/.gdignore") }

$toolPrefixes = @("AGENTS.md", ".agent/")   # 공통
# Claude: 상류 GS 스킬이 읽는 루트 자산 (project.yaml · docs/ · design/ · src/CLAUDE.md)
if ($Tools -contains "Claude") { $toolPrefixes += @("CLAUDE.md", ".claude/", "project.yaml", "docs/", "design/", "src/", "production/") }
if ($Tools -contains "Cursor") { $toolPrefixes += @(".cursor/") }
if ($Tools -contains "Gemini") { $toolPrefixes += @("GEMINI.md", "AGENT.md", ".gemini/") }
if ($Tools -contains "Codex") { $toolPrefixes += @(".agents/") }          # AGENTS.md 는 공통
if ($Tools -contains "Copilot") { $toolPrefixes += @(".github/copilot-instructions.md", ".github/instructions/", ".github/prompts/", ".github/skills/") }
if ($Tools -contains "OpenCode") { $toolPrefixes += @(".opencode/") }
if ($Tools -contains "Windsurf") { $toolPrefixes += @(".windsurf/") }
# Antigravity 는 공통 .agent/ (rules · workflows · skills) 로 충분

# 대상 프로젝트가 이미 쓰고 있을 수 있는 최상위 폴더 — 통째로 백업 · 삭제하지 않고 파일 단위로 병합한다
$mergeTop = @(".github", "docs", "design", "src", "production")
# 씨앗 — 프로젝트가 채우는 데이터. 대상에 이미 있으면 건드리지 않는다
$seedFiles = @("project.yaml", "docs/registry/architecture.yaml", "docs/architecture/tr-registry.yaml", "design/registry/entities.yaml")

# git 추적 파일만 — 로컬 잔재(settings.local.json, 로그, 백업)가 섞이지 않게
$files = @()
if (Test-Path (Join-Path $pkg ".git")) {
    $files = & git -C $pkg ls-files
    if ($LASTEXITCODE -ne 0) { throw "git ls-files 실패" }
} else {
    $files = Get-ChildItem $pkg -Recurse -File | ForEach-Object { $_.FullName.Substring($pkg.Length + 1).Replace('\', '/') }
}
$files = $files | Where-Object {
    $f = $_
    if ($excludeExact -contains $f) { return $false }
    foreach ($p in $excludePrefix) { if ($f.StartsWith($p)) { return $false } }
    foreach ($p in $toolPrefixes) { if ($f -eq $p -or $f.StartsWith($p)) { return $true } }
    return $false
}
$seedKept = @($files | Where-Object { ($seedFiles -contains $_) -and (Test-Path (Join-Path $Target $_)) })
if ($seedKept) { Write-Info "기존 프로젝트 데이터 보존: $($seedKept -join ', ')" }
$files = @($files | Where-Object { $seedKept -notcontains $_ })
Write-Info "복사 대상 $($files.Count)개 파일"

# 충돌 검사 — 최상위 단위 (병합 폴더는 파일 단위)
$topLevel = $files | ForEach-Object { ($_ -split "/")[0] } | Sort-Object -Unique
$conflicts = $topLevel | Where-Object { ($mergeTop -notcontains $_) -and (Test-Path (Join-Path $Target $_)) }
$mergeConflicts = $files | Where-Object { ($mergeTop -contains ($_ -split "/")[0]) -and (Test-Path (Join-Path $Target $_)) }
if ($mergeConflicts) {
    if (-not $Force) {
        Write-Host "  이미 존재: $($mergeConflicts -join ', ')" -ForegroundColor Red
        throw "기존 파일과 겹칩니다. 백업 후 덮어쓰려면 -Force 를 붙이세요."
    }
    $stampM = Get-Date -Format "yyyyMMdd-HHmmss"
    $backupM = Join-Path $Target ".claude.backup-$stampM"
    Write-Info "파일 백업: $backupM ($(@($mergeConflicts).Count)개 — 병합 폴더의 다른 파일은 그대로 둠)"
    if (-not $DryRun) {
        foreach ($f in $mergeConflicts) {
            $bdst = Join-Path $backupM $f
            New-Item -ItemType Directory -Force -Path (Split-Path -Parent $bdst) | Out-Null
            Copy-Item -Path (Join-Path $Target $f) -Destination $bdst -Force
        }
    }
}
if ($conflicts) {
    if (-not $Force) {
        Write-Host "  이미 존재: $($conflicts -join ', ')" -ForegroundColor Red
        throw "기존 설치가 있습니다. 백업 후 덮어쓰려면 -Force 를 붙이세요."
    }
    $stamp = Get-Date -Format "yyyyMMdd-HHmmss"
    $backup = Join-Path $Target ".claude.backup-$stamp"
    Write-Info "백업: $backup ($($conflicts -join ', '))"
    if (-not $DryRun) {
        New-Item -ItemType Directory -Force -Path $backup | Out-Null
        foreach ($c in $conflicts) { Copy-Item -Path (Join-Path $Target $c) -Destination $backup -Recurse -Force }
        # 디렉터리는 비워서 템플릿과 정확히 같게 만든다.
        # 단 머신별 설정 *.local.json (.claude/settings.local.json · artgen/studio config.local.json 등)은 보존한다
        foreach ($c in $conflicts) {
            $p = Join-Path $Target $c
            if (Test-Path $p -PathType Container) {
                $keeps = @(Get-ChildItem -Path $p -Recurse -File -Filter "*.local.json" -ErrorAction SilentlyContinue |
                           ForEach-Object { @{ Path = $_.FullName; Text = (Read-TextFile $_.FullName) } })
                Remove-Item $p -Recurse -Force
                foreach ($k in $keeps) {
                    New-Item -ItemType Directory -Force -Path (Split-Path -Parent $k.Path) | Out-Null
                    Write-TextFile $k.Path $k.Text
                }
                if ($keeps.Count) { Write-Info "보존: $($keeps.Count)개 *.local.json ($c)" }
            }
        }
    }
}

if (-not $DryRun) {
    foreach ($f in $files) {
        $src = Join-Path $pkg $f
        $dst = Join-Path $Target $f
        $dir = Split-Path -Parent $dst
        if (-not (Test-Path $dir)) { New-Item -ItemType Directory -Force -Path $dir | Out-Null }
        Copy-Item -Path $src -Destination $dst -Force
    }
    # MIT 고지 유지 — 원본 라이선스를 함께 둔다
    $lic = Join-Path $Target ".agent\licenses"
    New-Item -ItemType Directory -Force -Path $lic | Out-Null
    Copy-Item (Join-Path $pkg "LICENSE") $lic -Force
    Copy-Item (Join-Path $pkg "THIRD_PARTY_LICENSES.md") $lic -Force
    New-Item -ItemType Directory -Force -Path (Join-Path $Target "production\session-state") | Out-Null
}
Write-Ok "복사 완료 (+ .agent/licenses, production/session-state/)"

# === [2/6] 자리표시자 치환 ===
Write-Step "[2/6] 게임 폴더 매핑 · 공유 모듈"

if ($Games.Count -eq 0 -and [Environment]::UserInteractive -and -not [Console]::IsInputRedirected -and -not $DryRun) {
    $srcExt = @{ Unity = "*.cs"; Godot = "*.gd"; Unreal = "*.cpp" }[$Engine]
    $candRoot = if ($Engine -eq "Godot") { $Target } else { Join-Path $Target $codeRoot }
    Write-Info "$(Split-Path -Leaf $candRoot)/ 하위 후보 ($srcExt 수):"
    Get-ChildItem $candRoot -Directory -ErrorAction SilentlyContinue | Where-Object { $_.Name -notmatch '^\.' } | ForEach-Object {
        $n = (Get-ChildItem $_.FullName -Recurse -Filter $srcExt -ErrorAction SilentlyContinue | Measure-Object).Count
        if ($n -gt 0) { [PSCustomObject]@{ N = $n; Name = $_.Name } }
    } | Sort-Object N -Descending | ForEach-Object { Write-Info ("{0,6}  {1}" -f $_.N, $_.Name) }
    $answer = Read-Host "  게임 매핑 입력 (예: RPG=MyRpg,PZL=MyPuzzle · 비우면 건너뜀)"
    if ($answer) { $Games = $answer -split "," | ForEach-Object { $_.Trim() } | Where-Object { $_ } }
    if (-not $SharedModule) { $SharedModule = Read-Host "  공유 모듈 폴더명 (없으면 비움)" }
}

$pairs = @()
foreach ($g in $Games) {
    if ($g -notmatch "^\s*\[?([A-Za-z0-9_]+)\]?\s*=\s*(.+?)\s*$") { throw "Games 형식 오류: '$g' (TAG=폴더)" }
    $pairs += [PSCustomObject]@{ Tag = $Matches[1].ToUpper(); Folder = $Matches[2] }
}
foreach ($p in $pairs) {
    $gdir = if ($Engine -eq "Godot") { $p.Folder } else { "$codeRoot/$($p.Folder)" }
    if (-not (Test-Path (Join-Path $Target $gdir))) { Write-Host "  경고: $gdir 없음" -ForegroundColor DarkYellow }
}

# 치환 대상 = 템플릿이 자리표시자를 둔 문서·룰·래퍼 (.agent/skills 의 C# 템플릿은 /sf-add 가 주입 시 치환)
$placeholderFiles = @("AGENTS.md", ".claude/rules/doc-writing.md", ".claude/rules/gameplay-code.md",
                      ".agent/rules/doc-writing.md", ".agent/rules/gameplay-code.md",
                      ".cursor/rules/doc-writing.mdc", ".cursor/rules/gameplay-code.mdc",
                      ".github/instructions/doc-writing.instructions.md", ".github/instructions/gameplay-code.instructions.md",
                      ".windsurf/rules/doc-writing.md", ".windsurf/rules/gameplay-code.md",
                      ".claude/skills/ko-code-review/SKILL.md", ".claude/skills/sf-add/SKILL.md",
                      ".agent/workflows/ko-code-review.md", ".claude/docs/editor-automation-decision.md")

$changed = 0
foreach ($rel in $placeholderFiles) {
    $path = Join-Path $Target $rel
    if (-not (Test-Path $path)) { continue }
    $text = Read-TextFile $path
    $orig = $text

    if ($rel -eq "AGENTS.md" -and $pairs.Count -gt 0) {
        $rows = ($pairs | ForEach-Object { "| [$($_.Tag)] | $($_.Folder) |" }) -join "`n"
        $core = if ($SharedModule) { "`n| [CORE] | $SharedModule |" } else { "" }
        $text = [regex]::Replace($text, "\| \[GAME1\] \| YourFirstGame \|\r?\n\| \[GAME2\] \| YourSecondGame \|\r?\n\| \[CORE\] \| <SharedModule> \|", ($rows + $core))
    }
    if ($SharedModule) { $text = $text.Replace("<SharedModule>", $SharedModule) }
    if ($pairs.Count -gt 0 -and $rel -like "*gameplay-code*") {
        # 네임스페이스 예시만 — 첫 게임 폴더명을 prefix 로
        $text = [regex]::Replace($text, "\bYourGame\.(Gameplay|Core)\.", "$($pairs[0].Folder).`$1.")
    }
    if ($pairs.Count -gt 0 -and $rel -like "*doc-writing*") {
        $tags = ($pairs | ForEach-Object { "``[$($_.Tag)]``" }) -join ", "
        $text = $text.Replace("예: ``[GAME1]``, ``[GAME2]``, ``[CORE]``", "예: $tags, ``[CORE]``")
    }
    if ($text -ne $orig) { Write-TextFile $path $text; $changed++; Write-Info "치환: $rel" }
}
if ($pairs.Count -eq 0) { Write-Info "게임 매핑 없음 — AGENTS.md §6 표는 자리표시자 그대로 (단일 게임이면 무시해도 됨)" }
# CLAUDE.md 의 엔진 레퍼런스 import 줄을 대상 엔진으로 (매 세션 다른 엔진 문서를 읽지 않게 — /setup-engine 도 같은 줄을 고친다)
$cm = Join-Path $Target "CLAUDE.md"
if ((Test-Path $cm) -and ($Tools -contains "Claude")) {
    $ctext = Read-TextFile $cm
    $cnew = [regex]::Replace($ctext, '(?m)^@docs/engine-reference/[a-z]+/VERSION\.md', "@docs/engine-reference/$($Engine.ToLower())/VERSION.md")
    if ($cnew -ne $ctext) { Write-TextFile $cm $cnew; $changed++; Write-Info "치환: CLAUDE.md 엔진 레퍼런스 → $($Engine.ToLower())" }
}
Write-Ok "$changed 개 파일 치환"

# === [3/6] settings.local.json ===
Write-Step "[3/6] .claude/settings.local.json"
if (-not $isUnity) {
    Write-Info "$Engine — MCP for Unity 권한 없음, 건너뜀"
} elseif ($Tools -contains "Claude") {
    $allow = @(
        "mcp__UnityMCP__manage_scene", "mcp__UnityMCP__manage_gameobject", "mcp__UnityMCP__manage_components",
        "mcp__UnityMCP__manage_asset", "mcp__UnityMCP__manage_editor", "mcp__UnityMCP__batch_execute",
        "mcp__UnityMCP__refresh_unity", "mcp__UnityMCP__read_console", "Bash(mkdir -p production/session-logs)"
    )
    $slPath = Join-Path $Target ".claude\settings.local.json"
    if (Test-Path $slPath) {
        $json = Read-TextFile $slPath | ConvertFrom-Json
        if (-not $json.permissions) { $json | Add-Member -NotePropertyName permissions -NotePropertyValue ([PSCustomObject]@{}) }
        if (-not $json.permissions.allow) { $json.permissions | Add-Member -NotePropertyName allow -NotePropertyValue @() -Force }
        $existing = @($json.permissions.allow)
        $added = $allow | Where-Object { $existing -notcontains $_ }
        $json.permissions.allow = @($existing + $added)
        Write-TextFile $slPath (ConvertTo-PlainJson $json)
        Write-Ok "기존 파일에 권한 $(@($added).Count)개 병합"
    } else {
        $obj = [PSCustomObject]@{ permissions = [PSCustomObject]@{ allow = $allow } }
        Write-TextFile $slPath (ConvertTo-PlainJson $obj)
        Write-Ok "생성 (권한 $($allow.Count)개)"
    }
} else { Write-Info "Claude 미선택 — 건너뜀" }

# === [4/6] MCPForUnity ===
Write-Step "[4/6] MCPForUnity"
if (-not $isUnity) {
    Write-Info "$Engine — MCP for Unity 는 Unity 전용, 건너뜀 (에디터 자동화는 .claude/docs/engine-layers.md)"
} elseif ($SkipMcp) {
    Write-Info "-SkipMcp — 건너뜀"
} else {
    $manifest = Join-Path $Target "Packages\manifest.json"
    $mcpPkg = '"com.coplaydev.unity-mcp": "https://github.com/CoplayDev/unity-mcp.git?path=/MCPForUnity#main"'
    $mtext = Read-TextFile $manifest
    if ($mtext -match '"com\.coplaydev\.unity-mcp"') {
        Write-Info "manifest.json — 이미 있음"
    } else {
        # 텍스트 삽입 — ConvertTo-Json 왕복은 manifest 서식을 바꾸므로 피한다
        $new = [regex]::Replace($mtext, '"dependencies"\s*:\s*\{', "`"dependencies`": {`n    $mcpPkg,", 1)
        if ($new -eq $mtext) { throw "manifest.json 에서 dependencies 를 찾지 못했습니다" }
        Write-TextFile $manifest $new
        Write-Ok "manifest.json — com.coplaydev.unity-mcp 추가 (Unity 포커스 시 설치됨)"
    }

    $mcpJson = Join-Path $Target ".mcp.json"
    if (Test-Path $mcpJson) {
        Write-Info ".mcp.json — 이미 있음 (수정 안 함)"
    } else {
        $uvx = "uvx"
        if (-not (Get-Command uvx -ErrorAction SilentlyContinue)) {
            $cand = Join-Path $env:USERPROFILE ".local\bin\uvx.exe"
            if (Test-Path $cand) { $uvx = $cand.Replace('\', '/') }
            else { Write-Host "  경고: uvx 를 찾지 못함 — uv 설치 후 .mcp.json 의 command 확인 (https://docs.astral.sh/uv/)" -ForegroundColor DarkYellow }
        }
        $t = Read-TextFile (Join-Path $pkg ".mcp.json.template") | ConvertFrom-Json
        $server = $t.mcpServers.'unity-mcp'
        $server.command = $uvx
        $args2 = @($server.args)
        $pi = [Array]::IndexOf($args2, "--port")
        if ($pi -ge 0) { $args2[$pi + 1] = "$McpPort" }
        $server.args = $args2
        $out = [PSCustomObject]@{ mcpServers = [PSCustomObject]@{ 'unity-mcp' = $server } }
        Write-TextFile $mcpJson (ConvertTo-PlainJson $out)
        Write-Ok ".mcp.json — 생성 (command=$uvx, port=$McpPort)"
    }
}

# === [5/6] .gitignore ===
Write-Step "[5/6] .gitignore"
$gi = Join-Path $Target ".gitignore"
$need = @(".claude.backup-*/", ".claude/settings.local.json", ".claude/scheduled_tasks.lock", ".mcp.json",
          "production/session-logs/", "production/session-state/active.md", "production/stage.txt",
          "production/artgen/*/v*/", "production/artgen/*/replaced/", "production/artgen/_inbox/", ".agent/tools/artgen/artgen.config.local.json", "art-source/sound-library/",
          "production/studio/events.jsonl", "production/studio/PAUSED", "production/studio/logs/", "production/studio/locks/", ".agent/tools/studio/studio.config.local.json", ".agent/gamedesign/", "__pycache__/",
          "project.local.yaml", "CLAUDE.local.md", ".claude/agent-memory/", ".claude/worktrees/", "docs/consistency-failures.md")
$giText = ""
if (Test-Path $gi) { $giText = Read-TextFile $gi }
$lines = $giText -split "\r?\n"
$missing = $need | Where-Object { $lines -notcontains $_ }
if ($missing) {
    $nl = if ($giText -match "`r`n") { "`r`n" } else { "`n" }
    $block = "$nl# 게임 개발 통합 스킬 (scripts/install.ps1) — 머신별·런타임 파일$nl" + ($missing -join $nl) + $nl
    if ($giText -and -not $giText.EndsWith("`n")) { $block = $nl + $block }
    Write-TextFile $gi ($giText + $block)
    Write-Ok "$(@($missing).Count)개 항목 추가"
} else { Write-Info "이미 모두 있음" }

# === [6/6] 다음 단계 ===
Write-Step "[6/6] 완료 — 다음 단계"
if ($isUnity) { Write-Host "  1. Unity 에디터를 열어 MCPForUnity 패키지 설치 확인 (Window > MCP for Unity, 포트 $McpPort)" -ForegroundColor Cyan }
else { Write-Host "  1. $Engine — 엔진별 테스트 · 자동화 · 정적 검사 현황: .claude/docs/engine-layers.md" -ForegroundColor Cyan }
Write-Host "  2. 프로젝트 루트에서 Claude Code 실행:  cd `"$Target`"; claude" -ForegroundColor Cyan
Write-Host "  3. 사전 설치 점검 · 설치 (PC 마다 최초 1회):  /ko-prereq   (또는 python .agent/tools/setup/prereq.py check)" -ForegroundColor Cyan
Write-Host "  4. 엔진 설정 (최초 1회):  /ko-setup-engine" -ForegroundColor Cyan
Write-Host "  5. 메뉴 안내:  /unity-fullstack" -ForegroundColor Cyan
if ($pairs.Count -eq 0) { Write-Host "  (선택) 멀티 게임이면 AGENTS.md §6 게임 폴더 매핑 표를 채우세요." -ForegroundColor DarkCyan }
