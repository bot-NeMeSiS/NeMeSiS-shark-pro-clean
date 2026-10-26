"""Actual guarded Flask routes/login/CSRF/SQLite/quotas; no external providers."""
from html.parser import HTMLParser
import json
import sqlite3
import sys
from datetime import datetime, timedelta, timezone
from zoneinfo import ZoneInfo

import pytest

from test_shark_selected_pick_boundary import shark_probe

# Capture the real read-model entry before the selected-advice fixture installs
# its unrelated empty upstream collection. No application import or bypass.
REAL_PUBLIC_SUMMARY = getattr(sys.modules.get("app"), "get_public_home_sports_summary", None)


class Form(HTMLParser):
    def __init__(self):
        super().__init__()
        self.inside = False
        self.fields = {}
    def handle_starttag(self, tag, attrs):
        attrs = dict(attrs)
        if tag == "form":
            self.inside = attrs.get("action") == "/shark"
        if self.inside and tag == "input" and attrs.get("name"):
            self.fields[attrs["name"]] = attrs.get("value", "")
    def handle_endtag(self, tag):
        if tag == "form":
            self.inside = False


def snapshots(probe):
    with sqlite3.connect(probe["path"]) as conn:
        return [json.loads(row[0]) for row in conn.execute("SELECT payload_json FROM shark_context_snapshots")]


@pytest.mark.parametrize("payload", [[], 2, "question", {}, {"q": " "}, {"question": []}, {"question": {}}, {"question": "a" * 1001}, {"q": "hello", "question": "different"}, {"question": "hello", "match": "a", "match_id": "b"}, {"question": "hello", "pick_id": ["p"]}])
def test_invalid_api_input_is_rejected_before_real_quota_or_snapshot(shark_probe, payload):
    client, csrf = shark_probe["login"]("FREE")
    uid = shark_probe["users"]["FREE"][0]
    before, saved = shark_probe["quota_count"](uid), len(snapshots(shark_probe))
    response = client.post("/api/shark/ask", base_url="http://127.0.0.1", json=payload, headers={"X-CSRF-Token": csrf})
    assert response.status_code == 400, response.get_data(as_text=True)
    assert response.get_json()["quota_consumed"] is False
    assert shark_probe["quota_count"](uid) == before and len(snapshots(shark_probe)) == saved


def test_authorized_pick_derives_its_match_and_saves_once(shark_probe):
    client, csrf = shark_probe["login"]("ELITE")
    uid = shark_probe["users"]["ELITE"][0]
    before, saved = shark_probe["quota_count"](uid), len(snapshots(shark_probe))
    response = client.post("/api/shark/ask", base_url="http://127.0.0.1",
        json={"question": "Explica el pronóstico", "pick": shark_probe["published_pick"]}, headers={"X-CSRF-Token": csrf})
    assert response.status_code == 200
    result = response.get_json()["shark"]
    assert result["context"]["match"]["id"] == shark_probe["published_match"]
    assert result["context"]["pick"]["id"] == shark_probe["published_pick"]
    assert "raw_json" not in result["context"]["pick"]
    assert result["execution_source"] == "LOCAL" and result["external_calls"] == 0
    assert shark_probe["quota_count"](uid) == before + 1 and len(snapshots(shark_probe)) == saved + 1


@pytest.mark.parametrize("surface", ["/api/shark/ask", "/shark", "/shark-ai"])
def test_conflicting_authorized_pick_and_match_never_mix_or_charge(shark_probe, surface):
    client, csrf = shark_probe["login"]("ELITE")
    uid = shark_probe["users"]["ELITE"][0]
    body = {"q": "Explica el pronóstico", "pick_id": shark_probe["published_pick"], "match_id": shark_probe["draft_match"]}
    before, saved = shark_probe["quota_count"](uid), len(snapshots(shark_probe))
    kwargs = {"json": body, "headers": {"X-CSRF-Token": csrf}} if surface.startswith("/api/") else {"data": {**body, "csrf_token": csrf}}
    response = client.post(surface, base_url="http://127.0.0.1", **kwargs)
    assert response.status_code == 400
    assert shark_probe["quota_count"](uid) == before and len(snapshots(shark_probe)) == saved


