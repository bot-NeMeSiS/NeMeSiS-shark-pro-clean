# V884 Sentinel + Visual Worker Integration QA

## Integracion validada
- Continuous Sentinel preserva reglas V883.
- Visual Worker genera issues, tareas y prompts.
- Modos `visual-worker`, `company-worker` y `full-company-qa` siguen disponibles.
- Workflow recibe salida del worker.

## Cambio V884
El criterio deportivo se endurece:
- si no hay filas deportivas ni estado seguro, issue high;
- si hay estado seguro pero no filas reales, issue low y tarea admin.

## Resultado
El sistema ya no declara score 10 en el worker cuando `/partidos`, `/calendar`, `/live`, `/directo` y `/picks` no muestran filas reales.
