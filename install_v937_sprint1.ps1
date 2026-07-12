param(
    [string]$ProjectRoot = "C:\Users\aloha\OneDrive\Escritorio\NeMeSiS shark pro"
)

$ErrorActionPreference = "Stop"

Write-Host ""
Write-Host "NeMeSiS SHARK PRO - Instalador V937 Sprint 1" -ForegroundColor Cyan
Write-Host "Proyecto: $ProjectRoot"
Write-Host ""

if (-not (Test-Path $ProjectRoot)) {
    throw "No existe la carpeta del proyecto: $ProjectRoot"
}

$required = @("app.py", "VERSION.txt", "templates", "static")
foreach ($item in $required) {
    if (-not (Test-Path (Join-Path $ProjectRoot $item))) {
        throw "La carpeta seleccionada no parece ser la raíz del proyecto. Falta: $item"
    }
}

$branchInfo = ""
try {
    $branchInfo = git -C $ProjectRoot branch --show-current 2>$null
} catch {}

if ($branchInfo) {
    Write-Host "Rama detectada: $branchInfo"
    if ($branchInfo -ne "chatgpt/v937-product-perfection") {
        Write-Warning "No estás en chatgpt/v937-product-perfection. El instalador continuará solo si confirmas."
        $answer = Read-Host "Escribe SI para continuar"
        if ($answer -ne "SI") {
            throw "Instalación cancelada."
        }
    }
} else {
    Write-Warning "Git no está disponible desde PowerShell. Verifica manualmente la rama en GitHub Desktop."
}

$stamp = Get-Date -Format "yyyyMMdd_HHmmss"
$backupRoot = Join-Path $ProjectRoot "reports\V937_backup_$stamp"
New-Item -ItemType Directory -Force -Path $backupRoot | Out-Null

$files = @(
    "templates\home.html",
    "templates\components\v936_product.html",
    "static\v936-commercial.css",
    "reports\V937_SPRINT_1_HOME_DECISION_TRUST.md"
)

$payloadRoot = Join-Path $PSScriptRoot "payload"

foreach ($relative in $files) {
    $source = Join-Path $payloadRoot $relative
    $target = Join-Path $ProjectRoot $relative

    if (-not (Test-Path $source)) {
        throw "Falta archivo del parche: $relative"
    }

    if (Test-Path $target) {
        $backupFile = Join-Path $backupRoot $relative
        New-Item -ItemType Directory -Force -Path (Split-Path $backupFile -Parent) | Out-Null
        Copy-Item -Force $target $backupFile
    }

    New-Item -ItemType Directory -Force -Path (Split-Path $target -Parent) | Out-Null
    Copy-Item -Force $source $target
    Write-Host "Aplicado: $relative" -ForegroundColor Green
}

Write-Host ""
Write-Host "Verificando archivos..." -ForegroundColor Cyan

$allOk = $true
foreach ($relative in $files) {
    $source = Join-Path $payloadRoot $relative
    $target = Join-Path $ProjectRoot $relative
    $srcHash = (Get-FileHash $source -Algorithm SHA256).Hash
    $dstHash = (Get-FileHash $target -Algorithm SHA256).Hash
    if ($srcHash -eq $dstHash) {
        Write-Host "OK  $relative" -ForegroundColor Green
    } else {
        Write-Host "FALLO  $relative" -ForegroundColor Red
        $allOk = $false
    }
}

if (-not $allOk) {
    throw "Uno o más archivos no coinciden después de copiar."
}

Write-Host ""
Write-Host "Instalación completada correctamente." -ForegroundColor Green
Write-Host "Copia de seguridad: $backupRoot"
Write-Host ""
Write-Host "Ahora abre GitHub Desktop. Deben aparecer 4 cambios." -ForegroundColor Yellow
Write-Host "Commit sugerido:"
Write-Host "V937 Sprint 1 - Home decision and data trust"
Write-Host ""
