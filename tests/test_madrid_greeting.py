"""SIMULATED_QA: greetings use the server's Madrid clock and safe display names."""
from datetime import datetime, timezone
from html.parser import HTMLParser
from pathlib import Path

from flask import render_template
from markupsafe import Markup
import pytest

from engines import madrid_time_engine as madrid


class GreetingParser(HTMLParser):
    def __init__(self):
        super().__init__()
        self.headings = []
        self.active = False
        self.parts = []

    def handle_starttag(self, tag, attrs):
        if tag == "h1" and "data-madrid-greeting" in dict(attrs):
            self.active = True
            self.parts = []
        if self.active:
            assert tag not in {"script", "img"}

    def handle_data(self, data):
        if self.active:
            self.parts.append(data)

    def handle_endtag(self, tag):
        if self.active and tag == "h1":
            self.headings.append(" ".join("".join(self.parts).split()))
            self.active = False


@pytest.mark.parametrize("day", ["2026-01-15", "2026-07-15", "2026-03-29", "2026-10-25"])
@pytest.mark.parametrize("clock,expected", [
    ("04:59", "Buenas noches"), ("05:00", "Buenos d\u00edas"),
    ("11:59", "Buenos d\u00edas"), ("12:00", "Buenas tardes"),
    ("19:59", "Buenas tardes"), ("20:00", "Buenas noches"),
    ("23:59", "Buenas noches"), ("00:00", "Buenas noches"),
])
def test_greeting_boundaries_in_madrid_and_utc(day, clock, expected):
    local = datetime.fromisoformat(f"{day}T{clock}").replace(tzinfo=madrid.MADRID_TZ)
    assert madrid.madrid_greeting(now=local)["label"] == expected
    assert madrid.madrid_greeting(now=local.astimezone(timezone.utc))["label"] == expected


@pytest.mark.parametrize("instant,expected", [
    ("2026-03-29T00:59:00Z", "Buenas noches"),
    ("2026-03-29T01:00:00Z", "Buenas noches"),
    ("2026-03-29T02:59:00Z", "Buenas noches"),
    ("2026-03-29T03:00:00Z", "Buenos d\u00edas"),
    ("2026-10-25T00:30:00Z", "Buenas noches"),
    ("2026-10-25T01:30:00Z", "Buenas noches"),
    ("2026-10-25T03:59:00Z", "Buenas noches"),
    ("2026-10-25T04:00:00Z", "Buenos d\u00edas"),
    ("2026-07-15T10:00:00Z", "Buenas tardes"),
    ("2026-01-15T11:00:00Z", "Buenas tardes"),
    ("2026-07-15T18:00:00Z", "Buenas noches"),
    ("2026-07-14T22:00:00Z", "Buenas noches"),
])
def test_greeting_dst_fold_jump_and_utc_date_edges(instant, expected):
    assert madrid.madrid_greeting(now=instant)["label"] == expected


def test_greeting_default_uses_canonical_clock_without_caching(monkeypatch):
    for hour, label in [(11, "Buenos d\u00edas"), (12, "Buenas tardes"), (20, "Buenas noches")]:
        monkeypatch.setattr(madrid, "madrid_now", lambda: datetime(2026, 7, 15, hour, tzinfo=madrid.MADRID_TZ))
        assert madrid.madrid_greeting("Damian")["label"] == label


@pytest.mark.parametrize("name,username,expected", [
    ("Damian", "qa-id", "Damian"), ("  Mar\u00eda   del Mar  ", "qa-id", "Mar\u00eda"),
    ("Anne-Marie", None, "Anne-Marie"), ("O'Connor", None, "O'Connor"),
    (None, "qa-id", ""), ("", "qa-id", ""), ("Cliente SHARK", None, ""),
    ("Admin SHARK", None, ""), ("user_123", None, ""), ("reader", "reader", ""),
    ("Cliente QA", "cliente_qa", ""), ("Admin QA", "admin_qa", ""),
    ("qa@example.invalid", None, ""), ("None", None, ""), ("---", None, ""),
    ("A" * 100, None, ""), ("Damian\u202etext", None, ""),
    (Markup("<img src=x onerror=alert(1)>"), None, ""),
])
def test_greeting_never_falls_back_to_account_identifiers(name, username, expected):
    assert madrid.madrid_greeting(name, username=username)["name"] == expected


@pytest.mark.parametrize("template", ["home.html", "client_app_center.html"])
@pytest.mark.parametrize("name,username,expected", [
    ("Damian", "qa-id", "Buenas tardes, Damian"),
    (None, "qa-id", "Buenas tardes"),
    ("qa@example.invalid", "qa-id", "Buenas tardes"),
    ("Cliente QA", "cliente_qa", "Buenas tardes"),
    (Markup("<script>alert(1)</script>"), "qa-id", "Buenas tardes"),
    ("O'Connor", "qa-id", "Buenas tardes, O'Connor"),
])
def test_real_templates_share_request_greeting_and_escape_names(app_module, monkeypatch, template, name, username, expected):
    user = {"id": "qa-greeting", "name": name, "username": username, "membership": "FREE", "role": "FREE"}
    monkeypatch.setattr(app_module, "current_session_user", lambda: user.copy())
    monkeypatch.setattr(madrid, "madrid_now", lambda: datetime(2026, 7, 15, 12, tzinfo=madrid.MADRID_TZ))
    with app_module.app.test_request_context("/app"):
        html = render_template(template, data={})
    parser = GreetingParser()
    parser.feed(html)
    assert parser.headings == [expected]
    if name == "O'Connor":
        assert "O&#39;Connor" in html


def test_greeting_context_not_shared_between_users_or_times(app_module, monkeypatch):
    state = {"name": "Damian", "username": "qa-first", "hour": 11}
    monkeypatch.setattr(app_module, "current_session_user", lambda: dict(state))
    monkeypatch.setattr(madrid, "madrid_now", lambda: datetime(2026, 7, 15, state["hour"], tzinfo=madrid.MADRID_TZ))
    with app_module.app.test_request_context("/app"):
        assert app_module.inject_session_user()["greeting"] == {"label": "Buenos d\u00edas", "name": "Damian"}
    state.update(name=None, username="qa-second", hour=20)
    with app_module.app.test_request_context("/app"):
        assert app_module.inject_session_user()["greeting"] == {"label": "Buenas noches", "name": ""}


def test_no_template_defines_its_own_time_greeting():
    templates = Path(__file__).resolve().parents[1] / "templates"
    for path in templates.rglob("*.html"):
        text = path.read_text(encoding="utf-8")
        assert not any(label in text for label in ("Buenos d\u00edas", "Buenas tardes", "Buenas noches")), path.name
