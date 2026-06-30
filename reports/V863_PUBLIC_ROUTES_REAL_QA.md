# V863 Public Routes Real QA

## Render real probado

Base: `https://bot-apuestas-crgf.onrender.com`

| Ruta | Resultado real |
|---|---|
| `/` | 200 |
| `/cliente-login` | 200 |
| `/registro` | 200 |
| `/app` | 302 a `/cliente-login?next=/app` |
| `/inicio` | 302 a `/cliente-login?next=/app` |
| `/panel-cliente` | 302 a `/cliente-login?next=/app` |
| `/partidos` | 200 |
| `/calendar` | 200 |
| `/live` | 200 |
| `/directo` | 200 |
| `/picks` | 200 |
| `/shark` | 200 |
| `/telegram` | 302 a `/cliente-login?next=/telegram` |
| `/profile` | 302 a `/cliente-login` |
| `/support` | 200 |
| `/track-record` | 200 |

## Conclusión

Las rutas públicas probadas en Render real no devolvieron 500. Las rutas privadas de cliente redirigen a login sin sesión.
