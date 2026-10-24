# Verifier tier entrypoint. Installed as .assurance/tools/verify-fast.ps1, verify.ps1, and so on;
# the tier is the file name. Local runs and CI call this same file.
[CmdletBinding()]
param([Parameter(ValueFromRemainingArguments = $true)][string[]]$Rest)

$ErrorActionPreference = 'Stop'
$tier = [IO.Path]::GetFileNameWithoutExtension($PSCommandPath)
$python = if ($env:PYTHON) { $env:PYTHON } else {
    $candidate = Get-Command python3, python -ErrorAction SilentlyContinue | Select-Object -First 1
    if (-not $candidate) { throw 'Python 3.9 or newer is required; set PYTHON to its executable path.' }
    $candidate.Source
}

& $python (Join-Path $PSScriptRoot 'run_verifier.py') --tier $tier --root (Join-Path $PSScriptRoot '..\..') @Rest
exit $LASTEXITCODE
