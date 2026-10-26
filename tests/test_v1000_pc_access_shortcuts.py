"""PC shortcut installer: owned Windows COM fixtures, never the real Desktop."""
from __future__ import annotations

import base64
import hashlib
import inspect
import json
import os
from pathlib import Path
import re
import shutil
import subprocess

import pytest


ROOT = Path(__file__).resolve().parents[1]
INSTALLER = ROOT / "tools/local_desktop/install_pc_access_shortcuts.ps1"
# Prefer the installed host used by Codex. No execution-policy flags or policy
# changes are permitted; a host that denies -File will fail the functional gate.
POWERSHELL = (shutil.which("pwsh.exe") or shutil.which("powershell.exe")) if os.name == "nt" else None
WINDOWS_COM = pytest.mark.skipif(not POWERSHELL, reason="Windows WScript.Shell COM is required; portable contracts remain active")
APP_URL = "https://bot-apuestas-crgf.onrender.com/app"
ADMIN_URL = "https://bot-apuestas-crgf.onrender.com/admin/founder-os"
CLIENT = "NeMeSiS SHARK PRO.lnk"
PROJECT = "NeMeSiS Proyecto.lnk"
ADMIN = "NeMeSiS Admin.lnk"


def _quote(value):
    return "'" + str(value).replace("'", "''") + "'"


def _powershell(code):
    code = "[Console]::OutputEncoding = [Text.UTF8Encoding]::new($false)\n" + code
    encoded = base64.b64encode(code.encode("utf-16-le")).decode("ascii")
    result = subprocess.run([POWERSHELL, "-NoLogo", "-NoProfile", "-NonInteractive",
                             "-EncodedCommand", encoded], capture_output=True, text=True, timeout=45,
                            encoding="utf-8", errors="replace", check=False)
    assert result.returncode == 0, result.stdout + result.stderr
    return result.stdout.strip().lstrip("\ufeff")


def _owned_fixture(tmp_path, *, admin_profile='--profile-directory="Profile 1"',
                   client_profile='--profile-directory="Profile 1"', client=True):
    # Every path handed to COM belongs to this test. The dummy executable files
    # are shortcut targets only; no browser or application is ever launched.
    desktop = tmp_path / "Synthetic Desktop"
    backup = tmp_path / "Recoverable Backups"
    browser = tmp_path / "Owned Browser"
    project = tmp_path / "Existing Project"
    for folder in (desktop, browser, project):
        folder.mkdir()
    for name in ("chrome.exe", "chrome_proxy.exe"):
        (browser / name).write_bytes(b"owned-shortcut-target-only")
    icon = tmp_path / "approved-company.ico"
    icon.write_bytes(b"owned-existing-icon-reference")
    old_url = (tmp_path / "old-local-center.html").as_uri()
    admin_arguments = (admin_profile + ' --app="' + old_url + '"').strip()
    client_arguments = " " + client_profile + " --app-id=owned-pwa-app-id-preserve-exactly"
    code = f"""
$ErrorActionPreference = 'Stop'
$s = New-Object -ComObject WScript.Shell
$a = $s.CreateShortcut({_quote(desktop / ADMIN)})
$a.TargetPath = {_quote(browser / 'chrome.exe')}
$a.Arguments = {_quote(admin_arguments)}
$a.IconLocation = {_quote(str(icon) + ',0')}
$a.Description = 'Previous Admin; recover this exact file'
$a.Save()
$p = $s.CreateShortcut({_quote(desktop / PROJECT)})
$p.TargetPath = {_quote(project)}
$p.Arguments = ''
$p.Description = 'Existing project; never rewrite'
$p.Save()
"""
    if client:
        code += f"""
$c = $s.CreateShortcut({_quote(desktop / CLIENT)})
$c.TargetPath = {_quote(browser / 'chrome_proxy.exe')}
$c.Arguments = {_quote(client_arguments)}
$c.IconLocation = {_quote(str(icon) + ',0')}
$c.Description = 'Existing installed PWA; never recreate'
$c.Save()
"""
    _powershell(code)
    return {"root": tmp_path, "desktop": desktop, "backup": backup, "browser": browser,
            "project": project, "icon": icon, "old_url": old_url}


def _fingerprints(*folders):
    records = {}
    for folder in folders:
        if not folder.exists():
            records[str(folder)] = "MISSING"
            continue
        for path in (folder, *folder.rglob("*")):
            records[str(path)] = ("DIRECTORY" if path.is_dir() else hashlib.sha256(path.read_bytes()).hexdigest())
    return records


def _inspect(path):
    value = _powershell(f"""
$s = New-Object -ComObject WScript.Shell
$l = $s.CreateShortcut({_quote(path)})
[ordered]@{{ Target = $l.TargetPath; Arguments = $l.Arguments; Icon = $l.IconLocation; Description = $l.Description }} | ConvertTo-Json -Compress
""")
    return json.loads(value)


