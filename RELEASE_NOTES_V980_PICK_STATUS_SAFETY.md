# V980 — Liquidación segura según el estado del partido

La evaluación de pronósticos ya no trata cualquier texto que contenga `final`, `finished`, `ft`, `aet`, `pen`, `terminado` o `acabado` como un partido terminado. Solo se liquidan estados reconocidos de forma exacta; los estados en curso y ambiguos permanecen pendientes aunque ya exista un marcador. Se reconocen `FT`, `AET`, `PEN` y las descripciones finales del proveedor, incluido `Match Finished After Penalty`.

Un marcador agregado tras prórroga o penaltis no se usa para liquidar mercados que necesitan el resultado del tiempo reglamentario. La liquidación por mercado acepta selecciones explícitas; los periodos, selecciones ambiguas y combinadas sin desglose se mantienen pendientes. Esto evita validar una apuesta y calcular su beneficio a partir de un descanso, juego, penalización en curso o elección interpretada por coincidencias parciales.

Validación local del candidato: 224 pruebas de liquidación, publicación de pronósticos, integridad, resultados, registro y contratos de release; 15 reproducciones sintéticas independientes; compilación de Python y comprobación de formato. Los controles CI, integración y producción quedan pendientes.
