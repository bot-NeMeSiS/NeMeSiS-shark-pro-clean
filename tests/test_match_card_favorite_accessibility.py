from html.parser import HTMLParser


class FavoriteButton(HTMLParser):
    def __init__(self):
        super().__init__()
        self.attrs = None

    def handle_starttag(self, tag, attrs):
        values = dict(attrs)
        if tag == "button" and "fav-star" in values.get("class", ""):
            self.attrs = values


def _render_match_card(app_module, *, is_favorite):
    match = {
        "id": "favorite-accessibility-qa",
        "home_team": "Local QA",
        "away_team": "Visitante QA",
        "competition_name": "Liga QA",
        "kickoff_time": "20:30",
        "source": "SIMULATED_QA",
        "is_favorite": is_favorite,
    }
    with app_module.app.test_request_context("/"):
        template = app_module.app.jinja_env.from_string(
            "{% from 'components/v933_ui.html' import match_card with context %}"
            "{{ match_card(match, true, false) }}"
        )
        return template.render(match=match, current_user=object())


def test_favorite_button_names_match_the_saved_state(app_module):
    for saved, expected_label, expected_pressed in (
        (False, "Guardar favorito", "false"),
        (True, "Quitar favorito", "true"),
    ):
        parser = FavoriteButton()
        parser.feed(_render_match_card(app_module, is_favorite=saved))

        assert parser.attrs is not None
        assert parser.attrs["aria-label"] == "Favorito"
        assert parser.attrs["title"] == expected_label
        assert parser.attrs["aria-pressed"] == expected_pressed
        assert parser.attrs["data-label-add"] == "Guardar favorito"
        assert parser.attrs["data-label-remove"] == "Quitar favorito"


def test_favorite_toggle_updates_the_accessible_name_only_after_success():
    from pathlib import Path

    base = Path(__file__).resolve().parents[1] / "templates" / "base.html"
    source = base.read_text(encoding="utf-8")

    assert "if(data.ok!==false){" in source
    assert "btn.setAttribute('aria-pressed',nextActive.toString());" in source
    assert "const nextLabel=nextActive ? btn.dataset.labelRemove : btn.dataset.labelAdd;" in source
    assert "if(nextLabel) btn.title=nextLabel;" in source
