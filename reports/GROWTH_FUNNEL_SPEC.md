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
