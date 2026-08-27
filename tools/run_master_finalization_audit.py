from __future__ import annotations

import ast
import html
import json
import os
import re
import sys
import tempfile
from dataclasses import dataclass, field
from datetime import datetime
from html.parser import HTMLParser
from pathlib import Path
from typing import Any
from urllib.parse import urlparse


ROOT = Path(__file__).resolve().parents[1]
REPORT_DIR = ROOT / "reports" / "master_finalization"
REPORT_JSON = REPORT_DIR / "master_finalization_audit.json"
REPORT_MD = REPORT_DIR / "MASTER_FINALIZATION_AUDIT.md"


QUESTION_MOJIBAKE_RE = re.compile(r"[A-Za-zÁÉÍÓÚáéíóúÑñ]+\?[A-Za-zÁÉÍÓÚáéíóúÑñ]+")
ENCODING_MOJIBAKE_RE = re.compile(r"�|Ã.|Â.|â.")
TEXT_BROKEN_PATTERNS = [QUESTION_MOJIBAKE_RE, ENCODING_MOJIBAKE_RE]
QUERY_FRAGMENT_RE = re.compile(r"\b[\w-]+\?(?:[\w-]+|=)")


def _looks_like_query_or_asset(text: str) -> bool:
    value = str(text or "").lower()
    return bool(QUERY_FRAGMENT_RE.search(value) or ".svg?v" in value or ".css?v" in value or ".js?v" in value)


def _source_line_has_broken_text(line: str) -> bool:
    value = str(line or "")
    if ENCODING_MOJIBAKE_RE.search(value):
        return True
    if QUESTION_MOJIBAKE_RE.search(value):
        ignored = (
            "href=", "src=", "url(", "redirect(", "fetch(", "request.args", "request.form",
            "?lane=", "?tab=", "?mode=", "?dry_run=", "?q=", "?next=", "?secret=",
            "?force=", "?f=", "?filter=", "?result=", "?plan=", "?pick=", "?match=", "?team=", "?competition=", "?player=", "?utm", ".svg?v", ".js?v", ".css?v",
        )
        return not any(token in value for token in ignored)
    return False


TECHNICAL_VISIBLE = [
    "traceback",
    "payload",
    "engine.py",
    "AUTOMATION_SECRET",
    "TELEGRAM_BOT_TOKEN",
    "STRIPE_SECRET",
    "api_key",
]

CLIENT_CORE_ROUTES = [
    "/",
    "/landing",
    "/cliente-login",
    "/registro",
    "/forgot-password",
    "/app",
    "/calendar",
    "/partidos",
    "/live",
    "/match/local-match-2",
    "/team/club-local-qa",
    "/competition/liga-local-qa",
    "/player/local-player-101",
    "/favorites",
    "/picks",
    "/combis",
    "/track-record",
    "/memberships",
    "/telegram",
    "/profile",
    "/support",
    "/shark",
    "/shark-intelligence",
    "/action-platform",
    "/user-intelligence",
]

ADMIN_PUBLIC_AUTH_ROUTES = {
    "/admin-login",
    "/admin-bootstrap",
    "/admin-forgot-password",
    "/admin-reset-password/invalid-token",
}

ADMIN_CORE_ROUTES = [
    "/admin",
    "/admin/control-center",
    "/admin/founder-dashboard",
    "/admin/product-review-center",
    "/admin/executive-board",
    "/admin/go-to-market-office",
    "/admin/operations-center",
    "/admin/beta-center",
    "/admin/feedback-center",
    "/admin/company-board",
    "/admin/developer-center",
    "/admin/automation-center",
    "/admin/daily-automation",
    "/admin/telegram/command-center",
    "/admin/users",
    "/admin/memberships",
    "/admin/payments",
    "/admin/navigation-integrity",
    "/admin/route-health",
]


@dataclass
class HtmlSnapshot:
    route: str
    status: int
    final_location: str = ""
    title: str = ""
    text_count: int = 0
    links: list[dict[str, Any]] = field(default_factory=list)
    buttons: list[dict[str, Any]] = field(default_factory=list)
    forms: list[dict[str, Any]] = field(default_factory=list)
    images: list[dict[str, Any]] = field(default_factory=list)
    text_issues: list[str] = field(default_factory=list)
    technical_terms: list[str] = field(default_factory=list)


