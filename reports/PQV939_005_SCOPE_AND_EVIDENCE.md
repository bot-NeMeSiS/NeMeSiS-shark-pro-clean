# PQV939-005 - Alcance y evidencia

## Incidencia

- Identificador: `PQV939-005`.
- Prioridad: P2.
- Evidencia del vídeo: Inicio `00:00-00:12`, Picks `02:20-02:40` y SHARK `03:00-03:13`.
- Rutas consumidoras demostradas: `/app`, `/picks`, `/shark`, `/track-record` y detalle de partido cuando existe un recurso válido.
- Componente: macro compartido `customer_trust_panel()`.
- Elemento: reglas `Picks completos`, `Histórico evaluable` y `Sin beneficio garantizado`.
- Defecto visible: los iconos internos se presentan como rectángulos vacíos, mientras el icono principal del panel sí se dibuja.
- Impacto: apariencia de asset roto o control sin estado; reduce confianza visual en un panel cuyo propósito es precisamente explicar la fiabilidad del dato.

## Causa raíz demostrada

El macro genera tres chips hijos y cada chip contiene otro `span.v933-icon`. El selector `.v935-customer-trust-rules span` alcanza tanto al chip como al icono interno. Como el producto usa `box-sizing: border-box`, el icono de 14 px recibe también padding y borde de chip; el área útil del SVG colapsa y queda visible la caja heredada.

No es un fallo de Lucide, JavaScript, datos, navegación ni del macro de iconos. `v930-icons.js` inserta el SVG correctamente.

## Solución mínima autorizada

1. Limitar el estilo de chip al hijo directo: `.v935-customer-trust-rules > span`.
2. Limitar también el selector móvil del último chip al hijo directo.
3. Mantener la regla específica del icono en 14 x 14 px.
4. Añadir una comprobación estática compartida para Sentinel y AutoPilot.
5. Registrar el contrato y su resultado en el snapshot de Company Intelligence, sin escritura durante GET ni persistencia automática.

## Archivos autorizados

- `static/v933-product.css`.
- `engines/sentinel_autopilot_engine.py`.
- `engines/continuous_shark_sentinel_engine.py`.
- `engines/company_intelligence_engine.py`.
- `tests/test_v939_product_perfection_p2.py`.
- Informes y evidencia Browser QA específicos de `PQV939-005`.
- `reports/PRODUCT_QUALITY_MASTER_REVIEW_V939.md`, solo tras pasar todos los gates.

## Fuera de alcance

- Otros P2 y todos los P3.
- Rutas, arquitectura, datos deportivos y lógica de producto.
- SHARK, Telegram, Stripe, pagos, DB real y proveedores.
- Rediseño general o nuevas hojas CSS.
- NeMeSiS Sports Experience.

## Comportamiento esperado

- Cada chip conserva su contenedor, borde, fondo y texto.
- Cada SVG queda visible, sin padding, borde ni fondo heredados del chip.
- Desktop y móvil mantienen wrapping, jerarquía y navegación actuales.
- Sentinel abre una incidencia P2 y reduce su puntuación si reaparece el selector descendiente.
- AutoPilot crea una tarea con archivos probables y exige aprobación humana para CSS/DOM/código.

## Riesgo y validación

- Complejidad: baja.
- Riesgo de cambio: bajo; el macro compartido amplía el alcance de QA a todos sus consumidores.
- Validaciones: test específico por mutación, Jinja, rutas afectadas, Browser QA 1366 x 768 y 390 x 844, Sentinel, AutoPilot, Company Intelligence, Sports Data Contract y `match_card()`.
- Estado de producción tras el sprint: no certificado; no habrá deploy.

