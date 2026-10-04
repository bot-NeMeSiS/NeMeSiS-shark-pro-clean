# NeMeSiS Master Automation

El único propietario periódico es el recurso Render `telegram-auto-tick`, con
`tools/render_cron_master_tick.py`, cada cinco minutos. No se cambia su nombre,
cadencia, secretos ni almacenamiento. GitHub Actions ejecuta controles de QA,
no la operación periódica de la aplicación.

El registro `engines/automation_domains.py` concentra seis dominios de
producción sin importar módulos ni iniciar hilos. Los módulos y endpoints
existentes siguen siendo adaptadores compatibles. Sports, Odds y Delivery usan
requests independientes dentro del mismo Master Cron. Telegram no sincroniza
Sports, y Sports excluye Odds. Cada POST de esos carriles requiere readiness GET;
un POST con respuesta incierta nunca se repite.
El runner real consume sus endpoints desde este registro; Admin y Cron usan
la misma definición de propiedad. Sus constantes públicas se conservan como aliases.

| Dominio | Entrada del Cron | Estado / recuperación |
| --- | --- | --- |
| sports | `/api/automation/sports/sync` | `/admin/data-center` |
| odds | `/api/automation/odds/sync` | `/admin/data-center` |
| media | `/api/automation/highlights/sync` | `/admin/highlights-review` |
| postmatch | `/api/automation/postmatch/tick` | `/admin/highlights-review#postmatch-workers` |
| delivery | `/api/automation/telegram/tick` | `/admin/telegram/command-center` |
| maintenance | tick continuous-evolution y backup diario | `/admin/backups` |

Highlights y postmatch ya se ejecutaban en el Cron real, aunque el resumen
administrativo los describía como manuales. La presentación ahora refleja
esa propiedad; no se fuerza una activación si faltan permisos de fuentes.
Postmatch conserva configuración, cola durable, leases, caché, circuitos y
aplazamiento hasta el siguiente día Madrid sin consumir intentos por presupuesto.
Su presupuesto de partida permanece en 60/día.

Sports y Odds reservan 16 segundos para proveedores, con timeout de transporte
de hasta 4 segundos y limitado al tiempo restante. El cliente del Master espera
hasta 24 segundos para permitir persistencia y respuesta bajo el timeout de
Gunicorn de 30 segundos. El presupuesto es cooperativo; las operaciones locales
siguen requiriendo observación. PARTIAL y aplazamientos controlados terminan con
exit 0; errores técnicos terminan con exit 2. El disco existente conserva nombre
y mountPath; render.yaml refleja los 2 GB ya provisionados.

QA visual, responsive, navegación, seguridad, data truth, Browser QA y deploy
guard siguen separados del flujo normal. `automation_workforce/` es tooling
de QA/release: su nombre no convierte esos scripts en workers de producción.

`docs/automation-ownership.json` contiene inventario reproducible de imports,
referencias y rutas. Ejecutar `python tools/audit_automation_ownership.py`.
Las referencias estáticas no demuestran ejecución LIVE; las piezas sin
referencias son candidatas para inspección, no una autorización de borrado.
No se elimina ningún módulo en esta fase: los orquestadores usan nombres
dinámicos y los checks versionados sirven como evidencia de regresión.

El Command Center muestra observaciones registradas. Configuración READY no
equivale a éxito del Cron; falta de observación se presenta como no verificada.
Los accesos de operación manual son para diagnóstico, recuperación o emergencia.
