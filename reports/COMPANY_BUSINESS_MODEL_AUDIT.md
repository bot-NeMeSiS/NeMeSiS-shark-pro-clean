# NeMeSiS SHARK PRO - Auditoría de modelo de negocio

## Propuesta de valor

NeMeSiS no vende volumen de pronósticos; vende **criterio, trazabilidad y la capacidad de decir “hoy no hay evidencia suficiente”**. Esa propuesta es diferenciadora y compatible con una marca responsable. El producto visual la comunica mejor que la infraestructura comercial actual puede demostrarla.

## Segmentos y valor

| Segmento | Necesidad | Oferta actual | Riesgo |
|---|---|---|---|
| Explorador FREE | Ordenar la agenda y entender el producto | Calendario/live/estados seguros/SHARK limitado | Abandono si no hay datos frecuentes |
| Cliente PRO | Ahorrar tiempo y recibir contexto | Picks completos, SHARK ampliado, Telegram, histórico | Pago no certificado; valor depende de feed |
| Cliente ELITE | Prioridad, profundidad y soporte | Límites altos, análisis y acceso avanzado | Puede sonar a promesa superior sin SLA/datos |
| ELITE+ | Supuesto nivel adicional | Etiqueta, no tier técnico independiente | Confusión y riesgo contractual |
| Admin/operaciones | Controlar datos, envíos y salud | Command centers amplios | Exceso de superficies y evidencia dispersa |

## Diferenciación

Fortalezas:

1. Publicación condicionada por calidad de datos.
2. SHARK puede recomendar esperar.
3. Transparencia de riesgo, frescura y evidencia.
4. Track record orientado a evaluables.
5. Extensión Telegram integrada al mismo criterio.

No demostrado todavía:

- Calidad predictiva sostenida.
- Retención y willingness-to-pay.
- SLA de datos/soporte.
- Coste unitario estable.
- Conversión real FREE -> PRO -> ELITE.

## Catálogo y monetización

El catálogo real debe reducirse a los tiers implementados: FREE, PRO y ELITE. ELITE+ no debe venderse como plan separado hasta disponer de precio, entitlement, checkout, webhook, downgrade, soporte y términos propios.

Hallazgo de consistencia: la vista cliente muestra por defecto PRO 9.99 EUR y ELITE 24.99 EUR, mientras que cálculos administrativos usan 19/49 como estimación. MRR calculado sobre esa base no es contabilidad fiable.

## Economía unitaria

Costes variables previsibles:

- API deportiva y cuotas por llamada/plan.
- OpenAI por uso SHARK.
- Telegram por infraestructura/operación, aunque la API no cobre por mensaje.
- Render web, cron y disco.
- Stripe por transacción.
- Soporte, revisión editorial, legal y seguridad.

Costes fijos:

- Ingeniería/operaciones.
- Observabilidad y backups off-site.
- Cumplimiento y contabilidad.
- Marca, adquisición y soporte.

No existe evidencia suficiente para margen, CAC, LTV o punto de equilibrio.

## KPIs disponibles y ausentes

| KPI | Datos existentes | Estado |
|---|---|---|
| Usuarios registrados/activos | Tablas y panel | Snapshot local vacío; producción no verificada |
| Conversión por tier | Memberships/Stripe potencial | No certificada |
| Churn | Estado de suscripción | Definición y cohortes faltan |
| MRR/ARPU | Cálculo admin estimado | No fiable hasta catálogo Stripe único |
| CAC/LTV | No se observó fuente | Ausente |
| Uso SHARK/Telegram | Eventos/logs parciales | Falta definición y retención |
| Picks/win rate/ROI | Track record | Debe usar solo evaluables; producción no verificada |
| Disponibilidad/5xx/latencia | Health/reports | Sin serie externa continua |
| Frescura/consumo API | Sync runs/guards | Sin dashboard financiero operativo completo |
| Tickets/MTTR | No hay sistema confirmado | Ausente |

## Riesgo de claims

- No usar “mejores picks” sin métrica y periodo verificables.
- No asociar Índice de Confianza con probabilidad de acierto.
- No prometer rentabilidad, ganancias ni continuidad de datos.
- Mostrar fecha, muestra y criterio de ROI/win rate.
- Informar que el servicio es analítico e informativo, no casa de apuestas.

## Preparación comercial

| Dimensión | Nota | Motivo |
|---|---:|---|
| Propuesta | 8/10 | Clara y diferenciada |
| Producto percibido | 8.5/10 | Visual premium y coherente |
| Evidencia de valor | 5/10 | Feed/track record real no certificado |
| Cobro y entitlement | 5/10 | Buena base técnica, sin E2E real |
| Legal/privacidad | 4/10 | Revisión pendiente |
| Soporte | 5/10 | UI existe, proceso/SLA no |
| Economía | 4/10 | Sin unit economics ni datos reales |
| Escalabilidad comercial | 4/10 | Bus factor, SQLite y observabilidad |

## Experimentos seguros antes de vender

1. Beta gratuita con 20-50 usuarios, consentimiento y soporte manual.
2. Medir activación: primer calendario, primer SHARK, primer favorito, link Telegram.
3. Entrevistas sobre confianza y claridad, no sobre “aciertos”.
4. Prueba de precio sin cobro real o con Stripe test.
5. Cohorte de 30 días para retención y coste de datos/IA.

## Decisión

El modelo tiene una narrativa comercial defendible, pero no está listo para adquisición pagada ni cobro real. La prioridad es convertir la confianza visual en confianza operativa demostrable.

