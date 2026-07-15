# V937 GitHub Actions Preflight Fix

## Corrected order

The V937 guard now runs this sequence:

1. Official checkout.
2. Python `3.11.9`, matching Render.
3. Safe pip cache keyed by `requirements.txt`.
4. pip upgrade.
5. Production dependency installation from `requirements.txt`.
6. Installed import and `app.py` import checks.
7. Release version and expected SHA capture.
8. Python compile.
9. Complete Jinja parse.
10. Critical V937 checks.
11. Navigation Integrity.
12. Continuous Sentinel.
13. Secret Guard.
14. Route and link audits.
15. Release and manifest identity.
16. Event/ref authorization.

No application import occurs before dependency installation.

## Regression guard

`tools/check_v937_github_render_pipeline.py` verifies the step order and executes the pipeline certifier in dry-run mode. It fails if dependency installation is absent or appears after import validation.

## Real GitHub evidence

Workflow dispatch run: `29374356189`.

- `preflight`: `success`.
- `pipeline-dry-run`: `success`.
- `certify-production`: `skipped`, expected for dry-run.
- Production dependencies: installed before imports.
- Compile, Jinja, V937 checks, Navigation Integrity, Sentinel, Secret Guard, route/link audits, and release identity: passed.
- Dry-run status: `DRY_RUN_PASS`.
- Network requests: `0`.
- Deploy requested: `false`.
- DB writes: `0`.
- Telegram sends: `0`.
- Stripe actions: `0`.

Evidence URL: https://github.com/bot-NeMeSiS/NeMeSiS-shark-pro-clean/actions/runs/29374356189

## Legacy smoke compatibility

The PR exposed four independent failures in the historical smoke suite. They were corrected without changing product behavior:

- two version assertions frozen at V717/V729 now validate the release identity from `VERSION.txt`;
- the Cron authorization test now uses `X-Automation-Secret` with a CI-only placeholder instead of a query string;
- the home test distinguishes visible customer text from the required cache-busting version in asset URLs;
- the duplicate `/admin/client-screens` registration was removed while preserving the first and already effective destination.

Local result after correction: `30 passed`. The final added regression prevents the invalid SHARK pathname regular expression found by real Browser QA from returning.
