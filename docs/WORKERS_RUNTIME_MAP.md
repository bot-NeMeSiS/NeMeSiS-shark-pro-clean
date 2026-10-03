# Workers: GitHub and Render

Audited 2026-10-03 against main 296e4559. These are software modules, not separate employees or paid AI agents.

| Layer | Location | Execution and purpose |
| --- | --- | --- |
| CI | `.github/workflows/` | GitHub-hosted runners test, compile, check routes/security and run browser QA on PRs/main. Their isolated databases and QA fixtures are not production sports data. |
| Workforce | `automation_workforce/` | Shared release, navigation, runtime, browser, security and reporting modules. Called by CI, explicit tools and protected Admin routes. A file existing does not prove a continuously running process. |
| Web runtime | Render web `nemesissharkpro` | Gunicorn serves Flask and persisted client data using the existing production database. Multiple Gunicorn workers are request processors, not extra scheduled jobs. |
| Master Cron | Render `telegram-auto-tick` | Existing five-minute schedule runs `tools/render_cron_master_tick.py`, calling authenticated automation endpoints on the web service. It coordinates existing ingestion, highlights, postmatch and Telegram tasks. |
| Postmatch | `engines/postmatch_*` | Durable recovery queue with leases, bounded batches, budgets, backoff and provenance. Executes through the master Cron or explicit Admin action; a client GET does not run recovery. |

`render-deploy.yml` observes Render auto-deploy from main; it does not call a deployment hook. `postmatch-workers.yml` and `postmatch-delivery-qa.yml` are QA, not a second production scheduler. `automation_workforce` remains referenced by app.py, Admin and CI and must not be deleted as cache.

Rights remain independent of retrieval: TheSportsDB finding a URL or a paid subscription does not establish permission to publish its video. See https://www.thesportsdb.com/docs_terms_of_use.php (third-party content) and https://www.youtube.com/static?template=terms (embedded playback and restrictions). Source policies require verified identity and applicable scope before automatic publication can be enabled.
