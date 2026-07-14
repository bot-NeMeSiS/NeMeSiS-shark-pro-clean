from __future__ import annotations

import argparse
import json
import os
from pathlib import Path
import sys
from urllib.parse import urlparse


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from engines.browser_reference_comparison_engine import build_browser_reference_comparison
from tools.check_browser_qa_environment import detect_browser_qa_environment


VERSION = (ROOT / "VERSION.txt").read_text(encoding="utf-8-sig", errors="replace").strip()
PUBLIC_ROUTES = ["/", "/cliente-login", "/registro"]
CLIENT_ROUTES = ["/app", "/calendar", "/live", "/picks", "/track-record", "/shark", "/telegram", "/profile", "/memberships", "/support"]
ADMIN_SAFE_ROUTES = ["/admin-login"]
ADMIN_PROTECTED_ROUTES = [
    "/admin/dashboard",
    "/admin/telegram/command-center",
    "/admin/memberships",
    "/admin/users",
    "/admin/payments",
    "/admin/picks",
    "/admin/matches-sync",
    "/admin/realtime-center",
    "/admin/data-trust-center",
    "/admin/data-center",
    "/admin/automation-center",
    "/admin/daily-automation",
    "/admin/automation-workforce",
    "/admin/autonomous-company-sentinel",
    "/admin/sentinel-issues",
    "/admin/sentinel-codex-outbox",
    "/admin/not-found-events",
    "/admin/launch-certification",
    "/admin/final-certification",
    "/admin/system",
]


def _now_label() -> str:
    from datetime import datetime
    from zoneinfo import ZoneInfo

    return datetime.now(ZoneInfo("Europe/Madrid")).replace(microsecond=0).isoformat()


def _status_paths(output: Path) -> tuple[Path, Path, Path]:
    runtime_dir = ROOT / "data" / "runtime" / "autonomous_company_sentinel"
    runtime_dir.mkdir(parents=True, exist_ok=True)
    output.mkdir(parents=True, exist_ok=True)
    return (
        output / "browser_reference_qa_report.json",
        runtime_dir / "browser_qa_status.json",
        runtime_dir / "reference_gap_report.json",
    )


def _write_markdown_status(payload: dict, output: Path) -> None:
    if VERSION.startswith("V936_"):
        report_name = "V936_BROWSER_QA.md"
    elif VERSION.startswith("V935_"):
        report_name = "V935_BROWSER_QA.md"
    elif VERSION.startswith("V934_"):
        report_name = "V934_BROWSER_REFERENCE_COMPARISON.md"
    elif VERSION.startswith("V930_"):
        report_name = "V930_BROWSER_QA_COMPARISON.md"
    elif VERSION.startswith("V928_"):
        report_name = "V928_BROWSER_QA_STATUS.md"
    else:
        report_name = "V907_BROWSER_QA_STATUS.md"
    report = ROOT / "reports" / report_name
    status = payload.get("browser_qa_status") or ("CAPTURED" if payload.get("browser_available") else "BROWSER_QA_UNAVAILABLE")
    lines = [
        f"# {VERSION.split('_', 1)[0]} Browser QA Status",
        "",
        f"- Version: {payload.get('version', VERSION)}",
        f"- Status: {status}",
        f"- Playwright available: {payload.get('playwright_available', payload.get('browser_available', False))}",
        f"- Browsers available: {payload.get('browsers_available', payload.get('browser_available', False))}",
        f"- Screenshots captured: {payload.get('screenshots_captured', 0)}",
        f"- Output: `{output.as_posix()}`",
        f"- Reason: {payload.get('reason') or 'Sin error'}",
        "",
        "No se declara pixel-perfect sin capturas reales comparadas.",
    ]
    report.write_text("\n".join(lines) + "\n", encoding="utf-8")


