param(
    [switch]$SkipTests
)

$ErrorActionPreference = "Stop"

$ProjectRoot = Resolve-Path (Join-Path $PSScriptRoot "..")
$FrontendDir = Join-Path $ProjectRoot "frontend"
$Python = Join-Path $ProjectRoot ".conda\python.exe"
$OutputDir = Join-Path $ProjectRoot "dist\PersonalAIAssistant"
$BuildDir = Join-Path $ProjectRoot "build"

if (-not (Test-Path $Python)) {
    throw "Python environment not found at $Python"
}

if (-not (Test-Path (Join-Path $FrontendDir "package-lock.json"))) {
    throw "frontend\package-lock.json is required for npm ci"
}

Push-Location $FrontendDir
try {
    npm.cmd ci
    npm.cmd run lint
    npm.cmd run build
}
finally {
    Pop-Location
}

if (-not $SkipTests) {
    & $Python -m pytest
}

$ResolvedOutput = [System.IO.Path]::GetFullPath($OutputDir)
$ResolvedBuild = [System.IO.Path]::GetFullPath($BuildDir)
$ResolvedProject = [System.IO.Path]::GetFullPath($ProjectRoot)

if (-not $ResolvedOutput.StartsWith($ResolvedProject)) {
    throw "Refusing to clean output outside project root: $ResolvedOutput"
}
if (-not $ResolvedBuild.StartsWith($ResolvedProject)) {
    throw "Refusing to clean build outside project root: $ResolvedBuild"
}

if (Test-Path $ResolvedOutput) {
    Remove-Item -LiteralPath $ResolvedOutput -Recurse -Force
}

& $Python -m PyInstaller (Join-Path $ProjectRoot "PersonalAIAssistant.spec") --noconfirm

Write-Host "Desktop build created at $OutputDir"
