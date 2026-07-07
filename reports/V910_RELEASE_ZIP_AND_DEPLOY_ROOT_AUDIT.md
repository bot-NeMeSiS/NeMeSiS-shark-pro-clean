# V910 Release ZIP And Deploy Root Audit

- version: `V910_FULL_PROJECT_HIDDEN_AUDIT_ROUTE_NOT_FOUND_BROWSER_QA_READY_FINAL`
- build_tool: `tools/build_clean_release.py`
- audit_tool: `tools/audit_release_zip.py`
- required_root: `app.py, VERSION.txt, requirements.txt, templates, static, engines, tools, reports, reference_images, browser_qa, .github/workflows/browser-qa.yml`
- excluded: `.git, .pytest_cache, .venv, __pycache__, archive_legacy, backups, logs, node_modules, release_output, tmp, v636work`
- deploy_root_target: `release_output/V910_DEPLOY_ROOT_CONTENTS`

## Expected release result
- `forbidden_count=0`
- `missing_required_root=[]`
- no internal ZIPs
- no local DBs
- no real `.env`
- no logs
