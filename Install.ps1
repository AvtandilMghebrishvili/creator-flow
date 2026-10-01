[CmdletBinding()]
param(
    [switch]$Check,
    [switch]$WithoutTranscription,
    [switch]$WithWhisper,
    [switch]$WithArchive,
    [switch]$Premiere
)
$ErrorActionPreference = 'Stop'

function Find-PodcutPython {
    $candidates = @((Join-Path $PSScriptRoot '.venv\Scripts\python.exe'))
    foreach ($commandName in @('python', 'python3')) {
        $command = Get-Command $commandName -CommandType Application -ErrorAction SilentlyContinue
        if ($command -and $command.Source -notlike '*\Microsoft\WindowsApps\*') {
            $candidates += $command.Source
        }
    }
    if ($env:LOCALAPPDATA) {
        $candidates += Join-Path $env:LOCALAPPDATA 'Programs\Python\Python312\python.exe'
    }
    $launcher = Get-Command py -CommandType Application -ErrorAction SilentlyContinue
    if ($launcher) {
        foreach ($selector in @('-3.12', '-3')) {
            try { $candidate = & $launcher.Source $selector -c 'import sys; print(sys.executable)' 2>$null }
            catch { continue }
            if ($LASTEXITCODE -eq 0) { $candidates += $candidate }
        }
    }
    foreach ($candidate in ($candidates | Select-Object -Unique)) {
        if (-not (Test-Path -LiteralPath $candidate -PathType Leaf)) { continue }
        & $candidate -c 'import sys; sys.exit(0 if sys.version_info >= (3,10) and sys.maxsize > 2**32 else 1)' 2>$null
        if ($LASTEXITCODE -eq 0) { return $candidate }
    }
    return $null
}

$podcutPython = Find-PodcutPython
if (-not $podcutPython) {
    if ($Check) { Write-Output 'Missing: usable 64-bit Python 3.10+.'; exit 2 }
    $winget = Get-Command winget -CommandType Application -ErrorAction SilentlyContinue
    if (-not $winget) {
        throw 'Install 64-bit Python from python.org (or enable Windows App Installer/winget), then run this installer again.'
    }
    & $winget.Source install --id Python.Python.3.12 --exact --source winget --scope user --architecture x64 --no-upgrade --accept-source-agreements --accept-package-agreements
    if ($LASTEXITCODE -ne 0) { throw 'Python installation failed. Inspect the installer output.' }
    $env:PATH = $env:PATH + ';' + [Environment]::GetEnvironmentVariable('Path', 'User') + ';' + [Environment]::GetEnvironmentVariable('Path', 'Machine')
    $podcutPython = Find-PodcutPython
    if (-not $podcutPython) { throw 'Python is still unavailable. Reopen the terminal and rerun; no success is being assumed.' }
}
$podcutArgs = @((Join-Path $PSScriptRoot 'scripts\install.py'))
if ($Check) { $podcutArgs += '--check' }
if ($WithoutTranscription) { $podcutArgs += '--without-transcription' }
if ($WithWhisper) { $podcutArgs += '--with-whisper' }
if ($WithArchive) { $podcutArgs += '--with-archive' }
if ($Premiere) { $podcutArgs += '--premiere' }
& $podcutPython @podcutArgs
exit $LASTEXITCODE
