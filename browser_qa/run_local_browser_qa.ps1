$ErrorActionPreference = "Stop"
$Root = Split-Path -Parent (Split-Path -Parent $MyInvocation.MyCommand.Path)
Set-Location $Root

if (-not $env:BROWSER_QA_BASE_URL) {
  $env:BROWSER_QA_BASE_URL = "https://bot-apuestas-crgf.onrender.com"
}

python -m pip install -r browser_qa/playwright_requirements.txt
python -m playwright install chromium
python tools/check_browser_qa_environment.py
python tools/run_browser_reference_qa.py --base-url $env:BROWSER_QA_BASE_URL --output reports/browser_qa_render --mobile --desktop --write-json
python tools/import_browser_qa_results.py --input reports/browser_qa_render --update-runtime-data
