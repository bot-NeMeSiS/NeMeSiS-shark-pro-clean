# V906B Visible Artifacts QA

## Checks Added

Created `tools/check_no_visible_artifacts.py` to detect:

- UTF-8 BOM in critical files.
- visible `rn rn`, `` `r`n ``, `\\r\\n`, or `NeMeSiS SHARK PRO rn` artifacts.
- visible `None`, `null`, or `undefined` near the top of `/`.
- common mojibake markers.
- characters before the clean HTML/template start.

Created `tools/check_v906b_public_home_html_artifact_cleanup.py` to validate:

- V906B versioning.
- `VERSION.txt` without BOM.
- `static/app.css` without BOM.
- runtime alignment.
- public `/` starts with `<!doctype html>`.
- public `/` has no visible BOM, `rn`, `None/null/undefined`, or common mojibake near the top.
- `templates/base.html` no longer contains the literal `` `r`n `` residue.

## Local Evidence

Local `/` starts with:

`<!doctype html>`

Local `/api/runtime-version` reports:

- `version_files_match=true`
- `deployment_alignment_status=aligned_local_files`

## Render Evidence

Render real was checked at:

`https://bot-apuestas-crgf.onrender.com/api/runtime-version`

It still serves V905 until the V906B package is deployed manually. The public Render homepage was also checked and still shows literal `` `r`n `r`n `` at the top. Do not declare production fixed until Render reports V906B and the public homepage no longer shows `rn` or `` `r`n ``.

## Result

Visible artifact check passes locally.
