# V980 — Liquidación segura según el estado del partido

La evaluación de pronósticos ya no trata cualquier texto que contenga `final`, `finished`, `ft`, `aet`, `pen`, `terminado` o `acabado` como un partido terminado. Solo se liquidan estados finales reconocidos de forma exacta; estados en curso, pendientes, suspendidos o ambiguos permanecen pendientes aunque ya exista un marcador parcial. Se reconocen tanto los códigos `FT`, `AET` y `PEN` como las descripciones finales del proveedor, incluido `Match Finished After Penalty`.

Esto evita validar una apuesta y calcular su beneficio a partir de un partido en descanso, en juego o con estado de penalización en curso. Se añadieron regresiones de normalización y persistencia para comprobar que una apuesta publicada no se liquida antes de recibir un estado final.

Validación local del candidato: pruebas focalizadas de liquidación, integridad de pronósticos y evidencia de resultados; compilación de Python y comprobación de formato del cambio. Los controles CI, integración y producción quedan pendientes.
