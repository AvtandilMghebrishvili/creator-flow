[CmdletBinding()]
param([switch]$WithoutVendorClis)
$ErrorActionPreference = 'Stop'
$python = Join-Path $PSScriptRoot '.venv\Scripts\python.exe'
if (-not (Test-Path -LiteralPath $python)) { throw 'Run Install.ps1 first to create the Creator Flow environment.' }
& $python -m pip install -e "${PSScriptRoot}[connectors]"
if ($LASTEXITCODE -ne 0) { throw 'Studio dependency installation failed.' }
if (-not $WithoutVendorClis) {
    $node = Get-Command node -CommandType Application -ErrorAction Stop | Select-Object -First 1
    $npm = Get-Command npm.cmd -CommandType Application -ErrorAction Stop | Select-Object -First 1
    $major = & $node.Source -p 'Number(process.versions.node.match(/^[0-9]+/)[0])'
    if ([int]$major -lt 22) { throw 'Install Node.js 22 or newer, then rerun this installer.' }
    $target = Join-Path $PSScriptRoot 'tools\subscription-connectors'
    & $npm.Source install --prefix $target '@google/gemini-cli@0.62.0' '@anthropic-ai/claude-code@2.1.288' --no-audit --no-fund
    if ($LASTEXITCODE -ne 0) { throw 'Official vendor CLI installation failed.' }
}
Write-Output 'Installed. Run .\Start-Studio.ps1, then connect your own accounts in Studio. No sign-in or generation was performed by this installer.'
