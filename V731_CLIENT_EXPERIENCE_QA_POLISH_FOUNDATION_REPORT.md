# V731 — Client Experience QA Polish Foundation

## Resumen ejecutivo

V731 añade una capa segura de control de experiencia cliente sin mover rutas ni tocar flujos críticos. El objetivo es seguir mejorando sin romper Render, Telegram, Cron, Data Memory, Madrid Time, seguridad V729 ni la base de arquitectura V730.

Esta versión no rediseña la app desde cero. Añade un sistema de auditoría admin para revisar pantallas cliente, horarios Madrid, textos técnicos, empty states y checks visuales CSS.

## Cambios principales

- Nuevo motor `engines/client_experience_guard_engine.py`.
- Nueva vista admin protegida `/admin/client-experience`.
- Nueva API admin protegida `/api/admin/client-experience`.
- Nuevo template `templates/admin_client_experience.html`.
- Nuevo script `tools/check_v731_client_experience.py`.
- Nueva capa CSS V731 para la vista de QA cliente.
- Actualización de `tools/check_v729_security.py` para validar V729 o versiones posteriores.
- Actualización del release builder para incluir informes/manifiesto V731.

## Qué revisa el nuevo Client Experience QA

- Pantallas críticas: Home, Dashboard, Sports Hub, Live, Calendar, Picks, Combis, SHARK, Telegram, Favoritos, Perfil, Membresías y Match Detail.
- Templates cliente existentes.
- Uso de filtros Madrid en pantallas con partidos.
- Presencia de empty states.
- Riesgo de textos técnicos visibles al cliente.
- Riesgo de campos horarios crudos.
- Checks CSS: navegación inferior, widget SHARK, responsive, filas Live, capa V728/V731.

## Qué no se tocó

- No se movieron rutas a blueprints.
- No se tocó Render real.
- No se tocaron secrets.
- No se cambió `DB_PATH=/data/database.db`.
- No se tocó Telegram automático.
- No se tocó Cron.
- No se tocó Data Memory.
- No se rehízo visual V728.
- No se rompieron horarios Madrid V725/V728.
- No se cambió la seguridad V729 salvo checks compatibles con versiones posteriores.

## Validación ejecutada en sandbox

- `python -m py_compile app.py engines/client_experience_guard_engine.py tools/check_v731_client_experience.py`: OK
- `python -m compileall -q app.py engines tools`: OK
- `python tools/check_madrid_times.py`: OK
- `python tools/check_v728_client_experience.py`: OK
- `python tools/check_v729_security.py`: OK
- `python tools/check_v730_route_health.py`: OK
- `python tools/check_v731_client_experience.py`: OK
- Parseo Jinja de templates: OK
- `python tools/build_clean_release.py`: OK
- `python tools/audit_release_zip.py`: OK

## Limitación

El sandbox no tiene Flask instalado, por lo que `tools/smoke_check.py`, `tools/validate_release.py` y `pytest -q` no se han completado aquí. Deben ejecutarse en local/Render con dependencias instaladas.

## Veredicto

V731 queda como una mejora segura de QA visual/cliente y continuidad arquitectónica. La app mantiene el camino de avanzar sin romper, añadiendo visibilidad admin antes de futuras extracciones de blueprints o cambios mayores.
