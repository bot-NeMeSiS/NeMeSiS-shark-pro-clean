from __future__ import annotations

import ast
import os
import re
import sys
import zipfile
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
VERSION = "V912_VIDEO_ADMIN_UI_COPY_POLISH_BROWSER_QA_QUEUE_FINAL"
ZIP_NAME = f"NeMeSiS_SHARK_PRO_{VERSION}_RENDER_READY.zip"


def read(rel: str) -> str:
    return (ROOT / rel).read_text(encoding="utf-8-sig", errors="replace")


def require(condition: bool, message: str, failures: list[str]) -> None:
    if not condition:
        failures.append(message)


def app_version_from_source(source: str) -> str:
    tree = ast.parse(source)
    for node in tree.body:
        if isinstance(node, ast.Assign):
            for target in node.targets:
                if isinstance(target, ast.Name) and target.id == "APP_VERSION":
                    if isinstance(node.value, ast.Constant):
                        return str(node.value.value)
    return ""


def admin_session(client) -> None:
    with client.session_transaction() as sess:
        sess["user_id"] = "codex-v912-admin"
        sess["user_name"] = "Admin SHARK"
        sess["username"] = "admin"
        sess["user_email"] = "admin@example.invalid"
        sess["user_role"] = "ADMIN"
        sess["user_membership"] = "ADMIN"
        sess["membership"] = "ADMIN"


def text_has_concatenated_kpis(html: str) -> bool:
    compact = re.sub(r"\s+", "", html)
    bad_tokens = [
        "Capturas0desktop/mobile",
        "Comparaciones18reference_images",
        "Gapsresueltos0porcaptura",
        "Gapspendientes18requierenbrowserreal",
        "RunnerlocalListoPowerShell/bat/sh",
    ]
    return any(token in compact for token in bad_tokens)


def assert_no_raw_secrets(failures: list[str]) -> None:
    scan_paths = [
        ROOT / "templates" / "base.html",
        ROOT / "templates" / "home.html",
        ROOT / "templates" / "admin_autonomous_company_sentinel.html",
        ROOT / "templates" / "admin_shark_sentinel.html",
        ROOT / "templates" / "admin_sentinel_codex_outbox.html",
        ROOT / "static" / "app.css",
    ]
    unsafe = re.compile(r"(secret|token|api_key|apikey|password)=([^\s`'\"&<>)]+)", re.IGNORECASE)
    allowed = {"hidden", "configured", "missing", "AUTOMATION_SECRET", "$AUTOMATION_SECRET"}
    for path in scan_paths:
        text = path.read_text(encoding="utf-8", errors="replace")
        for match in unsafe.finditer(text):
            value = match.group(2).strip(",.;")
            if value in allowed or value.startswith("$") or "AUTOMATION_SECRET" in value:
                continue
            failures.append(f"possible raw secret in {path.relative_to(ROOT)}")


def assert_zip_clean(failures: list[str]) -> None:
    zip_path = ROOT / "release_output" / ZIP_NAME
    if not zip_path.exists():
        return
    with zipfile.ZipFile(zip_path) as zf:
        names = [name.replace("\\", "/") for name in zf.namelist()]
    for rel in ["app.py", "VERSION.txt", "requirements.txt", "templates/base.html", "static/app.css"]:
        require(rel in names, f"zip missing {rel}", failures)
    forbidden_bits = (".git/", ".venv/", "__pycache__/", ".pytest_cache/", "release_output/", "logs/")
    for name in names:
        if name.endswith((".zip", ".db", ".sqlite", ".sqlite3", ".db-wal", ".db-shm")) or any(bit in name for bit in forbidden_bits):
            failures.append(f"zip forbidden entry {name}")
            break


