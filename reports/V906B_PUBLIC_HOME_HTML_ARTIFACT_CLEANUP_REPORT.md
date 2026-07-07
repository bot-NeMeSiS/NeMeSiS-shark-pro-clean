# V906B Public Home HTML Artifact Cleanup Report

## Version

V906B_PUBLIC_HOME_HTML_ARTIFACT_CLEANUP_FINAL

## Base

Local workspace was on V906_REAL_BROWSER_QA_SCREENSHOT_REFERENCE_COMPARISON_FINAL when this hotfix started. Production Render was checked at `/api/runtime-version` and was still serving V905_FINAL_REFERENCE_GAPS_BROWSER_QA_AND_BOM_FIX_FINAL with `version_files_match=true` and `deployment_alignment_status=aligned_local_files`.

## Artifact Found

Render production `/` was checked during this hotfix and still showed visible literal artifacts before the public content:

```
`r`n `r`n
```

The local rendered `/` response after the V906B cleanup does not reproduce that artifact; it starts cleanly with `<!doctype html>`.

The concrete local residue found was in `templates/base.html`: the V902B/V903/V904 version comments contained literal PowerShell newline artifacts:

`<!-- ... -->`r`n  <!-- ... -->`r`n  <!-- ... -->`

Those literals were not needed and were removed. This is the exact class of artifact that can surface as visible `rn` text when HTML is cached, transformed, copied, or minified incorrectly.

## BOM Found

`static/app.css` had a UTF-8 BOM. It was rewritten as UTF-8 without BOM.

## Files Updated

- `VERSION.txt`
- `APP_VERSION`
- `app.py`
- `templates/base.html`
- `static/app.css`
- `tools/check_no_visible_artifacts.py`
- `tools/check_v906b_public_home_html_artifact_cleanup.py`
- `tools/check_v905_bom_reference_browser_qa.py`
- `tools/print_release_identity.py`
- `tools/check_deploy_root_identity.py`

## Runtime

Local runtime now returns:

- `version`: V906B_PUBLIC_HOME_HTML_ARTIFACT_CLEANUP_FINAL
- `app_version`: V906B_PUBLIC_HOME_HTML_ARTIFACT_CLEANUP_FINAL
- `version_txt`: V906B_PUBLIC_HOME_HTML_ARTIFACT_CLEANUP_FINAL
- `version_files_match`: true
- `deployment_alignment_status`: aligned_local_files
- `has_v906b_public_home_html_artifact_cleanup`: true

## Scope Control

No product redesign was performed. No secrets, DB data, users, sessions, payments, Telegram delivery logic, or Render Cron configuration were touched.
