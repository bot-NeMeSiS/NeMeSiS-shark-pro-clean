param(
  [Parameter(ValueFromRemainingArguments = $true)]
  [string[]]$PytestArgs = @()
)

$ErrorActionPreference = "Stop"
$repoRoot = (Resolve-Path (Join-Path $PSScriptRoot "..")).Path
$appData = [Environment]::GetFolderPath("LocalApplicationData")
$candidates = @(
  (Join-Path $repoRoot ".venv\Scripts\python.exe"),
  (Join-Path $appData "NeMeSiS\venvs\main-py311\Scripts\python.exe"),
  (Join-Path $appData "NeMeSiS\venvs\main-py312\Scripts\python.exe")
)
$python = $null

foreach ($candidate in $candidates) {
  if (-not (Test-Path -LiteralPath $candidate)) { continue }
  & $candidate -c "import flask, pytest, playwright, tzdata" *> $null
  if ($LASTEXITCODE -eq 0) {
    $python = $candidate
    break
  }
}

if (-not $python) {
  throw "No hay un entorno local completo. Ejecuta primero .\tools\setup_local_tests.ps1; conserva tu carpeta .venv actual, este instalador crea el entorno de Codex en LocalAppData."
}

$tempRoot = Join-Path $appData "NeMeSiS\pytest-runs"
New-Item -ItemType Directory -Path $tempRoot -Force | Out-Null
$baseTemp = Join-Path $tempRoot ("run-" + [guid]::NewGuid().ToString("N"))
New-Item -ItemType Directory -Path $baseTemp | Out-Null

Push-Location $repoRoot
try {
  Write-Host "Python: $python"
  Write-Host "Temporales de prueba: $baseTemp"
  & $python -m pytest -p no:cacheprovider --basetemp $baseTemp @PytestArgs
  exit $LASTEXITCODE
}
finally {
  Pop-Location
}
