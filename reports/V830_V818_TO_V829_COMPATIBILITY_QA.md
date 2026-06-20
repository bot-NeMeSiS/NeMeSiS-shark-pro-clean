# V830 V818 To V829 Compatibility QA

## Compatibilidad mantenida

V830 actúa como una capa final de corrección mobile. No sustituye ni elimina las capas funcionales anteriores.

## Marcadores conservados

- `data-v818-shell`
- `data-v819-shell`
- `data-v820-shell`
- `data-v821-shell`
- `data-v822-shell`
- `data-v825-shell`
- `data-v826-shell`
- `data-v827-shell`
- `data-v828-shell`
- `data-v829-shell`
- `data-v830-shell`

## Puntos críticos no tocados

- `/api/automation/master-tick`
- `/api/automation/health-check`
- rutas de escudos ligeras
- Telegram automático
- rutas admin
- rutas cliente
- pagos y membresías
- protección contra 502/database locked

## Resultado

La compatibilidad se verifica con `tools/check_v830_v818_to_v829_compatibility.py`.
