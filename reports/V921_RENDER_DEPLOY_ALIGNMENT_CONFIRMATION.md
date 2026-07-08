# V921 Render Deploy Alignment Confirmation

Version local: V921_AUTOMATED_BROWSER_QA_ARTIFACT_RUN_IMPORT_AND_VISUAL_QUEUE_UNLOCK_FINAL

Render runtime real checked: V917_WORKFORCE_FIRST_FULL_AUTOMATED_RUN_AND_REPORTING_FINAL

Alignment status:
- V921 local confirmed: yes.
- V921 deploy root confirmed: yes.
- V921 ZIP confirmed: yes.
- Production V921 confirmed: no.
- Push performed: no.
- Deploy performed: no.

Why production is not declared V921:
- /api/runtime-version did not return V921 during this check.
- The currently observed production runtime returned V917, despite the attached note saying V920.
- No production claim is made until Render returns V921.

Local Browser QA state:
- Playwright available: false.
- Browser QA local: attempted previously, but PACKAGE_MISSING.
- Artifacts found: true, JSON only.
- Valid screenshots: 0.
- Visual queue: 18 total / 18 blocked / 0 ready.
- Pixel-perfect allowed: false.

Deploy root:
- release_output/V921_DEPLOY_ROOT_CONTENTS
- Contains app.py, VERSION.txt, APP_VERSION, requirements.txt, templates, static, engines, tools, reports, reference_images, browser_qa, automation_workforce and .github/workflows.
- forbidden_count: 0.
- missing_required_root: [].

ZIP:
- release_output/NeMeSiS_SHARK_PRO_V921_AUTOMATED_BROWSER_QA_ARTIFACT_RUN_IMPORT_AND_VISUAL_QUEUE_UNLOCK_FINAL_RENDER_READY.zip
- forbidden_count: 0.
- missing_required_root: [].

Git status:
- git executable was not available in this session.
- No commit, push or deploy was executed.

Exact steps for Damian:
1. Open release_output/V921_DEPLOY_ROOT_CONTENTS.
2. Copy the contents inside that folder, not the folder itself.
3. Paste/commit those contents into the root of GitHub repo bot-NeMeSiS/NeMeSiS-shark-pro-clean on branch main.
4. Confirm GitHub root VERSION.txt is V921_AUTOMATED_BROWSER_QA_ARTIFACT_RUN_IMPORT_AND_VISUAL_QUEUE_UNLOCK_FINAL.
5. Confirm GitHub root app.py APP_VERSION is V921_AUTOMATED_BROWSER_QA_ARTIFACT_RUN_IMPORT_AND_VISUAL_QUEUE_UNLOCK_FINAL.
6. Deploy on Render.
7. Open https://bot-apuestas-crgf.onrender.com/api/runtime-version.
8. Confirm version, app_version and runtime_version all return V921.
9. Run GitHub Actions -> Browser QA with base_url=https://bot-apuestas-crgf.onrender.com.
10. Download browser-qa-render artifact, place contents in reports/browser_qa_render, then run the importer before starting visual fixes.

Safety reminders:
- Do not upload secrets or .env real.
- Do not declare pixel-perfect without screenshots.
- Do not unlock visual queue items without a valid screenshot_path.
