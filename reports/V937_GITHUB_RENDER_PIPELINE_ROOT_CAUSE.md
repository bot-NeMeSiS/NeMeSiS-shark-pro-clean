# V937 GitHub Render Pipeline Root Cause

## Decision

The failed deployment guard was caused by an invalid CI execution order, not by V937 product code or Render runtime.

## Evidence

- Repository: `bot-NeMeSiS/NeMeSiS-shark-pro-clean`.
- Failed workflow: `Render Deploy Guard`, run `29365094877`.
- Workflow file: `.github/workflows/render-deploy.yml`.
- Job: `deploy`.
- Failed step: `Validate before deploy`.
- Command that exposed the defect: `python tools/check_v915_automated_company_workforce.py`.
- Exception: `ModuleNotFoundError: No module named 'flask'`.
- Source location in the log: `tools/check_v915_automated_company_workforce.py`, during import of `app.py`.

The workflow configured Python but did not install `requirements.txt` before importing the application. The validation step therefore failed before Flask was available. The following steps were skipped by GitHub Actions: `Trigger Render deploy hook`, `Wait for Render`, and `Verify runtime version`.

## Root cause

CI treated interpreter setup as dependency setup. Those are separate operations. A production import was executed before the production dependency manifest had been installed.

## Scope

No DB, persistent disk, Telegram, Stripe, product view, or runtime behavior caused this failure. No V938 was created.
