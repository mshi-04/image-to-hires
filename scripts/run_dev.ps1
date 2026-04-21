Set-StrictMode -Version Latest
$ErrorActionPreference = "Stop"

$scriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
$repoRoot = Resolve-Path (Join-Path $scriptDir "..")
$mainModulePath = Join-Path $repoRoot "src\main.py"

if (-not (Test-Path -LiteralPath $mainModulePath -PathType Leaf)) {
    throw "Application entry point not found: $mainModulePath"
}

Push-Location $repoRoot
try {
    python -m src.main
}
finally {
    Pop-Location
}
