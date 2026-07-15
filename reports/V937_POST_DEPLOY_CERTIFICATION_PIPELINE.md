# V937 Post-Deploy Certification Pipeline

## Certifier

`tools/v937_post_deploy_certification.py` is a read-only production gate. It never deploys, writes DB data, sends Telegram, or starts Stripe operations.

It waits for:

- exact version `V937_PRODUCT_PERFECTION_FULL_ECOSYSTEM_LAUNCH_CLOSEOUT_FINAL`;
- exact expected Git SHA;
- aligned version files;
- V937 CSS cache busting;
- `NEMESIS_CACHE_V937` service worker identity;
- safe critical routes and safe 404 behavior;
- Sentinel without active issues;
- no public stale matches;
- no false live events;
- correct idle/live polling policy;
- no exposed secret patterns.

Possible terminal states are `DEPLOY_CONFIRMED`, `DEPLOY_TIMEOUT`, `WRONG_SHA`, `RUNTIME_ERROR`, `ASSET_MISMATCH`, and `HEALTH_FAILURE`.

## Production evidence for the current V937 hotfix

The already deployed product hotfix was certified at immediate, +2 minute, and +5 minute samples before this pipeline-only branch was prepared:

- Expected SHA: `261213048fe3f92a58488b1119092922cdfc5db5`.
- Reported Render SHA: `261213048fe3f92a58488b1119092922cdfc5db5`.
- Version: exact V937.
- Files: matched and aligned.
- Service worker: `NEMESIS_CACHE_V937`.
- Sentinel active issues: `0`.
- Public matches: `139` in the observed payload.
- Public live events: `0`.
- False live events: `0`.
- Stale diagnostics: `4`, retained only for internal diagnosis.
- Stale records in public arrays: `0`.
- Idle polling: `180` seconds.
- Critical-route 5xx responses: `0`.
- Sports synchronization: fresh during the successful observation window.

The four stale records were excluded from public arrays, counters, cards, badges, KPIs, SHARK, Telegram candidates, and public APIs. A valid live record remains admissible only when real live evidence and valid freshness are present.

## Monitoring windows

On a future `main` push the certifier checks immediately and at +2, +5, +15, and +60 minutes. The deployment wait is bounded to 15 minutes and the job to 90 minutes.

## Reduced production Browser QA

The public V937 deployment was opened in a real browser at `1440x900` and `390x844` for Home, Calendar, Live, and Picks:

- eight route/profile checks rendered the expected page title and H1;
- desktop navigation was visible only on desktop;
- mobile header and five-destination bottom navigation were visible only on mobile;
- global horizontal overflow: `0`;
- controls clipped outside intentional horizontal scrollers: `0`;
- visible internal-error states: `0`.

The browser console exposed one real pre-existing defect: an unterminated regular expression in the SHARK route guard inside `templates/base.html`. The branch replaces it with a deterministic pathname comparison and adds a regression test. Local result after the fix: `30 passed`, complete Jinja parse, and Sentinel `10.0` with zero issues. Production will retain the old JavaScript until PR #1 is approved, merged, and deployed.

The in-app browser screenshot command timed out twice, including in a clean tab. Therefore no new screenshot artifact is claimed. DOM/responsive Browser QA is complete; visual screenshot evidence remains `NOT_TESTABLE_IN_CURRENT_BROWSER_CAPTURE`.

## Honest limitations

- The pipeline branch itself has not been merged or deployed.
- The successful production deployment duration cannot be attributed to this new workflow because Render had already deployed the product hotfix independently.
- A later shell recheck was blocked by local network access and is recorded as `network_unavailable_from_shell`, not as a production regression.
- Reduced HTTP and responsive DOM QA passed. A new visual Browser QA screenshot set was not produced because the browser capture command timed out.
- `/shark` showed approximately 7-8 second latency in the production sample, above the 5 second warning threshold. It is a residual performance warning, not a CI/deploy integrity failure.
