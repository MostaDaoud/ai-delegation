<#
.SYNOPSIS
  Installs the ai-delegation skill pack into an Agent Skills directory.

.DESCRIPTION
  Copies the main skill and its four sub-skills as sibling folders (Agent
  Skills layout). Idempotent: re-running overwrites the previous install.

.EXAMPLE
  .\install.ps1
  .\install.ps1 -Target D:\my-skills
  .\install.ps1 -Uninstall
#>
[CmdletBinding()]
param(
    [string]$Target = (Join-Path $HOME ".agents\skills"),
    [switch]$Uninstall
)

$ErrorActionPreference = "Stop"
$ScriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path

$SkillNames = @(
    "ai-delegation",
    "ai-delegation-decide",
    "ai-delegation-wire",
    "ai-delegation-cost",
    "ai-delegation-audit"
)

$MainSkill = Join-Path $ScriptDir "ai-delegation"
if (-not (Test-Path (Join-Path $MainSkill "SKILL.md"))) {
    Write-Error "ai-delegation\SKILL.md not found next to install.ps1. Extract the full zip first."
    exit 1
}

if ($Uninstall) {
    foreach ($name in $SkillNames) {
        $p = Join-Path $Target $name
        if (Test-Path $p) {
            Remove-Item -LiteralPath $p -Recurse -Force
            Write-Host "  Removed: $name"
        }
    }
    Write-Host "Uninstall complete from $Target"
    exit 0
}

New-Item -ItemType Directory -Path $Target -Force | Out-Null

Copy-Item -LiteralPath $MainSkill -Destination (Join-Path $Target "ai-delegation") -Recurse -Force
Write-Host "  Installed: ai-delegation"

$SkillsRoot = Join-Path $ScriptDir "skills"
if (Test-Path $SkillsRoot) {
    foreach ($s in Get-ChildItem -LiteralPath $SkillsRoot -Directory -Filter "ai-delegation-*") {
        Copy-Item -LiteralPath $s.FullName -Destination (Join-Path $Target $s.Name) -Recurse -Force
        Write-Host "  Installed: $($s.Name)"
    }
}

# Verify all five skills landed with a valid SKILL.md
$missing = @()
foreach ($name in $SkillNames) {
    if (-not (Test-Path (Join-Path $Target "$name\SKILL.md"))) {
        $missing += $name
    }
}
if ($missing.Count -gt 0) {
    Write-Error ("Installation incomplete, missing SKILL.md for: " + ($missing -join ", "))
    exit 1
}

Write-Host ""
Write-Host "Installation complete: $($SkillNames.Count) skills installed to $Target"
Write-Host "Test with: /ai-delegation  (or decide | wire | cost | audit)"
