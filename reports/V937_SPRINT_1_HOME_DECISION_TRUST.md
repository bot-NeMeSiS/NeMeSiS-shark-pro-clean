# V937 Sprint 1 — Home Decision Center & Data Trust

## Objetivo
Convertir la home en un centro de decisión, no en una colección de módulos.

## Cambios
- Hero orientado a criterio: “Decide mejor. Descarta el ruido.”
- Radar de decisión con agenda validada, directo confirmado, picks publicables y registros pendientes.
- Nuevo Índice de Confianza del Dato.
- El índice no mide probabilidad ni rentabilidad.
- Sustituido el bloque técnico de proveedor por una explicación de calidad comprensible.
- Empty states orientados a decisión: esperar también es una decisión segura.
- Recorrido reorganizado: partidos → directo → picks → SHARK → Telegram → histórico.
- Copy comercial responsable para FREE/PRO/ELITE.

## Datos
No se añaden partidos, picks, cuotas, resultados, porcentajes ni métricas simuladas.

## Archivos
- templates/home.html
- templates/components/v936_product.html
- static/v936-commercial.css

## Integración
Copiar el contenido del ZIP sobre la raíz del proyecto manteniendo la estructura.

## Validación recomendada
- Parseo Jinja.
- GET / con y sin sesión.
- Desktop 1366/1440/1920.
- Móvil 390x844 y 430x932.
- Confirmar cero overflow.
- Confirmar valores procedentes de home_summary y picks reales.
