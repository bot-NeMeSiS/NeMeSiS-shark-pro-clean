# V921 Next Steps

1. Deploy V921 when ready.
2. Confirm /api/runtime-version returns V921.
3. Run GitHub Actions -> Browser QA with base_url=https://bot-apuestas-crgf.onrender.com.
4. Download artifact browser-qa-render.
5. Copy artifact contents into reports/browser_qa_render/.
6. Run:
   python tools/import_browser_qa_results.py --input reports/browser_qa_render --update-runtime-data
7. Re-run:
   python tools/check_v921_browser_qa_artifact_run.py
8. Only then review READY_FOR_CODEX visual queue items.

Reminder:
- Do not declare pixel-perfect without screenshots.
- Do not unlock visual items without screenshot_path.
- Do not expose secrets in reports, screenshots, chats or workflows.
