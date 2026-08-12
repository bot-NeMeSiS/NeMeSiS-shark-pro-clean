from __future__ import annotations

import json
import os
import re
import socket
import subprocess
import sys
import time
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
RUNNER = ROOT / "tools" / "local_desktop" / "run_local_desktop.py"


def _self_test(mode: str) -> dict:
    env = dict(os.environ)
    env.pop("NEMESIS_LOCAL_EXTERNAL_AUTHORIZED", None)
    env.pop("NEMESIS_LOCAL_EXTERNAL_ALLOWLIST", None)
    result = subprocess.run(
        [sys.executable, str(RUNNER), "--mode", mode, "--self-test"],
        cwd=ROOT,
        env=env,
        text=True,
        capture_output=True,
        timeout=180,
        check=False,
    )
    assert result.returncode == 0, result.stdout + result.stderr
    start = result.stdout.find("{")
    assert start >= 0, result.stdout
    return json.loads(result.stdout[start:])


def test_offline_safe_runner_isolated_and_blocks_external_actions():
    payload = _self_test("offline_safe")
    assert payload["ok"] is True
    assert payload["mode"] == "OFFLINE_SAFE"
    assert payload["portal"] == 200
    assert payload["client_login"] == 302
    assert payload["admin_login"] == 302
    assert payload["founder"] == 200
    assert all(status == 200 for status in payload["routes"].values())
    assert payload["network_blocked"] is True
    assert payload["telegram_blocked"] is True
    assert payload["stripe_route_blocked"] is True
    assert payload["stripe_engine_blocked"] is True
    assert payload["sync_blocked"] is True
    assert payload["db_isolated"] is True
    assert payload["production_modified"] is False
    assert payload["external_actions_executed"] == 0


def test_integration_shortcut_remains_closed_without_explicit_authorization():
    payload = _self_test("integration_test")
    assert payload["ok"] is True
    assert payload["mode"] == "INTEGRATION_TEST"
    assert payload["network_blocked"] is True
    assert payload["telegram_blocked"] is True
    assert payload["stripe_engine_blocked"] is True
    assert payload["external_actions_executed"] == 0


def test_local_desktop_scripts_are_project_bound_and_stop_only_owned_pid():
    start = (ROOT / "tools" / "local_desktop" / "start_nemesis_local.cmd").read_text(encoding="ascii")
    stop = (ROOT / "tools" / "local_desktop" / "stop_nemesis_local.ps1").read_text(encoding="utf-8")
    installer = (ROOT / "tools" / "local_desktop" / "install_desktop_shortcuts.ps1").read_text(encoding="utf-8")
    assert "run_local_desktop.py" in start
    assert 'cd /d "%~dp0\\..\\.."' in start
    assert "run_local_desktop.py" in stop
    assert "Stop-Process -Id $processId" in stop
    assert "Stop-Process -Name" not in stop
    assert "NeMeSiS LOCAL" in installer
    assert "DETENER NEMESIS LOCAL" in installer


def test_local_safe_assets_do_not_depend_on_remote_cdn():
    base = (ROOT / "templates" / "base.html").read_text(encoding="utf-8")
    portal = (ROOT / "templates" / "local_safe_portal.html").read_text(encoding="utf-8")
    external_asset = re.compile(r"<(?:script|link)[^>]+(?:src|href)=[\"']https?://", re.IGNORECASE)
    assert not external_asset.search(base)
    assert "DATOS EXTERNOS" not in portal.upper() or "NO DISPONIBLES" in portal.upper()
    assert "SIMULATED_QA" in portal


def test_gitignore_excludes_local_database_pid_logs_and_sensitive_config():
    ignore = (ROOT / ".gitignore").read_text(encoding="utf-8")
    assert "data/local_dev/" in ignore
    assert "tools/local_desktop/*.pid" in ignore
    assert "tools/local_desktop/*.log" in ignore
    assert ".env.local" in ignore

def _wait_for_pid_file(pid_file: Path, timeout: float = 45.0) -> dict:
    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        if pid_file.exists():
            try:
                return json.loads(pid_file.read_text(encoding="utf-8"))
            except (OSError, json.JSONDecodeError):
                pass
        time.sleep(0.1)
    raise AssertionError("NeMeSiS LOCAL no creo su registro de proceso a tiempo")


def _stop_runner(process: subprocess.Popen[str]) -> None:
    if process.poll() is None and process.stdin is not None:
        process.stdin.write("0\n")
        process.stdin.flush()
    process.wait(timeout=30)


def test_runner_handles_busy_port_duplicate_shutdown_and_restart():
    pid_file = ROOT / "data" / "local_dev" / "nemesis_local.pid.json"
    pid_file.unlink(missing_ok=True)
    env = dict(os.environ)
    env["NEMESIS_LOCAL_NO_BROWSER"] = "1"
    env.pop("NEMESIS_LOCAL_EXTERNAL_AUTHORIZED", None)
    occupied = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    occupied.bind(("127.0.0.1", 5000))
    occupied.listen(1)
    first = subprocess.Popen(
        [sys.executable, "-u", str(RUNNER), "--mode", "offline_safe"],
        cwd=ROOT,
        env=env,
        stdin=subprocess.PIPE,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=True,
    )
    try:
        first_metadata = _wait_for_pid_file(pid_file)
        assert first_metadata["port"] != 5000
        duplicate = subprocess.run(
            [sys.executable, "-u", str(RUNNER), "--mode", "offline_safe"],
            cwd=ROOT,
            env=env,
            text=True,
            capture_output=True,
            timeout=30,
            check=False,
        )
        assert duplicate.returncode == 0
        assert "ya esta funcionando" in duplicate.stdout.lower()
    finally:
        occupied.close()
        _stop_runner(first)
    assert not pid_file.exists()

    restarted = subprocess.Popen(
        [sys.executable, "-u", str(RUNNER), "--mode", "offline_safe"],
        cwd=ROOT,
        env=env,
        stdin=subprocess.PIPE,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=True,
    )
    try:
        restarted_metadata = _wait_for_pid_file(pid_file)
        assert int(restarted_metadata["pid"]) > 0
        assert Path(restarted_metadata["runner"]).resolve() == RUNNER.resolve()
        assert int(restarted_metadata["port"]) >= 5000
    finally:
        _stop_runner(restarted)
    assert not pid_file.exists()