@pytest.mark.parametrize("path", ["/shark", "/shark-ai"])
@pytest.mark.parametrize("selector", ["pick", "pick_id", "match", "match_id"])
def test_real_full_page_form_preserves_canonical_selection_and_submits_without_js(shark_probe, path, selector):
    client, _ = shark_probe["login"]("ELITE")
    uid = shark_probe["users"]["ELITE"][0]
    target = shark_probe["published_pick" if selector.startswith("pick") else "published_match"]
    before, saved = shark_probe["quota_count"](uid), len(snapshots(shark_probe))
    page = client.get(path, base_url="http://127.0.0.1", query_string={selector: target})
    assert page.status_code == 200
    assert shark_probe["quota_count"](uid) == before and len(snapshots(shark_probe)) == saved
    form = Form(); form.feed(page.get_data(as_text=True))
    assert form.fields["match_id"] == shark_probe["published_match"]
    assert form.fields["pick_id"] == shark_probe["published_pick"] and form.fields["csrf_token"]
    submitted = client.post(path, base_url="http://127.0.0.1", data={**form.fields, "q": "Explica el pronóstico"})
    assert submitted.status_code == 200, submitted.get_data(as_text=True)
    assert shark_probe["published_canary"] in submitted.get_data(as_text=True)
    assert shark_probe["quota_count"](uid) == before + 1 and len(snapshots(shark_probe)) == saved + 1
    context = snapshots(shark_probe)[-1]
    assert context["match"]["id"] == shark_probe["published_match"] and context["pick"]["id"] == shark_probe["published_pick"]


@pytest.mark.parametrize("language,question,expected", [("es", "mi plan", "Tu plan efectivo: FREE"), ("en", "my plan", "Your effective plan: FREE"), ("fr", "mon abonnement", "Votre offre effective : FREE")])
def test_actual_principal_locale_and_postconsumption_allowance_ignore_spoofed_values(shark_probe, language, question, expected):
    client, csrf = shark_probe["login"]("FREE")
    response = client.post("/api/shark/ask", base_url="http://127.0.0.1", headers={"X-CSRF-Token": csrf, "Accept-Language": language},
        json={"q": question, "membership": "ADMIN", "user_id": shark_probe["users"]["ELITE"][0], "locale": "wrong"})
    assert response.status_code == 200
    result = response.get_json()
    assert expected in result["shark"]["answer"] and "1/3" in result["shark"]["answer"]
    assert result["shark"]["context"]["user"]["id"] == shark_probe["users"]["FREE"][0]
    assert result["shark"]["context"]["locale"] == language and result["usage"]["remaining"] == 2


def test_missing_stored_fields_stay_missing_after_actual_normalization(shark_probe):
    with sqlite3.connect(shark_probe["path"]) as conn:
        conn.execute("UPDATE picks SET confidence=NULL,stake_units=NULL,risk_level=NULL WHERE id=?", (shark_probe["published_pick"],))
    client, csrf = shark_probe["login"]("ELITE")
    response = client.post("/api/shark/ask", base_url="http://127.0.0.1", headers={"X-CSRF-Token": csrf},
        json={"question": "pronóstico", "pick_id": shark_probe["published_pick"]})
    assert response.status_code == 200
    answer = response.get_json()["shark"]
    assert "confidence" not in answer["context"]["pick"] and "stake_units" not in answer["context"]["pick"]
    assert answer["context"]["pick"]["risk_level"] == ""
    assert "Stake registrado (unidades): Pendiente" in answer["answer"]


def test_full_page_invalid_question_does_not_charge(shark_probe):
    client, csrf = shark_probe["login"]("FREE")
    uid = shark_probe["users"]["FREE"][0]
    before, saved = shark_probe["quota_count"](uid), len(snapshots(shark_probe))
    response = client.post("/shark", base_url="http://127.0.0.1", data={"q": " ", "csrf_token": csrf})
    assert response.status_code == 400
    assert "No se ha descontado" in response.get_data(as_text=True)
    assert shark_probe["quota_count"](uid) == before and len(snapshots(shark_probe)) == saved


