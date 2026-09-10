from __future__ import annotations

from pathlib import Path

from flask import render_template

from engines.autonomous_product_qa_engine import (
    PINNED_REGRESSION_CONTRACTS,
    QA_EXECUTION_POLICY,
    build_quality_director_decision,
    build_autonomous_product_qa_status,
    detect_product_qa_issues,
    _regression_result_defaults,
    evaluate_production_sentinel,
    load_product_qa_memory,
    product_qa_review_findings,
    record_product_qa_run,
    set_product_qa_pause,
)
from engines.sentinel_issues_engine import (
    ISSUE_STATUSES,
    build_sentinel_issues_summary,
    canonicalize_sentinel_memory,
    normalize_sentinel_issue,
    reconcile_autonomous_workforce_evidence,
    upsert_sentinel_issues,
)
from engines.sentinel_codex_outbox_engine import write_codex_outbox
from engines.shark_sentinel_engine import _inspect_html, build_codex_prompts
from tools.run_autonomous_product_qa import (
    _apply_data_scenario,
    _cross_surface_competition_identity_evidence,
    _cross_surface_live_truth_evidence,
    _mobile_navigation_journey,
    _sports_golden_journey,
    _reference_crop_box,
    _reference_manifest_map,
    _shark_asset_contract,
    _shark_asset_contract_from_text,
    _sports_priority_regression,
)


def test_mobile_navigation_journey_uses_the_selected_mobile_viewport():
    clicks = [
        {
            "viewport": "mobile_430x932",
            "element": "Inicio",
            "expected_path": "/app",
            "actual_path": "/app",
            "clicked": True,
            "hit_target": True,
        },
        {
            "viewport": "mobile_430x932",
            "element": "Partidos",
            "expected_path": "/calendar",
            "actual_path": "/calendar",
            "clicked": True,
            "hit_target": True,
        },
    ]

    journey = _mobile_navigation_journey(clicks, "mobile_430x932")

    assert journey["pass"] is True
    assert journey["steps_total"] == 2
    assert journey["viewport"] == "mobile_430x932"


def test_mobile_navigation_journey_keeps_real_tap_failures_visible():
    clicks = [{
        "viewport": "mobile_430x932",
        "element": "Partidos",
        "expected_path": "/calendar",
        "actual_path": "/app",
        "clicked": True,
        "hit_target": True,
    }]

    journey = _mobile_navigation_journey(clicks, "mobile_430x932")

    assert journey["pass"] is False
    assert journey["actual"] == "FAILED_STEP"


def test_populated_visual_scenario_seeds_publishable_and_graded_pick_contracts(tmp_path: Path):
    import sqlite3
    from datetime import datetime
    from zoneinfo import ZoneInfo

    db_path = tmp_path / "visual-scenario.sqlite"
    with sqlite3.connect(db_path) as connection:
        connection.execute(
            """CREATE TABLE matches(
                id TEXT PRIMARY KEY, external_id TEXT, match_date TEXT, kickoff_iso TEXT,
                kickoff_time TEXT, match_time TEXT, home_team TEXT, away_team TEXT,
                home_team_id TEXT, away_team_id TEXT, home_logo TEXT, away_logo TEXT,
                status TEXT, minute TEXT, score TEXT, home_score TEXT, away_score TEXT,
                source TEXT, legal_note TEXT, last_synced_at TEXT, updated_at TEXT
            )"""
        )
        connection.execute(
            "INSERT INTO matches VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)",
            (
                "m-2", "m-2", "2026-09-08", "2026-09-08T20:30:00+02:00",
                "20:30", "20:30", "Club Este", "Club Oeste", "club-este", "club-oeste",
                "", "", "NS", None, "", None, None, "SIMULATED_QA", "Fixture aislado",
                None, "2026-09-07T12:00:00+02:00",
            ),
        )
        connection.execute(
            """CREATE TABLE picks(
                id TEXT PRIMARY KEY,match_id TEXT,match_date TEXT,sport_key TEXT,
                competition_key TEXT,competition_name TEXT,home_team TEXT,away_team TEXT,
                pick_type TEXT,selection TEXT,odds REAL,confidence INTEGER,stake_units REAL,
                status TEXT,source TEXT,legal_note TEXT,reasoning TEXT,raw_json TEXT,
                created_at TEXT,updated_at TEXT,market TEXT,bookmaker TEXT,
                stake_euros_example REAL,risk_level TEXT,warning_reason TEXT,
                membership_required TEXT,result_status TEXT,published_at TEXT
            )"""
        )

    _apply_data_scenario(
        db_path,
        "populated",
        datetime(2026, 9, 7, 12, 0, tzinfo=ZoneInfo("Europe/Madrid")),
    )

    with sqlite3.connect(db_path) as connection:
        published = connection.execute(
            "SELECT match_id,status,result_status,market,odds FROM picks WHERE id=?",
            ("pick-visual-qa-published",),
        ).fetchone()
        grading = connection.execute(
            "SELECT result_status,odds,stake,profit,auto_validated FROM pick_grading_results WHERE id=?",
            ("grading-visual-qa-won",),
        ).fetchone()
        run = connection.execute(
            "SELECT status,picks_checked,auto_validated FROM pick_grading_runs WHERE id=?",
            ("grading-run-visual-qa",),
        ).fetchone()

    assert published == ("m-3", "published", "pending", "Resultado final", 1.82)
    assert grading == ("won", 1.82, 1.0, 0.82, 1)
    assert run == ("completed", 1, 1)


