# V884 Visual Worker Local Run QA

## Proteccion local
- `/admin/visual-worker` sin sesion: protegido/redirige.
- `/api/admin/visual-worker/summary` sin sesion: 403.
- `/api/admin/visual-worker/run` sin sesion: 403.
- `/api/admin/visual-worker/issues` sin sesion: 403.
- `/api/admin/visual-worker/tasks` sin sesion: 403.
- `/api/automation/visual-worker/run` sin secret: 403.
- `/api/automation/visual-worker/run` con secret local y `dry_run=1`: 200.

## Modos ejecutados
| Modo | Score | Rutas | Issues | Tareas | Prompts |
|---|---:|---:|---:|---:|---:|
| quick | 9.6 | 9 | 3 low | 1 | 1 |
| visual | 9.2 | 18 | 5 low | 1 | 1 |
| product | 9.2 | 7 | 5 low | 1 | 1 |
| admin | 10.0 | 13 | 0 | 0 | 0 |
| full | 9.2 | 25 | 5 low | 1 | 1 |

## Issues reales detectados
- `/partidos`: pantalla deportiva sin datos reales visibles.
- `/calendar`: pantalla deportiva sin datos reales visibles.
- `/live`: pantalla deportiva sin datos reales visibles.
- `/directo`: pantalla deportiva sin datos reales visibles.
- `/picks`: pantalla deportiva sin datos reales visibles.

Hay estado seguro visible, pero no hay filas/cards deportivas reales. V884 lo mantiene como issue low y tarea admin para revisar sync, cache, filtros o temporada.
