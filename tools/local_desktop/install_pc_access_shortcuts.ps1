$ErrorActionPreference = "Stop"
$root = (Resolve-Path (Join-Path $PSScriptRoot "..\..")).Path
$desktop = [Environment]::GetFolderPath("Desktop")
if (-not (Test-Path -LiteralPath $desktop -PathType Container)) {
    throw "No se encuentra el Escritorio de Windows: $desktop"
}

$appUrl = "https://bot-apuestas-crgf.onrender.com/"
$adminUrl = "https://bot-apuestas-crgf.onrender.com/admin"
$renderUrl = "https://dashboard.render.com/web/srv-d7t9j2favr4c738hm0i0"
$commandCenter = Join-Path $root "tools\local_desktop\centro-de-mando.html"
$appIcon = Join-Path $root "static\img\app-icons\app-icon.ico"
if (-not (Test-Path -LiteralPath $commandCenter -PathType Leaf)) { throw "No se encuentra el Centro de mando: $commandCenter" }
if (-not (Test-Path -LiteralPath $appIcon -PathType Leaf)) { throw "No se encuentra el icono oficial de NeMeSiS: $appIcon" }

function Write-InternetShortcut([string]$name, [string]$url) {
    $path = Join-Path $desktop ($name + ".url")
    $contents = "[InternetShortcut]`r`nURL=$url`r`n"
    Set-Content -LiteralPath $path -Value $contents -Encoding ASCII
    Write-Output $path
}

$shell = New-Object -ComObject WScript.Shell
$projectPath = Join-Path $desktop "NeMeSiS Proyecto.lnk"
$shortcut = $shell.CreateShortcut($projectPath)
$shortcut.TargetPath = $root
$shortcut.Arguments = ""
$shortcut.WorkingDirectory = $root
$shortcut.Description = "Abrir la carpeta local del proyecto NeMeSiS"
$shortcut.Save()

Write-InternetShortcut "NeMeSiS App" $appUrl
Write-InternetShortcut "NeMeSiS Administracion" $adminUrl
Write-InternetShortcut "NeMeSiS Render" $renderUrl
$centerUrl = ([System.Uri]::new($commandCenter)).AbsoluteUri
$chromeCandidates = @(
    (Join-Path $env:ProgramFiles "Google\Chrome\Application\chrome.exe"),
    (Join-Path $env:LOCALAPPDATA "Google\Chrome\Application\chrome.exe")
)
$chromePath = $chromeCandidates | Where-Object { Test-Path -LiteralPath $_ -PathType Leaf } | Select-Object -First 1
if ($chromePath) {
    $centerShortcutPath = Join-Path $desktop "NeMeSiS Centro de Mando.lnk"
    $centerShortcut = $shell.CreateShortcut($centerShortcutPath)
    $centerShortcut.TargetPath = $chromePath
    $centerShortcut.Arguments = "--app=`"$centerUrl`""
    $centerShortcut.WorkingDirectory = $root
    $centerShortcut.Description = "Abrir el Centro de mando de NeMeSiS con sus accesos oficiales"
    $centerShortcut.IconLocation = "$appIcon,0"
    $centerShortcut.WindowStyle = 1
    $centerShortcut.Save()
    Write-Output $centerShortcutPath
} else {
    Write-InternetShortcut "NeMeSiS Centro de Mando" $centerUrl
}
Write-Output $projectPath