def test_live_visual_inspector_counts_visible_canonical_match_ids_before_kpi_copy():
    source = Path(__file__).resolve().parents[1].joinpath("tools", "run_autonomous_product_qa.py").read_text(encoding="utf-8")

    assert "visibleLiveIds" in source
    assert 'data-canonical-live="true"' in source
    assert "if (visibleLiveIds.size) return visibleLiveIds.size" in source


def test_track_record_uses_compact_mobile_results_instead_of_squeezing_seven_columns():
    project_root = Path(__file__).resolve().parents[1]
    template = project_root.joinpath("templates", "track_record.html").read_text(encoding="utf-8")
    css = project_root.joinpath("static", "v933-product.css").read_text(encoding="utf-8")

    assert "ns16-track-mobile-list" in template
    assert "ns16-track-result-evidence" in template
    assert ".ns16-track-recent > .v933-table-shell { display: none; }" in css
    assert ".ns16-track-recent .ns16-track-mobile-list { display: grid;" in css


def test_telegram_mobile_status_contract_uses_compact_rectangular_tiles():
    css = Path(__file__).resolve().parents[1].joinpath("static", "v933-product.css").read_text(encoding="utf-8")

    selector = "body.ns-app .v933-telegram-page > .ns-video-status-rail"
    child_selector = selector + " > .v933-kpi"
    assert selector in css
    assert child_selector in css
    assert "border-radius: 0 !important;" in css
    assert "border-radius: 6px !important;" in css


def test_sparse_sports_golden_journey_keeps_honest_optional_data_contract():
    source = Path(__file__).resolve().parents[1].joinpath("tools", "run_autonomous_product_qa.py").read_text(encoding="utf-8")

    assert _sports_golden_journey.__defaults__ == ("populated",)
    assert 'enrichment_contract = "STRICT_ENRICHED_DATA"' in source
    assert 'enrichment_contract = "HONEST_OPTIONAL_DATA"' in source
    assert '_optional_section_journey(page, base_url + "/match/m-1", "lineups")' in source
    assert '_optional_section_journey(page, base_url + "/match/m-1", "stats")' in source
    assert '_optional_section_journey(page, base_url + "/match/m-1", "video")' in source


def test_daily_policy_includes_sports_knowledge_summary_media_rights_and_time():
    checks = set(QA_EXECUTION_POLICY["daily"]["checks"])
    assert {"sports_knowledge", "summary_truth", "media_rights", "temporal_context"} <= checks


def test_sports_priority_regression_uses_canonical_ranking_without_external_calls(app_module):
    result = _sports_priority_regression(app_module)
    order = result["order"]
    assert result["status"] == "PASS"
    assert result["external_calls"] == 0
    for important in ("bayern-stuttgart", "lille-psg", "milan-venezia"):
        assert order.index(important) < order.index("k-league-2")
        assert order.index(important) < order.index("chinese-super-league")


def test_cross_surface_live_truth_worker_compares_same_canonical_match():
    clean = _cross_surface_live_truth_evidence([
        {"key": "home", "match_truth": [{"match_id": "m-1", "canonical_status": "STALE", "is_live": False}]},
        {"key": "directo", "match_truth": [{"match_id": "m-1", "canonical_status": "STALE", "is_live": False}]},
        {"key": "match", "match_truth": [{"match_id": "m-1", "canonical_status": "STALE", "is_live": False}]},
    ])
    mismatch = _cross_surface_live_truth_evidence([
        {"key": "home", "match_truth": [{"match_id": "m-1", "canonical_status": "LIVE", "is_live": True}]},
        {"key": "directo", "match_truth": [{"match_id": "m-1", "canonical_status": "STALE", "is_live": False}]},
    ])

    assert clean == {"observed": True, "pass": True, "matches_compared": 1, "mismatches": []}
    assert mismatch["observed"] is True
    assert mismatch["pass"] is False
    assert mismatch["mismatches"][0]["match_id"] == "m-1"


def test_cross_surface_competition_identity_compares_provider_backed_ids():
    clean = _cross_surface_competition_identity_evidence([
        {"key": "home", "competition_truth": [{"match_id": "m-1", "competition_id": "thesportsdb-api-competition-4400"}]},
        {"key": "partidos", "competition_truth": [{"match_id": "m-1", "competition_id": "thesportsdb-api-competition-4400"}]},
        {"key": "match", "competition_truth": [{"match_id": "m-1", "competition_id": "thesportsdb-api-competition-4400"}]},
    ])
    mismatch = _cross_surface_competition_identity_evidence([
        {"key": "home", "competition_truth": [{"match_id": "m-1", "competition_id": "thesportsdb-api-competition-4335"}]},
        {"key": "partidos", "competition_truth": [{"match_id": "m-1", "competition_id": "thesportsdb-api-competition-4400"}]},
    ])

    assert clean == {"observed": True, "pass": True, "matches_compared": 1, "mismatches": []}
    assert mismatch["pass"] is False
    assert mismatch["mismatches"][0]["match_id"] == "m-1"


def test_focused_pass_without_cross_surface_identity_does_not_open_false_p0():
    observation = clean_observation()
    observation["competition_identity"] = {
        "observed": False,
        "pass": None,
        "matches_compared": 0,
        "mismatches": [],
    }
    observation["temporal_context"] = {
        "observed": False,
        "checked_cards": 2,
        "missing_cards": 0,
        "ambiguous_cards": 0,
        "cross_surface_consistent": False,
        "madrid_time": True,
    }
    observation["visual"] = {
        "shark": {"observed": False, "classification": "NOT_OBSERVED"},
        "background": {"observed": False, "classification": "NOT_OBSERVED"},
    }
    observation["density"] = {
        "observed": False,
        "first_viewport_product": None,
        "sports_above_fold_ratio": 0,
    }

    issues = detect_product_qa_issues(observation)

    assert not any(issue["category"] == "COMPETITION_IDENTITY" for issue in issues)
    assert not any(issue["category"] == "TEMPORAL_CONTEXT" for issue in issues)
    assert not any(issue["category"] in {"VISUAL_SHARK", "VISUAL_BACKGROUND", "UI_DENSITY"} for issue in issues)


