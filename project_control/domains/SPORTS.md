# Sports

Responsable de revision: Datos deportivos / QA; coordinacion [cola](../CODEX_QUEUE.md).
SP-001 = QA, evidencia REAL_PRODUCTION historica; no nueva observacion en CX.

## Hogares y contratos

- `engines/v935_launch_trust_engine.py`: MATCH-STATUS-TRUTH-V2.
- `engines/v934_realtime_sports_engine.py`, `engines/live_match_experience_engine.py`:
  consumidores delegados; `app.py`: Home, Calendario/Partidos, detalle, permisos.
- `engines/sports_domain_model_engine.py`: entidad/procedencia;
  `engines/madrid_time_engine.py`: unica politica horaria.
- [SE-01](../CURRENT_TRUTH.md): PASS_LOCAL_SCOPE, sin publicacion del diff.

LIVE requiere evidencia confirmada y vigente; terminal respaldado gana.
Desaparecer del feed no equivale a FT. Un marcador ausente no es 0-0.
No minuto por kickoff ni correccion de fuente desde un tracker no disponible.

## Evidencia real y limites

[Sports certification](../../SPORTS_DATA_LIVE_CERTIFICATION.md) conserva DAY 1-5.
Ultima observacion DAY 5: 2026-09-08, SHA c6eaa003..., 72 senales recientes que
despues se excluyen al caducar. Eso no prueba 72 partidos realmente en juego.
No minuto/lineup/stats LIVE suficientes ni coherencia independiente para PASS real.
Home autenticada sigue fuera de esa muestra; catalogos/filtros no son el mismo universo.

## Siguiente consumidor

CX-RESULTS-01 BLOCKED por revision, no empezado. Reutilizar Calendario/Partidos:
ayer/hoy/manana/fecha, final confirmado, sin pick, Madrid/DST, detalle y vuelta.
Track Record sigue historico de picks. No crear archivo de resultados duplicado.
Proveedores y cron no se invocan para esta organizacion.
