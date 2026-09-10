# Locked Contracts

Contratos protegidos durante organizacion; documentos no cambian logica por si solos.
La comprobacion de integridad compara hashes del candidato, no solo HEAD.

| Contrato | Hogar actual | Invariante |
|---|---|---|
| MATCH-STATUS-TRUTH-V2 | `engines/v935_launch_trust_engine.py` | Terminal verificado nunca LIVE; stale/futuro/sin evidencia no son LIVE fresco |
| Consumidores LIVE | `engines/v934_realtime_sports_engine.py`, `engines/live_match_experience_engine.py`, `app.py` | Misma identidad/filtros; no minuto ni final por horario/score/cache |
| Tiempo Madrid | `engines/madrid_time_engine.py` | UTC/offset/DST coherentes; render no rejuvenece evidencia |
| Entidad/procedencia | `engines/sports_domain_model_engine.py` | Fuente de dato, no de adaptador no disponible; Primera 4335 != Segunda 4400 |
| Contexto | `engines/match_context_engine.py` | Hechos/analisis separados, stale explicito, evento != reloj actual |
| Observacion SE-01 | `services/sports_service.py` | SELECT parametrizado, mode=ro, sin init/sync/perfil ni endpoint publico |
| Historia nullable | `engines/shark_historical_intelligence_engine.py`, `engines/football_data_warehouse_engine.py` | Ausencia != cero; 0-0 confirmado se conserva; no liquidar por FT inferido |
| Derechos | `engines/content_rights_engine.py` | Derechos desconocidos -> fallback; sin stream, descarga o rehost no autorizado |
| Cuenta/negocio | `app.py`, rutas/servicios existentes | Aislamiento por usuario, permisos, membresias reales incluido ELITE+ si existe |
| Automatizacion | `tools/render_cron_master_tick.py`, `engines/product_review_system_engine.py` | No cambiar horarios, env, secretos, almacenamiento ni activacion |
| Calidad | `engines/autonomous_product_qa_engine.py`, `engines/autonomous_quality_platform_engine.py` | Rechazo humano prevalece; no borrar historia ni convertir NOT_TESTED en PASS |

## Autoridad de diseno preservada

[Vision](../NEMESIS_MASTER_VISION.md), [Producto](../NEMESIS_PRODUCT_BIBLE.md),
[Sports UX](../NEMESIS_SPORTS_UX_BIBLE.md), [Match UX](../NEMESIS_MATCH_CENTER_UX_BIBLE.md)
y [reglas congeladas NeMeSiS X](../NEMESIS_X_IMPLEMENTATION_RULES.md) no se editan.
NeMeSiS X sigue design-only y no se activa por reorganizar documentos.
LRM-001 sigue referencia estrategica/comercial, sin declarar su cierre.
REFERENCE_ONLY: solo PNG oficiales; no copiar/ejecutar codigo, payload o instaladores.

## Limites de trabajo

- Sin staging, commit, push, PR, merge, deploy ni fuerza en este encargo.
- Sin DB real, usuarios, sesiones productivas, membresias, pagos o envios.
- Sin llamadas deportivas, compras, cambios de cuotas, Render o cron.
- Sin mover app.py, engines, services, templates, static, tools, tests o reports.
- Sin purga por numero de version, ausencia de import estatico o igualdad de hash.
- UNKNOWN siempre se conserva. Runtime no es basura por ser mutable.
- QA/fuentes/fixtures conservan sus checks; no continue-on-error, skips o verde artificial.
- La futura publicacion requiere autorizacion del candidato, rama + PR + checks;
  observar auto-deploy existente sin lanzar duplicado. Este documento no la autoriza.
