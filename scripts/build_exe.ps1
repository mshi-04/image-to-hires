Set-StrictMode -Version Latest
$ErrorActionPreference = "Stop"

$scriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
$repoRoot = Resolve-Path (Join-Path $scriptDir "..")
$specPath = Join-Path $repoRoot "image_to_hires.spec"

if (-not (Test-Path -LiteralPath $specPath)) {
    throw "Spec file not found: $specPath"
}

Push-Location $repoRoot
try {
    python -m PyInstaller --clean --noconfirm --distpath dist --workpath build $specPath
}
finally {
    Pop-Location
}
