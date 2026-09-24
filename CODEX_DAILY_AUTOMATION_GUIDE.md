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

## Contrato de fiabilidad para bugs importantes (addendum 2026-09-23)

FIX != DONE. Esta guia exige ROOT CAUSE, FIX, REGRESSION TEST, PREVENTION, DETECTION y VERIFICATION antes de declarar RESOLVED. Una excepcion por no aplicabilidad debe tener motivo explicito; ausencia de evidencia no es PASS.

- Separar causa confirmada de hipotesis. Asociar incidencia existente, PR, SHA, archivos y evidencia sanitizada.
- Conservar reproduccion: prueba que falla antes y pasa despues, cuando sea tecnicamente reproducible. Los tests existentes sirven si protegen la misma condicion; no duplicarlos ni debilitar aserciones para obtener verde.
- Convertir la clase de fallo en una regla general razonable: historical_success != current_availability; UNKNOWN_VALUE != ZERO_VALUE; health=200 != deployment_certified.
- Asociar deteccion Sentinel y tests al incidente canonico. Reutilizar fingerprint/registro existente; similitud no confirma causa comun. Lecturas de pantalla no cuentan como nuevas ocurrencias.
- Verificar la condicion original y registrar FIX APPLIED / VERIFICATION PASS o FAILED, SHA, fecha, entorno y alcance. Local, CI y produccion son verificaciones separadas; un PASS local no cierra una incidencia cuyo alcance requiere CI o produccion.
- Si falta verificacion exigida, mantener FIXED_PENDING_VERIFICATION. RESOLVED exige evidencia aplicable. Si reaparece, conservar historial y registrar recurrencia.
- No guardar secretos, payloads privados ni tracebacks crudos. No rellenar fechas, contadores, tendencias o causas desconocidas con datos inventados.
- Acciones solo por el registro autorizado; aprobacion Admin para riesgo, limites/reintentos acotados y verificacion posterior. Procesar una cola puede producir envios irreversibles: no equivale a una accion reversible. Sin shell, SQL libre, codigo, despliegues, secretos, borrado de DB ni pagos.

Estado de aplicacion: norma documental activa; su enforcement en runtime y UI queda pendiente de PR91 verde, reconciliacion PR90 y base estable. No implica que el backend actual ya impida todos los cierres sin evidencia. El arreglo local PR91 db3670e7 sigue pendiente de CI y no esta RESOLVED remotamente.
