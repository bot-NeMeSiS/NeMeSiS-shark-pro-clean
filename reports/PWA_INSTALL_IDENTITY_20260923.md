# PWA install + identidad unificada · 23/09/2026

Extensión de PR75, sin tocar app.py ni la lógica de proveedores.

- Header público/cliente/admin usa la familia oficial de iconos versionada por APP_ICON_VERSION.
- Manifest público y Founder Control usan la misma familia 192/512; el href del manifest incorpora el fingerprint.
- Service worker existente ya incorpora APP_ICON_VERSION y recarga manifest/iconos.
- /instalar, /install-app y /anadir-a-inicio ofrecen una guía compartible.
- Chromium/Android/PC usan beforeinstallprompt cuando el navegador lo expone.
- iPhone/iPad muestran Compartir → Añadir a pantalla de inicio.
- El banner no aparece en superficies admin ni si la app ya está instalada.
- El rechazo “Ahora no” dura 7 días por versión de icono; un icono nuevo usa otra clave y vuelve a poder mostrarse.
- No hay descargas externas, llamadas a proveedores, cambios de cuenta ni escrituras de negocio.
