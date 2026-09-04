# ESTADO ACTUAL DEL PROYECTO

Fecha de referencia: 2026-09-04.

## Producto

NeMeSiS SHARK PRO es una plataforma deportiva premium en español con estrategia `Sports First → SHARK Second → Betting Third`.

## Estado técnico conocido

- Repositorio: `bot-NeMeSiS/NeMeSiS-shark-pro-clean`.
- Rama de producción: `main`.
- Producción Render: `nemesissharkpro` / `https://bot-apuestas-crgf.onrender.com`.
- Versión declarada: `V940_NEMESIS_SPORTS_EXPERIENCE_PHASE_1_FOUNDATION_FINAL`.
- Stack: Flask + SQLite persistente + Render + GitHub.
- Datos deportivos: API-Sports/API-Football, The Odds API y capas/fallbacks configuradas según disponibilidad.
- Automatización: Render Cron + tareas internas + vigilancia externa programada.

## Principios que no debemos romper

1. Datos reales; nunca inventar partidos, cuotas, resultados, escudos, estados LIVE o métricas.
2. Madrid Time como referencia de lifecycle y presentación.
3. Persistencia segura de usuarios, sesiones, membresías y datos.
4. No tocar ni mostrar secretos.
5. No enviar Telegram real ni ejecutar pagos reales durante QA salvo orden explícita.
6. No degradar funciones estables al mejorar diseño o UX.
7. Cliente, móvil y admin deben mantener navegación clara y separada.
8. Sports Truth debe gobernar lifecycle, LIVE, finalización, frescura y confianza.
9. SHARK debe ser útil y honesto sobre la disponibilidad real de IA.
10. Cada release debe ser limpia, auditable y Render Ready.

## Estado operativo actual

- No se ha confirmado una caída general persistente del servicio.
- Se han distinguido correctamente reinicios normales de deploy frente a incidentes reales.
- Sigue abierta una incidencia de Sports Truth: distintas superficies públicas pueden no consumir exactamente la misma decisión canónica LIVE.
- Se aplicó un hotfix para usar `last_synced_at` como evidencia de frescura de snapshots LIVE, pero la vigilancia posterior indicó que alguna ruta/capa pública podía seguir mostrando estado obsoleto.

## Prioridad actual

Cerrar Sports Truth de extremo a extremo para que Home, `/live`, `/calendar`, `/partidos`, Match Center, SHARK y cualquier contador/alerta consuman una única verdad de partido.
