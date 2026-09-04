# 01 — Estado actual

Fecha de referencia: 2026-09-04.

## Producto

NeMeSiS SHARK PRO es una plataforma deportiva premium en español con estrategia de producto `Sports First → SHARK Second → Betting Third`. La aplicación combina experiencia deportiva, directos, calendario, partidos, picks, SHARK, Telegram, membresías, pagos, administración, automatización, QA y despliegue en Render.

## Estado técnico conocido

- Repositorio operativo: `bot-NeMeSiS/NeMeSiS-shark-pro-clean`.
- Rama de producción: `main`.
- Producción Render: `nemesissharkpro` / `https://bot-apuestas-crgf.onrender.com`.
- Versión declarada: `V940_NEMESIS_SPORTS_EXPERIENCE_PHASE_1_FOUNDATION_FINAL`.
- Stack principal: Flask + SQLite persistente + Render + GitHub.
- Datos deportivos: API-Sports/API-Football, The Odds API y otras capas/fallbacks ya integradas según disponibilidad/configuración.
- Automatización: Render Cron + tareas internas + vigilancia externa programada.

## Principios que no deben romperse

1. Datos reales; nunca inventar partidos, cuotas, resultados, escudos, estados LIVE o métricas comerciales.
2. Madrid Time como referencia de presentación y lifecycle.
3. Persistencia segura de usuarios, sesiones, membresías y datos en Render Disk/DB_PATH.
4. No tocar secretos ni imprimir claves.
5. No enviar Telegram real ni ejecutar pagos reales durante QA salvo orden explícita.
6. No degradar funciones estables al mejorar visual o UX.
7. Cliente, móvil y admin deben compartir sistema visual coherente pero con navegación separada.
8. Sports Truth debe gobernar estado de partido, LIVE, finalización, frescura y confianza.
9. SHARK debe ser útil y honesto sobre disponibilidad de IA/proveedor.
10. Cada release debe ser limpia, auditable y Render Ready.

## Estado operativo observado hoy

- Servicio público disponible; no se ha confirmado una caída general persistente.
- Los reinicios de Gunicorn durante deploy se han distinguido correctamente de incidentes reales.
- Existe una incidencia de Sports Truth que ha demostrado que distintas superficies pueden no estar consumiendo exactamente el mismo estado canónico LIVE.
- Se aplicó un hotfix para usar `last_synced_at` como evidencia de frescura de snapshots LIVE, pero la vigilancia posterior detectó que el problema podía persistir en otra ruta/capa pública.

## Prioridad actual

Cerrar Sports Truth de extremo a extremo: Home, `/live`, `/calendar`, `/partidos`, Match Center, SHARK y contadores deben consumir una sola decisión canónica para `LIVE / HALFTIME / FINISHED / STALE / RESULT_PENDING` y para la confianza del dato.
