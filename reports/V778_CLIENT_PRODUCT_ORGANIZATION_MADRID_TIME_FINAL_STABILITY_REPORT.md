# V778_CLIENT_PRODUCT_ORGANIZATION_MADRID_TIME_FINAL_STABILITY

## Objetivo
Cerrar la organización cliente para dejar la app estable durante un tiempo: sin barras duplicadas, sin accesos escondidos, con jerarquía clara y hora oficial España/Madrid en las zonas visibles.

## Cambios principales
- Se elimina el rail global duplicado V777 del layout base.
- PC queda con navegación superior; móvil queda con navegación inferior; /menu es el mapa completo.
- `/app` se rehace como centro de mando final con prioridad del día, ruta recomendada y bloques por intención.
- `/menu` se rehace como mapa de producto por intención.
- `/mi-cuenta` se reordena como centro de plan, Telegram, favoritos, actividad y soporte.
- Se añade filtro `madrid_datetime_label` para evitar timestamps crudos en actividad, alertas y combis.
- Se eliminan shortcuts duplicados V775 de Calendario/Directo/Picks porque ya existen acciones y filtros propios.
- Se añade API/QA V778 para auditar organización cliente y riesgos de hora/texto.

## No tocado
- DB_PATH, usuarios, sesiones, membresías, pagos foundation, Telegram automático, Cron, AUTOMATION_SECRET, Track Record, highlights, Data Marketplace, Automation Center y motores de datos.

## Pendiente en Render
- Smoke real con Flask instalado.
- Revisión visual final en móvil después de deploy.
