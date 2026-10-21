from pathlib import Path
import mimetypes
import os
from urllib.parse import urlsplit

import pytest
from playwright.sync_api import sync_playwright


ROOT = Path(__file__).resolve().parents[1]


def _detail():
    match = {
        "id": "v944-match-1",
        "home_team": "Real Club Deportivo Local",
        "away_team": "Unión Deportiva Visitante",
        "competition_name": "Competición de prueba local",
        "competition_key": "test-local",
        "match_date": "2026-07-23",
        "kickoff_time": "20:30",
        "kickoff_iso": "2026-07-23T20:30:00+02:00",
        "status": "upcoming",
        "source": "fixture-local",
        "updated_at": "2026-07-23T19:45:00+02:00",
        "status_info": {
            "key": "UPCOMING", "label": "Próximo", "is_finished": False,
            "is_live": False, "is_upcoming": True,
        },
        "live_depth": {"state": "UPCOMING", "label": "Próximo", "minute": "20:30"},
        "home_identity": {"crest_url": "/team-crest.svg?name=Local"},
        "away_identity": {"crest_url": "/team-crest.svg?name=Visitante"},
    }
    return {
        "id": match["id"],
        "match": match,
        "favorite": True,
        "timeline": [{
            "minute": "20:30", "event_type": "state", "title": "Partido programado",
            "detail": "Estado confirmado en la fuente local.",
        }],
        "related_picks": [],
        "state": {"state": "UPCOMING", "shark_momentum": {"stats_available": False}},
        "statistics": {"items": []},
    }


@pytest.mark.parametrize("width,height", [(390, 844), (1440, 960)])
def test_recent_team_results_use_the_full_match_context_width_in_browser(
    client, app_module, monkeypatch, width, height,
):
    fixture = _detail()
    monkeypatch.setattr(app_module, "match_detail", lambda *_a, **_k: fixture)
    monkeypatch.setattr(app_module, "v935_enrich_match_lifecycle", lambda match: match)
    monkeypatch.setattr(app_module, "admin_operational_settings", lambda: {
        "settings_readable": True, "highlights_enabled": True,
    })

    def recent_form(team, **_kwargs):
        return {
            "contract": "NEMESIS-MATCH-RECENT-FORM-CACHE-V1",
            "available": True,
            "team": team,
            "matches": [{
                "match_id": "past-local-1", "href": "/match/past-local-1",
                "home_team": team, "away_team": "Club Visitante",
                "home_score": 2, "away_score": 1, "score": "2-1",
                "status": "FT", "form_result": "W", "match_date": "2026-07-20",
                "kickoff_iso": "2026-07-20T20:00:00+02:00", "source": "synthetic-test",
                "competition_identity": {"name": "Liga de prueba"},
            }],
            "form": ["W"], "sample_size": 1, "external_calls": 0,
        }

    monkeypatch.setattr(app_module, "recent_team_form", recent_form)
    monkeypatch.setattr(app_module, "sportsdb_highlights_for_match", lambda *_a: {
        "ok": True, "read_state": "VERIFIED", "highlights": [],
        "all_highlights": [], "candidate_sampled": 0,
    })
    monkeypatch.setattr(app_module, "v766_highlight_map_snapshot", lambda ids, **_kwargs: {
        "ok": True, "read_state": "VERIFIED", "map": {},
    })

    response = client.get("/match/v944-match-1")
    assert response.status_code == 200
    html = response.data
    assert b'data-recent-form-contract="NEMESIS-MATCH-RECENT-FORM-CACHE-V1"' in html

    with sync_playwright() as pw:
        browser = pw.chromium.launch(executable_path=os.environ.get("NEMESIS_QA_CHROMIUM"))
        context = browser.new_context(viewport={"width": width, "height": height}, java_script_enabled=False)
        page = context.new_page()

        def route(request):
            parsed = urlsplit(request.request.url)
            if parsed.netloc != "match-center-qa.invalid":
                request.abort()
                return
            if parsed.path == "/match/v944-match-1":
                request.fulfill(status=200, content_type="text/html; charset=utf-8", body=html)
                return
            if parsed.path.startswith("/static/"):
                asset = (ROOT / parsed.path.lstrip("/")).resolve()
                if not asset.is_relative_to(ROOT / "static") or not asset.is_file():
                    request.fulfill(status=404, body="Missing asset")
                    return
                request.fulfill(
                    status=200,
                    content_type=mimetypes.guess_type(parsed.path)[0] or "application/octet-stream",
                    body=asset.read_bytes(),
                )
                return
            request.fulfill(status=404, content_type="text/plain; charset=utf-8", body="")

        page.route("**/*", route)
        try:
            navigation = page.goto("http://match-center-qa.invalid/match/v944-match-1", wait_until="networkidle")
            assert navigation.status == 200
            rows = page.locator(".v944-context-list[data-recent-form-contract] > div")
            assert rows.count() == 2
            for row_index in range(2):
                row_locator = rows.nth(row_index)
                row_box = row_locator.bounding_box()
                list_locator = row_locator.locator(".v944-recent-results")
                list_box = list_locator.bounding_box()
                assert row_box and list_box
                assert list_box["width"] >= row_box["width"] * 0.85
                note = row_locator.locator("small.muted")
                assert note.is_visible()
                assert note.locator("xpath=..").bounding_box()["width"] >= row_box["width"] * 0.85
                assert row_locator.locator('a[href="/match/past-local-1"]').count() == 1
            assert page.locator(".v944-context-list[data-recent-form-contract]").inner_text().count(
                "Solo se enlazan vídeos con permisos de publicación verificados."
            ) == 2
            assert page.evaluate("document.documentElement.scrollWidth <= innerWidth + 2")
        finally:
            context.close()
            browser.close()
