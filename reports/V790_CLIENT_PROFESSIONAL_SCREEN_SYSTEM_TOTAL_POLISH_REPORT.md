# V790_CLIENT_PROFESSIONAL_SCREEN_SYSTEM_TOTAL_POLISH

## Objetivo

Convertir las pantallas cliente de NeMeSiS SHARK PRO en un sistema visual profesional y coherente, sin añadir riesgo a pagos, Telegram, Cron, DB_PATH, membresías existentes, picks, directo real ni legal/compliance.

## Problema detectado

La app ya tenía muchas funciones reales, pero varias pantallas cliente podían sentirse distintas entre sí: tarjetas demasiado juntas, letra pequeña, filtros apretados, live difícil de leer con muchos partidos y jerarquía desigual entre Inicio, Directo, Calendario, Picks, Membresías, Telegram y Mi Cuenta.

## Cambios principales

### Sistema visual global cliente

- Nueva bandera `data-v790-shell="true"` en `base.html`.
- Nueva capa CSS V790 al final de `static/app.css`.
- Mejora global de tipografía, line-height, contraste, aire entre tarjetas y jerarquía de títulos.
- Hero cliente más profesional en las pantallas principales.
- KPIs, tabs, filtros, botones y paneles con lenguaje visual común.

### Directo / Live

- Partidos con más separación visual.
- Cards más grandes y legibles.
- Estado, día/hora, equipos, marcador, liga y notas separados por zonas.
- Mejor grid en PC y móvil.
- Marcador más visible.
- Distinción visual de partidos en directo.

### Calendario / Partidos

- Agrupaciones por día y liga más claras.
- Filtros y date rail más legibles.
- Cards de partido con la misma jerarquía que Live.

### Picks

- Cards de picks más comerciales.
- Bloques “Qué apostar / Mercado / Cuota / Stake” más visibles.
- Lectura SHARK con más aire y menos saturación.
- Mejor comportamiento responsive.

### Membresías / Pagos

- Planes FREE/PRO/ELITE más profesionales.
- Precio, ventajas y aceptación legal mejor presentados.
- Checkout legal conservado de V787/V788.

### Mi Cuenta y Telegram

- Paneles más limpios y consistentes.
- Código Telegram más visible.
- Acciones y estados de cuenta con mayor jerarquía.

## No se ha tocado

- Telegram automático/manual.
- Cron y `tools/render_cron_telegram_tick.py`.
- `AUTOMATION_SECRET`.
- `DB_PATH`.
- Usuarios, sesiones y membresías existentes.
- Stripe core, checkout, webhook y portal.
- Directo V780.
- Escudos/banderas V779.
- Legal/compliance V787/V788.
- Real Launch Command Center V789.
- Picks/resultados/Track Record.
- Highlights.
- Data Marketplace y Automation Center.
- Madrid Time.

## Validación esperada

- `python -m py_compile app.py`
- `python -m compileall app.py engines tools`
- `python tools/check_v790_client_professional_screen_system.py`
- `python tools/check_madrid_times.py`
- checks V782-V789 compatibles.
- Jinja parse de templates.
- build clean release y audit ZIP.

## Resultado

V790 deja la app más cerca de un producto comercial real: menos saturación, más lectura, pantallas cliente coherentes y mejor sensación premium sin cambiar la lógica crítica.