class SnapshotParser(HTMLParser):
    def __init__(self, route: str):
        super().__init__(convert_charrefs=True)
        self.snapshot = HtmlSnapshot(route=route, status=0)
        self._in_title = False
        self._skip_text = False
        self._texts: list[str] = []

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        attrs_d = {k.lower(): (v or "") for k, v in attrs}
        tag_l = tag.lower()
        if tag_l == "title":
            self._in_title = True
        if tag_l in {"script", "style", "template"}:
            self._skip_text = True
        if tag_l == "a":
            self.snapshot.links.append(
                {
                    "href": attrs_d.get("href", ""),
                    "text": "",
                    "aria": attrs_d.get("aria-label", ""),
                    "class": attrs_d.get("class", ""),
                }
            )
        elif tag_l == "button":
            self.snapshot.buttons.append(
                {
                    "type": attrs_d.get("type", ""),
                    "disabled": "disabled" in attrs_d,
                    "onclick": attrs_d.get("onclick", ""),
                    "aria": attrs_d.get("aria-label", ""),
                    "class": attrs_d.get("class", ""),
                    "text": "",
                }
            )
        elif tag_l == "form":
            self.snapshot.forms.append(
                {
                    "method": attrs_d.get("method", "GET").upper(),
                    "action": attrs_d.get("action", ""),
                    "class": attrs_d.get("class", ""),
                }
            )
        elif tag_l == "img":
            self.snapshot.images.append(
                {
                    "src": attrs_d.get("src", ""),
                    "alt": attrs_d.get("alt", ""),
                    "class": attrs_d.get("class", ""),
                }
            )

    def handle_endtag(self, tag: str) -> None:
        tag_l = tag.lower()
        if tag_l == "title":
            self._in_title = False
        if tag_l in {"script", "style", "template"}:
            self._skip_text = False

    def handle_data(self, data: str) -> None:
        if self._skip_text:
            return
        text = " ".join((data or "").split())
        if not text:
            return
        if self._in_title:
            self.snapshot.title += text
        self._texts.append(text)

    def finalize(self) -> HtmlSnapshot:
        self.snapshot.text_count = len(self._texts)
        joined = "\n".join(self._texts)
        issues: list[str] = []
        for pattern in TEXT_BROKEN_PATTERNS:
            for issue in sorted(set(pattern.findall(joined)))[:25]:
                if "?" in issue and _looks_like_query_or_asset(issue):
                    continue
                issues.append(issue)
        raw_visible = re.findall(r"\b(None|null|undefined)\b", joined, re.IGNORECASE)
        if not self.snapshot.route.startswith("/admin"):
            issues.extend(sorted(set(raw_visible))[:25])
        self.snapshot.text_issues = sorted(set(issues))[:80]
        lower = joined.lower()
        technical = {term for term in TECHNICAL_VISIBLE if term.lower() in lower}
        if self.snapshot.route.startswith("/admin"):
            technical.update(str(term) for term in raw_visible)
        self.snapshot.technical_terms = sorted(technical)
        return self.snapshot


def setup_env() -> None:
    os.environ.setdefault("SECRET_KEY", "master-finalization-local-secret")
    os.environ.setdefault("ADMIN_EMAIL", "admin@example.com")
    os.environ.setdefault("ADMIN_PASSWORD", "admin-password")
    os.environ.setdefault("ADMIN_USERNAME", "admin")
    os.environ.setdefault("ADMIN_NAME", "Admin Local")
    os.environ.setdefault("AUTOMATION_SECRET", "master-finalization-automation-secret")
    os.environ.setdefault("BACKGROUND_JOBS_ENABLED", "false")
    os.environ.setdefault("AUTO_GENERATE_PICKS", "false")
    os.environ.setdefault("AUTO_SEND_TELEGRAM_PICKS", "false")
    os.environ.setdefault("NEMESIS_LOCAL_SAFE_MODE", "1")
    os.environ.setdefault("NEMESIS_LOCAL_OFFLINE", "1")
    os.environ.setdefault("DB_PATH", str(Path(tempfile.gettempdir()) / "nemesis_master_finalization_audit.db"))


def import_app():
    setup_env()
    if str(ROOT) not in sys.path:
        sys.path.insert(0, str(ROOT))
    import app as app_module

    app_module.app.config.update(TESTING=True)
    try:
        app_module.initialize_once()
    except Exception:
        pass
    return app_module


