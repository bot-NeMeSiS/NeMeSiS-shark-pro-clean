# V737 — Native App Feel, Microinteractions & Navigation Polish

## Versión
`V737_NATIVE_APP_FEEL_MICROINTERACTIONS_NAVIGATION_POLISH`

## Objetivo
Mejorar todavía más la experiencia visual global de NeMeSiS SHARK PRO para que se sienta más como una app premium nativa: más clara, táctil, fluida, consistente por membresía y cómoda en móvil, sin tocar la lógica crítica.

## Cambios principales

### Base global
- `base.html` añade datos seguros de ruta y plan visual: `data-ns-route` y `data-ns-plan`.
- Añadido brillo superior de ruta `ns-route-glow`.
- Añadido botón global de volver arriba `ns-scroll-top`.
- Añadido contenedor seguro de avisos visuales `ns-toast-host`.
- Añadido script ligero `nsAppEnhance` para mejorar navegación y microinteracciones.

### Navegación activa
- La navegación superior e inferior marca automáticamente la pantalla actual con `is-active` y `aria-current="page"`.
- El cliente sabe mejor dónde está dentro de la app.

### Sensación app nativa
- Estados táctiles `ns-touch` para botones, tarjetas, filas y navegación.
- Estados de carga `is-loading` solo para formularios POST, evitando romper SHARK IA o formularios AJAX.
- Botón global de volver arriba para pantallas largas.
- Sistema de avisos visuales `window.nsToast()` preparado para futuras acciones.

### Móvil y accesibilidad
- Soporte visual para `safe-area-inset-bottom` y navegación inferior en móviles modernos.
- Mejor foco visible para teclado/accesibilidad.
- Soporte `prefers-reduced-motion` para usuarios que prefieren menos animación.

### Nuevo panel admin
- `/admin/app-feel`
- `/admin/native-app-experience`
- `/api/admin/app-feel`
- `/api/admin/native-app-experience`

### Nuevo motor/check
- `engines/native_app_experience_engine.py`
- `tools/check_v737_app_feel.py`
- `templates/admin_app_feel.html`

## Alcance seguro
- No cambia picks.
- No cambia cuotas.
- No cambia Telegram.
- No cambia Cron.
- No activa pagos reales.
- No cambia membresías reales.
- No modifica `DB_PATH`.
- No toca secrets.
- No rompe Madrid Time.
- No rompe Go Live, Public Launch, Payments Foundation ni Track Record.

## Validación prevista
- `python -m py_compile app.py`
- `python -m compileall -q .`
- `python tools/check_madrid_times.py`
- `python tools/check_v728_client_experience.py`
- `python tools/check_v729_security.py`
- `python tools/check_v730_route_health.py`
- `python tools/check_v731_client_experience.py`
- `python tools/check_v732_production_readiness.py`
- `python tools/check_v733_client_success.py`
- `python tools/check_v734_public_launch.py`
- `python tools/check_v735_go_live.py`
- `python tools/check_v736_visual_experience.py`
- `python tools/check_v737_app_feel.py`
- `python tools/build_clean_release.py`
- `python tools/audit_release_zip.py`

## Nota honesta
Esta versión mejora la experiencia visual y de uso de forma segura. La validación real en Render, Telegram real, Stripe real y smoke Flask completo dependen del entorno de producción y sus variables reales.