@pytest.mark.parametrize("odds", ["NaN", "Infinity"])
def test_corrupt_numeric_odds_do_not_make_invalid_http_json(shark_probe, odds):
    with sqlite3.connect(shark_probe["path"]) as conn:
        conn.execute("UPDATE picks SET odds=? WHERE id=?", (odds, shark_probe["published_pick"]))
    client, csrf = shark_probe["login"]("ELITE")
    response = client.post("/api/shark/ask", base_url="http://127.0.0.1", headers={"X-CSRF-Token": csrf},
        json={"q": "pronóstico", "pick_id": shark_probe["published_pick"]})
    assert response.status_code == 200
    parsed = json.loads(response.get_data(as_text=True), parse_constant=lambda value: pytest.fail("Non-standard JSON number: " + value))
    assert parsed["shark"]["context"]["pick"]["odds"] is None


def test_unavailable_explicit_advice_is_not_replaced_by_another_allowed_pick(shark_probe):
    with sqlite3.connect(shark_probe["path"]) as conn:
        conn.execute("""INSERT INTO picks(id,match_id,home_team,away_team,status,membership_required,reasoning,odds)
                        SELECT 'qa-other-pro',match_id,home_team,away_team,'published','PRO','QA_OTHER_ALLOWED_PICK',odds FROM picks WHERE id=?""", (shark_probe["published_pick"],))
    client, csrf = shark_probe["login"]("PRO")
    response = client.post("/api/shark/ask", base_url="http://127.0.0.1", headers={"X-CSRF-Token": csrf},
        json={"q": "pronóstico", "pick_id": shark_probe["published_pick"], "match_id": shark_probe["published_match"]})
    assert response.status_code == 200
    assert not response.get_json()["shark"]["context"]["pick"]
    assert "QA_OTHER_ALLOWED_PICK" not in response.get_json()["shark"]["answer"]


@pytest.fixture
def prepared_probe(shark_probe, monkeypatch):
    """Real prepared fixture snapshot over this owned store; real clock only."""
    a = shark_probe["a"]
    assert REAL_PUBLIC_SUMMARY is not None, "Run via the original LOCAL SAFE supervisor"
    monkeypatch.setattr(a, "get_public_home_sports_summary", REAL_PUBLIC_SUMMARY)
    now = datetime.now(timezone.utc)
    kickoff = now - timedelta(minutes=55)
    with sqlite3.connect(shark_probe["path"]) as conn:
        columns = {row[1] for row in conn.execute("PRAGMA table_info(matches)")}
        for number, state, observation in ((99990001, "2H", now), (99990002, "NS", now), (99990003, "2H", now - timedelta(hours=2))):
            start = now + timedelta(hours=3) if state == "NS" else kickoff
            local = start.astimezone(ZoneInfo("Europe/Madrid"))
            record = {"id": "af-" + str(number), "external_id": str(number), "sport_key": "soccer", "home_team": "Club Norte QA", "away_team": "Club Sur QA",
                "home_team_id": "99911", "away_team_id": "99912", "competition_id": "140", "competition_key": "laliga", "competition_name": "LaLiga", "league_name": "LaLiga",
                "country": "Spain", "season": str(local.year), "match_date": local.date().isoformat(), "kickoff_iso": start.isoformat(), "kickoff_time": local.strftime("%H:%M"),
                "status": state, "minute": "55" if state == "2H" else "", "home_score": 0 if state == "2H" else None, "away_score": 0 if state == "2H" else None,
                "score": "0-0" if state == "2H" else "", "source": "api_football_cache", "updated_at": observation.isoformat(), "last_synced_at": observation.isoformat(),
                "raw_json": json.dumps({"fixture": {"id": number, "date": start.isoformat(), "status": {"short": state, "elapsed": 55 if state == "2H" else None}},
                    "league": {"id": 140, "name": "LaLiga", "country": "Spain", "season": local.year},
                    "teams": {"home": {"id": 99911, "name": "Club Norte QA"}, "away": {"id": 99912, "name": "Club Sur QA"}}, "goals": {"home": 0, "away": 0}, "qa_origin": "SIMULATED_QA"})}
            record = {key: value for key, value in record.items() if key in columns}
            conn.execute("INSERT INTO matches(" + ",".join(record) + ") VALUES(" + ",".join("?" for _ in record) + ")", tuple(record.values()))
        conn.execute("INSERT INTO teams(key,name,country,external_id,source) VALUES('qa-favorite-ref','Club Norte QA','Spain','99911','api-football')")
        conn.execute("INSERT INTO favorites(id,user_id,kind,value,created_at) VALUES('qa-team-fav',?,'team','@team:qa-favorite-ref',?)", (shark_probe["users"]["FREE"][0], now.isoformat()))
        conn.execute("INSERT INTO favorites(id,user_id,kind,value,created_at) VALUES('qa-match-fav',?,'match','af-99990002',?)", (shark_probe["users"]["PRO"][0], now.isoformat()))
    return shark_probe


