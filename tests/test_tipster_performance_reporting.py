"""Truthful tipster KPI labels: missing data never becomes a fictitious 0%."""
from pathlib import Path

from jinja2 import DictLoader, Environment

_SOURCE = Path(__file__).resolve().parents[1] / "templates" / "admin_pick_performance.html"


def _render(stats):
    env = Environment(loader=DictLoader({
        "base.html": "{% block content %}{% endblock %}",
        "admin_pick_performance.html": _SOURCE.read_text(encoding="utf-8"),
    }), autoescape=True)
    return env.get_template("admin_pick_performance.html").render(
        data={"pick_stats": stats, "global_tracking": [], "bankroll_users": []}
    )


def test_missing_metrics_are_not_fake_zero_percent():
    html = _render({"published": 0})
    assert "Picks publicados</span><strong>0</strong>" in html
    assert "Winrate</span><strong>Sin muestra evaluable</strong>" in html
    assert "ROI</span><strong>Sin muestra evaluable</strong>" in html
    assert "ROI</span><strong>0%" not in html


def test_recorded_zero_is_distinct_from_missing():
    html = _render({"published": 12, "winrate": 0, "roi": 0.0})
    assert "Winrate</span><strong>0%" in html
    assert "ROI</span><strong>0.0%" in html


def test_recorded_negative_roi_remains_visible():
    html = _render({"published": 10, "winrate": 40, "roi": -8.75})
    assert "ROI</span><strong>-8.75%" in html

def test_tipster_roi_copy_does_not_claim_real_wagers():
    html = _render({"published": 2, "winrate": 50, "roi": 0})
    assert "no acredita apuestas efectivamente realizadas" in html
    assert "no garantiza rentabilidad futura" in html
    assert "realmente arriesgadas" not in html
