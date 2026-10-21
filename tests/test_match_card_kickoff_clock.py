from html.parser import HTMLParser

import pytest


class MatchCardState(HTMLParser):
    def __init__(self):
        super().__init__()
        self.card = {}
        self.score_hidden = None
        self.score_parts = []
        self.kickoff_parts = []
        self._in_score = False
        self._in_kickoff = False

    def handle_starttag(self, tag, attrs):
        attrs = dict(attrs)
        if tag == "article" and "data-v934-match-card" in attrs:
            self.card = attrs
        if tag == "b" and "data-v934-score" in attrs:
            self.score_hidden = "hidden" in attrs
            self._in_score = True
        if tag == "time" and "data-match-kickoff-clock" in attrs:
            self._in_kickoff = True

    def handle_endtag(self, tag):
        if tag == "b":
            self._in_score = False
        elif tag == "time":
            self._in_kickoff = False

    def handle_data(self, data):
        if self._in_score:
            self.score_parts.append(data)
        if self._in_kickoff:
            self.kickoff_parts.append(data)


def _render_card(app_module, *, state="UPCOMING", home_score=None, away_score=None):
    match = {
        "id": "calendar-kickoff-qa",
        "home_team": "Local QA",
        "away_team": "Visitante QA",
        "competition_name": "Liga QA",
        "source": "SIMULATED_QA",
        "calendar_time": "21:00",
        "calendar_datetime_label": "22/10/2026 21:00",
        "client_schedule_label": "22/10/2026 21:00",
        "madrid_dt_iso": "2026-10-22T21:00:00+02:00",
        "status_info": {
            "key": state,
            "is_live": state == "LIVE",
            "is_finished": state == "FINISHED",
            "is_upcoming": state == "UPCOMING",
        },
        "home_score": home_score,
        "away_score": away_score,
    }
    with app_module.app.test_request_context("/calendario"):
        template = app_module.app.jinja_env.from_string(
            "{% from 'components/v933_ui.html' import match_card with context %}"
            "{{ match_card(match, false, false) }}"
        )
        html = template.render(match=match, current_user=None)
    parser = MatchCardState()
    parser.feed(html)
    return parser


@pytest.mark.parametrize(("home_score", "away_score"), [("", ""), ("  ", None)])
def test_upcoming_card_keeps_kickoff_when_provider_scores_are_blank(
        app_module, home_score, away_score):
    card = _render_card(app_module, home_score=home_score, away_score=away_score)

    assert card.card["data-canonical-status"] == "UPCOMING"
    assert card.score_hidden is True
    assert "".join(card.kickoff_parts) == "21:00"


@pytest.mark.parametrize(("home_score", "away_score", "expected"), [
    (0, 0, "0 - 0"),
    ("0", "0", "0 - 0"),
    (2, None, "2 - —"),
    (None, 1, "— - 1"),
])
def test_real_zero_and_partial_scores_remain_visible_without_kickoff(
        app_module, home_score, away_score, expected):
    card = _render_card(app_module, home_score=home_score, away_score=away_score)

    assert card.card["data-canonical-status"] == "UPCOMING"
    assert card.score_hidden is False
    assert "".join(card.score_parts) == expected
    assert card.kickoff_parts == []


@pytest.mark.parametrize(("state", "home_score", "away_score", "expected_live"), [
    ("LIVE", 1, 0, "true"),
    ("FINISHED", 0, 0, "false"),
])
def test_live_and_finished_cards_keep_canonical_state(
        app_module, state, home_score, away_score, expected_live):
    card = _render_card(
        app_module, state=state, home_score=home_score, away_score=away_score)

    assert card.card["data-canonical-status"] == state
    assert card.card["data-canonical-live"] == expected_live
    assert card.score_hidden is False
    assert card.kickoff_parts == []