def _install(fixture, *, preview=False):
    # DesktopPath is mandatory in this harness. No call can use the user's
    # desktop or the script's default backup directory.
    for name in ("desktop", "backup"):
        assert fixture[name].absolute().is_relative_to(fixture["root"].absolute())
    command = [POWERSHELL, "-NoLogo", "-NoProfile", "-NonInteractive",
               "-File", str(INSTALLER), "-DesktopPath", str(fixture["desktop"]),
               "-BackupDirectory", str(fixture["backup"])]
    if preview:
        command.append("-Preview")
    result = subprocess.run(command, capture_output=True, text=True, timeout=45,
                            encoding="utf-8", errors="replace", check=False)
    assert result.returncode == 0, result.stdout + result.stderr
    return json.loads(result.stdout.strip().lstrip("\ufeff"))


def test_installer_portable_contract_uses_online_routes_and_explicit_preview():
    source = INSTALLER.read_text(encoding="utf-8-sig")
    assert ADMIN_URL in source and APP_URL in source
    for parameter in ("Preview", "DesktopPath", "BackupDirectory"):
        assert re.search(r"\[\w+\]\$" + parameter + r"\b", source)
    assert "centro-de-mando.html" not in source
    assert "dashboard.render.com" not in source
    assert "Write-InternetShortcut" not in source
    assert "Start-Process" not in source
    assert "Remove-Item" not in source
    assert "--profile-directory=\"Profile 1\"" not in source


def test_installer_portable_contract_backups_precede_only_admin_replacement():
    source = INSTALLER.read_text(encoding="utf-8-sig")
    preview = source.index("if ($Preview)")
    backup = source.index("Copy-Item -LiteralPath $adminPath -Destination $backupPath")
    verify = source.index("Get-ShortcutSha256 $backupPath")
    replace = source.index("[IO.File]::Replace($staging, $adminPath, [NullString]::Value)")
    assert preview < backup < verify < replace
    assert "if (-not $clientAlreadyAvailable)" in source
    assert "if ($null -eq $existingProject)" in source
    assert "pwa_installation_performed = $false" in source


def test_test_helpers_respect_existing_host_execution_policy():
    helper_source = inspect.getsource(_powershell) + inspect.getsource(_install)
    assert "-ExecutionPolicy" not in helper_source
    assert "Set-ExecutionPolicy" not in helper_source


@WINDOWS_COM
def test_preview_then_actual_owned_com_preserves_pwa_project_and_backup(tmp_path):
    fixture = _owned_fixture(tmp_path)
    desktop, backup = fixture["desktop"], fixture["backup"]
    before = {name: (desktop / name).read_bytes() for name in (CLIENT, PROJECT, ADMIN)}
    pwa = _inspect(desktop / CLIENT)
    previous_admin = _inspect(desktop / ADMIN)
    fingerprint = _fingerprints(desktop, backup)

    preview = _install(fixture, preview=True)
    assert preview["preview"] is True
    assert preview["actions"] == ["BACKUP_AND_UPDATE_ADMIN"]
    assert _fingerprints(desktop, backup) == fingerprint  # zero file/directory writes

    report = _install(fixture)
    assert report["preview"] is False
    assert report["pwa_installation_performed"] is False
    assert report["removed_shortcuts"] == []
    for name in (CLIENT, PROJECT):
        assert (desktop / name).read_bytes() == before[name]
    assert _inspect(desktop / CLIENT) == pwa
    assert '--app-id=owned-pwa-app-id-preserve-exactly' in pwa["Arguments"]
    assert '--profile-directory="Profile 1"' in pwa["Arguments"]

    current_admin = _inspect(desktop / ADMIN)
    assert current_admin["Target"] == previous_admin["Target"]
    assert current_admin["Arguments"] == '--profile-directory="Profile 1" --app="' + ADMIN_URL + '"'
    assert current_admin["Icon"] == previous_admin["Icon"]
    assert fixture["old_url"] not in current_admin["Arguments"]
    assert {p.name for p in desktop.iterdir()} == {CLIENT, PROJECT, ADMIN}

    saved = Path(report["backup"])
    assert saved.is_relative_to(backup)
    assert saved.read_bytes() == before[ADMIN]
    manifest = json.loads(saved.with_name("manifest.json").read_text(encoding="utf-8-sig"))
    assert manifest["sha256"].lower() == hashlib.sha256(before[ADMIN]).hexdigest()
    restored = tmp_path / "Restore proof" / ADMIN
    restored.parent.mkdir()
    shutil.copyfile(saved, restored)  # restore only into another owned fixture path
    assert _inspect(restored) == previous_admin

    final_fingerprint = _fingerprints(desktop, backup)
    repeated = _install(fixture)
    assert repeated["actions"] == []
    assert repeated["backup"] == ""
    assert _fingerprints(desktop, backup) == final_fingerprint


@WINDOWS_COM
@pytest.mark.parametrize(("admin_profile", "client_profile", "expected"), [
    ('--profile-directory="Company Profile"', '--profile-directory="Profile 1"', '--profile-directory="Company Profile"'),
    ('', '--profile-directory="Work 7"', '--profile-directory="Work 7"'),
    ('', '', ''),
])
def test_existing_profile_is_reused_without_forcing_profile_one(tmp_path, admin_profile, client_profile, expected):
    fixture = _owned_fixture(tmp_path, admin_profile=admin_profile, client_profile=client_profile)
    client_before = (fixture["desktop"] / CLIENT).read_bytes()
    _install(fixture)
    arguments = _inspect(fixture["desktop"] / ADMIN)["Arguments"]
    if expected:
        assert arguments.startswith(expected + " ")
    else:
        assert "--profile-directory" not in arguments
    assert (fixture["desktop"] / CLIENT).read_bytes() == client_before


