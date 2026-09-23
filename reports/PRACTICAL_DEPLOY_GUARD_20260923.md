# Practical Deploy Guard · 23/09/2026

## Decision

The automatic production guard remains mandatory, but routine pushes no longer wait
one hour before Quality Sentinel.

## Routine main push

- exact-SHA Render deployment verification;
- production samples at 0, 60, 180 and 300 seconds;
- existing route, Sports Truth, stale/false-LIVE, secrets and 5xx checks;
- Production Quality Sentinel immediately after the 5-minute observation.

## Sensitive release

The existing manual `verify_existing` workflow keeps the extended
`0,120,300,900,3600` observation window. ChatGPT decides when the extended gate is
justified (for example Telegram transport, payments, data/provider lifecycle or other
high-risk runtime changes). The founder does not need to manage offsets or workflow
details.

## Preserved safeguards

No deploy hook, no manual duplicate deploy, exact SHA remains mandatory, preflight and
Smoke remain unchanged, Secret Guard and Continuous Sentinel remain unchanged, and the
post-deploy certifier stays read-only.
