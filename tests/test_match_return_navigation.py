"""Contextual return journeys use canonical lifecycle truth and constant local URLs."""
from datetime import datetime, timedelta, timezone
from pathlib import Path
import copy
import mimetypes
import os
import re
import sqlite3
from urllib.parse import urlsplit

import pytest
from playwright.sync_api import sync_playwright

from engines.v935_launch_trust_engine import match_status_truth

ROOT = Path(__file__).resolve().parents[1]


@pytest.fixture
def return_journey(app_module, monkeypatch, tmp_path):
    a = app_module
    path = tmp_path / "match-return.sqlite"
    monkeypatch.setattr(a, "DB_PATH", str(path))
    monkeypatch.setattr(a, "_SEEDED_DB_PATH", None)
    monkeypatch.setattr(a, "_SEEDING_DB_PATH", None)
    monkeypatch.setattr(a, "APP_INITIALIZED", False)
    a.seed_core()
    now = datetime.now(timezone.utc)
    with sqlite3.connect(path) as conn:
        for plan in ("FREE", "PRO", "ELITE"):
            conn.execute("""INSERT INTO users
                (id,name,username,email,password_hash,role,membership,
                 membership_source,membership_expires_at,created_at)
                VALUES(?,?,?,?,?,?,?,?,?,?)""",
                ("return-" + plan, "Synthetic " + plan, "return-" + plan,
                 "return-" + plan + "@example.invalid", "not-a-login-password",
                 plan, plan, "admin_manual", (now + timedelta(days=1)).isoformat(),
                 now.isoformat()))
    box = {}
    monkeypatch.setattr(a, "match_detail", lambda *_a, **_k: copy.deepcopy(box["detail"]))
    monkeypatch.setattr(a, "v935_enrich_match_lifecycle", lambda match: match)
    monkeypatch.setattr(a, "admin_operational_settings", lambda: {
        "settings_readable": True, "highlights_enabled": True})
    monkeypatch.setattr(a, "sportsdb_highlights_for_match", lambda *_a: {
        "ok": True, "read_state": "VERIFIED", "highlights": [], "all_highlights": []})
    monkeypatch.setattr(a, "v766_highlight_map_snapshot", lambda *_a, **_k: {
        "ok": True, "read_state": "VERIFIED", "map": {}})

    def render(kind, plan="FREE"):
        stamp = datetime.now(timezone.utc)
        match = {
            "id": "return-local", "home_team": "Club Local", "away_team": "Club Visitante",
            "competition_name": "Liga de prueba", "competition_key": "test-local",
            "source": "api_football", "status": "2H",
            "kickoff_iso": (stamp - timedelta(hours=1)).isoformat(),
            "match_date": stamp.date().isoformat(), "kickoff_time": "20:00",
            "updated_at": stamp.isoformat(), "last_synced_at": stamp.isoformat(),
            "home_score": 0, "away_score": 0,
        }
        if kind == "halftime":
            match["status"] = "HT"
        elif kind == "upcoming":
            match.update(status="NS", kickoff_iso=(stamp + timedelta(hours=1)).isoformat())
        elif kind == "finished":
            match["status"] = "FT"
        elif kind == "suspended":
            match["status"] = "SUSP"
        elif kind == "stale":
            match["v935_freshness"] = {"is_stale": True}
        elif kind == "conflict":
            match["provider_status"] = "FT"
        elif kind == "missing":
            match.pop("status")
            match.pop("kickoff_iso")
            match.pop("match_date")
            match.pop("kickoff_time")
        truth = match_status_truth(match)
        assert truth["is_live"] is (kind in {"live", "halftime"})
        box["detail"] = {"id": match["id"], "match": match, "timeline": [],
                         "related_picks": [], "statistics": {"items": []}}
        client = a.app.test_client()
        user = a.get_user_by_id("return-" + plan)
        with a.app.test_request_context():
            a.set_login_session(user)
            session = dict(a.session)
        with client.session_transaction() as state:
            state.update(session)
        response = client.get("/match/return-local?next=https://untrusted.invalid&return_to=//untrusted.invalid")
        assert response.status_code == 200
        return response.get_data(as_text=True), truth
    return render


@pytest.mark.parametrize("plan", ["FREE", "PRO", "ELITE"])
def test_return_journey_does_not_promote_stale_or_conflicting_live_evidence(return_journey, plan):
    for kind in ("live", "halftime", "upcoming", "finished", "suspended", "stale", "conflict", "missing"):
        html, truth = return_journey(kind, plan)
        nav = re.search(r'<nav class="v933-page-actions".*?</nav>', html, re.S).group()
        assert 'href="/calendario"' in nav
        assert ('href="/directo?f=live"' in nav) is truth["is_live"]
        assert 'href="#match-section-shark"' in nav and "Más opciones" in nav
        assert "untrusted.invalid" not in nav
        assert 'data-canonical-live="' + str(truth["is_live"]).lower() + '"' in html


@pytest.mark.parametrize("width", [320, 360, 390, 768, 1440])
def test_return_links_remain_visible_and_keyboard_usable_at_supported_widths(return_journey, width):
    html, _ = return_journey("live")
    with sync_playwright() as pw:
        browser = pw.chromium.launch(executable_path=os.environ.get("NEMESIS_QA_CHROMIUM"))
        context = browser.new_context(viewport={"width": width, "height": 960},
                                      java_script_enabled=False, reduced_motion="reduce")
        page = context.new_page()
        def route(request):
            target = urlsplit(request.request.url)
            if target.netloc != "return-journey.invalid":
                request.abort()
            elif target.path == "/match/return-local":
                request.fulfill(status=200, content_type="text/html; charset=utf-8", body=html)
            elif target.path.startswith("/static/"):
                asset = (ROOT / target.path.lstrip("/")).resolve()
                if asset.is_relative_to(ROOT / "static") and asset.is_file():
                    request.fulfill(status=200, content_type=mimetypes.guess_type(asset.name)[0] or "application/octet-stream", body=asset.read_bytes())
                else:
                    request.fulfill(status=404, body="")
            else:
                request.fulfill(status=200, content_type="text/html; charset=utf-8", body="<h1>Owned local navigation destination</h1>")
        page.route("**/*", route)
        try:
            page.goto("http://return-journey.invalid/match/return-local", wait_until="networkidle")
            nav = page.get_by_role("navigation", name="Acciones del partido", exact=True)
            direct = nav.get_by_role("link", name="Volver a Directo", exact=True)
            calendar = nav.get_by_role("link", name="Volver al Calendario", exact=True)
            for link in (direct, calendar):
                assert link.is_visible()
                bounds = link.bounding_box()
                assert bounds and bounds["width"] > 0 and bounds["x"] >= -1
                assert bounds["x"] + bounds["width"] <= width + 1
            assert page.evaluate("document.documentElement.scrollWidth <= innerWidth + 2")
            direct.focus()
            page.keyboard.press("Tab")
            assert calendar.evaluate("(node) => node === document.activeElement")
            with page.expect_navigation(wait_until="domcontentloaded"):
                page.keyboard.press("Enter")
            assert page.url == "http://return-journey.invalid/calendario"
            page.go_back(wait_until="networkidle")
            with page.expect_navigation(wait_until="domcontentloaded"):
                nav.get_by_role("link", name="Volver a Directo", exact=True).click()
            assert page.url == "http://return-journey.invalid/directo?f=live"
        finally:
            context.close()
            browser.close()
