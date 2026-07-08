# V918 Next Steps

## Current State

- V918 local package is prepared.
- Production V917 was externally confirmed before this work.
- Local shell network remains unavailable for direct Render checks.
- Browser QA local runtime is missing Playwright.
- Browser QA JSON artifacts exist, but no screenshot PNG files are available.
- Visual queue remains blocked: 18 blocked, 0 ready.
- Pixel-perfect claim allowed: false.

## Exact Next Action

1. Deploy V918 to Render from the clean deploy root.
2. Confirm `/api/runtime-version` returns:
   V918_WORKFORCE_POST_DEPLOY_BROWSER_QA_ACTIONS_AND_VISUAL_QUEUE_UNLOCK_FINAL
3. Run Browser QA with one of these paths:
   - Local PC with Playwright installed.
   - GitHub Action browser-qa workflow.
   - Import existing Browser QA results only if they include real screenshots.
4. Refresh the visual queue after screenshots exist.

## Do Not Do

- Do not declare pixel-perfect without screenshots.
- Do not unlock visual queue items without screenshot evidence.
- Do not expose deploy hooks or automation secrets.
- Do not send real Telegram messages.
- Do not touch payments or DB destructively.