def route_sample(rule: Any) -> str | None:
    if "GET" not in getattr(rule, "methods", set()):
        return None
    path = str(rule.rule)
    if path.startswith("/static/"):
        return None
    replacements = {
        "match_id": "local-match-2",
        "team_id": "club-local-qa",
        "competition_id": "liga-local-qa",
        "player_id": "local-player-101",
        "plan": "PRO",
        "token": "invalid-token",
        "name": "missing",
        "highlight_id": "missing",
        "export_key": "summary",
        "issue_id": "missing",
        "recommendation_id": "missing",
        "content_id": "missing",
        "user_id": "missing",
        "job_id": "missing",
    }
    for arg in sorted(rule.arguments, key=len, reverse=True):
        value = replacements.get(arg, f"sample-{arg}")
        path = re.sub(rf"<(?:[^:<>]+:)?{re.escape(arg)}>", value, path)
    if "<" in path or ">" in path:
        return None
    return path


def parse_html(route: str, status: int, body: bytes, location: str = "") -> HtmlSnapshot:
    parser = SnapshotParser(route)
    try:
        parser.feed(body.decode("utf-8", errors="replace"))
    except Exception:
        pass
    snapshot = parser.finalize()
    snapshot.status = status
    snapshot.final_location = location
    return snapshot


def seed_sessions(app_module: Any):
    client_public = app_module.app.test_client()
    client_user = app_module.app.test_client()
    client_admin = app_module.app.test_client()

    with client_user.session_transaction() as sess:
        sess["user_id"] = "local-client-audit"
        sess["user_name"] = "Cliente Local"
        sess["username"] = "cliente_local"
        sess["user_email"] = "cliente-local-audit"
        sess["user_role"] = "FREE"
        sess["user_membership"] = "FREE"
        sess["membership"] = "FREE"

    with client_admin.session_transaction() as sess:
        sess["user_id"] = "local-admin-audit"
        sess["user_name"] = "Admin Local"
        sess["username"] = "admin_local"
        sess["user_email"] = "admin-local-audit"
        sess["user_role"] = "ADMIN"
        sess["user_membership"] = "ADMIN"
        sess["membership"] = "ADMIN"

    return client_public, client_user, client_admin


def audit_routes(app_module: Any) -> dict[str, Any]:
    client_public, client_user, client_admin = seed_sessions(app_module)
    rules = sorted(app_module.app.url_map.iter_rules(), key=lambda r: r.rule)
    sampled = []
    seen = set()
    for rule in rules:
        path = route_sample(rule)
        if not path or path in seen:
            continue
        seen.add(path)
        sampled.append({"path": path, "endpoint": rule.endpoint, "methods": sorted(rule.methods or [])})

    public_snapshots = []
    user_snapshots = []
    admin_snapshots = []
    route_failures = []
    for item in sampled:
        path = item["path"]
        profile_client = client_admin if path.startswith("/admin") or path.startswith("/api/admin") else client_user
        for label, client, bucket in [
            ("public", client_public, public_snapshots),
            ("session", profile_client, user_snapshots if profile_client is client_user else admin_snapshots),
        ]:
            try:
                resp = client.get(path, follow_redirects=False)
                content_type = resp.headers.get("Content-Type", "")
                location = resp.headers.get("Location", "")
                body = resp.data if "text/html" in content_type and resp.status_code < 300 else b""
                snap = parse_html(path, resp.status_code, body, location)
                bucket.append(snap.__dict__)
                if resp.status_code >= 500:
                    route_failures.append({"path": path, "profile": label, "status": resp.status_code})
            except Exception as exc:
                route_failures.append({"path": path, "profile": label, "status": "EXCEPTION", "error": str(exc)[:220]})

    admin_exposure = []
    for path in ADMIN_CORE_ROUTES + [x["path"] for x in sampled if x["path"].startswith("/admin")][:120]:
        resp = client_user.get(path, follow_redirects=False)
        if path in ADMIN_PUBLIC_AUTH_ROUTES:
            continue
        if resp.status_code == 200:
            admin_exposure.append({"path": path, "status": resp.status_code})

    return {
        "routes_registered": len(rules),
        "routes_sampled": len(sampled),
        "public_snapshots": public_snapshots,
        "session_snapshots": user_snapshots,
        "admin_snapshots": admin_snapshots,
        "route_failures": route_failures,
        "admin_exposure": admin_exposure,
    }


