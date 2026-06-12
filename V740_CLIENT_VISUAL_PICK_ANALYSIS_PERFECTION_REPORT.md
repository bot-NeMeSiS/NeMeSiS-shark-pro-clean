# V740 Client Visual Pick Analysis Perfection

## Versión

`V740_CLIENT_VISUAL_PICK_ANALYSIS_PERFECTION`

## Objetivo

Rematar la experiencia visual del cliente sin tocar la lógica crítica: evitar textos pisados, reforzar escudos, mantener ligas/mercados en castellano y convertir los picks en una lectura profesional con motivo, riesgos y conclusión.

## Cambios aplicados

- Nuevo motor `engines/pick_analysis_experience_engine.py` para enriquecer cada pick con explicación en castellano.
- Nuevo motor `engines/client_visual_perfection_engine.py` para QA visual cliente.
- Nuevo panel admin `/admin/client-visual-qa` con alias `/admin/visual-qa` y `/admin/pick-analysis-qa`.
- Nueva API segura `/api/admin/client-visual-qa`.
- Picks premium rediseñados con bloque `Lectura SHARK`, motivos, riesgos y conclusión.
- Detalle de partido muestra también explicación enriquecida en picks relacionados.
- Home, Favoritos, Mi Día, Smart Dashboard y Track Record refuerzan escudos/fallbacks en teasers de partido.
- Sports Hub, Live, Calendar y Smart Dashboard fuerzan ligas por filtro `competition_es`.
- Base admin corregida para evitar enlace `Final` duplicado.
- CSS V740 anti-solape: `overflow-wrap`, ellipsis controlado, grid responsive, protección móvil y tarjetas de análisis.
- Ampliado diccionario de competiciones en castellano con ligas inglesas, europeas y categorías andaluzas/españolas.
- Histórico de picks enriquecido desde `payload_json` cuando existe, para mostrar equipos, escudos y competición sin inventar datos.

## Qué NO se toca

- No se toca Telegram.
- No se toca Cron.
- No se toca Stripe real.
- No se cambia DB_PATH.
- No se cambian membresías reales.
- No se alteran picks/cuotas ni se inventan resultados.
- No se cambia Madrid Time.
- No se exponen secrets.

## Resultado QA visual

- Score visual V740: `100/100`.
- Estado: `CLIENT_VISUAL_READY`.
- Checks: 6.
- Templates críticos revisados: 11.

## Validación ejecutada en sandbox

- `python -m py_compile app.py`: OK.
- `python -m compileall -q .`: OK.
- `tools/check_v740_client_visual_pick_analysis.py`: OK.
- Checks V728-V739: OK.
- Jinja parse templates: OK.
- `tools/build_clean_release.py`: OK.
- `tools/audit_release_zip.py`: OK, 0 prohibidos.

## ZIP final

- Archivo: `NeMeSiS_SHARK_PRO_V740_CLIENT_VISUAL_PICK_ANALYSIS_PERFECTION_RENDER_READY.zip`.
- Archivos: 345.
- Prohibidos: 0.

## Limitación honesta

El sandbox no tiene Flask instalado ni variables reales de Render/Telegram/Stripe, por lo que la prueba real de producción debe hacerse tras desplegar: `/api/runtime-version`, `/admin/client-visual-qa`, `/admin/final-release`, `/admin/telegram/command-center` y pantallas cliente reales.
