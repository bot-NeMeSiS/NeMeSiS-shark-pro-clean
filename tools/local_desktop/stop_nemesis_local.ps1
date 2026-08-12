param()
$ErrorActionPreference = "Stop"
$root = (Resolve-Path (Join-Path $PSScriptRoot "..\..")).Path
$localDir = Join-Path $root "data\local_dev"
$pidFile = Join-Path $localDir "nemesis_local.pid.json"
$logFile = Join-Path $localDir "nemesis_local.log"
if (-not (Test-Path -LiteralPath $pidFile)) {
    Write-Host "NeMeSiS LOCAL no esta funcionando."
    exit 0
}
try {
    $metadata = Get-Content -LiteralPath $pidFile -Raw | ConvertFrom-Json
    $processId = [int]$metadata.pid
} catch {
    Remove-Item -LiteralPath $pidFile -Force -ErrorAction SilentlyContinue
    Write-Host "Se limpio un estado local antiguo. NeMeSiS LOCAL no estaba funcionando."
    exit 0
}
$process = Get-CimInstance Win32_Process -Filter "ProcessId = $processId" -ErrorAction SilentlyContinue
if (-not $process) {
    Remove-Item -LiteralPath $pidFile -Force -ErrorAction SilentlyContinue
    Write-Host "NeMeSiS LOCAL ya estaba detenido."
    exit 0
}
$commandLine = [string]$process.CommandLine
$expectedRunner = (Resolve-Path (Join-Path $root "tools\local_desktop\run_local_desktop.py")).Path
$metadataRoot = [string]$metadata.project_root
$metadataRunner = [string]$metadata.runner
$pathsMatch = $metadataRoot.Equals($root, [StringComparison]::OrdinalIgnoreCase) -and $metadataRunner.Equals($expectedRunner, [StringComparison]::OrdinalIgnoreCase)
if (-not $pathsMatch -or -not $commandLine.ToLowerInvariant().Contains("run_local_desktop.py")) {
    Write-Host "DETENCION BLOQUEADA: el PID no pertenece al launcher oficial de esta carpeta."
    exit 2
}
Stop-Process -Id $processId -ErrorAction Stop
for ($attempt = 0; $attempt -lt 30; $attempt++) {
    if (-not (Get-Process -Id $processId -ErrorAction SilentlyContinue)) { break }
    Start-Sleep -Milliseconds 100
}
Remove-Item -LiteralPath $pidFile -Force -ErrorAction SilentlyContinue
New-Item -ItemType Directory -Force -Path $localDir | Out-Null
Add-Content -LiteralPath $logFile -Value "$(Get-Date -Format o) STOP_FROM_DESKTOP pid=$processId"
Write-Host "NeMeSiS LOCAL se ha detenido. Otros procesos Python no se han tocado."