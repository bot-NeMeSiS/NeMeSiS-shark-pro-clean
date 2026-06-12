# V730 Architecture Roadmap — NeMeSiS SHARK PRO

## Objetivo

Esta versión no migra rutas de golpe. Deja una base segura para empezar a dividir `app.py` sin romper Render, Telegram, Cron, sesiones, horarios Madrid ni la experiencia cliente.

## Regla de oro

No extraer todo `app.py` de una vez. El proyecto tiene muchas rutas críticas y automatizaciones conectadas; la migración debe hacerse por lotes pequeños con smoke tests.

## Orden recomendado

1. `blueprints/admin_api.py` — endpoints admin JSON pequeños y protegidos.
2. `blueprints/admin_pages.py` — páginas admin no críticas.
3. `blueprints/telegram_admin.py` — Command Center y diagnósticos Telegram.
4. `blueprints/public.py` — home, login y registro solo cuando CSRF/rate-limit esté estable.
5. `blueprints/client.py` — dashboard, picks, combis, calendar, live.
6. `blueprints/cron.py` — solo al final, porque Cron/secret es crítico.

## Requisitos antes de cada extracción

- Mantener endpoint y nombre de ruta.
- Mantener templates y contexto igual.
- Ejecutar `python tools/check_v730_route_health.py`.
- Ejecutar `python tools/smoke_check.py` con Flask instalado.
- Verificar Cron 403/200.
- Verificar login cliente/admin.

## Por qué esta versión mejora el proyecto

- Da visibilidad real a las 200+ rutas actuales.
- Detecta templates faltantes antes del ZIP.
- Clasifica rutas por admin, cliente, API, cron, público y Telegram.
- Prepara una migración gradual sin riesgo innecesario.
