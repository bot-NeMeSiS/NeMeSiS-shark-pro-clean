# V928 Render Real Regression Queue

| Prioridad | Regresion | Evidencia | Archivo | Estado |
|---|---|---|---|---|
| P0 | Sincronizacion externa durante render | `/live` timeout; 23 respuestas 502; sonda de 9-23 s | `app.py` | Corregido local, pendiente redeploy |
| P1 | Payload completo visible en forma/historico | Detalle real desktop y mobile de miles de pixeles | `templates/match_detail.html` | Corregido local, pendiente redeploy |
| P1 | Cuota media 0.71 con 0 picks completos | Capturas `/picks` desktop/mobile | `app.py`, `templates/picks.html` | Corregido local, pendiente redeploy |
| P2 | `/mes` duplicado en PRO/ELITE | Captura `/memberships` mobile | `templates/membership.html` | Corregido local, pendiente redeploy |
| P2 | Mensaje de agenda contradictorio | Home: 35 partidos y `Sin agenda real cargada` | `templates/home.html` | Corregido local, pendiente redeploy |
| Gate | Admin autenticado no certificado | No habia sesion segura | Sin cambio de codigo | Pendiente sesion humana |
| Gate | Cliente autenticado no certificado | No se crea usuario en produccion | Sin cambio de codigo | Pendiente sesion humana |

No procede crear V929 todavia. Procede redesplegar el V928 corregido, confirmar `has_v928_render_cache_only_route_fix=true` y repetir Browser QA remoto.
