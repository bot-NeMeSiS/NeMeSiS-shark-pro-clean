from __future__ import annotations

import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
VERSION = "V817_REFERENCE_PIXEL_POLISH_CLIENT_ADMIN_FINAL"
TEMPLATES = {
    "home.html": ("home", "home-public"),
    "client_login.html": ("client_login",),
    "client_app_center.html": ("client_app_center",),
    "calendar.html": ("calendar",),
    "live.html": ("live",),
    "picks.html": ("picks",),
    "match_detail.html": ("match_detail",),
    "shark.html": ("shark",),
    "profile.html": ("profile",),
    "telegram.html": ("telegram",),
}


def text(path: Path) -> str:
    return path.read_text(encoding="utf-8", errors="replace")


def main() -> None:
    base = text(ROOT / "templates" / "base.html")
    css = text(ROOT / "static" / "app.css")
    template_results = {}
    for name, markers in TEMPLATES.items():
        raw = text(ROOT / "templates" / name)
        template_results[name] = {
            "has_v817_template_marker": all(f'data-v817-template="{marker}"' in raw for marker in markers),
            "has_extends_base": "{% extends" in raw or name == "profile.html",
        }

    checks = {
        "body_has_v817": 'data-v817-shell="true"' in base,
        "source_comment": "NEMESIS V817 REFERENCE PIXEL POLISH ACTIVE" in base,
        "css_cache_busting": f"?v={VERSION}" in base,
        "decorative_shark": "v815-client-shark-backdrop" in base and "data-v817-shell" in css,
        "single_widget_markup": base.count('class="shark-widget"') == 1,
        "shark_page_hides_widget": '[data-ns-route="/shark"] .shark-widget' in css or ".is-on-shark-page" in css,
        "bottom_nav_polished": ".bottom-nav-clean" in css and "data-v817-shell" in css,
        "admin_not_shark_backdrop": ".ns-admin .v815-client-shark-backdrop" in css,
        "all_templates_marked": all(item["has_v817_template_marker"] for item in template_results.values()),
    }
    failed = [name for name, ok in checks.items() if not ok]
    print(json.dumps({
        "ok": not failed,
        "version": VERSION,
        "checks": checks,
        "templates": template_results,
        "failed": failed,
    }, ensure_ascii=False, indent=2))
    raise SystemExit(1 if failed else 0)


if __name__ == "__main__":
    main()