def test_unobserved_focused_contracts_remain_not_run_without_masking_real_failures():
    observation = clean_observation()
    observation["sports_truth"]["cross_surface_live_truth"] = None
    observation["sports_truth"]["cross_surface_live_mismatches"] = []
    observation["density"] = {"observed": False}
    observation["temporal_context"] = {"observed": False}
    observation["security"] = {"client_admin_separation": "NOT_RUN"}

    results = _regression_result_defaults(observation)

    assert results["CROSS_SURFACE_LIVE_TRUTH"]["status"] == "NOT_RUN"
    assert results["RECTANGLE_FATIGUE_CONTENT_DENSITY"]["status"] == "NOT_RUN"
    assert results["SPORTS_ABOVE_FOLD_RATIO"]["status"] == "NOT_RUN"
    assert results["TEMPORAL_CONTEXT_CONSISTENCY"]["status"] == "NOT_RUN"
    assert results["CLIENT_ADMIN_SEPARATION"]["status"] == "NOT_RUN"

    observation["security"] = {"client_admin_separation": "FAIL"}
    assert _regression_result_defaults(observation)["CLIENT_ADMIN_SEPARATION"]["status"] == "FAIL"


def test_layout_collision_evidence_opens_real_visual_issue():
    observation = clean_observation()
    observation["layout_collisions"] = [{
        "type": "text_border_collision",
        "screen": "/profile",
        "viewport": "mobile_360x800",
        "element": "button.v933-action",
        "actual": "text bounds escape element bounds",
        "evidence": "Configuración de notificaciones toca el borde derecho.",
    }]

    issues = detect_product_qa_issues(observation)

    issue = next(item for item in issues if item["category"] == "LAYOUT_COLLISION")
    assert issue["severity"] == "P1"
    assert issue["worker"] == "visual_experience_inspector"
    assert PINNED_REGRESSION_CONTRACTS["NO_TEXT_BORDER_COLLISION"]["severity"] == "P1"
    assert PINNED_REGRESSION_CONTRACTS["MOBILE_360_LAYOUT"]["test"] == "mobile_360_collision_and_overflow_scan"


def test_home_dense_match_cards_use_the_active_home_container():
    project_root = Path(__file__).resolve().parents[1]
    template = (project_root / "templates" / "home.html").read_text(encoding="utf-8")
    css = (project_root / "static" / "v933-product.css").read_text(encoding="utf-8")

    assert "sports-priority-home" in template
    rule = next(line for line in css.splitlines()
                if line.startswith(".sports-priority-home .v933-match-card :is("))
    assert ".v937-confidence-badge" in rule
    assert ".v937-card-trust" not in rule  # Its sibling time must remain visible.


def test_brand_shark_cache_version_is_consistent_across_active_surfaces():
    project_root = Path(__file__).resolve().parents[1]
    paths = [
        project_root / "app.py",
        project_root / "static" / "app.css",
        project_root / "templates" / "base.html",
        project_root / "templates" / "admin_navigation_map.html",
        project_root / "templates" / "admin_telegram_pro_preview.html",
        project_root / "templates" / "client_navigation_map.html",
        project_root / "templates" / "partials" / "brand_logo.html",
    ]
    active_sources = "\n".join(path.read_text(encoding="utf-8") for path in paths)

    assert "design1-brand-3" not in active_sources
    assert "nemesis-shark-brand.svg?v=design2-brand-1" in active_sources


def test_visual_inspector_rejects_mesh_shark_and_accepts_anatomical_contract():
    project_root = Path(__file__).resolve().parents[1]
    atmosphere = (project_root / "static" / "img" / "nemesis-shark-atmosphere.svg").read_text(encoding="utf-8")
    brand = (project_root / "static" / "img" / "nemesis-shark-brand.svg").read_text(encoding="utf-8")
    rejected = _shark_asset_contract_from_text(
        atmosphere.replace("reference-anatomical-body", "data-mesh"),
        brand,
    )
    accepted = _shark_asset_contract_from_text(atmosphere, brand)

    assert rejected["status"] == "FAIL"
    assert rejected["classification"] == "MAJOR_GAP"
    assert "data-mesh" in rejected["forbidden_markers"]
    assert accepted["status"] == "PASS"
    assert accepted["classification"] == "FOUNDER_REVIEW_REQUIRED"


def test_active_atmospheric_shark_is_optimized_transparent_original_recreation():
    contract = _shark_asset_contract()

    assert contract["status"] == "PASS"
    assert contract["classification"] == "FOUNDER_REVIEW_REQUIRED"
    assert contract["asset"] == "static/img/nemesis-shark-atmosphere-v2.webp"
    assert contract["provenance"] == "ORIGINAL_RECREATION_FOR_NEMESIS"
    assert contract["dimensions"] == [1400, 758]
    assert contract["size_bytes"] < 350_000
    assert contract["alpha_extrema"] == [0, 255]


