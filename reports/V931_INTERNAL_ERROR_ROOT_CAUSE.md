# V931 Internal Error Root Cause

## Causa comun

El helper cliente `dashboard_data()` cargaba partidos mediante `get_matches()`. La consulta esperaba columnas del esquema moderno, incluida `priority`. En una DB de produccion con esquema antiguo o parcial, SQLite devolvia:

`sqlite3.OperationalError: no such column: priority`

La excepcion atravesaba el render porque las rutas no tenian fallback de schema drift. Ademas, `rows()` solo cerraba la conexion en el camino correcto, por lo que una consulta fallida podia dejar conexiones abiertas y agravar un posible `database locked`.

## Matriz por ruta

| Ruta | Estado antes | Excepcion y ubicacion | Causa raiz | Solucion V931 | Estado despues |
| --- | --- | --- | --- | --- | --- |
| `/cliente-login` | Internal Error observado con sesion activa | Redireccion a `/app`; el destino fallaba en `dashboard_data()` -> `get_matches()` -> `rows()` | El formulario anonimo era sano; el error visible procedia del destino autenticado | `/app` usa `v931_safe_dashboard_data()` y el login captura errores de lectura de sesion/DB | 200 anonimo; redireccion autenticada segura |
| `/app` | 500 con sesion | `app.py`, `v757_client_app_center_page()`; `OperationalError: no such column: priority` | Consulta de partidos incompatible con schema antiguo | Fallback DB/cache, filtrado de datos completos y contexto opcional protegido | 302 sin sesion; 200 con sesion mock |
| `/calendar` | 500 | `app.py`, `calendar_page()`; misma cadena SQLite | Dependencia obligatoria del dashboard completo | `v931_calendar_context()` lee columnas disponibles y normaliza sin migrar ni escribir | 200 |
| `/calendario` | Dependia de la ruta rota | Alias de `/calendar` | Heredaba el mismo fallo | Alias conserva destino recuperado | 200 |
| `/live` | 500 | `app.py`, `live_page()`; misma cadena SQLite | Schema drift y flujo de render demasiado acoplado | `v931_live_context()` usa solo DB/cache y no llama proveedores | 200 |
| `/directo` | Dependia de la ruta rota | Alias de `/live` | Heredaba el mismo fallo | Alias conserva destino recuperado | 200 |
| `/picks` | 500 | `app.py`, `picks_page()`; misma cadena SQLite | El dashboard fallaba antes de poder mostrar un estado vacio | Dashboard seguro, picks completos solamente y escritura de actividad no critica protegida | 200 |
| `/login` | Riesgo de caer en destino roto | Alias/login cliente | Mismo destino autenticado | Flujo cliente recuperado | 200 |

## Otras causas revisadas

- `Jinja UndefinedError`: no reproducido tras V931.
- Macro/include V930 ausente: no; 177 templates parsean.
- Archivo runtime opcional ausente: no provoca 500.
- Tabla ausente o schema incompleto: cubierto por DB vacia y DB legacy.
- `database locked`: cubierto; las rutas responden 200 con fallback acotado.
- API durante render: bloqueada en pruebas; 0 llamadas externas.
- Sesion ausente: `/app` y `/profile` redirigen de forma segura.

La reparacion no migra ni modifica la DB de produccion. Detecta la capacidad real del esquema y degrada la interfaz a un estado seguro.
