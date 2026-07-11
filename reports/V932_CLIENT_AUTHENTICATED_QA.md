# V932 Client Authenticated QA

## Alcance seguro

Se uso una sesion Flask mock aislada sobre DB temporal. No se consultaron ni modificaron usuarios reales y no se guardaron cookies o credenciales en reportes.

| Ruta | Estado | Tiempo local aproximado | Error visible |
| --- | ---: | ---: | --- |
| `/app` | 200 | 1079 ms | No |
| `/calendar` | 200 | 937 ms | No |
| `/live` | 200 | 875 ms | No |
| `/picks` | 200 | 875 ms | No |
| `/track-record` | 200 | 891 ms | No |
| `/shark` | 200 | 937 ms | No |
| `/telegram` | 200 | 63 ms | No |
| `/profile` | 200 | 828 ms | No |
| `/memberships` | 200 | 812 ms | No |
| `/favorites` | 200 | 703 ms | No |

## Login y logout

- Login correcto mock con destino interno: `/calendar`.
- Un `next=https://...` queda bloqueado y redirige a `/app`.
- `/logout` limpia la sesion y redirige a `/`.
- No se envio Telegram, no se ejecuto checkout y no se modifico membresia.

## Produccion autenticada

- Cuenta real autorizada disponible: no.
- Browser QA autenticado de Render: no ejecutado.
- Capturas: 0.
- Overflow visual autenticado: pendiente de una sesion autorizada.

Las rutas quedan funcionalmente certificadas en local, pero no se presenta ese resultado como certificacion visual autenticada de produccion.
