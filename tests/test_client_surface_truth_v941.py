"""Current client surfaces, canonical routes and QA guard truth."""
from pathlib import Path

from engines.client_experience_guard_engine import client_experience_snapshot

ROOT = Path(__file__).resolve().parents[1]


def test_client_experience_guard_tracks_current_product_surfaces():
    snapshot = client_experience_snapshot(ROOT)
    by_route = {item["route"]: item for item in snapshot["critical_screens"]}
    assert "/dashboard" not in by_route
    assert by_route["/app"]["template"] == "client_app_center.html"
    assert by_route["/track-record"]["template"] == "track_record.html"
    assert by_route["/profile"]["template"] == "profile.html"
    assert by_route["/membresias"]["template"] == "membership.html"
    assert all(item["exists"] and item["time_status_ok"] for item in snapshot["critical_screens"])
    assert snapshot["status"] == "OK"
    assert snapshot["score"] == 100


def test_client_templates_use_spanish_canonical_support_and_plan_routes():
    names = (
        "templates/profile.html",
        "templates/company_platform.html",
        "templates/components/platform_faq.html",
        "templates/home.html",
        "templates/recommendations.html",
    )
    combined = "\n".join((ROOT / name).read_text(encoding="utf-8") for name in names)
    assert "'/memberships'" not in combined
    assert "'/support'" not in combined
    assert "'/membresias'" in combined
    assert "'/soporte'" in combined


def test_secondary_client_copy_uses_current_spanish_vocabulary():
    sports=(ROOT / "templates/sports_hub.html").read_text(encoding="utf-8")
    favorites=(ROOT / "templates/favorites.html").read_text(encoding="utf-8")
    recommendations=(ROOT / "templates/recommendations.html").read_text(encoding="utf-8")
    for forbidden in (">Picks</a>", "<span>Picks</span>", "<span>Combis</span>", "calendario o picks"):
        assert forbidden not in sports
    assert "Pronósticos" in sports and "Combinadas" in sports
    for forbidden in ("Sports Hub, Live, Calendar", "Live relacionados", "Picks relacionados", "Pick SHARK"):
        assert forbidden not in favorites
    assert "Centro deportivo, Directo, Calendario" in favorites
    assert "Pronósticos relacionados" in favorites
    assert "Picks publicados" not in recommendations
    assert "Pronósticos publicados" in recommendations


def test_confirmed_orphan_legacy_templates_stay_purged():
    for name in ("client_progress.html", "product_audit.html", "admin_autonomous_ecosystem.html"):
        assert not (ROOT / "templates" / name).exists()
