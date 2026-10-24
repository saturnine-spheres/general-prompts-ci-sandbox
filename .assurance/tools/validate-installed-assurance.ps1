[CmdletBinding()]
param(
    [string]$Root = (Resolve-Path (Join-Path $PSScriptRoot '..\..')).Path,
    [string]$ReportPath
)

$ErrorActionPreference = 'Stop'
$python = if ($env:PYTHON) { $env:PYTHON } else {
    $candidate = Get-Command python3, python -ErrorAction SilentlyContinue | Select-Object -First 1
    if (-not $candidate) { throw 'Python 3.9 or newer is required; set PYTHON to its executable path.' }
    $candidate.Source
}

$arguments = @((Join-Path $PSScriptRoot 'validate_installed_assurance.py'), '--root', $Root)
if ($ReportPath) { $arguments += @('--report', $ReportPath) }
& $python @arguments
exit $LASTEXITCODE
