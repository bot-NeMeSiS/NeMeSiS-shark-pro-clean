# V909 Next Steps

Version: `V909_BROWSER_QA_EXECUTION_PIPELINE_AND_VISUAL_FIX_QUEUE_FINAL`

1. Deploy V909 after uploading the deploy root contents.
2. Confirm `/api/runtime-version` returns V909.
3. Run Browser QA locally or with GitHub Actions.
4. Download artifacts from `reports/browser_qa_render/`.
5. Review `visual_fix_queue.json`.
6. Create the next visual fix pass from screenshot-backed `READY_FOR_CODEX` items.

No production claim is allowed until Render confirms V909. No pixel-perfect claim is allowed until screenshots exist and are reviewed.
