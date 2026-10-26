[CmdletBinding()]
param(
    [switch]$Preview,
    [string]$DesktopPath = "",
    [string]$BackupDirectory = ""
)

# This installer creates links only. It never starts a browser, installs a PWA,
# changes profiles/cookies, or removes existing shortcuts. Use -Preview first.
Set-StrictMode -Version Latest
$ErrorActionPreference = "Stop"
[Console]::OutputEncoding = [Text.UTF8Encoding]::new($false)
$root = (Resolve-Path (Join-Path $PSScriptRoot "..\..")).Path
if ([string]::IsNullOrWhiteSpace($DesktopPath)) {
    $DesktopPath = [Environment]::GetFolderPath("Desktop")
}
$desktop = [IO.Path]::GetFullPath($DesktopPath)
if (-not (Test-Path -LiteralPath $desktop -PathType Container)) {
    throw "No se encuentra la carpeta de accesos: $desktop"
}
if ([string]::IsNullOrWhiteSpace($BackupDirectory)) {
    $BackupDirectory = Join-Path ([Environment]::GetFolderPath("LocalApplicationData")) "NeMeSiS\shortcut-backups"
}
$backupRoot = [IO.Path]::GetFullPath($BackupDirectory)
if ($backupRoot.TrimEnd('\') -eq $desktop.TrimEnd('\')) {
    throw "La copia de seguridad necesita una carpeta distinta del Escritorio."
}

$appUrl = "https://bot-apuestas-crgf.onrender.com/app"
$adminUrl = "https://bot-apuestas-crgf.onrender.com/admin/founder-os"
$appIcon = Join-Path $root "static\img\app-icons\app-icon.ico"
$adminPath = Join-Path $desktop "NeMeSiS Admin.lnk"
$clientPath = Join-Path $desktop "NeMeSiS SHARK PRO.lnk"
$projectPath = Join-Path $desktop "NeMeSiS Proyecto.lnk"
$shell = New-Object -ComObject WScript.Shell

function Read-ExistingShortcut([string]$path) {
    if (-not (Test-Path -LiteralPath $path -PathType Leaf)) { return $null }
    $item = Get-Item -LiteralPath $path -Force
    if (($item.Attributes -band [IO.FileAttributes]::ReparsePoint) -ne 0) {
        throw "Se conserva sin modificar un enlace especial: $path"
    }
    $link = $shell.CreateShortcut($path)
    return [pscustomobject]@{
        Target = [string]$link.TargetPath
        Arguments = [string]$link.Arguments
        Icon = [string]$link.IconLocation
        WorkingDirectory = [string]$link.WorkingDirectory
        Description = [string]$link.Description
    }
}

function Get-ShortcutSha256([string]$path) {
    # .NET is present in Windows PowerShell; no optional module is required.
    $stream = [IO.File]::OpenRead($path)
    $sha = [Security.Cryptography.SHA256]::Create()
    try { return [BitConverter]::ToString($sha.ComputeHash($stream)).Replace("-", "") }
    finally { $sha.Dispose(); $stream.Dispose() }
}

function Get-ProfileArguments($shortcut) {
    if ($null -eq $shortcut) { return "" }
    $tokens = @()
    foreach ($flag in @("user-data-dir", "profile-directory")) {
        $pattern = '(?i)(?:^|\s)(--' + $flag + '(?:=|\s+)(?:"[^"]*"|[^\s"]+))(?=\s|$)'
        $match = [regex]::Match($shortcut.Arguments, $pattern)
        if ($match.Success) { $tokens += $match.Groups[1].Value }
    }
    return ($tokens -join " ")
}

function Get-BrowserPath($admin, $client) {
    foreach ($known in @($admin, $client)) {
        if ($null -eq $known) { continue }
        $name = [IO.Path]::GetFileName($known.Target)
        if ($name -in @("chrome.exe", "msedge.exe") -and (Test-Path -LiteralPath $known.Target -PathType Leaf)) {
            return $known.Target
        }
        if ($name -in @("chrome_proxy.exe", "msedge_proxy.exe")) {
            $executable = if ($name -eq "chrome_proxy.exe") { "chrome.exe" } else { "msedge.exe" }
            $candidate = Join-Path (Split-Path -Parent $known.Target) $executable
            if (Test-Path -LiteralPath $candidate -PathType Leaf) { return $candidate }
        }
    }
    foreach ($base in @($env:ProgramFiles, ${env:ProgramFiles(x86)}, $env:LOCALAPPDATA)) {
        if ([string]::IsNullOrWhiteSpace($base)) { continue }
        foreach ($relative in @("Google\Chrome\Application\chrome.exe", "Microsoft\Edge\Application\msedge.exe")) {
            $candidate = Join-Path $base $relative
            if (Test-Path -LiteralPath $candidate -PathType Leaf) { return $candidate }
        }
    }
    return ""
}

function Get-BrowserFamily([string]$target) {
    $name = [IO.Path]::GetFileName($target)
    if ($name -in @("chrome.exe", "chrome_proxy.exe")) { return "chrome" }
    if ($name -in @("msedge.exe", "msedge_proxy.exe")) { return "edge" }
    return ""
}

function Get-CompanyIcon($admin, $client) {
    foreach ($known in @($admin, $client)) {
        if ($null -eq $known -or [string]::IsNullOrWhiteSpace($known.Icon) -or $known.Icon -eq ",0") { continue }
        $iconFile = $known.Icon -replace ',\s*-?\d+$', ''
        $iconFile = $iconFile.Trim('"')
        if (Test-Path -LiteralPath $iconFile -PathType Leaf) { return $known.Icon }
    }
    if (Test-Path -LiteralPath $appIcon -PathType Leaf) { return "$appIcon,0" }
    throw "No se encuentra un icono oficial existente para los accesos."
}

function Publish-NewShortcut([string]$path, [string]$target, [string]$arguments, [string]$description, [string]$icon) {
    if (Test-Path -LiteralPath $path) { throw "No se sobrescribe el acceso existente: $path" }
    $link = $shell.CreateShortcut($path)
    $link.TargetPath = $target
    $link.Arguments = $arguments
    $link.WorkingDirectory = if (Test-Path -LiteralPath $target -PathType Container) { $target } else { Split-Path -Parent $target }
    $link.Description = $description
    if (-not [string]::IsNullOrWhiteSpace($icon)) { $link.IconLocation = $icon }
    $link.WindowStyle = 1
    $link.Save()
}

$existingAdmin = Read-ExistingShortcut $adminPath
$existingClient = Read-ExistingShortcut $clientPath
$existingProject = Read-ExistingShortcut $projectPath
$browser = Get-BrowserPath $existingAdmin $existingClient
$profileArguments = Get-ProfileArguments $existingAdmin
if ([string]::IsNullOrWhiteSpace($profileArguments) -and $null -ne $existingClient -and
    (Get-BrowserFamily $browser) -eq (Get-BrowserFamily $existingClient.Target)) {
    $profileArguments = Get-ProfileArguments $existingClient
}
$icon = Get-CompanyIcon $existingAdmin $existingClient
$adminArguments = (($profileArguments + ' --app="' + $adminUrl + '"').Trim())
$clientArguments = (($profileArguments + ' --app="' + $appUrl + '"').Trim())
if ([string]::IsNullOrWhiteSpace($browser)) {
    # A normal web link remains functional without claiming a PWA installation.
    $browser = Join-Path $env:WINDIR "explorer.exe"
    $adminArguments = $adminUrl
    $clientArguments = $appUrl
}

# Existing client and project links are read only, including their icon, target,
# opaque app-id, exact arguments, profile, and all bytes not exposed by COM.
$clientAlreadyAvailable = $null -ne $existingClient
if (-not $clientAlreadyAvailable) {
    foreach ($name in @("NeMeSiS App.url", "NeMeSiS SHARK PRO.url")) {
        $legacyPath = Join-Path $desktop $name
        if (Test-Path -LiteralPath $legacyPath -PathType Leaf) {
            $urlLine = Get-Content -LiteralPath $legacyPath | Where-Object { $_ -match '^URL=https://bot-apuestas-crgf\.onrender\.com/(?:app)?/?$' }
            if ($urlLine) { $clientAlreadyAvailable = $true }
        }
    }
}
$adminNeedsUpdate = ($null -eq $existingAdmin -or $existingAdmin.Target -ne $browser -or
    $existingAdmin.Arguments -cne $adminArguments -or $existingAdmin.Icon -cne $icon)
$actions = @()
if ($adminNeedsUpdate) { $actions += if ($null -ne $existingAdmin) { "BACKUP_AND_UPDATE_ADMIN" } else { "CREATE_ADMIN_WEB_ACCESS" } }
if (-not $clientAlreadyAvailable) { $actions += "CREATE_CLIENT_WEB_ACCESS" }
if ($null -eq $existingProject) { $actions += "CREATE_PROJECT_ACCESS" }
$result = [ordered]@{ preview = [bool]$Preview; desktop_path = $desktop; admin_url = $adminUrl; actions = $actions;
    existing_client_preserved = ($null -ne $existingClient); existing_project_preserved = ($null -ne $existingProject);
    pwa_installation_performed = $false; removed_shortcuts = @(); backup = "" }
if ($Preview) { $result | ConvertTo-Json -Depth 5; return }

if ($adminNeedsUpdate -and $null -ne $existingAdmin) {
    $originalHash = Get-ShortcutSha256 $adminPath
    $backupFolder = Join-Path $backupRoot (([DateTime]::UtcNow.ToString("yyyyMMddTHHmmssfffZ")) + "-" + [guid]::NewGuid().ToString("N"))
    New-Item -ItemType Directory -Path $backupFolder -Force | Out-Null
    $backupPath = Join-Path $backupFolder "NeMeSiS Admin.lnk"
    Copy-Item -LiteralPath $adminPath -Destination $backupPath
    if ((Get-ShortcutSha256 $backupPath) -cne $originalHash) { throw "No se pudo verificar la copia del acceso Admin." }
    [ordered]@{ original_name = "NeMeSiS Admin.lnk"; sha256 = $originalHash; created_utc = [DateTime]::UtcNow.ToString("o");
        recovery = "Copiar NeMeSiS Admin.lnk de esta carpeta a la carpeta original de accesos." } |
        ConvertTo-Json | Set-Content -LiteralPath (Join-Path $backupFolder "manifest.json") -Encoding UTF8
    if ((Get-ShortcutSha256 $adminPath) -cne $originalHash) { throw "El acceso Admin ha cambiado durante la revisión; se conserva." }
    $result.backup = $backupPath
    $staging = Join-Path $desktop (".nemesis-admin-" + [guid]::NewGuid().ToString("N") + ".lnk")
    Publish-NewShortcut $staging $browser $adminArguments "Centro de Mando en línea de NeMeSiS SHARK PRO" $icon
    # Only this named Admin link is updated, after an independently hashed copy.
    [IO.File]::Replace($staging, $adminPath, [NullString]::Value)
} elseif ($adminNeedsUpdate) {
    Publish-NewShortcut $adminPath $browser $adminArguments "Centro de Mando en línea de NeMeSiS SHARK PRO" $icon
}
if (-not $clientAlreadyAvailable) {
    Publish-NewShortcut $clientPath $browser $clientArguments "Acceso web de cliente NeMeSiS; no instala una PWA" $icon
}
if ($null -eq $existingProject) {
    Publish-NewShortcut $projectPath $root "" "Abrir la carpeta local del proyecto NeMeSiS" ""
}
$result | ConvertTo-Json -Depth 5
