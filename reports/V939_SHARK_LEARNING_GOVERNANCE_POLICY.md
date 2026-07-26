# V939 Politica de gobierno SHARK

## Niveles

1. `OBSERVE`: leer y describir patrones; nivel por defecto.
2. `RECOMMEND`: proponer una revision con evidencia y limitaciones.
3. `APPROVED_CHANGE`: solo tras aprobacion explicita, trazabilidad y prueba de regresion.

V939 habilita por defecto solo `OBSERVE` y `RECOMMEND`. Una aprobacion se registra, pero nunca ejecuta el cambio.

## Prohibiciones

- Ajustar pesos por una muestra insuficiente.
- Confundir confianza del analisis con probabilidad de ganar.
- Optimizar para gasto compulsivo.
- Publicar picks desde el motor de aprendizaje.
- Ocultar segmentos perdedores o voids.
- Usar datos sinteticos como evidencia real.

## Cambio autorizado futuro

Requiere muestra minima, hipotesis, propietario, efecto esperado, backtest aislado, guardrails, rollback, aprobacion humana y certificacion posterior.