def audit_static_and_templates() -> dict[str, Any]:
    href_problem_re = re.compile(r"""<[^>]+\bhref\s*=\s*(['"])(#|javascript:void\(0\)|)\1""", re.IGNORECASE)
    onclick_re = re.compile(r"""onclick\s*=\s*(['"])(.*?)\1""", re.IGNORECASE | re.DOTALL)
    shark_refs = []
    text_issues = []
    href_problems = []
    onclicks = []
    template_count = 0
    source_files = list((ROOT / "templates").rglob("*.html")) + list((ROOT / "static").rglob("*.css")) + list((ROOT / "static").rglob("*.js")) + [ROOT / "app.py"]
    for path in source_files:
        if not path.exists() or path.suffix.lower() not in {".html", ".css", ".js", ".py"}:
            continue
        rel = path.relative_to(ROOT).as_posix()
        text = path.read_text(encoding="utf-8", errors="replace")
        if path.suffix == ".html":
            template_count += 1
        if "shark-logo.svg" in text or "nemesis-shark-official.svg" in text:
            shark_refs.append(
                {
                    "file": rel,
                    "legacy_refs": text.count("shark-logo.svg"),
                    "official_refs": text.count("nemesis-shark-official.svg"),
                }
            )
        for i, line in enumerate(text.splitlines(), start=1):
            if _source_line_has_broken_text(line):
                text_issues.append({"file": rel, "line": i, "text": line.strip()[:220]})
            if href_problem_re.search(line):
                href_problems.append({"file": rel, "line": i, "text": line.strip()[:220]})
            if onclick_re.search(line):
                onclicks.append({"file": rel, "line": i, "text": line.strip()[:220]})
    return {
        "templates_scanned": template_count,
        "files_scanned": len(source_files),
        "text_source_issues": text_issues,
        "href_source_problems": href_problems,
        "onclick_source_count": len(onclicks),
        "onclick_source_samples": onclicks[:40],
        "shark_refs": shark_refs,
    }


def audit_templates_render_refs() -> dict[str, Any]:
    tree = ast.parse((ROOT / "app.py").read_text(encoding="utf-8", errors="replace"))
    templates = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Call):
            name = getattr(node.func, "id", None) or getattr(node.func, "attr", None)
            if name == "render_template" and node.args:
                first = node.args[0]
                if isinstance(first, ast.Constant) and isinstance(first.value, str):
                    templates.add(first.value)
    missing = sorted(t for t in templates if not (ROOT / "templates" / t).exists())
    return {"render_templates": len(templates), "missing_templates": missing}


def summarize(payload: dict[str, Any]) -> dict[str, Any]:
    routes = payload["routes"]
    source = payload["source"]
    rendered = [
        *routes["public_snapshots"],
        *routes["session_snapshots"],
        *routes["admin_snapshots"],
    ]
    link_count = sum(len(x.get("links") or []) for x in rendered)
    button_count = sum(len(x.get("buttons") or []) for x in rendered)
    form_count = sum(len(x.get("forms") or []) for x in rendered)
    text_count = sum(int(x.get("text_count") or 0) for x in rendered)
    rendered_text_issues = sum(len(x.get("text_issues") or []) for x in rendered)
    broken_images = [
        {"route": snap["route"], "src": img.get("src")}
        for snap in rendered
        for img in snap.get("images") or []
        if not img.get("src") or img.get("src") == "#"
    ]
    dead_links = [
        {"route": snap["route"], "href": link.get("href")}
        for snap in rendered
        for link in snap.get("links") or []
        if str(link.get("href") or "").strip() in {"", "#"} or str(link.get("href") or "").lower().startswith("javascript:void")
    ]
    empty_button_count = sum(
        1
        for snap in rendered
        for button in snap.get("buttons") or []
        if not (button.get("text") or button.get("aria") or button.get("class"))
    )
    source_text_count = len(source["text_source_issues"])
    technical_warning_count = sum(len(x.get("technical_terms") or []) for x in rendered)
    fail_count = len(routes["route_failures"]) + len(routes["admin_exposure"]) + len(dead_links) + source_text_count + rendered_text_issues + len(broken_images)
    warning_count = len(source["href_source_problems"]) + source["onclick_source_count"] + empty_button_count + technical_warning_count
    score = max(0, round(100 - fail_count * 0.85 - warning_count * 0.08, 1))
    return {
        "score": score,
        "routes_audited": routes["routes_sampled"],
        "routes_registered": routes["routes_registered"],
        "buttons_audited": button_count,
        "links_audited": link_count,
        "texts_audited": text_count,
        "forms_audited": form_count,
        "route_failures": len(routes["route_failures"]),
        "admin_exposure": len(routes["admin_exposure"]),
        "dead_links": len(dead_links),
        "broken_images": len(broken_images),
        "source_text_issues": source_text_count,
        "rendered_text_issues": rendered_text_issues,
        "warnings": warning_count,
        "technical_warnings": technical_warning_count,
        "dead_link_samples": dead_links[:40],
        "broken_image_samples": broken_images[:40],
    }


