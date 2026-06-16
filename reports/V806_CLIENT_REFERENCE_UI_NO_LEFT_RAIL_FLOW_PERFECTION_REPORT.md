# V806 Client Reference UI No Left Rail Flow Perfection

Versión: `V806_CLIENT_REFERENCE_UI_NO_LEFT_RAIL_FLOW_PERFECTION`

## Revisión usada
- ZIP completo actual del usuario: se detectó una barra lateral izquierda cliente tipo rail en la entrada como usuario.
- Vídeo de usuario: la barra lateral aparecía fija en todas las pantallas y rompía el formato de app premium de las referencias.
- Fotos de referencia: objetivo visual con navegación superior en PC y navegación inferior limpia en móvil, sin rail vertical izquierdo.

## Cambios principales
- Eliminado el rail lateral cliente de `templates/base.html`.
- Añadida capa `data-v806-shell` para forzar experiencia cliente sin barra lateral.
- Añadido CSS defensivo para ocultar cualquier resto de `.v798-client-rail` / `.v799-client-rail`.
- Restaurado layout centrado de `ns-main-shell` para que ninguna pantalla quede desplazada por margen izquierdo antiguo.
- Reforzada navegación superior en PC y navegación inferior móvil.
- Bottom nav móvil simplificada a Inicio, Partidos, Directo, Picks y Cuenta.
- Botón Salir sigue visible en topbar y cuenta, pero sin invadir la pantalla móvil.

## Regla de datos reales
No se han introducido datos deportivos inventados: no se inventa ningún partido, cuota, ataque, balón, resultado ni pick. Esta versión es visual/UX y mantiene la lógica V803-V805 de API-Football Live Tracker con datos reales o estados pendientes.

## No tocado
- DB_PATH
- AUTOMATION_SECRET
- Telegram/Cron
- usuarios/sesiones
- membresías
- pagos/Stripe
- keys reales de API-Football