def _write_reference_gap_status(comparison: dict) -> None:
    _, _, gap_path = _status_paths(ROOT / "reports" / "V907_browser_qa")
    try:
        existing = json.loads(gap_path.read_text(encoding="utf-8-sig", errors="replace")) if gap_path.exists() else {}
    except Exception:
        existing = {}
    comparisons = comparison.get("comparisons") or []
    existing["v907_browser_reference_status"] = {
        "version": VERSION,
        "browser_qa_status": comparison.get("browser_qa_status"),
        "screenshots_captured": comparison.get("screenshots_captured", 0),
        "reference_comparisons": comparison.get("reference_comparisons", 0),
        "visual_gaps_resolved": comparison.get("visual_gaps_resolved", 0),
        "visual_gaps_pending": comparison.get("visual_gaps_pending", 0),
        "pixel_perfect_claim": False,
        "updated_at_madrid": _now_label(),
    }
    existing["v907_browser_gap_report"] = comparisons
    compatibility_status = {
        "version": VERSION,
        "browser_qa_status": comparison.get("browser_qa_status"),
        "screenshots_captured": comparison.get("screenshots_captured", 0),
        "reference_comparisons": comparison.get("reference_comparisons", 0),
        "visual_gaps_resolved": comparison.get("visual_gaps_resolved", 0),
        "visual_gaps_pending": comparison.get("visual_gaps_pending", 0),
        "pixel_perfect_claim": False,
        "updated_by": "V907 browser QA enablement",
        "updated_at_madrid": _now_label(),
    }
    if VERSION.startswith("V928_"):
        existing["v928_browser_reference_status"] = compatibility_status
        existing["v928_browser_gap_report"] = comparisons
    if VERSION.startswith("V930_"):
        existing["v930_browser_reference_status"] = compatibility_status
        existing["v930_browser_gap_report"] = comparisons
    if VERSION.startswith("V936_"):
        existing["v936_browser_reference_status"] = compatibility_status
        existing["v936_browser_gap_report"] = comparisons
    existing["v906_browser_status"] = compatibility_status
    existing["v906_browser_reference_status"] = compatibility_status
    existing["v906_browser_gap_report"] = comparisons
    existing["v905_final_reference_gap_status"] = compatibility_status
    gap_path.write_text(json.dumps(existing, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def _write_outbox(comparison: dict) -> None:
    outbox = ROOT / "data" / "runtime" / "autonomous_company_sentinel" / "outbox" / "codex_outbox.md"
    outbox.parent.mkdir(parents=True, exist_ok=True)
    comparisons = comparison.get("comparisons") or []
    captured = [item for item in comparisons if item.get("screenshot_path")]
    pending = [item for item in comparisons if item.get("classification") != "RESOLVED_VISUALLY"]
    admin = [item for item in pending if str(item.get("route") or "").startswith("/admin")]
    client_mobile = [item for item in pending if item.get("profile") and "mobile" in str(item.get("profile"))]
    picks_live = [item for item in pending if item.get("route") in {"/picks", "/live", "/calendar"}]
    shark_telegram = [item for item in pending if item.get("route") in {"/shark", "/telegram", "/admin/telegram/command-center"}]

    def prompt_block(items: list[dict], limit: int = 8) -> list[str]:
        if not items:
            return ["- Sin prompts activos en esta sección."]
        lines: list[str] = []
        for item in items[:limit]:
            lines.extend([
                f"## Ruta {item.get('route')}",
                "",
                f"- Captura actual: `{item.get('screenshot_path') or 'pendiente'}`",
                f"- Referencia usada: `{item.get('reference_used') or 'pendiente'}`",
                f"- Clasificación: {item.get('classification')}",
                f"- Gap: {'; '.join(item.get('notes') or ['Pendiente de Browser QA'])}",
                "- Archivos probables: `templates/`, `static/app.css`, `templates/partials/`",
                "- Restricciones: no inventar datos, no tocar secretos, no pagos, no Telegram real.",
                "- Validaciones: Browser QA, Sentinel, smoke Flask, sin overflow y sin mojibake.",
                "",
                "```text",
                str(item.get("codex_prompt") or "Revisar pantalla con captura real antes de tocar visual."),
                "```",
                "",
            ])
        return lines

    release_tag = VERSION.split("_", 1)[0]
    lines = [
        f"# Codex Outbox - {release_tag} Browser QA",
        "",
        "pixel_perfect_claim: false",
        f"generated_at_madrid: {_now_label()}",
        f"screenshots_captured: {comparison.get('screenshots_captured', 0)}",
        f"reference_comparisons: {comparison.get('reference_comparisons', 0)}",
        f"visual_gaps_resolved: {comparison.get('visual_gaps_resolved', 0)}",
        f"visual_gaps_pending: {comparison.get('visual_gaps_pending', 0)}",
        "",
        f"# {release_tag}_BROWSER_QA_FINDINGS",
        f"- Browser QA status: {comparison.get('browser_qa_status')}",
        f"- Capturas reales: {len(captured)}",
        f"- Pendientes: {len(pending)}",
        "",
        "# SCREENSHOT_BASED_VISUAL_PROMPTS",
        *prompt_block([item for item in pending if item.get("screenshot_path")]),
        "# ADMIN_SCREENSHOT_PROMPTS",
        *prompt_block(admin),
        "# CLIENT_MOBILE_SCREENSHOT_PROMPTS",
        *prompt_block(client_mobile),
        "# PICKS_LIVE_CALENDAR_SCREENSHOT_PROMPTS",
        *prompt_block(picks_live),
        "# SHARK_TELEGRAM_SCREENSHOT_PROMPTS",
        *prompt_block(shark_telegram),
        "# PENDING_BROWSER_QA",
        *prompt_block([item for item in pending if not item.get("screenshot_path")]),
        "# PENDING_HUMAN_VISUAL_REVIEW",
        "- Revisión humana visual requerida para cualquier gap que necesite criterio de referencia/pixel real.",
        "# ARCHIVED_STATIC_PROMPTS",
        "- Prompts estáticos anteriores quedan archivados si no tienen captura asociada o si no se reproducen con Browser QA.",
    ]
    outbox.write_text("\n".join(lines) + "\n", encoding="utf-8")


def _write_visual_fix_queue(comparison: dict) -> dict:
    queue_path = ROOT / "data" / "runtime" / "autonomous_company_sentinel" / "visual_fix_queue.json"
    queue_path.parent.mkdir(parents=True, exist_ok=True)
    comparisons = comparison.get("comparisons") or []
    items = []
    release_tag = VERSION.split("_", 1)[0]
    for index, item in enumerate(comparisons, start=1):
        if item.get("classification") == "RESOLVED_VISUALLY":
            continue
        route = item.get("route") or "unknown"
        device = str(item.get("profile") or item.get("device") or "desktop")
        has_screenshot = bool(item.get("screenshot_path") or item.get("screenshot"))
        severity = "high" if route.startswith("/admin") or route in {"/app", "/picks", "/live", "/calendar"} else "medium"
        status = "READY_FOR_CODEX" if has_screenshot else "BLOCKED_NO_SCREENSHOT"
        items.append({
            "id": f"{release_tag}-{index:03d}",
            "route": route,
            "device": "mobile" if "mobile" in device else "desktop",
            "screenshot": item.get("screenshot_path") or item.get("screenshot") or "",
            "reference": item.get("reference_used") or item.get("reference") or "reference_manifest",
            "gap": "; ".join(item.get("notes") or ["Browser QA screenshot pending"]),
            "severity": severity,
            "safe_fix_type": "STRUCTURAL_UI_FIX" if has_screenshot else "WAIT_FOR_SCREENSHOT",
            "codex_prompt": item.get("codex_prompt") or f"Capture and compare {route} before applying a visual fix.",
            "status": status,
        })
    payload = {
        "version": VERSION,
        "generated_at_madrid": _now_label(),
        "items": items,
        "queue_count": len(items),
        "blocked_no_screenshot_count": len([item for item in items if item["status"] == "BLOCKED_NO_SCREENSHOT"]),
        "ready_for_codex_count": len([item for item in items if item["status"] == "READY_FOR_CODEX"]),
        "pixel_perfect_claim_allowed": False,
    }
    queue_path.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return payload


def _write_standard_outputs(output: Path, payload: dict, comparison: dict) -> None:
    output.mkdir(parents=True, exist_ok=True)
    (output / "browser_qa_result.json").write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    (output / "reference_comparison.json").write_text(json.dumps(comparison, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    _write_visual_fix_queue(comparison)


def _write_payload(output: Path, payload: dict, comparison: dict | None = None) -> dict:
    report_path, status_path, _ = _status_paths(output)
    payload["version"] = VERSION
    payload["browser_qa_status"] = payload.get("browser_qa_status") or ("CAPTURED" if payload.get("browser_available") else "BROWSER_QA_UNAVAILABLE")
    payload["write_json"] = True
    if comparison:
        payload["comparison_summary"] = {
            "reference_comparisons": comparison.get("reference_comparisons"),
            "visual_gaps_resolved": comparison.get("visual_gaps_resolved"),
            "visual_gaps_pending": comparison.get("visual_gaps_pending"),
        }
        _write_standard_outputs(output, payload, comparison)
    report_path.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    status_path.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    _write_markdown_status(payload, output)
    return payload


def _unavailable_payload(output: Path, reason: str, env: dict | None = None) -> dict:
    output.mkdir(parents=True, exist_ok=True)
    payload = {
        "ok": False,
        "version": VERSION,
        "generated_at_madrid": _now_label(),
        "browser_available": False,
        "playwright_available": bool((env or {}).get("playwright_available")),
        "browsers_available": bool((env or {}).get("browsers_available")),
        "can_capture": False,
        "browser_qa_status": (env or {}).get("browser_qa_status") or "BROWSER_QA_UNAVAILABLE",
        "recommended_install_command": (env or {}).get("recommended_install_command") or "",
        "reason": reason,
        "screenshots": [],
        "screenshots_captured": 0,
        "routes_captured": [],
        "desktop_routes": [],
        "tablet_routes": [],
        "mobile_routes": [],
        "issues": [{
            "title": "BROWSER_QA_UNAVAILABLE",
            "area": "reference_visual",
            "severity": "low",
            "source": "browser_reference_qa_v907",
            "route": "browser",
            "evidence": reason,
            "recommendation": "Instalar Playwright/Chromium o ejecutar Browser QA en un entorno con navegador disponible.",
        }],
        "note": "No se declara pixel-perfect ni equivalencia visual exacta sin capturas reales.",
    }
    comparison = build_browser_reference_comparison(ROOT, qa_payload=payload, output_dir=output)
    _write_reference_gap_status(comparison)
    _write_outbox(comparison)
    _write_standard_outputs(output, payload, comparison)
    _write_payload(output, payload, comparison)
    return payload


def run_browser_reference_qa(
    *,
    base_url: str,
    output: Path,
    desktop: bool,
    mobile: bool,
    admin_safe: bool,
    no_login_required: bool,
    timeout: int,
    write_json: bool = True,
    v928_matrix: bool = False,
    safe_mock_sessions: bool = False,
    safe_session_secret: str = "",
    tablet: bool = False,
) -> dict:
    output.mkdir(parents=True, exist_ok=True)
    env = detect_browser_qa_environment()
    if not env.get("can_capture"):
        return _unavailable_payload(output, str(env.get("reason") or env.get("browser_qa_status") or "BROWSER_QA_UNAVAILABLE"), env)

    routes = PUBLIC_ROUTES + CLIENT_ROUTES + ADMIN_SAFE_ROUTES
    if admin_safe or no_login_required:
        routes += ADMIN_PROTECTED_ROUTES
    routes = list(dict.fromkeys(routes))

    devices = []
    if desktop and v928_matrix:
        devices.extend([
            ("desktop", "desktop_1366x768", {"width": 1366, "height": 768}),
            ("desktop", "desktop_1440x900", {"width": 1440, "height": 900}),
            ("desktop", "desktop_1600x900", {"width": 1600, "height": 900}),
            ("desktop", "desktop_1920x1080", {"width": 1920, "height": 1080}),
        ])
    elif desktop:
        devices.append(("desktop", "desktop_1440x900", {"width": 1440, "height": 900}))
    if mobile and v928_matrix:
        devices.extend([
            ("mobile", "mobile_360x800", {"width": 360, "height": 800}),
            ("mobile", "mobile_390x844", {"width": 390, "height": 844}),
            ("mobile", "mobile_430x932", {"width": 430, "height": 932}),
        ])
    elif mobile:
        devices.append(("mobile", "mobile_390x844", {"width": 390, "height": 844}))
    if tablet:
        devices.extend([
            ("tablet", "tablet_768x1024", {"width": 768, "height": 1024}),
            ("tablet", "tablet_1024x1366", {"width": 1024, "height": 1366}),
        ])
    if not devices:
        devices.append(("desktop", "desktop_1440x900", {"width": 1440, "height": 900}))

    captures: list[dict] = []
    try:
        from playwright.sync_api import sync_playwright  # type: ignore

        with sync_playwright() as p:
            browser = p.chromium.launch()
            try:
                signed_sessions = {}
                local_base = base_url.startswith("http://127.0.0.1") or base_url.startswith("http://localhost")
                if safe_mock_sessions and local_base:
                    from app import app as flask_app

                    if safe_session_secret:
                        flask_app.config["SECRET_KEY"] = safe_session_secret
                    serializer = flask_app.session_interface.get_signing_serializer(flask_app)
                    cookie_name = flask_app.config.get("SESSION_COOKIE_NAME", "session")
                    signed_sessions = {
                        "cookie_name": cookie_name,
                        "client": serializer.dumps({
                            "user_id": "v928-browser-client",
                            "user_name": "Browser QA Client",
                            "username": "browser_qa_client",
                            "user_email": "browser-qa-client@example.invalid",
                            "user_role": "FREE",
                            "membership": "FREE",
                            "user_membership": "FREE",
                        }),
                        "admin": serializer.dumps({
                            "user_id": "v928-browser-admin",
                            "user_name": "Browser QA Admin",
                            "username": "browser_qa_admin",
                            "user_email": "browser-qa-admin@example.invalid",
                            "user_role": "ADMIN",
                            "membership": "ADMIN",
                            "user_membership": "ADMIN",
                        }),
                    }
                for device, profile, viewport in devices:
                    device_dir = output / device
                    device_dir.mkdir(parents=True, exist_ok=True)
                    contexts = {}
                    for role in ("public", "client", "admin"):
                        # Visual evidence must represent the current release assets, not a
                        # service-worker cache left by an earlier local capture.
                        context = browser.new_context(viewport=viewport, service_workers="block")
                        if signed_sessions and role in {"client", "admin"}:
                            context.add_cookies([{
                                "name": signed_sessions["cookie_name"],
                                "value": signed_sessions[role],
                                "url": base_url.rstrip("/"),
                                "httpOnly": True,
                            }])
                        contexts[role] = (context, context.new_page())
                    for route in routes:
                        safe_name = (route.strip("/") or "home").replace("/", "__").replace("-", "_")
                        shot = device_dir / f"{safe_name}__{viewport['width']}x{viewport['height']}.png"
                        role = "public"
                        if signed_sessions and route in CLIENT_ROUTES:
                            role = "client"
                        elif signed_sessions and route in ADMIN_PROTECTED_ROUTES:
                            role = "admin"
                        page = contexts[role][1]
                        item = {
                            "device": device,
                            "profile": profile,
                            "session_profile": role,
                            "route": route,
                            "url": base_url.rstrip("/") + route,
                            "screenshot": str(shot.relative_to(ROOT)),
                        }
                        try:
                            response = page.goto(item["url"], wait_until="domcontentloaded", timeout=timeout)
                            page.wait_for_timeout(400)
                            page.evaluate("window.scrollTo(0, 0)")
                            page.wait_for_timeout(80)
                            scroll_width = page.evaluate("document.documentElement.scrollWidth")
                            inner_width = page.evaluate("window.innerWidth")
                            geometry = page.evaluate("""
                                () => {
                                  const main = document.querySelector('main');
                                  const first = main && main.firstElementChild;
                                  const desktopNav = document.querySelector('.v930-client-topbar, .v930-public-topbar, .v930-admin-topbar');
                                  const rect = (node) => node ? node.getBoundingClientRect() : null;
                                  const style = main ? getComputedStyle(main) : null;
                                  return {
                                    scrollY: window.scrollY,
                                    mainTop: rect(main)?.top ?? null,
                                    firstContentTop: rect(first)?.top ?? null,
                                    navBottom: rect(desktopNav)?.bottom ?? null,
                                    mainPaddingTop: style?.paddingTop ?? null,
                                    mainClass: main?.className || '',
                                  };
                                }
                            """)
                            body_text = page.locator("body").inner_text(timeout=3000)[:1000]
                            item.update({
                                "status": response.status if response else None,
                                "final_url": page.url,
                                "overflow_x": bool(scroll_width and inner_width and scroll_width > inner_width + 2),
                                "scroll_width": scroll_width,
                                "inner_width": inner_width,
                                "geometry": geometry,
                                "body_text_sample": body_text,
                            })
                            page.screenshot(path=str(shot), full_page=False)
                        except Exception as exc:
                            item["error"] = f"{exc.__class__.__name__}: {str(exc)[:220]}"
                        captures.append(item)
                    for context, _page in contexts.values():
                        context.close()
            finally:
                browser.close()
    except Exception as exc:
        return _unavailable_payload(output, f"Playwright instalado, pero navegador no disponible: {exc.__class__.__name__}: {str(exc)[:240]}", env)

    capture_errors = [item for item in captures if item.get("error")]
    auth_redirect_issues = []
    for item in captures:
        final_path = urlparse(str(item.get("final_url") or "")).path
        role = item.get("session_profile")
        if role == "client" and final_path in {"/cliente-login", "/login", "/entrar"}:
            auth_redirect_issues.append(item)
        elif role == "admin" and final_path in {"/admin-login", "/admin/login"}:
            auth_redirect_issues.append(item)
    overflow_issues = [item for item in captures if item.get("overflow_x")]
    qa_ok = not capture_errors and not auth_redirect_issues and not overflow_issues
    payload = {
        "ok": qa_ok,
        "version": VERSION,
        "generated_at_madrid": _now_label(),
        "browser_available": True,
        "playwright_available": True,
        "browsers_available": True,
        "browser_qa_status": "CAPTURED" if qa_ok else "CAPTURED_WITH_ISSUES",
        "base_url": base_url,
        "screenshots": captures,
        "screenshots_captured": len([item for item in captures if item.get("screenshot") and not item.get("error")]),
        "routes_captured": sorted({item["route"] for item in captures if item.get("screenshot") and not item.get("error")}),
        "desktop_routes": [item["route"] for item in captures if item.get("device") == "desktop"],
        "tablet_routes": [item["route"] for item in captures if item.get("device") == "tablet"],
        "mobile_routes": [item["route"] for item in captures if item.get("device") == "mobile"],
        "capture_errors": capture_errors,
        "auth_redirect_issues": auth_redirect_issues,
        "overflow_issues": overflow_issues,
        "safe_mock_sessions": bool(signed_sessions),
        "viewport_profiles": [profile for _, profile, _ in devices],
        "note": "Capturas locales; no prueban produccion Render.",
    }
    comparison = build_browser_reference_comparison(ROOT, qa_payload=payload, output_dir=output)
    _write_reference_gap_status(comparison)
    _write_outbox(comparison)
    _write_visual_fix_queue(comparison)
    if write_json:
        _write_payload(output, payload, comparison)
    return payload


def main() -> int:
    parser = argparse.ArgumentParser(description="Real browser screenshot/reference QA with V928 matrix support.")
    parser.add_argument("--base-url", default="http://127.0.0.1:5000")
    parser.add_argument("--output", default="reports/V907_browser_qa")
    parser.add_argument("--mobile", action="store_true")
    parser.add_argument("--desktop", action="store_true")
    parser.add_argument("--tablet", action="store_true")
    parser.add_argument("--admin-safe", action="store_true")
    parser.add_argument("--no-login-required", action="store_true")
    parser.add_argument("--timeout", type=int, default=15000)
    parser.add_argument("--timeout-ms", type=int)
    parser.add_argument("--write-json", action="store_true")
    parser.add_argument("--v928-matrix", action="store_true")
    parser.add_argument("--safe-mock-sessions", action="store_true")
    parser.add_argument("--safe-session-secret", default="")
    args = parser.parse_args()
    session_key = args.safe_session_secret or os.getenv("BROWSER_QA_SESSION_SECRET", "")
    payload = run_browser_reference_qa(
        base_url=args.base_url,
        output=ROOT / args.output,
        desktop=bool(args.desktop or not (args.mobile or args.tablet)),
        mobile=bool(args.mobile),
        admin_safe=bool(args.admin_safe),
        no_login_required=bool(args.no_login_required),
        timeout=int(args.timeout_ms or args.timeout),
        write_json=True,
        v928_matrix=bool(args.v928_matrix),
        safe_mock_sessions=bool(args.safe_mock_sessions),
        safe_session_secret=session_key,
        tablet=bool(args.tablet),
    )
    # Keep the Windows console path ASCII-safe; reports retain their UTF-8 data.
    print(json.dumps(payload, ensure_ascii=True, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
