# V844 Picks App Telegram Consistency QA

## Reglas
- Telegram no debe mandar picks inexistentes.
- Telegram no debe mandar cuota inexistente como real.
- Telegram no debe mandar ROI inventado.
- Telegram no debe mandar partido sin posibilidad de abrirlo en app.
- Un partido destacado sin pick no debe parecer pick.

## Aplicación
	elegram_pick_sendability() ahora incorpora la decisión V844. Si el partido/pick no tiene calidad comercial suficiente, no entra en candidatos elegibles.

## Resultado
	ools/check_v844_picks_app_telegram_consistency.py pasa correctamente.
