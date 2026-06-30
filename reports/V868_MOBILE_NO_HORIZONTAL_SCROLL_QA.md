# V868 Mobile No Horizontal Scroll QA

Protecciones CSS activas:

- `html, body[data-v868-shell="true"] { max-width: 100%; overflow-x: clip; }`
- En móvil se fuerza `overflow-x: hidden`.
- `main`, `.content`, `.ns-main`, `.wrap`, `.page` y `.container` usan `max-width: 100vw`.
- Acciones/filtros con overflow horizontal interno y scroll controlado.
- Cards y filas clave usan `min-width: 0`, `text-overflow` y grid de una columna en móvil.

No se inventan datos para llenar pantallas. Si no hay directos/picks reales, se mantiene estado premium seguro.

Medición real local con navegador:

| Ruta solicitada | Ruta final | Viewport | Scroll width | Resultado |
|---|---|---:|---:|---|
| `/` | `/` | 390 | 375 | Sin scroll horizontal |
| `/app` | `/cliente-login` | 390 | 375 | Sin scroll horizontal |
| `/picks` | `/picks` | 390 | 375 | Sin scroll horizontal |
| `/live` | `/live` | 390 | 375 | Sin scroll horizontal |
| `/shark` | `/shark` | 390 | 375 | Sin scroll horizontal |
| `/telegram` | `/cliente-login` | 390 | 375 | Sin scroll horizontal |
| `/admin/dashboard` | `/admin-login` | 390 | 375 | Sin scroll horizontal |
| `/admin/continuous-sentinel` | `/admin-login` | 390 | 375 | Sin scroll horizontal |

Nota honesta: no se inició sesión como admin/cliente durante esta validación, por lo que las pantallas protegidas se validaron en su redirección segura local.
