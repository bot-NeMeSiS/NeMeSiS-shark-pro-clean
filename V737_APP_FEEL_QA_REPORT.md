# V737 App Feel QA Report

## Resultado esperado
La capa V737 debe estar lista si:

- `base.html` contiene `nsAppEnhance`, `nsScrollTop`, `nsToastHost`, `data-ns-route` y `data-ns-plan`.
- `static/app.css` contiene la sección `V737 Native App Feel`.
- Las pantallas críticas siguen extendiendo `base.html`.
- La navegación activa no requiere cambiar rutas ni lógica Flask.
- Los estados de carga solo se aplican a formularios POST para no bloquear SHARK IA.
- El CSS respeta `prefers-reduced-motion`.

## Pantallas cubiertas por la capa global
- Home
- Sports Hub
- Live
- Calendar
- Picks
- Combis
- Favoritos
- Match Detail
- Match Hub
- Team Detail
- SHARK
- Telegram
- Perfil
- Membresías
- Track Record
- Guía / Ayuda

## Revisión manual recomendada tras subir a Render
1. Abrir `/api/runtime-version` y confirmar V737.
2. Probar navegación inferior en móvil.
3. Probar `/sports-hub`, `/calendar`, `/live`, `/picks`, `/combis`, `/favorites`, `/perfil`.
4. Confirmar que la pestaña actual queda marcada.
5. Confirmar que SHARK IA responde y no queda el botón Enviar bloqueado.
6. Confirmar que el botón volver arriba aparece en pantallas largas.
7. Revisar FREE, PRO y ELITE si hay usuarios de prueba disponibles.
