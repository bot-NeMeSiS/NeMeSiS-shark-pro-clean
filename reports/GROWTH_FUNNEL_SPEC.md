# Growth Funnel Spec

Contrato: `NEMESIS-GROWTH-REVENUE-OS-V1`.

Principio: ningun porcentaje de conversion se declara si no existe denominador real, fuente trazable y muestra suficiente.

## Funnel Oficial

| Etapa | Definicion | Evidencia minima | Estado sin datos |
| --- | --- | --- | --- |
| DISCOVERY | Persona descubre NeMeSiS por canal medible | Fuente, canal, timestamp agregado, consentimiento cuando aplique | INSUFFICIENT_REAL_DATA |
| LANDING | Visita una superficie publica y entiende valor | Visita agregada, pagina, fuente, sin fingerprinting | INSUFFICIENT_REAL_DATA |
| REGISTRATION | Crea cuenta | Conteo agregado de usuarios, fecha, plan inicial | INSUFFICIENT_REAL_DATA |
| FREE | Usa plan gratuito | Plan FREE agregado y actividad propia | INSUFFICIENT_REAL_DATA |
| FIRST VALUE | Encuentra partido, equipo, competicion o briefing util | Evento minimizado de primer valor | INSUFFICIENT_REAL_DATA |
| ACTIVATED | Repite accion clave o configura favorito | Evento de activacion definido y repetible | INSUFFICIENT_REAL_DATA |
| RETURNING | Vuelve en otra sesion o dia | Cohorte agregada diaria/semanal | INSUFFICIENT_REAL_DATA |
| PREMIUM INTENT | Muestra interes en PRO/ELITE | Vista de membresias, preview o checkout iniciado | INSUFFICIENT_REAL_DATA |
| PRO / ELITE | Plan de pago confirmado | Plan agregado o pago certificado | INSUFFICIENT_REAL_DATA |
| RETAINED | Mantiene uso o renovacion | Cohorte, renovacion o uso sostenido | INSUFFICIENT_REAL_DATA |
| REFERRAL | Invita y activa otra persona | Invite, accepted, activated, converted | INSUFFICIENT_REAL_DATA |

## KPIs Recomendados

Primarios:

- Activacion: usuarios que alcanzan `FIRST_VALUE` y `ACTIVATED`.
- Conversion responsable: `PRO / ELITE` sobre usuarios con `PREMIUM_INTENT` y denominador suficiente.
- Retencion: usuarios que vuelven en ventana diaria/semanal certificada.

Drivers:

- Tiempo hasta primer valor.
- Favorito creado.
- Briefing diario consumido.
- Preview premium visto.
- Soporte sin resolver.

Guardrails:

- Baja de Telegram.
- Cancelacion.
- Quejas de copy o expectativas.
- Estados sin datos mal explicados.
- Cualquier claim comercial sin evidencia.

## Origen De Evidencia

Permitido:

- `SYSTEM_OBSERVATION`.
- `REAL_AGGREGATED`.
- `SIMULATED_GROWTH_QA`, siempre etiquetado como simulacion.
- `MANUAL_ADMIN`.

Prohibido:

- Presentar simulaciones como usuarios reales.
- Estimar visitas sin fuente.
- Inventar conversiones.
- Usar datos sensibles innecesarios.
## Phase 01 - Instrumentacion certificada

Contrato de evento: NEMESIS-GROWTH-FUNNEL-EVENT-V1.

- FIRST_VALUE: cuenta autenticada abre un Match Center canonico con partido resoluble.
- ACTIVATED: FIRST_VALUE mas favorito o segundo Match Center distinto.
- Atribucion: canal allowlisted y campaign_id sanitizado.
- Privacidad: sin URL completa, IP, user agent, PII ni fingerprint.
- Anonimos: la landing permanece en sesion y no se persiste sin consentimiento.
- Idempotencia: eventos deduplicados por etapa, usuario y objetivo.
- Fuente: actividad first-party; no trackers externos.

| Metrica | Numerador | Denominador |
| --- | --- | --- |
| visitor_to_registration | registros | visitantes consentidos; no disponible |
| registration_to_first_value | FIRST_VALUE | registros |
| first_value_to_activation | ACTIVATED | FIRST_VALUE |
| activation_to_returning | RETURNING | ACTIVATED |
| free_to_premium_intent | PREMIUM_INTENT | FREE |
| premium_intent_to_paid | PRO + ELITE | PREMIUM_INTENT |

Sin denominador real se muestra 0 / INSUFFICIENT_REAL_DATA.
