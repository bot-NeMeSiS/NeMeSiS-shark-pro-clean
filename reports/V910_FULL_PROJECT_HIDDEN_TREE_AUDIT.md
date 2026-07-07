# V910 Full Project Hidden Tree Audit

- version: `V910_FULL_PROJECT_HIDDEN_AUDIT_ROUTE_NOT_FOUND_BROWSER_QA_READY_FINAL`
- generated_at: `2026-07-07T23:35:15`
- total_files_detected: `39299`
- hidden_directories_detected: `520`
- local_databases_detected: `80`
- zip_files_detected: `119`
- log_files_detected: `0`
- env_like_files_detected: `27`
- pycache_files_detected: `1239`

## Hidden directories reviewed
- `.agents`
- `.git`
- `.git/hooks`
- `.git/info`
- `.git/logs`
- `.git/logs/refs`
- `.git/logs/refs/heads`
- `.git/logs/refs/remotes`
- `.git/logs/refs/remotes/origin`
- `.git/objects`
- `.git/objects/00`
- `.git/objects/01`
- `.git/objects/02`
- `.git/objects/03`
- `.git/objects/04`
- `.git/objects/05`
- `.git/objects/06`
- `.git/objects/07`
- `.git/objects/08`
- `.git/objects/09`
- `.git/objects/0a`
- `.git/objects/0b`
- `.git/objects/0c`
- `.git/objects/0d`
- `.git/objects/0e`
- `.git/objects/0f`
- `.git/objects/10`
- `.git/objects/11`
- `.git/objects/12`
- `.git/objects/13`
- `.git/objects/14`
- `.git/objects/15`
- `.git/objects/16`
- `.git/objects/17`
- `.git/objects/18`
- `.git/objects/19`
- `.git/objects/1a`
- `.git/objects/1b`
- `.git/objects/1c`
- `.git/objects/1d`
- `.git/objects/1e`
- `.git/objects/1f`
- `.git/objects/20`
- `.git/objects/21`
- `.git/objects/22`
- `.git/objects/23`
- `.git/objects/24`
- `.git/objects/25`
- `.git/objects/26`
- `.git/objects/27`
- `.git/objects/28`
- `.git/objects/29`
- `.git/objects/2a`
- `.git/objects/2b`
- `.git/objects/2c`
- `.git/objects/2d`
- `.git/objects/2e`
- `.git/objects/2f`
- `.git/objects/30`
- `.git/objects/31`
- `.git/objects/32`
- `.git/objects/33`
- `.git/objects/34`
- `.git/objects/35`
- `.git/objects/36`
- `.git/objects/37`
- `.git/objects/38`
- `.git/objects/39`
- `.git/objects/3a`
- `.git/objects/3b`
- `.git/objects/3c`
- `.git/objects/3d`
- `.git/objects/3e`
- `.git/objects/3f`
- `.git/objects/40`
- `.git/objects/41`
- `.git/objects/42`
- `.git/objects/43`
- `.git/objects/44`
- `.git/objects/45`

## Dangerous/local-only files detected
- DB/local sqlite files stay out of the clean ZIP: `80`
- ZIP files stay out of the clean ZIP: `119`
- logs stay out of the clean ZIP: `0`
- `.env` real files stay out of the clean ZIP. Env-like files found: `.env.example, .env.render.clean, env.example, release_output/V895_DEPLOY_ROOT_FROM_V894_ZIP_READY/.env.example, release_output/V895_DEPLOY_ROOT_FROM_V894_ZIP_READY/.env.render.clean, release_output/V898_DEPLOY_ROOT_CONTENTS/.env.example, release_output/V898_DEPLOY_ROOT_CONTENTS/.env.render.clean, release_output/V902B_DEPLOY_ROOT_CONTENTS/.env.example, release_output/V902B_DEPLOY_ROOT_CONTENTS/.env.render.clean, release_output/V902_DEPLOY_ROOT_CONTENTS/.env.example, release_output/V902_DEPLOY_ROOT_CONTENTS/.env.render.clean, release_output/V903_DEPLOY_ROOT_CONTENTS/.env.example, release_output/V903_DEPLOY_ROOT_CONTENTS/.env.render.clean, release_output/V904_DEPLOY_ROOT_CONTENTS/.env.example, release_output/V904_DEPLOY_ROOT_CONTENTS/.env.render.clean, release_output/V905_DEPLOY_ROOT_CONTENTS/.env.example, release_output/V905_DEPLOY_ROOT_CONTENTS/.env.render.clean, release_output/V906B_DEPLOY_ROOT_CONTENTS/.env.example, release_output/V906B_DEPLOY_ROOT_CONTENTS/.env.render.clean, release_output/V906_DEPLOY_ROOT_CONTENTS/.env.example, release_output/V906_DEPLOY_ROOT_CONTENTS/.env.render.clean, release_output/V907_DEPLOY_ROOT_CONTENTS/.env.example, release_output/V907_DEPLOY_ROOT_CONTENTS/.env.render.clean, release_output/V908_DEPLOY_ROOT_CONTENTS/.env.example, release_output/V908_DEPLOY_ROOT_CONTENTS/.env.render.clean, release_output/V909_DEPLOY_ROOT_CONTENTS/.env.example, release_output/V909_DEPLOY_ROOT_CONTENTS/.env.render.clean`

## Included in clean release
- `app.py`
- `VERSION.txt`
- `requirements.txt`
- `templates`
- `static`
- `engines`
- `tools`
- `reports`
- `reference_images`
- `browser_qa`
- `.github/workflows/browser-qa.yml`

## Excluded from clean release
- `.git`
- `.pytest_cache`
- `.venv`
- `__pycache__`
- `archive_legacy`
- `backups`
- `logs`
- `node_modules`
- `release_output`
- `tmp`
- `v636work`

## Human action
No destructive cleanup was executed. Local DBs, caches and hidden folders are documented and excluded from release packaging.
