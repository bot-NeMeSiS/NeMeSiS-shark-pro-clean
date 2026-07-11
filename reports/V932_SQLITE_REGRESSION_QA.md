# V932 SQLite Regression QA

## Regresiones reproducidas

Antes del guard V932, un esquema antiguo sin la columna `priority` podia propagar `sqlite3.OperationalError` desde `dashboard_data()` y romper vistas autenticadas. El fallback de favoritos tambien carecia de la estructura `favorite_insights.by_kind`, lo que producia `Jinja UndefinedError` al degradarse la DB.

## Solucion

- Contexto base V932 para todas las rutas autenticadas prioritarias.
- Callbacks admin encapsulados con valores seguros por modulo.
- Fallback de favoritos con la forma esperada por Jinja.
- Preflight de solo lectura que detecta un bloqueo antes del refresco de membresia.
- Una sola repeticion corta para lecturas transitorias.
- Cierre de conexion garantizado por `rows()` incluso al lanzar excepcion.
- Incidencia Sentinel deduplicada por ruta, excepcion, version y alcance, sin datos de usuario.

## Matriz

| Perfil DB | Rutas probadas | Resultado |
| --- | ---: | --- |
| Con columna `priority` | 4 | 4/4 sin 500 |
| Legacy sin `priority` | 4 | 4/4 sin 500 |
| Vacia | 4 | 4/4 sin 500 |
| Bloqueada | 4 | 4/4 en 200, sin texto de lock |

La DB bloqueada respondio en aproximadamente 1.625 s por ruta en la matriz. No quedo ningun `database locked` persistente ni se aplicaron migraciones o escrituras sobre una DB real.