def test_r12_reference_maps_to_match_center_not_generic_shark():
    references = _reference_manifest_map()

    assert references["/match/m-1"]["reference_id"] == "REF-12"
    assert references["/match/m-1"]["screen"] == "Match Center"
    assert "/shark" not in references


def test_reference_crop_selects_embedded_desktop_and_mobile_compositions():
    size = (1672, 941)

    desktop = _reference_crop_box(size, 1366, "reference_images/client/reference_import_v900_08.png")
    mobile = _reference_crop_box(size, 390, "reference_images/client/reference_import_v900_08.png")
    admin = _reference_crop_box(size, 1366, "reference_images/admin/reference_import_v900_01.png")

    assert desktop[0] < 50
    assert desktop[2] < 1400
    assert mobile[0] > 1200
    assert mobile[2] == 1667
    assert admin == (0, 0, 1672, 941)


def test_rendered_layout_competition_and_temporal_evidence_reaches_regression_manager(tmp_path: Path):
    observation = clean_observation()
    observation["competition_identity"] = {"pass": True, "matches_compared": 2, "mismatches": []}
    observation["layout"] = {
        "observed": True,
        "captures": 171,
        "collision_types": [],
        "collisions": 0,
        "mobile_360_captures": 16,
        "mobile_360_collisions": 0,
        "mobile_360_overflow": 0,
    }
    observation["temporal_context"] = {
        "checked_cards": 18,
        "missing_cards": 0,
        "ambiguous_cards": 0,
        "cross_surface_consistent": True,
        "madrid_time": True,
    }

    result = record_product_qa_run(
        observation,
        project_root=tmp_path,
        storage_root=tmp_path / "ce",
        now="2026-08-31T16:00:00+02:00",
    )
    statuses = {item["regression_id"]: item["status"] for item in result["regression_manager"]["items"]}
    assert statuses["CROSS_SURFACE_COMPETITION_IDENTITY"] == "PASS"
    assert statuses["NO_TEXT_BORDER_COLLISION"] == "PASS"
    assert statuses["NO_CARD_OVERFLOW"] == "PASS"
    assert statuses["SPANISH_COPY_STRESS"] == "PASS"
    assert statuses["MOBILE_360_LAYOUT"] == "PASS"
    assert statuses["TEMPORAL_CONTEXT_CONSISTENCY"] == "PASS"


def failing_observation() -> dict:
    return {
        "production_sha": "fixture-sha",
        "evidence_complete": True,
        "navigation_clicks": [
            {
                "screen": "/app",
                "viewport": "desktop_1366x768",
                "element": "Partidos",
                "expected_path": "/calendar",
                "actual_path": "/app",
                "clicked": False,
                "hit_target": False,
                "http_status": 200,
                "page_ready": True,
            }
        ],
        "sports_truth": {
            "screen": "/",
            "confirmed_live_count": 0,
            "displayed_live_count": 2,
            "ft_rendered_live": 1,
            "cross_surface_live_truth": False,
            "cross_surface_live_mismatches": [{"match_id": "sportsdb-9c185a90a281810876", "home": "LIVE", "directo": "STALE", "match": "LIVE"}],
        },
        "temporal_context": {
            "screen": "match surfaces",
            "checked_cards": 9,
            "missing_cards": 2,
            "ambiguous_cards": 1,
            "cross_surface_consistent": False,
            "madrid_time": False,
        },
        "sports_knowledge": {
            "screen": "/match/m-1",
            "lineup_confirmed": True,
            "lineup_player_links": 0,
            "summary_ai_calls": 1,
            "summary_unsupported_claims": 1,
            "unsafe_media_visible": 1,
        },
        "client_copy": {
            "screen": "/live",
            "visible_text": "Provider cache hit. Próxima revisión en 180 s.",
        },
        "visual": {
            "shark": {"screen": "/app", "viewport": "desktop_1366x768", "classification": "MAJOR_GAP", "evidence": "legacy shark marker"},
            "background": {"screen": "/app", "viewport": "desktop_1366x768", "classification": "REBUILD_REQUIRED", "evidence": "flat background"},
        },
        "composition": {"observed": True, "dead_space_flags": [{"screen": "/app", "flag": "LARGE_UNJUSTIFIED_EMPTY_REGION"}], "empty_dashboard_flags": [{"screen": "/picks", "flag": "EMPTY_ANALYTICS_DASHBOARD"}], "home_sports_above_fold_ratio": 0.0},
        "density": {"screen": "/app", "viewport": "desktop_1366x768", "first_viewport_product": False, "nested_panel_depth": 4, "nested_card_depth": 4, "dead_space_flags": ["LARGE_UNJUSTIFIED_EMPTY_REGION"], "empty_dashboard_flags": ["EMPTY_ANALYTICS_DASHBOARD"], "sports_above_fold_ratio": 0.0},
        "mobile": {"screen": "/app", "viewport": "mobile_390x844", "overflow": True},
        "runtime": {"js_errors": ["TypeError: blocked topbar"], "broken_images": ["/static/img/missing.png"]},
        "journeys": [{"journey": "sports", "route": "/app", "expected": "/match/", "actual": "/app", "pass": False}],
    }


