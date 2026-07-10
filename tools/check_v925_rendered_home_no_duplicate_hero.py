from __future__ import annotations

import ast
import json
import os
import re
import sys
import tempfile
from html.parser import HTMLParser
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
VERSION = "V925_REFERENCE_MODEL_FULL_APP_REBUILD_QUALITY_PASS_FINAL"
V926_CONTAINER_VERSION = "V926_DESKTOP_REFERENCE_MODEL_COMMAND_CENTER_AND_SPORTS_VALUE_PASS_FINAL"
ALLOWED_CONTAINER_VERSIONS = {VERSION, V926_CONTAINER_VERSION}
TEMP_DB = Path(tempfile.gettempdir()) / f"nemesis_v925_rendered_home_{os.getpid()}.sqlite"
sys.dont_write_bytecode = True


def read(rel: str) -> str:
    return (ROOT / rel).read_text(encoding="utf-8-sig", errors="replace")


def source_app_version(source: str) -> str:
    for node in ast.parse(source).body:
        if not isinstance(node, ast.Assign):
            continue
        for target in node.targets:
            if isinstance(target, ast.Name) and target.id == "APP_VERSION":
                return str(getattr(node.value, "value", ""))
    return ""


class RenderedHomeParser(HTMLParser):
    VOID_TAGS = {"area", "base", "br", "col", "embed", "hr", "img", "input", "link", "meta", "param", "source", "track", "wbr"}

    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self.stack: list[str] = []
        self.all_text: list[str] = []
        self.h1_texts: list[str] = []
        self._h1_buffer: list[str] | None = None
        self.hero_count = 0
        self.legacy_classes: set[str] = set()
        self.v925_root_depth: int | None = None
        self.first_v925_child_classes: set[str] | None = None

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        attr_map = {key: value or "" for key, value in attrs}
        classes = set(attr_map.get("class", "").split())
        if tag == "main" and "v925-shell" in classes and ({"v925-page", "v925-public-shell"} & classes):
            self.v925_root_depth = len(self.stack)
        elif self.v925_root_depth is not None and len(self.stack) == self.v925_root_depth + 1:
            if self.first_v925_child_classes is None and tag in {"section", "article", "div"}:
                self.first_v925_child_classes = classes

        if "v925-public-hero" in classes:
            self.hero_count += 1
        self.legacy_classes.update(
            classes.intersection(
                {
                    "v783-public-hero",
                    "v922-public-hero",
                    "v924-public-hero",
                    "public-home-hero",
                    "landing-hero",
                }
            )
        )
        if tag == "h1":
            self._h1_buffer = []
        if tag not in self.VOID_TAGS:
            self.stack.append(tag)

    def handle_endtag(self, tag: str) -> None:
        if tag == "h1" and self._h1_buffer is not None:
            self.h1_texts.append(" ".join("".join(self._h1_buffer).split()))
            self._h1_buffer = None
        if tag in self.stack:
            reverse_index = self.stack[::-1].index(tag)
            del self.stack[len(self.stack) - reverse_index - 1 :]

    def handle_data(self, data: str) -> None:
        self.all_text.append(data)
        if self._h1_buffer is not None:
            self._h1_buffer.append(data)

    @property
    def normalized_text(self) -> str:
        return " ".join(" ".join(self.all_text).split())


def clean_temp_db() -> None:
    for suffix in ("", "-wal", "-shm", "-journal"):
        try:
            Path(str(TEMP_DB) + suffix).unlink(missing_ok=True)
        except OSError:
            pass


