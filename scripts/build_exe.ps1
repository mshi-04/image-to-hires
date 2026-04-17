Set-StrictMode -Version Latest
$ErrorActionPreference = "Stop"

$scriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
$repoRoot = Resolve-Path (Join-Path $scriptDir "..")
$specPath = Join-Path $repoRoot "image_to_hires.spec"
$realcuganExe = Join-Path $repoRoot "bin\\realcugan\\realcugan-ncnn-vulkan.exe"
$realcuganModelsDir = Join-Path $repoRoot "models\\realcugan\\models-se"

if (-not (Test-Path -LiteralPath $specPath)) {
    throw "Spec file not found: $specPath"
}

if (-not (Test-Path -LiteralPath $realcuganExe -PathType Leaf)) {
    throw "Real-CUGAN executable not found: $realcuganExe`nPlace the Windows runtime under bin\\realcugan\\ before building."
}

if (-not (Test-Path -LiteralPath $realcuganModelsDir -PathType Container)) {
    throw "Real-CUGAN models directory not found: $realcuganModelsDir`nPlace the extracted models under models\\realcugan\\models-se\\ before building."
}

Push-Location $repoRoot
try {
    python -m PyInstaller --clean --noconfirm --distpath dist --workpath build $specPath
}
finally {
    Pop-Location
}