def write_reports(payload: dict[str, Any]) -> None:
    REPORT_DIR.mkdir(parents=True, exist_ok=True)
    payload["summary"] = summarize(payload)
    REPORT_JSON.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    s = payload["summary"]
    rows = [
        ("Rutas", s["routes_audited"], s["routes_audited"] - s["route_failures"], s["route_failures"], 0),
        ("Botones", s["buttons_audited"], s["buttons_audited"], 0, 0),
        ("Enlaces", s["links_audited"], s["links_audited"] - s["dead_links"], s["dead_links"], len(payload["source"]["href_source_problems"])),
        ("Textos", s["texts_audited"], max(0, s["texts_audited"] - s["rendered_text_issues"]), s["rendered_text_issues"], s["source_text_issues"]),
        ("Formularios", s["forms_audited"], s["forms_audited"], 0, 0),
        ("Cliente/Admin", len(payload["routes"]["admin_exposure"]), 0 if payload["routes"]["admin_exposure"] else 1, len(payload["routes"]["admin_exposure"]), 0),
        ("Assets", len(payload["source"]["shark_refs"]), len(payload["source"]["shark_refs"]), 0, sum(x["legacy_refs"] for x in payload["source"]["shark_refs"])),
    ]
    lines = [
        "# Master Finalization Audit",
        "",
        f"- generated_at: `{datetime.now().isoformat(timespec='seconds')}`",
        f"- score: `{s['score']}/100`",
        f"- routes_registered: `{s['routes_registered']}`",
        f"- routes_audited: `{s['routes_audited']}`",
        f"- buttons_audited: `{s['buttons_audited']}`",
        f"- links_audited: `{s['links_audited']}`",
        f"- texts_audited: `{s['texts_audited']}`",
        f"- forms_audited: `{s['forms_audited']}`",
        "",
        "| Area | Revisados | PASS | FAIL | WARNING |",
        "|---|---:|---:|---:|---:|",
    ]
    for row in rows:
        lines.append(f"| {row[0]} | {row[1]} | {row[2]} | {row[3]} | {row[4]} |")
    lines.extend([
        "",
        "## Fallos",
        f"- route_failures: `{s['route_failures']}`",
        f"- admin_exposure: `{s['admin_exposure']}`",
        f"- dead_links: `{s['dead_links']}`",
        f"- broken_images: `{s['broken_images']}`",
        f"- source_text_issues: `{s['source_text_issues']}`",
        f"- rendered_text_issues: `{s['rendered_text_issues']}`",
        "",
        "## Shark Assets",
    ])
    for ref in payload["source"]["shark_refs"]:
        lines.append(f"- `{ref['file']}` legacy=`{ref['legacy_refs']}` official=`{ref['official_refs']}`")
    lines.extend(["", "## Samples"])
    for key in ("route_failures", "admin_exposure"):
        lines.append(f"### {key}")
        for item in payload["routes"][key][:80]:
            lines.append(f"- `{item}`")
    lines.append("### source_text_issues")
    for item in payload["source"]["text_source_issues"][:120]:
        lines.append(f"- `{item['file']}:{item['line']}` {html.escape(item['text'])}")
    lines.append("### dead_links")
    for item in s["dead_link_samples"]:
        lines.append(f"- `{item['route']}` -> `{item['href']}`")
    REPORT_MD.write_text("\n".join(lines) + "\n", encoding="utf-8")


def main() -> int:
    app_module = import_app()
    payload = {
        "routes": audit_routes(app_module),
        "source": audit_static_and_templates(),
        "templates": audit_templates_render_refs(),
    }
    write_reports(payload)
    print(json.dumps(payload["summary"], ensure_ascii=False, indent=2))
    print(str(REPORT_MD))
    return 0 if payload["summary"]["route_failures"] == 0 and payload["summary"]["admin_exposure"] == 0 else 1


if __name__ == "__main__":
    raise SystemExit(main())
