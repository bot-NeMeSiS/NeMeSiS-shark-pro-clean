# V759 GLOBAL TOP APP MERGED QUALITY EXPERIENCE RELEASE

## Objetivo

Consolidar V755, V756, V757 y V758 en una versión coherente, limpia, verificable y preparada para beta comercial.

## Cambios aplicados

- Versión activa actualizada a `V759_GLOBAL_TOP_APP_MERGED_QUALITY_EXPERIENCE_RELEASE`.
- Conservada la lógica V755 de Telegram auto-picks y normalización de candidatos.
- Conservados motores V756, V757 y V758.
- Añadida capa V759 visual ligera en Home, Picks, Calendar, Live y Track Record.
- Corregidos textos visibles con mojibake en plantillas principales.
- Checks V748-V758 actualizados para aceptar V759 como versión fusionada.
- Creado `tools/check_v759_global_top_app_merged_quality.py`.
- Reforzado `tools/build_clean_release.py` para incluir reportes V759 y excluir basura.

## Qué mejora para el cliente

- Inicio más claro.
- Picks más orientados a producto de pago.
- Calendario con accesos rápidos.
- Live más compacto.
- Track Record más honesto.
- Experiencia PC/móvil conservada.

## Qué mejora para admin

- QA V759 específico.
- Control de compatibilidad V755-V758.
- Release limpio y auditable.

## Qué no se tocó

- Secrets.
- `DB_PATH`.
- Telegram real.
- Cron de Render.
- Scheduler sensible.
- Usuarios, sesiones y membresías reales.

## Limitaciones honestas

- El envío real Telegram debe certificarse en Render, no localmente.
- La cobertura deportiva real depende de APIs y disco persistente.
- `app.py` sigue siendo grande y debería modularizarse con calma más adelante.
