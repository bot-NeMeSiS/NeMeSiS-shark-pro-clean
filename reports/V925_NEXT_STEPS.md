# V925 Next Steps

## Deploy

1. Upload the **contents inside** `release_output/V925_DEPLOY_ROOT_CONTENTS` to the GitHub repository root on `main`. Do not upload the parent folder itself.
2. Confirm that GitHub root directly contains `app.py`, `VERSION.txt`, `requirements.txt`, `templates/`, `static/`, `engines/`, `tools/`, `reports/`, `reference_images/`, `browser_qa/` and `automation_workforce/`.
3. Trigger the authorized Render deployment or use the configured auto-deploy flow.
4. Open `/api/runtime-version` and require the V925 identity, `version_files_match=true` and `deployment_alignment_status=aligned_local_files`.
5. Do not call V925 production until that endpoint confirms it.

## Post-deploy video review

Record desktop and mobile navigation through:

- public home and its single hero;
- `/app` after login;
- calendar, live and picks;
- SHARK and Telegram safe states;
- profile and memberships;
- admin dashboard, Workforce, Sentinel, issues, outbox and Telegram command center.

Check for first-viewport empty space, clipped labels, accidental horizontal scroll, repeated navigation, data without a source and any client element inside admin.

## Browser QA evidence

Run the Browser QA workflow against V925, download/import its artifacts, and only then move matching visual queue items from `BLOCKED_NO_SCREENSHOT`. Pixel-perfect remains false until valid screenshots and comparisons exist.
