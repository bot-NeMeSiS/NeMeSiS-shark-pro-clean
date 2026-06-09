# V704 PICKS AUDIT

## Diagnostico

El problema no era solo ausencia de picks. Habia tres causas:

1. Candidatos limitados a 24 partidos.
2. Picks hot limitados visualmente a 6.
3. Cuotas guardadas como `outcomes` no siempre se transformaban en home/draw/away.

## Cambios

- Candidatos suben a 80 partidos y 21 dias.
- Smart board analiza hasta 80 candidatos.
- Hot picks visibles suben a 12.
- PRO/ELITE locked preview sube a 8.
- Pagina `/picks` pide 80 candidatos.
- Extraccion de odds reconoce `outcomes` de The Odds API.

## Resultado en smoke local

- Picks publicados visibles: 6.
- Candidatos detectados: 12.
- Recomendaciones SHARK: 12.
- Partidos con cuotas reconocidas: 16.

## Filtros que se mantienen

- No se generan picks falsos.
- Partidos finalizados o live penalizan o quedan fuera de recomendaciones prepartido.
- Si no hay cuota, se muestra como candidato o recomendacion pendiente, no como pick real.
- La publicacion real sigue dependiendo de admin/auto picks con calidad minima.

## Que falta para mas oportunidades reales

- Ejecutar sync Odds con mercados reales.
- Configurar regiones/mercados suficientes.
- Tener partidos proximos reales en DB.
- Validar rendimiento de Auto Picks con varios dias de datos.