def clean_observation() -> dict:
    return {
        "production_sha": "clean-sha",
        "evidence_complete": True,
        "navigation_clicks": [
            {
                "screen": "/app",
                "viewport": "desktop_1366x768",
                "element": "Partidos",
                "expected_path": "/calendar",
                "actual_path": "/calendar",
                "clicked": True,
                "hit_target": True,
                "http_status": 200,
                "page_ready": True,
            }
        ],
        "sports_truth": {"screen": "/", "confirmed_live_count": 0, "displayed_live_count": 0, "ft_rendered_live": 0, "cross_surface_live_truth": True, "cross_surface_live_mismatches": []},
        "temporal_context": {"screen": "match surfaces", "checked_cards": 9, "missing_cards": 0, "ambiguous_cards": 0, "cross_surface_consistent": True, "madrid_time": True},
        "sports_knowledge": {"screen": "/match/m-1", "lineup_confirmed": True, "lineup_player_links": 1, "summary_ai_calls": 0, "summary_unsupported_claims": 0, "unsafe_media_visible": 0},
        "client_copy": {"screen": "/live", "visible_text": "No hay partidos en directo."},
        "visual": {
            "shark": {"screen": "/app", "viewport": "desktop_1366x768", "classification": "MINOR_GAP", "evidence": "official shark rendered"},
            "background": {"screen": "/app", "viewport": "desktop_1366x768", "classification": "MINOR_GAP", "evidence": "official ocean composition"},
        },
        "composition": {"observed": True, "dead_space_flags": [], "empty_dashboard_flags": [], "home_sports_above_fold_ratio": 0.18, "home_viewport_content_coverage": 0.71},
        "density": {"screen": "/app", "viewport": "desktop_1366x768", "first_viewport_product": True, "nested_panel_depth": 1, "nested_card_depth": 1, "bordered_containers": 9, "dead_space_flags": [], "empty_dashboard_flags": [], "sports_above_fold_ratio": 0.18},
        "mobile": {"screen": "/app", "viewport": "mobile_390x844", "overflow": False},
        "runtime": {"js_errors": [], "broken_images": []},
        "journeys": [{"journey": "sports", "route": "/app", "expected": "/match/", "actual": "/match/m-1", "pass": True}],
    }


def test_acceptance_fixture_detects_all_demonstrated_failures():
    issues = detect_product_qa_issues(failing_observation(), detected_at="2026-08-30T10:00:00+02:00")
    categories = {item["category"] for item in issues}
    assert {"NAVIGATION", "SPORTS_TRUTH", "TEMPORAL_CONTEXT", "SPORTS_KNOWLEDGE", "SUMMARY_TRUTH", "MEDIA_RIGHTS", "CLIENT_COPY", "VISUAL_SHARK", "VISUAL_BACKGROUND", "UI_DENSITY", "MOBILE_LAYOUT", "JAVASCRIPT", "BROKEN_IMAGE", "USER_JOURNEY"} <= categories
    assert next(item for item in issues if item["category"] == "NAVIGATION")["severity"] == "P0"
    assert next(item for item in issues if item["category"] == "SPORTS_TRUTH")["severity"] == "P0"
    assert next(item for item in issues if item["category"] == "SPORTS_TRUTH")["worker"] == "sports_truth_qa"
    assert next(item for item in issues if item["category"] == "SPORTS_KNOWLEDGE")["worker"] == "sports_knowledge_qa"
    assert next(item for item in issues if item["category"] == "SUMMARY_TRUTH")["worker"] == "summary_truth_qa"
    assert next(item for item in issues if item["category"] == "MEDIA_RIGHTS")["worker"] == "media_rights_qa"


def test_clean_fixture_is_a_real_pass_candidate():
    assert detect_product_qa_issues(clean_observation()) == []


def test_founder_video_review_is_permanent_product_memory(tmp_path: Path):
    record_product_qa_run(clean_observation(), project_root=tmp_path, storage_root=tmp_path / "ce")
    memory = load_product_qa_memory(tmp_path, storage_root=tmp_path / "ce")
    incident = next(item for item in memory["founder_overrides"] if item["override_id"] == "FOUNDER_VIDEO_REVIEW_2026_08_31")
    assert set(incident["categories"]) == {"SHARK", "BACKGROUND_DEPTH", "DEAD_SPACE", "RECTANGLE_DENSITY", "EMPTY_STATES", "SPORTS_HIERARCHY"}
    assert {"LARGE_UNJUSTIFIED_EMPTY_REGION", "EMPTY_DASHBOARD", "SPORTS_ABOVE_FOLD_RATIO"} <= set(PINNED_REGRESSION_CONTRACTS)


def test_browser_inspector_measures_composition_and_empty_states_are_resolved():
    inspector = (Path(__file__).parents[1] / "tools" / "run_autonomous_product_qa.py").read_text(encoding="utf-8")
    assert all(marker in inspector for marker in ("dead_space_flags", "empty_dashboard_flags", "bordered_containers", "nested_card_depth", "sports_above_fold_ratio", "purposefulSportsContent", "componentSelectors", "componentInstances"))
    for template in ("live.html", "picks.html", "shark.html", "track_record.html"):
        source = (Path(__file__).parents[1] / "templates" / template).read_text(encoding="utf-8")
        assert 'data-empty-dashboard="resolved"' in source


def test_browser_workforce_never_deletes_an_existing_qa_database():
    inspector = (Path(__file__).parents[1] / "tools" / "run_autonomous_product_qa.py").read_text(encoding="utf-8")

    assert 'parser.add_argument("--db-path", default="")' in inspector
    assert 'QA database already exists; use a new isolated --db-path' in inspector
    assert "db_path.unlink()" not in inspector


def test_browser_workforce_can_use_an_installed_browser_without_downloading_one():
    inspector = (Path(__file__).parents[1] / "tools" / "run_autonomous_product_qa.py").read_text(encoding="utf-8")

    assert 'parser.add_argument("--browser-executable", default="")' in inspector
    assert 'launch_options["executable_path"]' in inspector


