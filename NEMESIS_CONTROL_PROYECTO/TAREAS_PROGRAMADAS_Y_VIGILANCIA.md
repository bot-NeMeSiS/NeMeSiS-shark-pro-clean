# TAREAS PROGRAMADAS Y VIGILANCIA

Fecha de referencia: 2026-09-04.

## Vigilancia operativa

### NeMeSiS Production Watch
- Cada hora.
- Detecta caídas, 5xx repetidos, latencia severa, navegación crítica rota y Sports Truth incorrecto.
- Compara Home, `/live`, `/calendar`, `/partidos` y Match Center para el mismo partido.
- Solo alerta ante problemas HIGH/CRITICAL reales.

### NeMeSiS Daily Audit
- Diaria por la mañana.
- Revisa health/runtime, versión, superficies críticas, Sports Truth y riesgos accionables.

### Sports Reality Watch
- Diaria por la tarde/noche.
- Usa partidos reales importantes para certificar LIVE, marcador, minuto, eventos, alineaciones, jugadores, estadísticas, frescura y highlights autorizados.

## Inteligencia semanal

### Competitor Intelligence — lunes
Flashscore, Sofascore, FotMob y otros productos deportivos fuertes.

### Sports API Watch — martes
API-Sports/API-Football, TheSportsDB y The Odds API: cobertura, cuotas, límites, endpoints, planes y oportunidades.

### AI Opportunity Watch — miércoles
IA útil para SHARK, sports intelligence, QA autónomo, agentes, personalización y media autorizada.

### Platform Security Watch — jueves
Render, GitHub, Flask/Python, Stripe y arquitectura de despliegue.

### Commercial Readiness — viernes
Preparación real para usuarios controlados y comercialización.

### NeMeSiS Weekly Board — domingo
Resumen ejecutivo semanal con mejoras, regresiones, bloqueos y cinco prioridades.

## Decisión actual

No añadir más automatizaciones por ahora. La cobertura es suficiente. Cuando aparezca una nueva necesidad, primero se debe comprobar si encaja ampliando una tarea existente.
