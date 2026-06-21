@"
# V844 V818 To V843 Compatibility QA

## Compatibilidad conservada
V844 añade un filtro antes del envío, sin cambiar contratos de cola, dedupe, master tick ni health-check.

## Elementos preservados
- /api/automation/master-tick
- /api/automation/health-check
- telegram_scheduler_delivery
- process_premium_telegram_queue
- data-v843-shell
- data-v842-shell
- data-v830-shell

## Resultado
	ools/check_v844_v818_to_v843_compatibility.py pasa correctamente.
