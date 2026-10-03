[CmdletBinding()]
param(
    [string]$Workspace = (Join-Path ([Environment]::GetFolderPath('LocalApplicationData')) 'CreatorFlow\Studio'),
    [int]$Port = 8772,
    [string[]]$ExtensionId = @()
)
$ErrorActionPreference = 'Stop'
$python = Join-Path $PSScriptRoot '.venv\Scripts\python.exe'
if (-not (Test-Path -LiteralPath $python)) { throw 'Run Install.ps1 and Install-Studio.ps1 first.' }
$vendorRoot = Join-Path $PSScriptRoot 'tools\subscription-connectors\node_modules'
$gemini = Join-Path $vendorRoot '@google\gemini-cli\bundle\gemini.js'
$claude = Join-Path $vendorRoot '@anthropic-ai\claude-code\bin\claude.exe'
if (Test-Path -LiteralPath $gemini) { $env:CREATOR_FLOW_GEMINI_CLI = $gemini }
if (Test-Path -LiteralPath $claude) { $env:CREATOR_FLOW_CLAUDE_CLI = $claude }
$arguments = @('-X', 'utf8', '-m', 'podcut', 'studio-serve', '--workspace', $Workspace, '--port', "$Port")
foreach ($id in $ExtensionId) { $arguments += @('--extension-id', $id) }
& $python @arguments
exit $LASTEXITCODE
