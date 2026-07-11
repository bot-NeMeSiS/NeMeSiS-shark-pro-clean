# V931 Production Smoke Matrix

## DB normal

| Contexto | Ruta | Estado |
| --- | --- | --- |
| Publico | `/` | 200 |
| Publico | `/cliente-login`, `/login`, `/registro` | 200 |
| Publico | `/calendar`, `/calendario` | 200 |
| Publico | `/live`, `/directo` | 200 |
| Publico | `/picks`, `/track-record`, `/support` | 200 |
| Sin sesion | `/app`, `/profile`, `/telegram` | 302 seguro |
| Sin sesion | `/shark`, `/memberships` | 200 seguro |
| Cliente mock | `/app`, `/calendar`, `/live`, `/picks`, `/track-record` | 200 |
| Cliente mock | `/profile`, `/telegram`, `/shark`, `/memberships` | 200 |
| Publico | `/admin-login` | 200 |
| Admin mock | `/admin/dashboard`, `/admin/navigation-integrity` | 200 |

## Perfiles degradados

La matriz automatizada cubrio 81 peticiones en:

- DB temporal normal.
- DB vacia sin tablas.
- DB legacy con tablas y columnas incompletas.
- SQLite bajo bloqueo exclusivo.
- Sin archivos runtime opcionales requeridos por las rutas.
- Sin sesion, cliente mock y admin mock.
- Proveedor externo bloqueado durante render.

Resultado: 0 rutas con 500, 0 `Jinja UndefinedError`, 0 respuestas con `database is locked`, 0 llamadas externas durante render.

## Errores y recuperacion

- HTML 500: 500 seguro, vista V930/V931, sin traceback, botones Inicio y Entrar.
- API 500: JSON con `ok=false`, `error_type`, `safe_message` y version; sin traceback.
- HTML 404: 404 premium.
- API 404: 404 JSON seguro.
- Runtime local: 200, version V931, archivos alineados, cache CSS activo y cache `NEMESIS_CACHE_V931`.

## Validacion global

- Python compile/compileall: OK.
- Madrid Time: OK.
- Jinja: 177 templates OK.
- V929 navigation integrity: OK.
- V930 canonical visual parity: OK.
- V931 hotfix check: OK.
- Sentinel: score 10.0, 0 issues.
- Imports/rutas: 612, sin templates/static ausentes.
- Navegacion: 646 rutas, 931 enlaces, 0 rotos, 0 bucles.
