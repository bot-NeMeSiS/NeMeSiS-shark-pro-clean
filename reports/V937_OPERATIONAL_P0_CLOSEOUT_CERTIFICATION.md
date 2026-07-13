# V937 Operational P0 Closeout Certification

Generated at Madrid: 2026-07-13T16:05:02+02:00

## Executive decision

- Controlled deployment of the corrected V937 release: **GO**.
- External launch with paying users: **NO-GO** until the corrected V937 is deployed and production records a successful sports Cron tick plus non-destructive Stripe configuration evidence.
- Version remains exactly `V937_PRODUCT_PERFECTION_FULL_ECOSYSTEM_LAUNCH_CLOSEOUT_FINAL`. No V938 was created.

## What was actually wrong

| P0 | Production evidence | Root cause | Corrective action | Local result | Production gate |
|---|---|---|---|---|---|
| Sports freshness | Last known provider sync `2026-07-09T19:42:34Z`; observed age about 89.3 hours | No isolated sports Cron existed in `render.yaml`; sports refresh depended on startup flags and expensive provider windows | Protected sports-only endpoint and Render Cron every 15 minutes; DB/cache window check; conservative provider calls; no Telegram or payments | Safe simulated cycle PASS, no real provider calls | First real tick pending deploy |
| Route latency | Render: Home 2.982 s, Calendar 7.861 s, Live 5.831 s, Picks 5.830 s | Every SELECT opened a new SQLite connection and reapplied connection setup; sports pages built a full dashboard context they did not use | One query-only SQLite connection per request plus compact DB/cache-only sports context | Home 0.043 s, Admin 0.122 s, Calendar 0.100 s, Live 0.081 s, Picks 0.064 s | Re-measure after deploy |
| Cron proof | Sports schedule absent; other production schedules not observable from the unauthenticated Render session | Configuration and execution evidence were mixed; secrets had also been accepted in runner URLs | Header-only secret transport, compact masked output, dedicated sports runner, runtime recency fields | Sports runner PASS; Telegram dry-run PASS with zero sends | Sports first tick, Telegram/master/grading recency pending Render evidence |
| Stripe | Production environment and webhook history not observable; no safe basis for PASS | Checkout had no explicit retry idempotency key; processed webhook events could be applied again | Stable 10-minute checkout key, duplicate webhook pre-check, exact SDK pin | Stripe 15.3.0; Checkout and Portal contracts PASS without network; signature PASS; FREE-PRO-ELITE-FREE PASS | Products, prices, portal and webhook in Render remain NOT_TESTABLE |

## Safety and data truth

- Real provider calls during verification: `0`.
- Real Telegram sends: `0`.
- Real payments: `0`.
- The sports cycle never creates matches, scores, odds or picks. It only imports provider evidence and grades complete real records.
- Live refresh is skipped when DB/cache has neither live events nor a kickoff within three hours.
- Fixture window cache is six hours; the protected Cron still runs every 15 minutes and records controlled cache outcomes.
- Secrets are sent only in protected headers and are never included in URLs or reports.

## Cron evidence matrix

| Process | Result |
|---|---|
| Sports endpoint without secret | PASS, HTTP 403 |
| Sports endpoint with local protected header | PASS_LOCAL_SAFE_SIMULATION |
| Sports runner isolation | PASS, no Telegram, no payments, no fake data |
| Telegram runner secret transport | PASS, header only |
| Telegram dry-run | PASS_ZERO_SENDS |
| Pick grading in sports cycle | PASS on temporary DB; only complete real records eligible |
| Render sports schedule | CONFIGURED_IN_RELEASE, pending Blueprint sync/deploy |
| First production sports tick | NOT_TESTABLE_BEFORE_DEPLOY |
| Existing production Telegram/master/grading schedules | NOT_TESTABLE_WITHOUT_RENDER_AUTH |

## Product and visual gate

- Browser QA: `CAPTURED`, 238 screenshots, 34 routes, 7 profiles.
- Capture errors: `0`; unexpected authentication redirects: `0`; horizontal overflow: `0`.
- Human-assisted review covered home desktop, client dashboard desktop, calendar mobile and admin dashboard desktop.
- No evidence-based visual regression was found, so no subjective redesign or extra CSS layer was introduced.
- Sentinel: score `10.0`, 39 critical routes checked, 664 routes inventoried, 929 links, 0 active issues, 0 broken links and 0 loops.

## Regression and release evidence

- V929 navigation, V930 visual system, V931 route/SQLite guards, V932 authentication, V933-V936 product checks and both V937 checks passed.
- Jinja: 182 templates parsed, 0 errors.
- Import and route verification: 625 routes, 0 missing templates or static files.
- Source cleanup removed generated caches, temporary V937 databases and a local debug log only. Runtime data, DB, references, tests, migrations and assets were preserved.
- Final release audit: `forbidden_count=0` and `missing_required_root=[]`.

## Remaining risk and required action

Production currently serves V937 commit `395b15a3cea7b5c47258ebcd1cfbba8c3153a6b9`, but it does not yet expose the new P0 operational fields. This proves the corrected same-version release is not deployed.

Required sequence:

1. Review and commit only the V937 P0 changes.
2. Push to the authorized V937 branch/main flow and sync the Render Blueprint so `nemesis-sports-sync` exists.
3. Confirm `AUTOMATION_SECRET` is present for the web service and Cron without printing it.
4. Observe one successful sports tick and a provider timestamp newer than six hours.
5. Re-measure Home, Calendar, Live and Picks on Render.
6. Confirm Stripe keys, both Price IDs, Portal and webhook endpoint by presence and non-destructive evidence only.
7. Keep external launch at NO-GO until all six checks are evidenced.

## Product score

- Before P0 closeout: `6.4/10` operational readiness. Visual quality was strong, but stale data and multi-second sports routes undermined trust.
- Corrected local candidate: `8.8/10` operational readiness.
- Current production score remains `6.4/10` until deployment and first-tick evidence close the gap.