@WINDOWS_COM
def test_custom_user_data_directory_is_preserved_without_opening_it(tmp_path):
    profile_root = tmp_path / "Existing profile directory with spaces"
    # This path is only a shortcut argument. No profile/cookie folder is opened.
    flags = '--user-data-dir="' + str(profile_root) + '" --profile-directory="Company"'
    fixture = _owned_fixture(tmp_path, admin_profile=flags)
    _install(fixture)
    arguments = _inspect(fixture["desktop"] / ADMIN)["Arguments"]
    assert arguments.startswith(flags + " ")
    assert not profile_root.exists()


@WINDOWS_COM
def test_chrome_profile_is_not_forced_into_an_existing_edge_admin(tmp_path):
    fixture = _owned_fixture(tmp_path, admin_profile="")
    edge = fixture["browser"] / "msedge.exe"
    edge.write_bytes(b"owned-edge-shortcut-target-only")
    _powershell(f"""
$s = New-Object -ComObject WScript.Shell
$a = $s.CreateShortcut({_quote(fixture['desktop'] / ADMIN)})
$a.TargetPath = {_quote(edge)}
$a.Save()
""")
    pwa_before = (fixture["desktop"] / CLIENT).read_bytes()
    _install(fixture)
    admin = _inspect(fixture["desktop"] / ADMIN)
    assert Path(admin["Target"]) == edge
    assert "--profile-directory" not in admin["Arguments"]
    assert (fixture["desktop"] / CLIENT).read_bytes() == pwa_before


@WINDOWS_COM
def test_missing_admin_browser_does_not_transfer_its_profile_to_another_family(tmp_path):
    chrome_profile = tmp_path / "Owned Chrome profile reference"
    edge_profile = tmp_path / "Owned Edge profile reference"
    chrome_flags = '--user-data-dir="' + str(chrome_profile) + '" --profile-directory="Chrome Company"'
    edge_flags = '--user-data-dir="' + str(edge_profile) + '" --profile-directory="Edge Company"'
    fixture = _owned_fixture(tmp_path, admin_profile=chrome_flags)
    (fixture["browser"] / "chrome.exe").unlink()  # owned dummy target, never a real browser
    edge = fixture["browser"] / "msedge.exe"
    edge.write_bytes(b"owned-edge-shortcut-target-only")
    _powershell(f"""
$s = New-Object -ComObject WScript.Shell
$c = $s.CreateShortcut({_quote(fixture['desktop'] / CLIENT)})
$c.TargetPath = {_quote(edge)}
$c.Arguments = {_quote(edge_flags + ' --app-id=owned-pwa-app-id-preserve-exactly')}
$c.Save()
""")
    client_before = (fixture["desktop"] / CLIENT).read_bytes()
    project_before = (fixture["desktop"] / PROJECT).read_bytes()
    _install(fixture)
    admin = _inspect(fixture["desktop"] / ADMIN)
    assert Path(admin["Target"]) == edge
    assert admin["Arguments"] == edge_flags + ' --app="' + ADMIN_URL + '"'
    assert str(chrome_profile) not in admin["Arguments"]
    assert (fixture["desktop"] / CLIENT).read_bytes() == client_before
    assert (fixture["desktop"] / PROJECT).read_bytes() == project_before
    assert not chrome_profile.exists() and not edge_profile.exists()


@WINDOWS_COM
def test_missing_client_creates_only_web_access_and_does_not_claim_pwa(tmp_path):
    fixture = _owned_fixture(tmp_path, client=False)
    project_before = (fixture["desktop"] / PROJECT).read_bytes()
    report = _install(fixture)
    new_client = _inspect(fixture["desktop"] / CLIENT)
    assert "CREATE_CLIENT_WEB_ACCESS" in report["actions"]
    assert report["pwa_installation_performed"] is False
    assert APP_URL in new_client["Arguments"]
    assert "--app-id" not in new_client["Arguments"]
    assert "no instala una PWA" in new_client["Description"]
    assert (fixture["desktop"] / PROJECT).read_bytes() == project_before
    assert not list(fixture["desktop"].glob("*.url"))


@WINDOWS_COM
def test_existing_client_url_is_preserved_and_not_duplicated(tmp_path):
    fixture = _owned_fixture(tmp_path, client=False)
    existing = fixture["desktop"] / "NeMeSiS App.url"
    existing.write_bytes(("[InternetShortcut]\r\nURL=" + APP_URL + "\r\n").encode("ascii"))
    before = existing.read_bytes()
    report = _install(fixture)
    assert "CREATE_CLIENT_WEB_ACCESS" not in report["actions"]
    assert existing.read_bytes() == before
    assert not (fixture["desktop"] / CLIENT).exists()
