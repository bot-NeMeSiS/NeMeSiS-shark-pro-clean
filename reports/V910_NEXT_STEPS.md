# V910 Next Steps

1. Deploy V910 only by copying the contents of `release_output/V910_DEPLOY_ROOT_CONTENTS` to GitHub root.
2. In Render, run Manual Deploy with Clear build cache.
3. Confirm `/api/runtime-version` returns `V910_FULL_PROJECT_HIDDEN_AUDIT_ROUTE_NOT_FOUND_BROWSER_QA_READY_FINAL`.
4. Execute Browser QA in an authorized Playwright environment.
5. Use `visual_fix_queue.json` to close screenshot-based gaps; do not claim pixel-perfect without screenshots.
