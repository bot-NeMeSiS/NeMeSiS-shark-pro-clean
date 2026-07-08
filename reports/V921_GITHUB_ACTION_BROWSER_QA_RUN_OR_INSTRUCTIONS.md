# V921 GitHub Action Browser QA Run Or Instructions

Version: V921_AUTOMATED_BROWSER_QA_ARTIFACT_RUN_IMPORT_AND_VISUAL_QUEUE_UNLOCK_FINAL

GitHub Action status: GITHUB_ACTION_MANUAL_RUN_REQUIRED

Workflow found:
- .github/workflows/browser-qa.yml
- workflow_dispatch: available
- installs Playwright: yes
- installs Chromium: yes
- uploads Browser QA artifacts: yes

Codex did not trigger GitHub Actions from this local session.

Manual steps:
1. Open GitHub repository bot-NeMeSiS/NeMeSiS-shark-pro-clean.
2. Go to Actions.
3. Select Browser QA.
4. Click Run workflow.
5. Use base_url: https://bot-apuestas-crgf.onrender.com
6. Wait for completion.
7. Download artifact browser-qa-render.
8. Place artifact contents in reports/browser_qa_render/.
9. Run: python tools/import_browser_qa_results.py --input reports/browser_qa_render --update-runtime-data

No secrets are required for public screenshot capture.
