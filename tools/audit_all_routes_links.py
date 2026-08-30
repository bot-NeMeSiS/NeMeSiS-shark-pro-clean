from __future__ import annotations

import json
import os
import re
import sys
from datetime import datetime
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
VERSION = (ROOT / "VERSION.txt").read_text(encoding="utf-8-sig", errors="replace").strip()
VERSION_TAG = VERSION.split("_", 1)[0] if VERSION else "DEV"
REPORT = ROOT / "reports" / f"{VERSION_TAG}_ROUTES_LINKS_AND_ALIASES_AUDIT.md"
JSON_REPORT = ROOT / "reports" / f"{VERSION_TAG}_ROUTES_LINKS_AND_ALIASES_AUDIT.json"


def rel(path: Path) -> str:
    return path.relative_to(ROOT).as_posix()


def scan_template_links() -> dict:
    href_re = re.compile(r"""href\s*=\s*["']([^"']+)["']""", re.IGNORECASE)
    action_re = re.compile(r"""<form\b[^>]*?(?:action\s*=\s*["']([^"']*)["'])?[^>]*?>""", re.IGNORECASE | re.DOTALL)
    direct_api_hrefs: list[dict] = []
    empty_links: list[dict] = []
    js_void_links: list[dict] = []
    forms_without_action: list[dict] = []
    templates_scanned = 0
    for path in sorted((ROOT / "templates").rglob("*.html")):
        templates_scanned += 1
        text = path.read_text(encoding="utf-8", errors="replace")
        for match in href_re.finditer(text):
            href = match.group(1).strip()
            entry = {"file": rel(path), "href": href}
            if href == "#":
                empty_links.append(entry)
            if href.lower().startswith("javascript:void"):
                js_void_links.append(entry)
            if href.startswith("/api/admin/") or href.startswith("/api/automation/"):
                direct_api_hrefs.append(entry)
        for match in action_re.finditer(text):
            action = (match.group(1) or "").strip()
            form_text = match.group(0).lower()
            if "method=" not in form_text or action == "#":
                forms_without_action.append({"file": rel(path), "action": action or "missing", "has_method": "method=" in form_text})
    return {
        "templates_scanned": templates_scanned,
        "direct_api_hrefs": direct_api_hrefs,
        "empty_links": empty_links,
        "js_void_links": js_void_links,
        "forms_without_action": forms_without_action,
    }


def smoke_routes() -> dict:
    os.environ.setdefault("AUTOMATION_SECRET", "codex-v910-local-secret")
    if str(ROOT) not in sys.path:
        sys.path.insert(0, str(ROOT))
    import app as app_module

    client = app_module.app.test_client()
    paths = [
        "/",
        "/cliente-login",
        "/registro",
        "/app",
        "/calendar",
        "/calendario",
        "/live",
        "/directo",
        "/picks",
        "/shark",
        "/telegram",
        "/profile",
        "/support",
        "/track-record",
        "/admin-login",
        "/admin/dashboard",
        "/admin/autonomous-company-sentinel",
        "/admin/sentinel-issues",
        "/admin/sentinel-codex-outbox",
        "/admin/not-found-events",
        "/admin/telegram/command-center",
        "/api/runtime-version",
        "/ruta-inventada-v910",
        "/api/ruta-inventada-v910",
        "/manifest.json",
        "/service-worker.js",
    ]
    results = []
    for path in paths:
        headers = {"X-NEMESIS-QA-PROBE": "1"} if "ruta-inventada-v910" in path else {}
        response = client.get(path, follow_redirects=False, headers=headers)
        ctype = response.headers.get("Content-Type", "")
        safe = response.status_code in {200, 302, 303, 307, 308, 403, 404}
        if path.startswith("/api/ruta-inventada"):
            safe = response.status_code == 404 and "application/json" in ctype
        if path == "/ruta-inventada-v910":
            safe = response.status_code == 404 and b"Ruta no encontrada" in response.data
        results.append({"path": path, "status": response.status_code, "content_type": ctype, "safe": safe})
    return {
        "routes_registered": len(list(app_module.app.url_map.iter_rules())),
        "smoke_results": results,
        "unsafe_smoke": [item for item in results if not item["safe"]],
    }


def write_report(payload: dict) -> None:
    REPORT.parent.mkdir(parents=True, exist_ok=True)
    lines = [
        f"# {VERSION_TAG} Routes Links And Aliases Audit",
        "",
        f"- version: `{VERSION}`",
        f"- generated_at: `{datetime.now().isoformat(timespec='seconds')}`",
        f"- routes_registered: `{payload['smoke']['routes_registered']}`",
        f"- templates_scanned: `{payload['links']['templates_scanned']}`",
        f"- direct_api_hrefs: `{len(payload['links']['direct_api_hrefs'])}`",
        f"- empty_hash_links: `{len(payload['links']['empty_links'])}`",
        f"- javascript_void_links: `{len(payload['links']['js_void_links'])}`",
        f"- forms_without_method_or_safe_action: `{len(payload['links']['forms_without_action'])}`",
        f"- unsafe_smoke_count: `{len(payload['smoke']['unsafe_smoke'])}`",
        "",
        "## Smoke",
    ]
    for item in payload["smoke"]["smoke_results"]:
        lines.append(f"- `{item['path']}` -> `{item['status']}` safe=`{str(item['safe']).lower()}`")
    lines.extend([
        "",
        "## Notes",
        "- Admin protected routes are expected to redirect or deny without session.",
        "- API 404 is expected to return safe JSON.",
        "- HTML 404 is expected to render the premium not-found template.",
        "- Direct admin/automation API hrefs should be replaced with buttons/fetch in future UI passes if any remain.",
    ])
    REPORT.write_text("\n".join(lines) + "\n", encoding="utf-8")
    JSON_REPORT.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def main() -> int:
    payload = {
        "version": VERSION,
        "links": scan_template_links(),
        "smoke": smoke_routes(),
    }
    write_report(payload)
    print(json.dumps({
        "ok": True,
        "report": str(REPORT),
        "routes_registered": payload["smoke"]["routes_registered"],
        "unsafe_smoke_count": len(payload["smoke"]["unsafe_smoke"]),
        "direct_api_hrefs": len(payload["links"]["direct_api_hrefs"]),
    }, ensure_ascii=False, indent=2))
    return 0 if not payload["smoke"]["unsafe_smoke"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
