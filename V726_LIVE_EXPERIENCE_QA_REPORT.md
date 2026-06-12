# V726 Live Experience QA Report

## Objetivo

Validar que Live, Calendar y Sports Hub se sienten más compactos, deportivos y seguros sin cambiar la lógica estable de Telegram, SHARK, Cron, membresías ni Render.

## Live

- Ruta probada: `/live`.
- Resultado: 200.
- Cambios:
  - tarjetas más compactas;
  - estado vacío premium;
  - marcador sin inventar;
  - minuto real si existe;
  - texto `En directo` si no hay minuto real;
  - favoritos visibles con estrella;
  - próximos partidos relacionados más limpios.

## Calendar

- Rutas probadas:
  - `/calendar`
  - `/calendar?lane=tomorrow`
  - `/calendar?lane=week`
  - `/calendar?lane=favorites`
  - `/calendar?lane=with_pick`
- Resultado: todas 200.
- Cambios:
  - filtros reales por Hoy, Mañana, Semana, Favoritos y Con pick;
  - agrupación por día;
  - hora española;
  - filas compactas;
  - estado vacío claro;
  - directos sin minuto muestran `En directo`.

## Sports Hub

- Ruta probada: `/sports-hub`.
- Resultado: 200.
- Cambios:
  - fila compacta más clara;
  - directos con minuto real o `En directo`;
  - partidos no live con hora Madrid;
  - favorita visible;
  - menor ruido visual.

## Cron y automatización

- `/api/automation/telegram/tick`: 403 sin secret.
- `/api/automation/telegram/tick?secret=test-secret`: 200.
- `/api/automation/daily/run`: 403 sin secret.
- `/api/automation/daily/run?secret=test-secret`: 200.

El comportamiento de seguridad V710+ se mantiene.

## Rutas adicionales probadas

- `/`: 200.
- `/api/health`: 200.
- `/dashboard`: 302 por sesión.
- `/picks`: 200.
- `/combis`: 200.
- `/telegram`: 302 por sesión.
- `/shark`: 200.
- `/favorites`: 302 por sesión.
- `/perfil`: 302 por sesión.
- `/membership`: 200.
- `/admin/time-diagnostics`: 302 por sesión admin.
- `/admin/codex-automation`: 302 por sesión admin.
- `/admin/telegram/diagnostics`: 302 por sesión admin.
- `/admin/data-memory`: 302 por sesión admin.
- `/admin/team-identity`: 302 por sesión admin.
- `/api/runtime-version`: 200.

## Resultado

No se detectaron errores 500 en la validación local con cliente Flask.

La experiencia Live/Calendar queda más cercana a una app deportiva compacta: más partidos por pantalla, menos texto innecesario, estados más claros y sin inventar minuto ni marcador.
