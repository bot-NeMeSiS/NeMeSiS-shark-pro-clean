# V937 Render Auto-Deploy Strategy

## Selected strategy

Primary strategy: **Render Auto-Deploy from `main`**.

Observed repository history showed Render receiving the final `main` SHA even when the former GitHub deploy-hook step was skipped. No GitHub deployment records, repository Actions secrets, or deploy-hook evidence were present. The coherent single mechanism is therefore Render's repository-linked Auto-Deploy.

The repaired workflow never calls a Render deploy hook. It validates pull requests and `main`, then observes Render until `/api/runtime-version` reports both the exact V937 version and the exact expected Git SHA.

## Trigger and deployment boundaries

- Pull request to `main`: preflight only.
- Push to `main`: preflight, then read-only production certification.
- Manual `dry_run`: preflight plus zero-effect dry-run.
- Manual `verify_existing`: restricted to `main` and performs read-only certification.
- Other branches cannot run production certification.

## Secrets

No deploy secret is required for Strategy A. `PUBLIC_BASE_URL` is public configuration, not a secret. The workflow does not consume `RENDER_DEPLOY_HOOK_URL`, `RENDER_API_KEY`, DB credentials, Telegram credentials, Stripe credentials, cookies, or sessions.

If Strategy B is ever selected later, Auto-Deploy must first be disabled and only then may a masked `RENDER_DEPLOY_HOOK_URL` secret be introduced. Both mechanisms must never be active together.

## Required repository controls

The audit found no active branch protection and no pre-existing GitHub `production` environment. Before merging PR #1:

- protect `main`;
- require the `preflight` status check;
- require pull-request review;
- reject force pushes and branch deletion;
- create/protect the `production` environment;
- optionally require a human approval for production certification.

These remote controls are intentionally not represented as completed until GitHub confirms them.
