param()
$ErrorActionPreference = "Stop"
$root = (Resolve-Path (Join-Path $PSScriptRoot "..\..")).Path
$desktop = [Environment]::GetFolderPath("Desktop")
$start = Join-Path $root "tools\local_desktop\start_nemesis_local.cmd"
$stop = Join-Path $root "tools\local_desktop\stop_nemesis_local.cmd"
$wsh = New-Object -ComObject WScript.Shell
function New-NemesisShortcut([string]$name, [string]$targetScript, [string]$arguments, [string]$description, [int]$iconIndex) {
    $path = Join-Path $desktop ($name + ".lnk")
    $shortcut = $wsh.CreateShortcut($path)
    $shortcut.TargetPath = $env:ComSpec
    $shortcut.Arguments = '/d /c ""' + $targetScript + '" ' + $arguments + '"'
    $shortcut.WorkingDirectory = $root
    $shortcut.Description = $description
    $shortcut.IconLocation = "$env:SystemRoot\System32\shell32.dll,$iconIndex"
    $shortcut.WindowStyle = 1
    $shortcut.Save()
    return $path
}
$created = @()
$created += New-NemesisShortcut "NeMeSiS LOCAL" $start "offline_safe" "Abrir NeMeSiS en modo local offline seguro" 14
$created += New-NemesisShortcut "NeMeSiS LOCAL - INTEGRATION TEST" $start "integration_test" "Abrir NeMeSiS local para integraciones expresamente autorizadas" 18
$created += New-NemesisShortcut "DETENER NEMESIS LOCAL" $stop "" "Detener solo el proceso iniciado por NeMeSiS LOCAL" 131
$created | ForEach-Object { Write-Output $_ }