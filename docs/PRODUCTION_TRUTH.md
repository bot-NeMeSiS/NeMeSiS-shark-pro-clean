# PRODUCTION TRUTH & CONSOLIDATION

Baseline: main cc1481c0a29f91be49f92abaaea48e3dde345356, VERSION V941.
Evidence observed on 2026-10-02. This document distinguishes intended configuration
from production certification. No secret values belong in this document.

## Canonical operation

- Render web: nemesissharkpro, srv-d7t9j2favr4c738hm0i0, Starter, Oregon,
  gunicorn app:app, main, automatic deployment on commit.
- Render cron: telegram-auto-tick, crn-d8mlmhq8qa3s73e9v2tg,
  python tools/render_cron_master_tick.py, main, automatic deployment on commit.
- Cadence: */5 * * * *. Preserve the existing production cadence for sports and
  Telegram compatibility. Quota control remains inside workers, not in the schedule.
  This change resolves the repository's obsolete */10 declaration.
- Required web health check: /api/health. The live Render field was empty at audit;
  committing render.yaml alone does not certify that an existing service applies it.
- Persistent disk: /data, 1 GB, confirmed by the service metadata.
- Required DB_PATH: /data/database.db. Blueprint declaration confirmed; the actual
  environment value and on-disk integrity require authenticated verification.
- Existing scheduler controls in render.yaml remain authoritative production intent:
  SCHEDULER_ENABLED=0, ENABLE_AUTO_SYNC=0, AUTO_SYNC_ON_STARTUP=0,
  DAILY_AUTOMATION_ENABLED=0, DATA_BACKUP_ENABLED=1,
  CONTINUOUS_EVOLUTION_SAFE_MODE=1 and persistent evolution storage under /data.
  .env.example contains development defaults, including SCHEDULER_ENABLED=true;
  it must not be copied wholesale into production.
- The stateless cron needs PUBLIC_BASE_URL and the existing AUTOMATION_SECRET;
  never replace that secret, duplicate schedulers or give the cron a second DB.

## Cron closure

Existing PR #143 owns the minimal correction. HTTP 200 and ok=true are necessary,
but not sufficient: PARTIAL must contain nonempty jobs with explicitly approved
states and reasons (DAILY_BUDGET, TICK_BUDGET, SOURCE_COOLDOWN or completed work).
Keep postmatch_status=PARTIAL visible while an otherwise healthy run exits zero.
Unknown reasons, FAILED jobs, transport/storage errors and failures of other ticks
remain nonzero. Do not convert every PARTIAL into success.

## Provider hierarchy and evidence

Current orchestration in app.py exposes api_football_primary, sportsdb_fallback,
live_refresh and odds_refresh. API-Football is the preferred fixture/enrichment
source where its access and coverage are established; TheSportsDB is the existing
fallback. Odds supplies prices, not replacement scores or fixture facts.

Use these operational meanings without replacing detailed existing diagnostics:

| State | Required evidence |
| --- | --- |
| AVAILABLE | Recent successful response for the relevant capability and scope |
| LIMITED | Access, coverage or quota restricts that capability; keep reason/time |
| STALE | Stored evidence is outside its freshness window or lacks a valid clock |
| UNAVAILABLE | A current failed attempt or absent usable access/data |

Unknown or historical observations must remain unknown/historical, not be promoted
to a current state. At 14:55 Europe/Madrid the cron selected SPORTSDB_FALLBACK;
SportsDB contributed data, API-Football reported cached access restrictions,
and three match rows were stale. Historical quota/access observations from
September 10 do not certify current authentication or remaining quota.

## Persistence and recovery gate

The app's active create/restore wrappers use engines/data_vault_engine.py.
services/backup_service.py also exists; do not redirect callers merely because
the names look duplicated. The vault validates SQLite integrity and manifest
hashes, stages restore and creates a verified safety copy before restoring.

Run backup/restore tests only with synthetic SQLite databases and explicitly
isolated directories. This certifies the mechanism, not the real daily backup.
Production certification additionally requires observing a natural backup run,
verified manifest/hash, retention and a restore rehearsal of a protected copy
in an isolated environment. Never restore onto /data/database.db for this phase.

## Runtime, engines and navigation

237 tracked files exist under data/runtime at baseline, including Sentinel
outbox/state and visual/navigation reports. Do not bulk delete or move them:
some may be fixtures or historical evidence. Next safe step is a caller-by-caller
read/write and test inventory, then a configurable persistent destination under
/data with fallback compatibility and rollback before untracking generated files.

Active entry points observed in app.py:

| Area | Existing entry points | Consolidation gate |
| --- | --- | --- |
| Live | live_engine, live_presentation_engine | Prove data vs presentation ownership |
| Picks | enrich_pick_quality, grading and decision history | Preserve grading/history contracts |
| SHARK | shark_engine, shark_intelligence_platform_engine, shark_learning_engine | Trace context and learning consumers |
| Sentinel | static, continuous, autopilot, autonomous company engines | Prove distinct trigger/storage responsibilities |
| Telegram | delivery, reliability, presentation, quality and preferences engines | Preserve uncertain-send safety and dedupe |

These are candidates for responsibility mapping, not proven interchangeable
duplicates. Keep them until contract tests and a reversible migration exist.

base.html delegates the active shell to components/v933_shells.html and
components/v933_navigation.html. Desired primary client groups: Inicio, Partidos,
Live, Picks, SHARK. Desired admin groups: Empresa, Usuarios, Membresías, Deportes,
Picks, Telegram, Ingresos, Operaciones, Sentinel. Preserve existing routes,
entitlements, secondary links and browser coverage; defer menu rewrites until
each current destination is mapped and authenticated PC/tablet/mobile QA passes.

## Release and exact rollback

Integrate #143 and the cadence/documentation PR separately through protected main.
Required qa, smoke and preflight checks must pass on each final head. Render's
existing auto-deploy is the delivery path; no duplicate manual deployment hook.
After merge verify both deploys match the merged SHA, /api/health and
/api/runtime-version, request 5xx logs, persistent disk/DB identity, a natural
cron run and backup evidence. Browser CI is synthetic, not real-user certification.

For cadence rollback restore render.yaml's schedule to */10 in a revert PR;
production cadence remains */5 unless explicitly changed in Render. For cron
rollback revert only #143's merge commit through a PR, preserving later changes.
Baseline deployment reference is cc1481c0a29f91be49f92abaaea48e3dde345356
(web dep-davqb8u0tbcc73evlji0). If service configuration is changed, record its
before/after values and restore only those fields; healthCheckPath was empty.
Never rollback data by replacing the database with a repository copy. Schema or
data recovery needs a separately verified backup and deliberate maintenance plan.