def test_resolved_empty_state_must_still_fill_an_intentional_visual_stage():
    project_root = Path(__file__).resolve().parents[1]
    inspector = (project_root / "tools" / "run_autonomous_product_qa.py").read_text(encoding="utf-8")
    css = (project_root / "static" / "v933-product.css").read_text(encoding="utf-8")

    assert ".ns-video-empty-dashboard" in inspector
    assert "&& !emptyDashboardResolved && !purposefulSportsContent" not in inspector
    assert "min-height: clamp(156px, 22vh, 196px)" in css
    assert "width: min(660px, 100%)" in css


def test_track_record_pending_only_does_not_render_evaluable_history_dashboard(app_module):
    data = {
        "track_record": {
            "pending_results": [{"pick_id": "pending-1"}],
            "closed_count": 0,
            "graded_count": 0,
            "roi": None,
            "winrate": None,
        }
    }
    with app_module.app.test_request_context("/track-record"):
        html = render_template("track_record.html", data=data)

    assert 'data-empty-dashboard="resolved"' in html
    assert "El histórico empieza con resultados reales" in html
    assert "ROI real" not in html


def test_memory_keeps_first_seen_and_recurrence(tmp_path: Path):
    first = record_product_qa_run(
        failing_observation(),
        project_root=tmp_path,
        storage_root=tmp_path / "ce",
        now="2026-08-30T10:00:00+02:00",
    )
    second = record_product_qa_run(
        failing_observation(),
        project_root=tmp_path,
        storage_root=tmp_path / "ce",
        now="2026-08-31T10:00:00+02:00",
    )
    first_by_id = {item["issue_id"]: item for item in first["issues"]}
    second_by_id = {item["issue_id"]: item for item in second["issues"]}
    assert first_by_id.keys() == second_by_id.keys()
    for issue_id in first_by_id:
        assert second_by_id[issue_id]["first_seen"] == first_by_id[issue_id]["first_seen"]
        assert second_by_id[issue_id]["seen_count"] == 2


def test_critical_scope_does_not_resolve_full_findings_or_replace_full_baseline(tmp_path: Path):
    failing = {**failing_observation(), "scope": "full", "run_id": "PQA-FULL-FAIL"}
    critical = {**clean_observation(), "scope": "critical", "run_id": "PQA-CRITICAL-PASS"}
    full_clean = {**clean_observation(), "scope": "full", "run_id": "PQA-FULL-PASS"}

    record_product_qa_run(failing, project_root=tmp_path, storage_root=tmp_path / "ce")
    critical_result = record_product_qa_run(critical, project_root=tmp_path, storage_root=tmp_path / "ce")
    status_after_critical = build_autonomous_product_qa_status(tmp_path, storage_root=tmp_path / "ce")

    assert critical_result["result"] == "PASS"
    assert status_after_critical["open_issue_count"] > 0
    assert critical_result["previous_good_run_id"] is None
    assert critical_result["previous_good_critical_run_id"] == "PQA-CRITICAL-PASS"

    full_result = record_product_qa_run(full_clean, project_root=tmp_path, storage_root=tmp_path / "ce")
    assert full_result["result"] == "PASS"
    assert full_result["previous_good_run_id"] == "PQA-FULL-PASS"


def test_two_full_clean_retests_resolve_non_visual_but_keep_founder_visual_review(tmp_path: Path):
    failing = {**failing_observation(), "scope": "full", "run_id": "PQA-FAIL"}
    clean_one = {**clean_observation(), "scope": "full", "run_id": "PQA-CLEAN-1"}
    clean_two = {**clean_observation(), "scope": "full", "run_id": "PQA-CLEAN-2"}

    record_product_qa_run(failing, project_root=tmp_path, storage_root=tmp_path / "ce")
    record_product_qa_run(clean_one, project_root=tmp_path, storage_root=tmp_path / "ce")
    record_product_qa_run(clean_two, project_root=tmp_path, storage_root=tmp_path / "ce")
    status = build_autonomous_product_qa_status(tmp_path, storage_root=tmp_path / "ce")
    by_category = {}
    for issue in status["issues"]:
        by_category.setdefault(issue["category"], []).append(issue)

    assert all(item["status"] == "RESOLVED" for item in by_category["NAVIGATION"])
    assert all(item["status"] == "RESOLVED" for item in by_category["SPORTS_TRUTH"])
    assert all(item["status"] == "RESOLVED" for item in by_category["CLIENT_COPY"])
    assert all(item["status"] == "FIXED_PENDING_VERIFICATION" for item in by_category["VISUAL_SHARK"])
    assert all(item["status"] == "FIXED_PENDING_VERIFICATION" for item in by_category["VISUAL_BACKGROUND"])


def test_founder_override_and_calibration_are_honest(tmp_path: Path):
    record_product_qa_run(clean_observation(), project_root=tmp_path, storage_root=tmp_path / "ce")
    status = build_autonomous_product_qa_status(tmp_path, storage_root=tmp_path / "ce")
    assert status["founder_overrides"][0]["type"] == "FOUNDER_QA_OVERRIDE"
    assert status["founder_overrides"][0]["previous_automation_result"] == "PASS"
    assert status["founder_overrides"][0]["founder_result"] == "FAIL"
    assert all(item["calibration"]["state"] == "INSUFFICIENT_HISTORY" for item in status["workers"])


def test_pause_resume_changes_only_product_qa_control(tmp_path: Path):
    paused = set_product_qa_pause(tmp_path, paused=True, actor="Founder", storage_root=tmp_path / "ce")
    assert paused["paused"] is True
    resumed = set_product_qa_pause(tmp_path, paused=False, actor="Founder", storage_root=tmp_path / "ce")
    assert resumed["paused"] is False
    assert len(resumed["history"]) == 2


