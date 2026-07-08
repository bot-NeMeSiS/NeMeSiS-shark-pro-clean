# Browser QA Pipeline - NeMeSiS SHARK PRO

Version: `V913_BROWSER_QA_EXECUTION_STATUS_TRUTH_AND_RUNTIME_CLEANUP_FINAL`

This folder prepares real screenshot QA without storing secrets or touching production data.

## Local Run

From the project root:

```powershell
pip install -r browser_qa/playwright_requirements.txt
python -m playwright install chromium
python tools/check_browser_qa_environment.py
python tools/run_browser_reference_qa.py --base-url https://bot-apuestas-crgf.onrender.com --output reports/browser_qa_render --mobile --desktop --write-json
python tools/import_browser_qa_results.py --input reports/browser_qa_render --update-runtime-data
```

PowerShell helper:

```powershell
.\browser_qa\run_local_browser_qa.ps1
```

Windows cmd helper:

```bat
browser_qa\run_local_browser_qa.bat
```

Linux/macOS helper:

```bash
sh browser_qa/run_local_browser_qa.sh
```

## Output

The expected output is:

- `reports/browser_qa_render/browser_qa_result.json`
- `reports/browser_qa_render/reference_comparison.json`
- `reports/browser_qa_render/desktop/`
- `reports/browser_qa_render/mobile/`
- `data/runtime/autonomous_company_sentinel/browser_qa_status.json`
- `data/runtime/autonomous_company_sentinel/browser_reference_comparison.json`
- `data/runtime/autonomous_company_sentinel/reference_gap_report.json`
- `data/runtime/autonomous_company_sentinel/visual_fix_queue.json`

If the capture was executed outside this workspace, place the generated files under
`reports/browser_qa_render/` and run:

```powershell
python tools/import_browser_qa_results.py --input reports/browser_qa_render --update-runtime-data
```

## Safety

This pipeline does not use real secrets, does not send Telegram messages, does not touch payments, and does not write destructive database changes. Protected admin routes are captured only as safe login/redirect/control screens unless explicit credentials are provided outside this repository.

No pixel-perfect claim is allowed until real screenshots exist and are compared against `reference_images/reference_manifest.json`.
