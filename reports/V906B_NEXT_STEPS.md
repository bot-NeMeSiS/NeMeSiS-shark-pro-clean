# V906B Next Steps

## Deploy Steps

1. Use the generated ZIP:
   `release_output/NeMeSiS_SHARK_PRO_V906B_PUBLIC_HOME_HTML_ARTIFACT_CLEANUP_FINAL_RENDER_READY.zip`
2. Or copy the prepared deploy root:
   `release_output/V906B_DEPLOY_ROOT_CONTENTS`
3. Paste the internal contents into the GitHub repository root, not inside a nested folder.
4. Confirm GitHub root shows:
   - `app.py`
   - `VERSION.txt`
   - `APP_VERSION`
   - `requirements.txt`
   - `templates/`
   - `static/`
   - `engines/`
   - `tools/`
   - `reports/`
   - `reference_images/`
5. In Render, run Manual Deploy with Clear build cache & deploy.
6. Open:
   `https://bot-apuestas-crgf.onrender.com/api/runtime-version`
7. Confirm:
   - `version=V906B_PUBLIC_HOME_HTML_ARTIFACT_CLEANUP_FINAL`
   - `version_files_match=true`
   - `deployment_alignment_status=aligned_local_files`
8. Open:
   `https://bot-apuestas-crgf.onrender.com/`
9. Confirm the page no longer shows `NeMeSiS SHARK PRO rn rn` or any visible BOM/mojibake artifact.

## If Render Still Shows V905

Check:

- GitHub root was updated with the V906B files.
- `VERSION.txt` in GitHub root says V906B exactly.
- `app.py` in GitHub root has `APP_VERSION = 'V906B_PUBLIC_HOME_HTML_ARTIFACT_CLEANUP_FINAL'`.
- Render is connected to the correct repo and branch.
- Render root directory is empty/correct.
- Build cache was cleared.

