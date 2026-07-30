# Master Roadmap

## Resumen ejecutivo

- **El roadmap organiza decisiones, no despliegues automáticos.** Cada bloque requiere evidencia, aprobación y QA antes de convertirse en desarrollo.
- **La prioridad inmediata es beta cerrada y Release 1.0.** El producto no debe saltar a nuevas capacidades grandes sin validar uso real.
- **El futuro se ordena por horizontes.** Primero estabilidad y confianza; despues profundidad deportiva; despues inteligencia, crecimiento y escala.

## Horizontes

| Horizonte | Resultado | Areas dominantes | Gate de avance |
| --- | --- | --- | --- |
| H0 Lockdown | Producto estable local y operativo | Operaciones, Seguridad, UX | READY FOR CLOSED BETA |
| H1 Beta cerrada | Aprendizaje con usuarios reales | Usuario, Soporte, Marketing | Retencion y feedback medidos |
| H2 Release 1.0 | Venta controlada | Membresias, Telegram, Stripe, Soporte | Produccion y pagos certificados |
| H3 Sports Depth | Centros deportivos superiores | Sports, SHARK, Gateway | Cobertura y licencias validadas |
| H4 Daily Companion | Uso recurrente | Usuario, Telegram, Comunidad | Uso semanal y churn medidos |
| H5 Intelligence Network | Decisiones trazables en todo el ecosistema | IA, Motor de decisiones, Sports Graph | Evidencia y explicabilidad completas |
| H6 Scale Platform | Decenas de miles de usuarios | Escalabilidad, Operaciones, Seguridad | Observabilidad, coste y recovery certificados |

## Roadmap por fase

### Fase 0: Cierre pre-beta

- Git limpio y release congelado.
- Produccion certificada read-only.
- Cron, Master Tick, Restore, Telegram, Stripe y observabilidad en PASS controlado.
- Soporte y límites conocidos visibles.
- Onboarding beta preparado.

### Fase 1: Beta cerrada

- Medir activacion y tiempo hasta valor.
- Registrar feedback estructurado.
- Observar fricción FREE -> PRO.
- Confirmar que SHARK se entiende.
- Confirmar que Telegram no se percibe como ruido.

### Fase 2: Release 1.0

- Comercializar solo promesas certificadas.
- Activar planes con soporte y cancelación clara.
- Publicar metodología responsable.
- Mantener go/no-go semanal.

### Fase 3: Profundidad deportiva

- Mejorar Match, Team, Competition y Player Centers con datos licenciados.
- Elevar Live Center sin crear ruido.
- Preparar Sports Graph enriquecido.

### Fase 4: Companero diario

- Briefings personalizados con control de privacidad.
- Comunidad responsable.
- Alertas por valor, no por volumen.
- Historial de decisiones y aprendizaje personal.

### Fase 5: Plataforma inteligente

- IA asistiva solo cuando exista evidencia y guardrails.
- SHARK con explicación de confianza, contradicciones y fuentes.
- Motor de decisiones como contrato universal.

### Fase 6: Escala

- Costes por usuario monitorizados.
- Colas, caches, fallbacks y recovery probados.
- Observabilidad de negocio y tecnología unificada.

## Priorizacion de áreas

| Area | Prioridad actual | Motivo | Siguiente decisión |
| --- | --- | --- | --- |
| Operaciones | P0 | Sin operación estable no hay beta | Certificar bloqueadores finales |
| UX | P1 | El usuario debe entender valor rápido | Test de primer uso |
| Sports | P1 | Es el corazón del producto | Medir localización y comprensión |
| SHARK | P1 | Diferenciacion principal | Validar entendimiento y confianza |
| Telegram | P1 | Retencion y premium | Medir valor vs ruido |
| Seguridad | P1 | Reputacion y cumplimiento | Mantener guardrails antes de crecimiento |
| Marketing | P2 | Necesario para beta | Mensaje claro y honesto |
| Comunidad | P3 | Puede crecer despues de retención | Disenar sin presión ni spam |
| Integraciones | P3 | Valor futuro alto, riesgo alto | Registrar licencias y costes primero |

## Regla de avance

Una fase no empieza por ganas. Empieza cuando el gate anterior tiene evidencia suficiente.
## Communication System - 2026-07-30

La fase Telegram premium incorpora un lenguaje de mensajes único para picks, resumen diario/nocturno, live, resultados, SHARK, Action Platform y administración. El avance es de comunicación y QA: no cambia lógica de envío, scheduler, cron, dedupe, destinos ni seguridad.
