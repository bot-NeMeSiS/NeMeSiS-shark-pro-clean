# V915 Final Secret Guard Deploy QA

- Version: `V915_AUTOMATED_COMPANY_WORKFORCE_RENDER_DEPLOY_PIPELINE_FINAL`
- Scope revisado: `app.py`, `tools/`, `engines/`, `automation_workforce/`, `reports/`, `templates/`, `.github/`, `browser_qa/`.
- Politica: permitir solo placeholders o estados enmascarados.

## Permitido

- `***hidden***`
- `***configured***`
- `***missing***`
- `${{ secrets.RENDER_DEPLOY_HOOK_URL }}`
- Nombres de variables de entorno sin valor real.

## No permitido

- Tokens reales.
- Deploy hook real.
- `AUTOMATION_SECRET` real.
- `RENDER_API_KEY` real.
- `TELEGRAM_BOT_TOKEN` real.
- `STRIPE_SECRET` real.
- `OPENAI_API_KEY` real.

## Resultado esperado

Ejecutar:

```bash
python automation_workforce/security_secret_guard.py --dry-run
python tools/check_v915_automated_company_workforce.py
```

Debe devolver `findings_count=0` y check V915 OK.

