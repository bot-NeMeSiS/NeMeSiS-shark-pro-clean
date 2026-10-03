# NeMeSiS Master Automation

El único propietario periódico es el recurso Render `telegram-auto-tick`, con
`tools/render_cron_master_tick.py`, cada cinco minutos. No se cambia su nombre,
cadencia, secretos ni almacenamiento. GitHub Actions ejecuta controles de QA,
no la operación periódica de la aplicación.

El registro `engines/automation_domains.py` concentra cinco dominios de
producción sin importar módulos ni iniciar hilos. Los módulos y endpoints
existentes siguen siendo adaptadores compatibles. Sports y delivery comparten
el tick existente: dividirlos físicamente duplicaría llamadas y entrega.
El runner real consume sus endpoints desde este registro; Admin y Cron usan
la misma definición de propiedad. Sus constantes públicas se conservan como aliases.

| Dominio | Entrada del Cron | Estado / recuperación |
| --- | --- | --- |
| sports | `/api/automation/telegram/tick` | `/admin/data-center` |
| media | `/api/automation/highlights/sync` | `/admin/highlights-review` |
| postmatch | `/api/automation/postmatch/tick` | `/admin/highlights-review#postmatch-workers` |
| delivery | tick Telegram compartido | `/admin/telegram/command-center` |
| maintenance | tick continuous-evolution y backup diario | `/admin/backups` |

Highlights y postmatch ya se ejecutaban en el Cron real, aunque el resumen
administrativo los describía como manuales. La presentación ahora refleja
esa propiedad; no se fuerza una activación si faltan permisos de fuentes.
Postmatch conserva configuración, cola durable, leases, caché, circuitos y
aplazamiento hasta el siguiente día Madrid sin consumir intentos por presupuesto.
Su presupuesto de partida permanece en 60/día.

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
