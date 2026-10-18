$ErrorActionPreference = "Stop"
$repoRoot = (Resolve-Path (Join-Path $PSScriptRoot "..")).Path
$appData = [Environment]::GetFolderPath("LocalApplicationData")
$pyLauncher = Get-Command py -ErrorAction SilentlyContinue
$baseCommand = $null
$baseArgs = @()
$baseVersion = $null

if ($pyLauncher) {
  foreach ($minor in @("3.11", "3.12")) {
    & $pyLauncher.Source "-$minor" -c "import sys; raise SystemExit(0 if sys.version_info[:2] == tuple(map(int, '$minor'.split('.'))) else 1)" *> $null
    if ($LASTEXITCODE -eq 0) {
      $baseCommand = $pyLauncher.Source
      $baseArgs = @("-$minor")
      $baseVersion = $minor
      break
    }
  }
}

if (-not $baseCommand) {
  $bundledPython = Join-Path $env:USERPROFILE ".cache\codex-runtimes\codex-primary-runtime\dependencies\python\python.exe"
  if (Test-Path -LiteralPath $bundledPython) {
    $baseCommand = $bundledPython
    $baseVersion = (& $baseCommand -c "import sys; print(f'{sys.version_info.major}.{sys.version_info.minor}')").Trim()
    if ($baseVersion -notin @("3.11", "3.12")) {
      throw "El Python incluido con Codex ($baseVersion) no es compatible con el entorno de desarrollo recomendado. Instala Python 3.11 o 3.12 y vuelve a ejecutar este script."
    }
  }
}

if (-not $baseCommand) {
  throw "No encuentro Python 3.11 ni 3.12. El proyecto declara $((Get-Content (Join-Path $repoRoot '.python-version') -Raw).Trim()); instala esa versión y vuelve a ejecutar este script."
}

$tag = "py" + ($baseVersion -replace "\.", "")
$venvPath = Join-Path $appData "NeMeSiS\venvs\main-$tag"
$venvPython = Join-Path $venvPath "Scripts\python.exe"
New-Item -ItemType Directory -Path (Split-Path -Parent $venvPath) -Force | Out-Null

if (-not (Test-Path -LiteralPath $venvPython)) {
  & $baseCommand @baseArgs -m venv $venvPath
  if ($LASTEXITCODE -ne 0) { throw "No se pudo crear el entorno Python en $venvPath" }
}

Push-Location $repoRoot
try {
  & $venvPython -m pip install --disable-pip-version-check -r requirements-dev.txt
  if ($LASTEXITCODE -ne 0) { throw "No se pudieron instalar las dependencias de desarrollo." }

  $browserPath = (& $venvPython -c "from playwright.sync_api import sync_playwright; p=sync_playwright().start(); print(p.chromium.executable_path); p.stop()" | Select-Object -Last 1).Trim()
  if (-not (Test-Path -LiteralPath $browserPath)) {
    & $venvPython -m playwright install chromium
    if ($LASTEXITCODE -ne 0) { throw "No se pudo instalar Chromium para las pruebas locales." }
  }

  Write-Host "Entorno listo: $venvPython"
  & $venvPython --version
}
finally {
  Pop-Location
}
