# V761_VIDEO_UX_SECOND_AUDIT

## Problemas detectados por vídeo/uso
- Sensación de desorden por demasiados bloques heredados de versiones internas.
- SHARK no parecía usable o se abría sin responder de forma clara.
- Doble sensación de navegación: top, bottom, botones flotantes y accesos técnicos.
- Calendario/live no dejaban suficientemente claro el día, hora, finalizado/directo/próximo y resultado.
- El detalle de partido conservaba un enlace roto a SHARK (`/sharkmatch=`).
- Home tenía todavía accesos de experiencia técnica que no aportan venta al cliente.

## Correcciones V761
- SHARK visible, estable y con fallback.
- Navegación limpia en PC y móvil.
- Home con flujo recomendado.
- Picks con lectura ordenada.
- Calendar/live con fecha/resultado/estado visibles.
- Menú cliente reestructurado para uso real.
- Sin tocar Telegram/Cron/DB.