def main() -> int:
    failures: list[str] = []
    app_source = read("app.py")
    home_source = read("templates/home.html")
    css = read("static/app.css")
    version_bytes = (ROOT / "VERSION.txt").read_bytes()

    if version_bytes.startswith(b"\xef\xbb\xbf"):
        failures.append("VERSION.txt contains UTF-8 BOM")
    local_version = version_bytes.decode("utf-8").strip()
    if local_version not in ALLOWED_CONTAINER_VERSIONS:
        failures.append("VERSION.txt is not a supported V925/V926 container")
    if source_app_version(app_source) != local_version:
        failures.append("APP_VERSION does not match the local V925/V926 container")

    os.environ["DB_PATH"] = str(TEMP_DB)
    clean_temp_db()
    if str(ROOT) not in sys.path:
        sys.path.insert(0, str(ROOT))
    import app as app_module

    app_module.app.config.update(TESTING=True, PROPAGATE_EXCEPTIONS=True)
    client = app_module.app.test_client()
    response = client.get("/", follow_redirects=False)
    rendered = response.get_data(as_text=True)
    parser = RenderedHomeParser()
    parser.feed(rendered)

    if response.status_code != 200:
        failures.append(f"GET / returned {response.status_code}")
    if len(parser.h1_texts) != 1:
        failures.append(f"rendered home has {len(parser.h1_texts)} H1 elements")
    elif parser.h1_texts[0] != "NeMeSiS SHARK PRO":
        failures.append(f"unexpected home H1: {parser.h1_texts[0]}")
    if parser.hero_count != 1:
        failures.append(f"rendered home has {parser.hero_count} V925 public heroes")
    if parser.legacy_classes:
        failures.append(f"legacy public hero classes rendered: {sorted(parser.legacy_classes)}")
    valid_first_child = bool(
        parser.first_v925_child_classes
        and (
            "v925-public-hero" in parser.first_v925_child_classes
            or "v926-home-desktop-overview" in parser.first_v925_child_classes
        )
    )
    if not valid_first_child:
        failures.append("V925 hero or its V926 desktop overview is not the first structural child")

    legacy_primary_copy = "Partidos, directos, picks y análisis premium en español"
    legacy_secondary_copy = "Partidos, directos, picks y planes en una pantalla clara"
    legacy_secondary_title = "NeMeSiS SHARK PRO app deportiva premium"
    rendered_lower = parser.normalized_text.casefold()
    legacy_hits = [
        phrase
        for phrase in (legacy_primary_copy, legacy_secondary_copy, legacy_secondary_title)
        if phrase.casefold() in rendered_lower
    ]
    if legacy_secondary_title.casefold() in rendered_lower:
        failures.append("legacy second hero title is visible")
    if legacy_primary_copy.casefold() in rendered_lower and legacy_secondary_copy.casefold() in rendered_lower:
        failures.append("both legacy public hero copies are visible")

    required_sections = ("Hoy en NeMeSiS", "Qué hace la app", "Planes", "Confianza")
    missing_sections = [section for section in required_sections if section.casefold() not in rendered_lower]
    if missing_sections:
        failures.append(f"rendered home missing sections: {missing_sections}")

    if home_source.count('class="v925-public-hero v925-above-fold"') != 1:
        failures.append("home source does not contain exactly one V925 hero")
    if any(marker in home_source for marker in ("v783-public-hero", legacy_secondary_title, legacy_secondary_copy)):
        failures.append("home source still contains a legacy public hero marker")
    if ".v925-public-hero" not in css or "body.ns-admin .ns-main-shell" not in css:
        failures.append("V925 home/admin compact CSS contract is incomplete")

    client_routes = (
        "/cliente-login",
        "/login",
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
    )
    admin_routes = (
        "/admin/dashboard",
        "/admin/automation-workforce",
        "/admin/autonomous-company-sentinel",
    )
    route_status: dict[str, int] = {}
    for route in client_routes + admin_routes:
        route_response = client.get(route, follow_redirects=False)
        route_status[route] = route_response.status_code
        if route_response.status_code >= 500:
            failures.append(f"route {route} returned {route_response.status_code}")

    admin_templates = "\n".join(
        read(rel)
        for rel in (
            "templates/admin_dashboard.html",
            "templates/admin_automation_workforce.html",
            "templates/admin_autonomous_company_sentinel.html",
            "templates/admin_sentinel_issues.html",
            "templates/admin_sentinel_codex_outbox.html",
            "templates/admin_telegram_command_center.html",
        )
    )
    for forbidden in ("Salir cliente", "Capturas0", "Comparaciones18"):
        if forbidden in admin_templates:
            failures.append(f"admin template contains forbidden glued/legacy copy: {forbidden}")
    if "V925 admin command center reference rebuild" not in admin_templates:
        failures.append("admin command-center V925 marker is missing")

    safe_route_states: dict[str, bool] = {}
    for route in ("/calendar", "/live", "/picks", "/shark"):
        page = client.get(route, follow_redirects=False).get_data(as_text=True).casefold()
        safe_route_states[route] = any(
            marker in page
            for marker in ("datos reales", "modo seguro", "sin partidos", "sin directos", "sin picks", "estado seguro")
        )
        if not safe_route_states[route]:
            failures.append(f"route {route} lacks a visible real-data or safe-state marker")

    runtime = client.get("/api/runtime-version").get_json() or {}
    if runtime.get("version") != local_version or not runtime.get("version_files_match"):
        failures.append("local runtime identity is not aligned with the V925/V926 container")

    result = {
        "ok": not failures,
        "version": local_version,
        "failures": failures,
        "rendered_home": {
            "status": response.status_code,
            "h1_count": len(parser.h1_texts),
            "h1_texts": parser.h1_texts,
            "v925_public_hero_count": parser.hero_count,
            "legacy_classes": sorted(parser.legacy_classes),
            "legacy_copy_hits": legacy_hits,
            "first_structural_child_classes": sorted(parser.first_v925_child_classes or []),
            "required_sections_present": {section: section not in missing_sections for section in required_sections},
            "duplicate_hero": bool(
                len(parser.h1_texts) != 1
                or parser.hero_count != 1
                or parser.legacy_classes
                or legacy_secondary_title.casefold() in rendered_lower
            ),
        },
        "route_status": route_status,
        "safe_route_states": safe_route_states,
        "admin_compact_contract": {
            "v925_marker": "V925 admin command center reference rebuild" in admin_templates,
            "client_exit_copy_absent": "Salir cliente" not in admin_templates,
            "glued_values_absent": all(value not in admin_templates for value in ("Capturas0", "Comparaciones18")),
            "compact_css_present": "body.ns-admin .ns-main-shell" in css,
        },
        "runtime": {
            "version": runtime.get("version"),
            "version_files_match": runtime.get("version_files_match"),
            "deployment_alignment_status": runtime.get("deployment_alignment_status"),
        },
    }
    print(json.dumps(result, ensure_ascii=False, indent=2))
    clean_temp_db()
    return 0 if result["ok"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
