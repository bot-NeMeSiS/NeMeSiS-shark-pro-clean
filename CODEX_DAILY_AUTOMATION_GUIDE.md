# Codex Daily Automation Guide

## Objetivo

Mantener NeMeSiS SHARK PRO limpio, validado y preparado para continuar cada día sin arrastrar contexto viejo, ZIPs antiguos ni basura local.

## Uso Diario Recomendado

### Control V725 de hora Madrid

Antes de construir el release, comprobar que todas las horas deportivas pasan por Europe/Madrid:

```bash
python tools/check_madrid_times.py
```

Reglas:

- `2026-06-12T19:00:00Z` debe mostrarse como `21:00` en España.
- `2026-12-12T20:00:00Z` debe mostrarse como `21:00` en España.
- No usar sumas fijas `+1` o `+2`.
- No mostrar ISO, UTC, `Z` ni `+00:00` al cliente.
- Templates y Telegram deben usar `madrid_display`, `madrid_time`, `safe_time` o `display_datetime`.

1. Generar informe y prompt diario:

```bash
python tools/nemesis_daily_codex.py
```

2. Revisar el prompt actualizado:

```bash
reports/CODEX_DAILY_PROMPT_CURRENT.txt
```

3. Auditar el árbol del proyecto:

```bash
python tools/audit_project_tree.py
```

4. Simular purga segura:

```bash
python tools/purge_project_safe.py --dry-run
```

5. Verificar imports, rutas, templates y static:

```bash
python tools/verify_imports_and_routes.py
```

6. Generar ZIP Render Ready:

```bash
python tools/build_clean_release.py
```

7. Auditar ZIP:

```bash
python tools/audit_release_zip.py
```

8. Validar release completo:

```bash
python tools/validate_release.py
```

## Panel Admin

La vista interna está disponible en:

```text
/admin/codex-automation
```

Solo ADMIN. Muestra:

- estado de limpieza
- ZIP actual
- entregables
- Data Memory
- basura segura detectada
- elementos a revisar
- prompt diario para copiar en ChatGPT/Codex

## Regla De Seguridad

No subir nunca a Render:

- `.git`
- `.venv`
- `__pycache__`
- `.pytest_cache`
- bases SQLite locales
- logs
- ZIPs internos
- backups locales
- secretos reales

El ZIP se crea por lista blanca para evitar inclusiones accidentales. Desde V725 se intenta guardar fuera del proyecto en `../releases`; si el sistema no permite escribir fuera, se usa `release_output/`, que queda excluido del propio ZIP.

## Contrato de fiabilidad y despliegue (integracion PR92)

REPARADO != RESUELTO. Para fallos importantes documentar ROOT CAUSE (separada de hipotesis), FIX, REGRESSION TEST rojo antes/verde despues cuando reproducible, PREVENTION, DETECTION y VERIFICATION del SHA/entorno pertinente. Reutilizar incidente Sentinel y evidencia canonica; no cerrar alcance CI/produccion por un PASS local.

check/sprint label != deployed runtime version. Distinguir runtime leido de VERSION.txt/APP_VERSION/app.py, etiqueta historica de sprint/check y version candidata. Una etiqueta V944 con BASE_RUNTIME V940 no demuestra runtime V944. Autoridades ausentes o contradictorias fallan; health200 no acredita despliegue.

MERGE TO MAIN = POSSIBLE PRODUCTION DEPLOY si branch: main + autoDeployTrigger: commit constan en configuracion conocida. Advertir que afecta a web y cron. Separar GIT CHANGE, RELEASE CANDIDATE, MERGE TO MAIN, PRODUCTION DEPLOY y POST-DEPLOY VERIFICATION. No sortear prohibiciones alterando render.yaml o Render. PRs de integracion permanecen DRAFT sin merge ni despliegue hasta autorizacion explicita.

Runtime Reliability, fingerprints ampliados y radar siguen pendientes de implementacion; esta guia no afirma que sus mecanismos ya existan.
