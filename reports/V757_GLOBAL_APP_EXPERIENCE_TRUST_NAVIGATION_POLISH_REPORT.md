# V757_GLOBAL_APP_EXPERIENCE_TRUST_NAVIGATION_POLISH

## Objetivo
Avance general grande sobre V756 para mejorar la experiencia global de cliente, navegación, confianza y track record sin tocar Telegram/Cron/DB_PATH.

## Implementado
- Nuevo motor `engines/client_growth_engine.py` con centro global de app, transparencia y siguientes acciones.
- Nueva página cliente `/app`, `/mi-app`, `/inicio`, `/panel-cliente`.
- Nuevas APIs cliente `/api/client/app-center` y `/api/client/trust-snapshot`.
- Home, Picks, Calendar y Track Record reciben bloques V757 de orientación, confianza y navegación.
- Track Record muestra transparencia sin inventar ROI ni winrate.
- CSS responsive V757 para móvil/web.

## No tocado
- Telegram automático V754.
- Render Cron runner.
- `AUTOMATION_SECRET`.
- `DB_PATH`.
- Usuarios y membresías.
- Madrid Time.

## Validación esperada
- Rutas cliente sin 500.
- `/api/runtime-version` debe devolver `V757_GLOBAL_APP_EXPERIENCE_TRUST_NAVIGATION_POLISH`.
- `/app` debe requerir login y mostrar centro cliente.
