@echo off
setlocal
cd /d "%~dp0\.."
if "%BROWSER_QA_BASE_URL%"=="" set BROWSER_QA_BASE_URL=https://bot-apuestas-crgf.onrender.com
python -m pip install -r browser_qa\playwright_requirements.txt
python -m playwright install chromium
python tools\check_browser_qa_environment.py
python tools\run_browser_reference_qa.py --base-url "%BROWSER_QA_BASE_URL%" --output reports/browser_qa_render --mobile --desktop --write-json
endlocal
