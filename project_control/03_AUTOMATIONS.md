# 03 — Automatizaciones activas

Estado de referencia: 2026-09-04, Europe/Madrid.

## Vigilancia operativa

### NeMeSiS Production Watch
- Cadencia: cada hora.
- Tipo: condition watch.
- Objetivo: detectar regresiones públicas críticas/altas, 5xx repetidos, caída, latencia severa, navegación crítica rota y Sports Truth falso/stale.
- Regla: solo notificar cuando haya un problema significativo; no modificar producción.

### NeMeSiS Daily Audit
- Cadencia: diaria, franja de mañana.
- Objetivo: auditoría ejecutiva de health/runtime, versión desplegada, superficies críticas, Sports Truth y riesgos accionables.

### Sports Reality Watch
- Cadencia: diaria, tarde/noche.
- Tipo: condition watch.
- Objetivo: usar partidos reales importantes como certificación externa de LIVE, score, minuto, eventos, alineaciones, jugadores, estadísticas, frescura y highlights autorizados.

## Inteligencia semanal

### Competitor Intelligence
- Lunes.
- Vigila Flashscore, Sofascore, FotMob y productos deportivos fuertes.
- Compara UX, Match Center, navegación, personalización, IA, alertas, monetización y móvil con la estrategia NeMeSiS.

### Sports API Watch
- Martes.
- Revisa API-Sports/API-Football, TheSportsDB y The Odds API: documentación, cobertura, cuotas, límites, endpoints, planes y oportunidades.

### AI Opportunity Watch
- Miércoles.
- Busca innovaciones útiles para SHARK, sports intelligence, QA autónomo, visual regression, agentes, personalización y media autorizada.

### Platform Security Watch
- Jueves.
- Revisa seguridad/reliability relevante en Render, GitHub, Flask/Python, Stripe y arquitectura de despliegue.

### Commercial Readiness
- Viernes.
- Evalúa preparación para usuarios reales/controlados y comercialización: producto, datos deportivos, SHARK, memberships, Stripe, Telegram, onboarding, soporte, observabilidad y seguridad.

### NeMeSiS Weekly Board
- Domingo.
- Informe ejecutivo semanal: qué mejoró, qué empeoró, bloqueos, qué parar y cinco prioridades de mayor valor.

## Decisión actual sobre nuevas tareas

No añadir más automatizaciones por ahora. Nueve tareas cubren suficientemente operaciones, producto, realidad deportiva, competencia, proveedores, IA, seguridad, comercialización y dirección. Añadir más ahora aumentaría duplicación y ruido.

La mejora de mayor valor no es crear otra tarea, sino endurecer `NeMeSiS Production Watch` y `Sports Reality Watch` para exigir consistencia transversal entre Home, `/live`, `/calendar`, `/partidos` y Match Center cuando evalúen Sports Truth.