def test_real_prepared_live_excludes_stale_and_preserves_zero(prepared_probe):
    client, csrf = prepared_probe["login"]("ELITE")
    response = client.post("/api/shark/ask", base_url="http://127.0.0.1", headers={"X-CSRF-Token": csrf}, json={"q": "directo"})
    assert response.status_code == 200
    result = response.get_json()["shark"]
    live = result["context"]["collections"]["live"]
    assert live["state"] == "AVAILABLE", live
    assert "af-99990001" in {item["id"] for item in live["matches"]}
    assert "af-99990003" not in {item["id"] for item in live["matches"]}
    assert "0–0" in result["answer"] and "55" in result["answer"]


def test_real_prepared_favorites_are_owned_and_resolve_team_references(prepared_probe):
    answers = {}
    for plan in ("FREE", "PRO", "ELITE"):
        client, csrf = prepared_probe["login"](plan)
        response = client.post("/api/shark/ask", base_url="http://127.0.0.1", headers={"X-CSRF-Token": csrf}, json={"q": "favoritos", "user_id": prepared_probe["users"]["FREE"][0]})
        assert response.status_code == 200
        answers[plan] = response.get_json()["shark"]["context"]["collections"]["favorites"]
    assert answers["FREE"]["state"] == "AVAILABLE" and answers["FREE"]["saved_count"] == 1
    assert "af-99990001" in {item["id"] for item in answers["FREE"]["matches"]}
    assert answers["PRO"]["state"] == "AVAILABLE" and answers["PRO"]["saved_count"] == 1
    assert {item["id"] for item in answers["PRO"]["matches"]} == {"af-99990002"}
    assert answers["ELITE"] == {"state": "EMPTY", "matches": [], "total": 0, "saved_count": 0}


def test_mutated_prepared_cohort_does_not_invent_a_live_total(prepared_probe, monkeypatch):
    a = prepared_probe["a"]
    def changed_cohort():
        summary = REAL_PUBLIC_SUMMARY()
        assert summary.get("all_valid_matches"), "Actual owned fixture rows must be present"
        # Deliberate local fault injection after genuine preparation: the second
        # object duplicates a local action ID and has no retained owner proof.
        duplicate = dict(summary["all_valid_matches"][0])
        summary["all_valid_matches"].append(duplicate)
        return summary
    monkeypatch.setattr(a, "get_public_home_sports_summary", changed_cohort)
    client, csrf = prepared_probe["login"]("ELITE")
    response = client.post("/api/shark/ask", base_url="http://127.0.0.1", headers={"X-CSRF-Token": csrf}, json={"q": "directo"})
    assert response.status_code == 200
    live = response.get_json()["shark"]["context"]["collections"]["live"]
    assert live["state"] == "UNAVAILABLE" and live["total"] is None
