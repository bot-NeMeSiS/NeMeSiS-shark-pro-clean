# V587 — Performance Proof & ROI Dashboard

## Objetivo

Convertir los picks cerrados en prueba visible de rendimiento para mejorar confianza y conversión comercial.

## Añadido

- Motor interno de rendimiento SHARK.
- Cálculo de ROI, winrate, beneficio en unidades, stake total, racha y picks pendientes.
- Estadísticas por liga y por mercado.
- Últimos picks con estado ganado/perdido/nulo/pendiente.
- Tablas SQLite seguras:
  - `shark_performance_summary`
  - `shark_performance_daily`
- Endpoints:
  - `/api/performance/summary`
  - `/api/performance/rebuild`
- Integración en dashboard cliente.
- Integración en Admin Data Center con botón para reconstruir rendimiento.

## Archivos modificados

- `app.py`
- `templates/client_overview.html`
- `templates/admin_data_center.html`
- `VERSION.txt`

## Seguridad

No se toca:

- login
- membresías
- Telegram
- Auto Picks
- SHARK Learning
- Live V584
- Render
- rutas existentes críticas

## Validación

- `app.py` compila correctamente con `py_compile`.
- ZIP generado limpio para GitHub/Render.
- Se eliminan `.git`, `__pycache__`, bases de datos locales, logs y ZIPs internos del paquete final.

## Nota

El rendimiento depende de que existan picks con estado/resultados cerrados (`won`, `lost`, `void` o equivalentes). Si no hay suficientes picks cerrados, la app muestra estado transparente sin inventar datos.