def main() -> int:
    failures: list[str] = []
    app_py = read("app.py")
    base = read("templates/base.html")
    home = read("templates/home.html")
    css = read("static/app.css")
    version_bytes = (ROOT / "VERSION.txt").read_bytes()

    require(not version_bytes.startswith(b"\xef\xbb\xbf"), "VERSION.txt has BOM", failures)
    require(version_bytes.decode("utf-8").strip() == VERSION, "VERSION.txt is not V912", failures)
    require(read("APP_VERSION").strip().lstrip("\ufeff") == VERSION, "APP_VERSION is not V912", failures)
    require(app_version_from_source(app_py) == VERSION, "app.py APP_VERSION is not V912", failures)
    require("data-v912-video-admin-fix" in base, "base V912 video admin marker missing", failures)
    require("show_mobile_bottom_nav = (not current_user and not is_admin_surface) or is_client_area" in base, "admin/client bottom nav guard missing", failures)
    require("Cerrar sesión admin" in base and "Vista pública" in base, "admin rail labels not fixed", failures)
    require("V912 video admin UI + copy polish" in css, "V912 CSS marker missing", failures)
    require("v912-admin-kpi-grid" in css and "v912-kpi-label" in css and "v912-kpi-value" in css and "v912-kpi-hint" in css, "V912 KPI CSS contract missing", failures)
    require("get_safe_runtime_identity_for_admin" in app_py, "safe runtime identity helper missing", failures)
    require("NEMESIS_CACHE_V912" in app_py, "service worker cache V912 missing", failures)
    require("gua al cliente" not in home, "home still contains gua al cliente", failures)
    require("La app guía al cliente" in home, "home does not contain corrected guia copy", failures)
    require("Informacion deportiva" not in base, "base still contains Informacion", failures)
    require("Terminos" not in base, "base still contains Terminos", failures)
    require("Información deportiva" in base and "Términos" in base, "public footer accents missing", failures)

    assert_no_raw_secrets(failures)

    os.environ.setdefault("AUTOMATION_SECRET", "codex-v912-local-secret")
    if str(ROOT) not in sys.path:
        sys.path.insert(0, str(ROOT))
    import app as app_module

    client = app_module.app.test_client()
    admin_session(client)
    runtime_resp = client.get("/api/runtime-version")
    runtime = runtime_resp.get_json(silent=True) or {}
    require(runtime_resp.status_code == 200, "runtime-version not 200", failures)
    require(runtime.get("version") == VERSION, "runtime version is not V912", failures)
    require(runtime.get("version_files_match") is True, "runtime version_files_match false", failures)
    require(runtime.get("deployment_alignment_status") == "aligned_local_files", "runtime not aligned", failures)
    for flag in [
        "has_v912_video_admin_ui_copy_polish",
        "has_v912_admin_client_nav_separation",
        "has_v912_browser_qa_queue_panel_polish",
        "has_v912_public_spanish_copy_polish",
    ]:
        require(runtime.get(flag) is True, f"runtime flag false: {flag}", failures)

    routes = [
        "/admin-login",
        "/admin/dashboard",
        "/admin/shark-sentinel",
        "/admin/autonomous-company-sentinel",
        "/admin/sentinel-issues",
        "/admin/sentinel-codex-outbox",
        "/admin/not-found-events",
    ]
    for route in routes:
        response = client.get(route)
        require(response.status_code in {200, 302}, f"{route} unexpected status {response.status_code}", failures)
        html = response.get_data(as_text=True)
        require("Salir cliente" not in html, f"{route} contains Salir cliente", failures)
        require('data-nav-zone="client-bottom"' not in html, f"{route} leaks client bottom nav", failures)
        require('data-nav-zone="client-sidebar"' not in html, f"{route} leaks client sidebar", failures)
        require('class="shark-widget"' not in html, f"{route} leaks client floating SHARK", failures)
        require("v825-public-floating-shark" not in html, f"{route} leaks public floating SHARK", failures)

    sentinel_html = client.get("/admin/autonomous-company-sentinel").get_data(as_text=True)
    require(not text_has_concatenated_kpis(sentinel_html), "autonomous sentinel has concatenated KPI text", failures)
    require("Runtime actual de esta app" in sentinel_html, "runtime identity label missing", failures)
    require("Render externo no consultado en esta vista." in sentinel_html, "safe Render-not-consulted copy missing", failures)
    require("<p>Render: <strong>No consultado" not in sentinel_html, "old confusing Render status still present", failures)
    require("v912-admin-kpi-grid" in sentinel_html, "V912 KPI grid not rendered", failures)

    home_resp = client.get("/")
    home_html = home_resp.get_data(as_text=True)
    require(home_resp.status_code == 200, "home not 200", failures)
    require("gua al cliente" not in home_html, "home response contains gua al cliente", failures)
    require("Informacion" not in home_html and "Terminos" not in home_html, "home response contains unaccented legal copy", failures)
    require("None" not in home_html and "undefined" not in home_html, "home response contains technical placeholder", failures)

    sw = client.get("/service-worker.js")
    require(sw.status_code == 200 and "NEMESIS_CACHE_V912" in sw.get_data(as_text=True), "service worker cache V912 not served", failures)
    require("res.status===404" in sw.get_data(as_text=True), "service worker 404 guard missing", failures)
    require(client.get("/ruta-inventada-v912").status_code == 404, "HTML 404 not 404", failures)
    api_404 = client.get("/api/ruta-inventada-v912")
    require(api_404.status_code == 404 and api_404.is_json, "API 404 JSON missing", failures)

    for rel in ["templates/admin_autonomous_company_sentinel.html", "templates/admin_shark_sentinel.html", "templates/admin_sentinel_codex_outbox.html"]:
        text = read(rel)
        require('href="#"' not in text, f"{rel} has href #", failures)
        require("javascript:void(0)" not in text, f"{rel} has javascript:void(0)", failures)

    assert_zip_clean(failures)
    if failures:
        print("V912 video admin UI copy polish check FAILED")
        for failure in failures:
            print(f"- {failure}")
        return 1
    print("V912 video admin UI copy polish check OK")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
