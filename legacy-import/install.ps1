$ErrorActionPreference = "Stop"

$SkillDir = Join-Path $env:USERPROFILE ".claude\skills\youtube-techcrush"
$Src      = Join-Path $PSScriptRoot "skills\youtube-techcrush"

if (-not (Test-Path (Join-Path $Src "SKILL.md"))) {
    Write-Error "Run this from the repository root."
}

New-Item -ItemType Directory -Force -Path $SkillDir | Out-Null
Copy-Item -Recurse -Force (Join-Path $Src "*") $SkillDir

Write-Host "Installed to $SkillDir" -ForegroundColor Green
Write-Host "Next: cd to your project and run"
Write-Host "  node `"$SkillDir\scripts\doctor.js`""
