# V871 Visible UI Defects Buttons Copy and Real Progress Fix Report

## Resumen ejecutivo
V871 corrige defectos visibles que los checks anteriores no capturaban: duplicación de labels, mojibake en texto visible, macros con copy roto y JavaScript base con ternarias dañadas.

## Corregido
- Versionado a `V871_VISIBLE_UI_DEFECTS_BUTTONS_COPY_AND_REAL_PROGRESS_FIX_FINAL`.
- Runtime añade `has_v871_visible_ui_defects_buttons_copy_fix`.
- `base.html` añade `data-v871-shell` y cache busting V871.
- Rail cliente deja de mostrar pares tipo `Partidos / Partidos`.
- Rail admin deja de mostrar pares tipo `Panel / Panel`.
- `support` deja de tener `span` vacío.
- Telegram corrige textos rotos de conexión, vinculación, envío y código.
- Macros `ui_components` corrigen mojibake y añaden `aria-label` sin duplicar texto visual.
- Se reparan ternarias JavaScript dañadas en CSRF, favoritos, navegación activa, dispositivo y reloj.
- Sentinel añade detector de texto duplicado en botones/enlaces.

## No tocado
- No se modificó lógica de picks, cuotas, live, pagos, usuarios ni Telegram real.
