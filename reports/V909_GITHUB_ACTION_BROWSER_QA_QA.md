# V909 GitHub Action Browser QA QA

Version: `V909_BROWSER_QA_EXECUTION_PIPELINE_AND_VISUAL_FIX_QUEUE_FINAL`

## Workflow

Created manual workflow: `.github/workflows/browser-qa.yml`

## Safety

- Trigger: `workflow_dispatch` only.
- Base URL: configurable input.
- No secrets required by default.
- No tokens are written in the workflow.
- Artifacts uploaded: screenshots, browser QA result, comparison files, and visual queue.

## Expected Use

Run the workflow manually after the target version is deployed to Render. Use `https://bot-apuestas-crgf.onrender.com` as base URL unless testing another authorized environment.
