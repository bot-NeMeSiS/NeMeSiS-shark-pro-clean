# Sports Core Unified Domain Model Report

Decision: LOCAL PASS

Base used: current local main with MATCH-INTELLIGENCE-EVIDENCE-V1 already integrated.
Production modified: false.
External providers called: false.
Telegram sent: false.
Database real written: false.
Stripe touched: false.

## What Was Built

A single read-only Sports Core domain model was added in `engines/sports_domain_model_engine.py`.

Canonical contracts implemented:

- SPORTS-CORE-UNIFIED-DOMAIN-MODEL-V1
- SPORTS-CORE-MATCH-ENTITY-V1
- SPORTS-CORE-TEAM-ENTITY-V1
- SPORTS-CORE-COMPETITION-ENTITY-V1
- SPORTS-CORE-PLAYER-ENTITY-V1
- SPORTS-CORE-TIMELINE-EVENT-V1
- SPORTS-CORE-EVIDENCE-V1
- SPORTS-CORE-FRESHNESS-V1
- SPORTS-CORE-GRAPH-FOUNDATION-V1
- SPORTS-CORE-TELEGRAM-READONLY-V1

## Integrations

MatchContext now builds and exposes `domain_model`, `sports_graph` and `telegram_readonly_contract` from the same already-loaded facts used by Match Center.

Live Story now keeps the legacy event shape for UI compatibility while attaching the canonical Timeline Event Entity to each event.

Match Intelligence now accepts canonical match and canonical timeline inputs and keeps MATCH-INTELLIGENCE-EVIDENCE-V1 unchanged for consumers.

Telegram Intelligence now receives a read-only sports contract when MatchContext/Match Intelligence are supplied. It does not send, write or alter dedupe.

Developer Center and Company Board are updated through the shared sports platform registry: `sports_domain_model` is now an integrated capability.

## Confirmed Guardrails

- No DB writes in the domain model.
- No external calls in the domain model.
- No Telegram sends.
- No generative AI calls.
- No automatic entity merges based only on similar names.
- Stale and unknown freshness are explicit states.
- Missing facts remain missing; no fake players, competitions, events, odds or statistics are generated.

## Compatibility

Legacy consumers still receive previous fields such as `home_team`, `away_team`, `score`, `status`, `timeline` and `shark_context`.

The new canonical model is additive and read-only. No route, database schema, provider call, Telegram delivery path or payment path was changed.

## Risks

- Production freshness is not certified in this sprint because no Render deploy or provider call was authorized.
- Some legacy provider adapters still write their own normalized rows during sync jobs; this sprint provides the canonical read model but does not remove all legacy sync paths.
- Team Center, Competition Center and Player Center are contract-ready only; they are not implemented as full experiences.

## Approval Criteria Status

1. Unified canonical entities: PASS local.
2. Match Center and SHARK same snapshot: PASS local.
3. Live Story normalized events: PASS local.
4. Telegram read-only contract: PASS local.
5. No DB writes by new model: PASS local.
6. No external calls in validation: PASS local.
7. No invented data: PASS local by contract/tests.
8. Stale/insufficient explicit: PASS local.
9. Existing sports tests: PASS affected suite.
10. New tests: PASS 8/8. Full pytest also PASS locally.
11. Browser QA: PASS local. Six Playwright captures across desktop, tablet and mobile; ready and partial scenarios; 0 console errors, 0 page errors, 0 server 5xx, 0 external/provider requests, 0 horizontal overflow, CLS 0.
12. Sentinel: PASS. Continuous Sentinel static score 10/10 with 0 open issues and 0 critical issues.
13. No parallel architecture: PASS, registry uses one Sports Domain Model capability.
14. Future centers prepared: PASS contract-only.
15. Full report: PASS.
## Final Local QA Evidence

- `python -m py_compile` on touched files: PASS.
- `python -m compileall app.py engines tools tests`: PASS.
- `python tools/check_madrid_times.py`: PASS.
- `pytest tests/test_sports_core_unified_domain_model.py`: PASS 8/8.
- Affected Sports Core suite: PASS 28/28.
- Full pytest suite: PASS locally.
- Jinja/template integrity: PASS.
- Import and route verification: PASS.
- Route/link audit: PASS with no broken links or unsafe smoke routes.
- Secret/Privacy Guard: PASS, 0 confirmed secret findings and values not printed.
- Continuous Sentinel static: PASS, score 10/10.
- Browser QA: PASS on desktop 1366x768, tablet 834x1194 and mobile 390x844 for ready and partial match scenarios.
- Performance microbenchmark for domain snapshot plus Match Intelligence: 300 iterations, median 0.941 ms, p95 1.481 ms, max 2.514 ms, external_calls=0, db_writes=0.

## Browser QA Fixture Note

The Browser QA script uses two local scenario IDs (`/match/v944-ready` and `/match/v944-partial`). They were seeded only in the isolated QA database `data/browser_qa_v944_domain.sqlite` using the existing schema and normalized tracker tables. This did not touch production, the real database, Telegram, Stripe or external providers.

