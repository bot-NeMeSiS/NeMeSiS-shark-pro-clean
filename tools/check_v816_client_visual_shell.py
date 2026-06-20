from __future__ import annotations

import json
import pathlib


ROOT = pathlib.Path(__file__).resolve().parents[1]
VERSION = "V816_RENDER_LIVE_REFERENCE_VISUAL_DIFF_CLIENT_ADMIN_FINAL"
CURRENT_VERSION = "V817_REFERENCE_PIXEL_POLISH_CLIENT_ADMIN_FINAL"

CLIENT_TEMPLATES = {
    "home.html": ["home", "home-public"],
    "client_login.html": ["client_login"],
    "client_app_center.html": ["client_app_center"],
    "calendar.html": ["calendar"],
    "live.html": ["live"],
    "picks.html": ["picks"],
    "match_detail.html": ["match_detail"],
    "shark.html": ["shark"],
    "profile.html": ["profile"],
    "telegram.html": ["telegram"],
}


def fail(message: str, details=None) -> None:
    print(json.dumps({"ok": False, "error": message, "details": details or {}}, ensure_ascii=False, indent=2))
    raise SystemExit(1)


def main() -> None:
    base = (ROOT / "templates" / "base.html").read_text(encoding="utf-8", errors="replace")
    css = (ROOT / "static" / "app.css").read_text(encoding="utf-8", errors="replace")
    template_results = {}
    for name, markers in CLIENT_TEMPLATES.items():
        raw = (ROOT / "templates" / name).read_text(encoding="utf-8", errors="replace")
        template_results[name] = {
            "has_v816_template_marker": any(f'data-v816-template="{marker}"' in raw for marker in markers),
            "has_extends_base": '{% extends "base.html" %}' in raw,
        }
    checks = {
        "body_has_v816": 'data-v816-shell="true"' in base,
        "source_comment": "NEMESIS V816 LIVE REFERENCE VISUAL DIFF ACTIVE" in base or "NEMESIS V817 REFERENCE PIXEL POLISH ACTIVE" in base,
        "css_cache_busting": VERSION in base or CURRENT_VERSION in base,
        "decorative_shark": "v815-client-shark-backdrop" in base and "v815-client-shark-backdrop" in css,
        "single_widget_markup": base.count('class="shark-widget"') == 1,
        "shark_page_hides_widget": '[data-ns-route="/shark"] .shark-widget' in css,
        "bottom_nav_polished": ".bottom-nav-clean" in css and "data-v816-shell" in css,
        "admin_not_shark_backdrop": "current_user.role != 'ADMIN'" in base and "v815-client-shark-backdrop" in base,
        "all_templates_marked": all(v["has_v816_template_marker"] for v in template_results.values()),
    }
    failed = [name for name, ok in checks.items() if not ok]
    if failed:
        fail("Fallan checks visuales V816: " + ", ".join(failed), {"templates": template_results, "checks": checks})
    print(json.dumps({"ok": True, "version": VERSION, "checks": checks, "templates": template_results}, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()


