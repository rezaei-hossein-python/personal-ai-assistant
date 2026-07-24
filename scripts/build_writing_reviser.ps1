param(
    [switch]$SkipTests
)

$ErrorActionPreference = "Stop"

$ProjectRoot = Resolve-Path (Join-Path $PSScriptRoot "..")
$Python = Join-Path $ProjectRoot ".conda\python.exe"
$OutputDir = Join-Path $ProjectRoot "dist\PersonalAIWritingReviser"
$BuildDir = Join-Path $ProjectRoot "build"

if (-not (Test-Path $Python)) {
    throw "Python environment not found at $Python"
}

if (-not $SkipTests) {
    & $Python -m pytest --basetemp=.pytest-temp
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

& $Python -m PyInstaller (Join-Path $ProjectRoot "PersonalAIWritingReviser.spec") --noconfirm

Write-Host "Writing reviser build created at $OutputDir"