def test_open_product_qa_issues_become_product_review_findings(tmp_path: Path):
    record_product_qa_run(failing_observation(), project_root=tmp_path, storage_root=tmp_path / "ce")
    status = build_autonomous_product_qa_status(tmp_path, storage_root=tmp_path / "ce")
    findings = product_qa_review_findings(status)
    assert findings
    assert {item["priority"] for item in findings} >= {"P0", "P1"}
    assert all(item["automatic_execution_allowed"] is False for item in findings)


def test_sentinel_preserves_exact_product_qa_evidence_fields():
    raw = {
        "issue_id": "PQA-STABLE",
        "stable_key": "worker|navigation|/app|desktop|partidos",
        "title": "Topbar bloqueada",
        "category": "NAVIGATION",
        "severity": "critical",
        "worker": "digital_user_journey_tester",
        "screen": "/app",
        "viewport": "desktop_1366x768",
        "element": "Partidos",
        "expected": "/calendar",
        "actual": "/app",
        "evidence": "elementFromPoint no devuelve el enlace",
        "screenshot": "evidence/home.png",
        "production_sha": "abc123",
        "confidence": "HIGH",
    }
    first = normalize_sentinel_issue(raw, "autonomous_product_qa")
    second = normalize_sentinel_issue({**raw, "actual": "overlay intercepts click"}, "autonomous_product_qa")
    merged = upsert_sentinel_issues([first], [second])
    assert len(merged) == 1
    assert merged[0]["issue_id"] == "PQA-STABLE"
    assert merged[0]["seen_count"] == 2
    assert merged[0]["actual"] == "overlay intercepts click"


def test_canonical_ledger_rejects_synthetic_404_and_codex_noise():
    synthetic = normalize_sentinel_issue({
        "title": "Ruta devuelve Not Found",
        "route": "/ruta-inventada-v999",
        "evidence": "Probe de QA sin navegación interna real.",
        "actual": "404",
        "status": "OPEN",
    })
    context_only = normalize_sentinel_issue({
        "title": "Contexto sin muestra real",
        "area": "growth",
        "status": "INSUFFICIENT_EVIDENCE",
        "evidence": "No existe todavía muestra REAL_USER suficiente.",
    })
    memory = canonicalize_sentinel_memory({"issues": [synthetic, context_only], "events": []})
    summary = build_sentinel_issues_summary("TEST", memory)

    assert ISSUE_STATUSES == [
        "OPEN_REAL", "FIXED_PENDING_VERIFICATION", "RESOLVED", "FALSE_POSITIVE",
        "STALE", "DUPLICATE", "EXTERNAL_BLOCKER", "INSUFFICIENT_EVIDENCE",
    ]
    assert summary["counts"]["open"] == 0
    assert summary["issue_health"]["false_positive"] == 1
    assert summary["issue_health"]["insufficient_evidence"] == 1
    assert summary["codex_ready_issues"] == []


def test_founder_issue_gate_has_no_indefinite_pending_statuses(tmp_path: Path):
    summary = reconcile_autonomous_workforce_evidence(
        tmp_path,
        latest_product_qa={"result": "PASS", "evidence_complete": True, "issues_detected": 0},
        production_sha="sha-under-review",
        save=False,
    )
    by_key = {item.get("stable_key"): item for item in summary["issues"]}

    assert by_key["founder-shark-identity"]["status"] == "OPEN_REAL"
    assert by_key["founder-ocean-background"]["status"] == "OPEN_REAL"
    assert by_key["founder-reference-mismatch"]["status"] == "OPEN_REAL"
    assert by_key["founder-false-live-kpi"]["status"] == "RESOLVED"
    assert by_key["founder-rectangle-fatigue"]["status"] == "RESOLVED"
    assert not any(item["status"] == "FIXED_PENDING_VERIFICATION" for item in by_key.values())

def test_honest_empty_sports_state_is_not_an_issue_or_codex_work():
    context = " Consulta calendario, favoritos y próximos encuentros cuando haya datos reales."
    html = (
        "<html><body><main class='sports-screen'><section class='v933-empty-state'>"
        "<h1>Partidos</h1><p>No hay partidos en este momento.</p>"
        f"<p>{context * 5}</p></section></main></body></html>"
    )

    assert _inspect_html("FREE", "/partidos", 200, html) == []
    assert build_codex_prompts([]) == []


def test_codex_outbox_accepts_only_verified_open_real(tmp_path: Path):
    blocked = normalize_sentinel_issue({
        "title": "Contexto sin evidencia",
        "status": "INSUFFICIENT_EVIDENCE",
        "evidence": "Muestra real pendiente.",
    })
    ready = normalize_sentinel_issue({
        "title": "Enlace interno roto",
        "status": "OPEN_REAL",
        "route": "/app",
        "evidence": "Clic real desde Home termina en una ruta 404.",
        "actual": "404 después del clic",
        "expected": "Match Center",
        "evidence_origin": "LOCAL_QA",
        "evidence_sufficient": True,
    })
    result = write_codex_outbox(tmp_path, [blocked, ready])

    assert result["prompt_count"] == 1
    assert ready["id"] in Path(result["combined_path"]).read_text(encoding="utf-8")
    assert blocked["id"] not in Path(result["combined_path"]).read_text(encoding="utf-8")


