# V937 Deploy Security And Rollback

## Security controls in code

- Workflow permission: `contents: read` only.
- Official GitHub actions only: checkout, setup-python, upload-artifact.
- Checkout credentials are not persisted.
- Pull requests receive no production secrets.
- CI uses a disposable `/tmp` DB path and disables background jobs, auto-picks, and Telegram sends.
- Concurrency cancels obsolete runs for the same ref.
- Preflight timeout: 40 minutes.
- Dry-run timeout: 5 minutes.
- Production certification timeout: 90 minutes.
- Production certification is limited to `main` pushes or an authorized `verify_existing` run on `main`.
- Expected SHA is captured from `GITHUB_SHA` and compared with Render runtime.
- Secret Guard is tracked and executed in CI with zero findings.

## External security state

At initial audit time:

- Repository Actions secrets: none.
- GitHub environments: none.
- `main` branch protection: none.
- GitHub deployment records: none.

After the green PR checks, GitHub was configured and read back successfully:

- strict required checks on `main`: `preflight`, `qa`, `smoke`;
- one pull-request approval;
- stale review dismissal and conversation resolution;
- force pushes disabled;
- branch deletion disabled;
- `production` environment limited to protected branches;
- no environment reviewer, preserving optional manual approval.

No repository secret was added because Render Auto-Deploy does not require one.

## Rollback

Rollback reference: `c578199e7282ece9b8aef6cd43af7622fbe474b1`.

On failed production certification:

1. Mark `NO-GO` and stop promotion.
2. Deploy the known previous commit through the existing Render/Git integration.
3. Keep the DB, persistent disk, `DB_PATH`, mount path, service, and plan unchanged.
4. Do not recreate the service and do not restore/replace the DB.
5. Verify exact runtime SHA, login, critical routes, service worker, and Sentinel.

No automatic destructive rollback is implemented. Enabling one requires separate explicit authorization.
