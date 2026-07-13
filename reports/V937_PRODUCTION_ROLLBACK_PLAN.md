# V937 Production Rollback Plan

Prepared: 2026-07-13 07:48 Madrid

## Baseline before merge

- Origin main SHA: `6dafad26de43e5217f8b601d449802767c9c23f8`
- Production runtime observed before deploy: V936 with a controlled `FileNotFoundError` runtime response
- Candidate branch: `chatgpt/v937-product-perfection`
- Candidate SHA before certification commit: `2500491262a8bbe246823163f1e361b008bc21d7`
- Backup branch target: `backup/pre-v937-production`

## Rollback rule

Rollback changes application code only. It must never delete, replace, restore or remount the production database or persistent disk.

## Procedure

1. Confirm the backup branch still points to `6dafad26de43e5217f8b601d449802767c9c23f8`.
2. Create a normal rollback commit on `main` that restores the application tree from that SHA. Do not force-push.
3. Push the rollback commit to `origin/main` and deploy that commit through the existing Render service.
4. Keep the persistent disk, mount path, `DB_PATH`, plan and cron jobs unchanged.
5. Verify `/api/runtime-version`, `/`, `/cliente-login`, `/admin-login`, `/manifest.json` and `/service-worker.js`.
6. Verify client login and one protected admin route with an authorized test account.
7. Confirm no user, membership, session or sports record was replaced.

## Stop conditions

Rollback immediately if V937 causes a critical 5xx loop, login failure, missing persistent DB, secret exposure, incorrect charge path, uncontrolled Telegram send, public incomplete pick, or stale data presented as current.

Render service settings, environment presence and disk mount must be read back from Render before final GO. They are not inferred from local files.