def test_quality_director_never_lets_lower_evidence_override_founder_failure():
    founder_issue = {
        "issue_id": "FOUNDER-TOPBAR",
        "category": "NAVIGATION",
        "severity": "P0",
        "status": "OPEN_REAL",
        "evidence_origin": "FOUNDER_QA_OVERRIDE",
    }
    decision = build_quality_director_decision(
        [founder_issue],
        evidence_complete=True,
        regression_manager={"items": []},
        supplemental_evidence={"NAVIGATION": {"status": "PASS", "origin": "UNIT_STATIC_TEST"}},
    )

    assert decision["decision"] == "FAIL"
    assert decision["release_quality_pass"] is False
    assert decision["open_p0"] == 1
    assert next(item for item in decision["gates"] if item["area"] == "NAVIGATION")["authority"] == "FOUNDER_CONFIRMED_FAILURE"


def test_regression_manager_pins_all_known_founder_regressions(tmp_path: Path):
    result = record_product_qa_run(
        clean_observation(),
        project_root=tmp_path,
        storage_root=tmp_path / "ce",
        now="2026-08-30T11:00:00+02:00",
    )

    manager = result["regression_manager"]
    assert manager["protected_regressions"] == len(PINNED_REGRESSION_CONTRACTS)
    assert {item["regression_id"] for item in manager["items"]} == set(PINNED_REGRESSION_CONTRACTS)
    assert next(item for item in manager["items"] if item["regression_id"] == "OFFICIAL_SHARK_REFERENCE")["status"] == "FOUNDER_REVIEW_REQUIRED"
    assert next(item for item in manager["items"] if item["regression_id"] == "OFFICIAL_BACKGROUND_REFERENCE")["status"] == "FOUNDER_REVIEW_REQUIRED"
    assert next(item for item in manager["items"] if item["regression_id"] == "VISUAL_FALSE_PASS_RECURRENCE")["status"] == "FOUNDER_REVIEW_REQUIRED"


def test_cross_surface_live_truth_is_a_p0_and_persists_recurrence(tmp_path: Path):
    record_product_qa_run(
        clean_observation(),
        project_root=tmp_path,
        storage_root=tmp_path / "ce",
        now="2026-08-30T22:35:00+02:00",
    )
    first = record_product_qa_run(
        failing_observation(),
        project_root=tmp_path,
        storage_root=tmp_path / "ce",
        now="2026-08-30T22:40:00+02:00",
    )
    second = record_product_qa_run(
        failing_observation(),
        project_root=tmp_path,
        storage_root=tmp_path / "ce",
        now="2026-08-30T22:45:00+02:00",
    )

    item = next(
        entry for entry in second["regression_manager"]["items"]
        if entry["regression_id"] == "CROSS_SURFACE_LIVE_TRUTH"
    )
    assert first["quality_director"]["decision"] == "FAIL"
    assert first["quality_director"]["open_p0"] >= 1
    assert item["status"] == "FAIL"
    assert item["memory_key"] == "LIVE_TRUTH_CROSS_SURFACE_RECURRENCE"
    assert item["recurrence_count"] >= 1
    assert len(item["verification_history"]) >= 3

def test_regression_manager_increments_recurrence_after_clean_retest(tmp_path: Path):
    record_product_qa_run(
        clean_observation(),
        project_root=tmp_path,
        storage_root=tmp_path / "ce",
        now="2026-08-30T11:00:00+02:00",
    )
    result = record_product_qa_run(
        failing_observation(),
        project_root=tmp_path,
        storage_root=tmp_path / "ce",
        now="2026-08-31T11:00:00+02:00",
    )

    topbar = next(item for item in result["regression_manager"]["items"] if item["regression_id"] == "TOPBAR_REAL_NAVIGATION")
    assert topbar["status"] == "FAIL"
    assert topbar["recurrence_count"] == 1
    assert result["quality_director"]["decision"] == "FAIL"


def test_production_sentinel_requires_all_post_deploy_checks():
    checks = {
        "health": "PASS",
        "sha_alignment": "PASS",
        "logs_recent": "PASS",
        "critical_routes": "PASS",
        "topbar_click_journey": "PASS",
        "mobile_nav": "PASS",
        "sports_truth": "PASS",
        "temporal_context": "PASS",
        "performance_sample": "PASS",
        "critical_visual_surfaces": "PASS",
        "client_admin_protection": "PASS",
    }
    certified = evaluate_production_sentinel(
        {"production_sha": "sha-good", "deployment": checks},
        {"open_p0": 0},
    )
    incomplete = evaluate_production_sentinel(
        {"production_sha": "sha-unknown", "deployment": {**checks, "logs_recent": "NOT_AVAILABLE"}},
        {"open_p0": 0},
    )

    assert certified["result"] == "PRODUCTION_CERTIFIED"
    assert certified["rollback_recommended"] is False
    assert incomplete["result"] == "BLOCKED"


def test_production_sentinel_recommends_rollback_for_post_deploy_p0():
    decision = evaluate_production_sentinel(
        {
            "production_sha": "sha-bad",
            "deployment": {
                "health": "PASS",
                "sha_alignment": "PASS",
                "logs_recent": "PASS",
                "critical_routes": "PASS",
                "topbar_click_journey": "FAIL",
                "mobile_nav": "PASS",
                "sports_truth": "PASS",
                "temporal_context": "PASS",
                "performance_sample": "PASS",
                "critical_visual_surfaces": "PASS",
                "client_admin_protection": "PASS",
            },
        },
        {"open_p0": 1},
    )

    assert decision["result"] == "REGRESSION_DETECTED"
    assert decision["rollback_recommended"] is True
