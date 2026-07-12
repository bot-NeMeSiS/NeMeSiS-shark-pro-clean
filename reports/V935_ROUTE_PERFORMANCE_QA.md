# V935 Route Performance QA

## Causa corregida

Las rutas reutilizaban poco el mismo resumen deportivo y el Track Record podia intentar preparar esquema durante una lectura GET. V935 usa cache local por peticion y el resumen historico abre SQLite en `mode=ro`, `query_only=ON`, timeout corto y cierre garantizado.

## Medicion local

| Ruta | Tiempo observado |
| --- | ---: |
| `/` | 627.24 ms |
| `/calendar` | 961.94 ms |
| `/live` | 346.21 ms |
| `/picks` | 397.06 ms |
| `/track-record` | 964.71 ms |
| `/app` | 972.43 ms |
| `/admin/dashboard` | 1128.39 ms |
| `/admin/data-trust-center` | 793.18 ms |

Todas las rutas medidas respondieron 200 y quedaron dentro del presupuesto local. La degradacion con DB bloqueada paso de aproximadamente 1625 ms en la matriz V932 a 291.50 ms en esta prueba, con respuesta 200 y estado seguro.

## Contratos

- APIs externas durante render: 0.
- Escrituras DB durante GET del Track Record: 0.
- `Server-Timing` y `X-Nemesis-Route-Budget`: presentes.
- Contexto deportivo repetido dentro de la peticion: reutilizado.
