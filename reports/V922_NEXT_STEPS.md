# V922 Next Steps

1. Re-run Browser QA and make sure artifacts include actual image files under reports/browser_qa_render/desktop/ and reports/browser_qa_render/mobile/.
2. Re-run tools/import_browser_qa_results.py --input reports/browser_qa_render --update-runtime-data.
3. Confirm v922_valid_screenshots_count is greater than 0.
4. Review visual_fix_queue.json and apply safe visual fixes only to items with valid screenshot_path.
5. Do not claim pixel-perfect until screenshots and comparison evidence are sufficient.
