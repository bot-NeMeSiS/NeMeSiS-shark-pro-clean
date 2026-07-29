# Visual Audit Report

## Status

PASS_WITH_REVIEW_ITEMS

## Coverage

- Screens scanned: 174
- CSS files scanned: 8
- CSS findings capped: 0

## Findings

| severity | category | screen | title | evidence |
| --- | --- | --- | --- | --- |
| P3 | density | templates/action_platform.html | Pantalla fragmentada en demasiados bloques | sections=14, words=113 |
| P3 | density | templates/adaptive_experience.html | Muchas cards con baja densidad informativa | cards=12, words_per_card=5.5 |
| P3 | density | templates/admin_automation.html | Muchas cards con baja densidad informativa | cards=12, words_per_card=4.9 |
| P3 | density | templates/admin_autonomous_ecosystem.html | Muchas cards con baja densidad informativa | cards=12, words_per_card=7.6 |
| P3 | density | templates/admin_betting_center.html | Muchas cards con baja densidad informativa | cards=12, words_per_card=6.6 |
| P3 | density | templates/admin_ceo_dashboard.html | Pantalla fragmentada en demasiados bloques | sections=10, words=195 |
| P3 | density | templates/admin_command_center.html | Muchas cards con baja densidad informativa | cards=34, words_per_card=3.9 |
| P3 | density | templates/admin_company_audit.html | Pantalla fragmentada en demasiados bloques | sections=10, words=112 |
| P3 | density | templates/admin_data_trust_center.html | Pantalla fragmentada en demasiados bloques | sections=10, words=166 |
| P3 | density | templates/admin_developer_center.html | Pantalla fragmentada en demasiados bloques | sections=10, words=170 |
| P3 | density | templates/admin_go_live.html | Muchas cards con baja densidad informativa | cards=28, words_per_card=5.0 |
| P3 | density | templates/admin_intelligence_engine.html | Muchas cards con baja densidad informativa | cards=12, words_per_card=7.5 |
| P3 | density | templates/admin_observability.html | Muchas cards con baja densidad informativa | cards=14, words_per_card=7.0 |
| P3 | density | templates/admin_production_readiness.html | Muchas cards con baja densidad informativa | cards=17, words_per_card=5.9 |
| P3 | density | templates/admin_public_launch.html | Muchas cards con baja densidad informativa | cards=20, words_per_card=4.2 |
| P3 | density | templates/admin_retention_center.html | Muchas cards con baja densidad informativa | cards=12, words_per_card=4.2 |
| P3 | density | templates/admin_route_health.html | Muchas cards con baja densidad informativa | cards=12, words_per_card=6.4 |
| P3 | density | templates/admin_sale_ready.html | Muchas cards con baja densidad informativa | cards=15, words_per_card=5.1 |
| P3 | density | templates/admin_sentinel_codex_outbox.html | Muchas cards con baja densidad informativa | cards=20, words_per_card=8.0 |
| P3 | density | templates/admin_shark_center.html | Muchas cards con baja densidad informativa | cards=12, words_per_card=4.5 |
| P3 | density | templates/admin_telegram.html | Muchas cards con baja densidad informativa | cards=26, words_per_card=5.7 |
| P3 | density | templates/admin_telegram_audit.html | Muchas cards con baja densidad informativa | cards=15, words_per_card=9.9 |
| P3 | density | templates/admin_track_record.html | Muchas cards con baja densidad informativa | cards=12, words_per_card=8.2 |
| P3 | density | templates/admin_visual_worker.html | Muchas cards con baja densidad informativa | cards=14, words_per_card=8.1 |
| P3 | density | templates/auto_picks.html | Muchas cards con baja densidad informativa | cards=12, words_per_card=3.9 |
| P3 | density | templates/autonomous_ecosystem.html | Muchas cards con baja densidad informativa | cards=19, words_per_card=5.0 |
| P3 | density | templates/combis.html | Pantalla fragmentada en demasiados bloques | sections=10, words=110 |
| P3 | density | templates/competition_detail.html | Pantalla fragmentada en demasiados bloques | sections=24, words=180 |
| P3 | density | templates/daily_briefing.html | Muchas cards con baja densidad informativa | cards=12, words_per_card=7.8 |
| P3 | density | templates/discovery.html | Muchas cards con baja densidad informativa | cards=13, words_per_card=7.4 |
| P3 | density | templates/player_detail.html | Pantalla fragmentada en demasiados bloques | sections=28, words=163 |
| P3 | density | templates/shark_intelligence_center.html | Pantalla fragmentada en demasiados bloques | sections=16, words=127 |
| P3 | density | templates/team_detail.html | Pantalla fragmentada en demasiados bloques | sections=28, words=176 |
| P3 | density | templates/user_intelligence_center.html | Pantalla fragmentada en demasiados bloques | sections=16, words=96 |
| P3 | density | static/app.css | Altura fija grande puede crear espacio vacio o scroll excesivo | min-height:100vh |
| P3 | density | static/app.css | Altura fija grande puede crear espacio vacio o scroll excesivo | min-height:100vh |
| P3 | density | static/app.css | Altura fija grande puede crear espacio vacio o scroll excesivo | height:100vh |
| P3 | density | static/app.css | Altura fija grande puede crear espacio vacio o scroll excesivo | min-height:100vh |
| P3 | density | static/app.css | Altura fija grande puede crear espacio vacio o scroll excesivo | min-height:100vh |
| P3 | density | static/v928-canonical.css | Altura fija grande puede crear espacio vacio o scroll excesivo | min-height: 100vh |
| P3 | density | static/v937-product-client.css | Altura fija grande puede crear espacio vacio o scroll excesivo | min-height:100vh |


## Permanent Rule

Exceso de scroll, bloques enormes, espacios vacios y baja densidad no se corrigen con parches a ciegas: primero evidencia visual, despues cambio minimo y QA.
