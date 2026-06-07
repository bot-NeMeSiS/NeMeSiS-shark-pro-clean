# NeMeSiS SHARK PRO — V538 QUALITY CENTER DATA HEALTH POLISH

Build Render-ready basada en V537.

## Incluye

- Nuevo `/admin/quality-center` protegido para ADMIN.
- Nueva API `/api/quality-center/summary`.
- Nueva API cliente segura `/api/client/app-pulse`.
- Score de salud global del ecosistema.
- Control de calidad de partidos, live, resultados, equipos, escudos, picks, usuarios y Telegram.
- Recomendaciones accionables para evitar pantallas vacías.
- Navegación admin mejorada con acceso a Calidad.
- CSS mobile para el nuevo centro de calidad.
- `app.py` compila correctamente.

## Objetivo

Ayudar a controlar el crecimiento del ecosistema antes de seguir añadiendo módulos: ver qué datos faltan, qué está publicado, qué necesita sincronización y qué debe revisar el admin.

## Rutas nuevas

- `/admin/quality-center`
- `/api/quality-center/summary`
- `/api/client/app-pulse`

## Mantiene

- Login cliente/admin.
- Dashboard cliente.
- Calendario, resultados, live, picks, combis, favoritos, SHARK, Telegram y Data Center.
- SQLite persistente con `DB_PATH=/data/database.db`.

## Limpieza

ZIP sin `.git`, sin `__pycache__`, sin logs, sin DB local y sin ZIPs antiguos.
