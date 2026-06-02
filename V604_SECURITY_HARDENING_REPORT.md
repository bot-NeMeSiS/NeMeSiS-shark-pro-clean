# V604 — Security Hardening & Production Readiness

Actualización limpia sobre la base actual del proyecto.

## Añadido

- Protección CSRF ligera para formularios HTML sensibles.
- Token CSRF disponible en todas las plantillas como `{{ csrf_token }}`.
- Rate limiting defensivo en login cliente, login admin, registro y bootstrap admin.
- Auditoría de seguridad en tabla `security_events`.
- Cabeceras de seguridad HTTP:
  - `X-Frame-Options`
  - `X-Content-Type-Options`
  - `Referrer-Policy`
  - `Permissions-Policy`
  - `Content-Security-Policy`
- SECRET_KEY endurecida:
  - En producción/Render se exige `SECRET_KEY` o `FLASK_SECRET_KEY` con longitud suficiente.
  - En local permite fallback solo de desarrollo.
- Endpoints admin:
  - `/api/security/summary`
  - `/api/v604/security-check`

## Archivos incluidos en esta actualización

- `app.py`
- `VERSION.txt`
- `engines/security_engine.py`
- `templates/*.html` con formularios POST actualizados con CSRF
- `V604_SECURITY_HARDENING_REPORT.md`
- `V604_UPDATE_README.md`

## Variables Render recomendadas

Asegúrate de tener:

```env
SECRET_KEY=una_clave_larga_y_segura_de_32_o_mas_caracteres
```

No uses valores simples como `1234`, `secret`, `admin` o similares.

## Validación realizada

- `compileall app.py engines` OK.
- Motor `security_engine.py` importado correctamente.
- Plantillas actualizadas para CSRF en formularios POST.
