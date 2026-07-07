# V907 Next Steps

## Immediate

1. Deploy V907 only after pushing the clean root contents.
2. Confirm `/api/runtime-version` returns:
   `V907_BROWSER_QA_ENABLEMENT_FIRST_SCREENSHOT_GAP_FIX_FINAL`.
3. In an authorized local/CI environment, install Playwright:

```powershell
.\.venv\Scripts\python.exe -m pip install playwright
.\.venv\Scripts\python.exe -m playwright install chromium
```

4. Start the Flask app locally.
5. Run:

```powershell
.\.venv\Scripts\python.exe tools\run_browser_reference_qa.py --base-url http://127.0.0.1:5000 --output reports/V907_browser_qa --mobile --desktop --admin-safe --no-login-required --write-json
```

## After Screenshots Exist

1. Review `reports/V907_browser_qa/desktop/` and `reports/V907_browser_qa/mobile/`.
2. Review `browser_reference_comparison.json`.
3. Apply only safe visual fixes:
   - overflow;
   - spacing;
   - compact cards;
   - grids;
   - visible copy glitches;
   - admin/client nav isolation.
4. Keep dangerous work in prompts/manual approval.

