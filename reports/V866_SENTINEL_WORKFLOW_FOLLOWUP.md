# V866 Sentinel workflow follow-up

## Contexto
V865 dejó Continuous Sentinel dry-run OK, score 9.1, 19 avisos low y 0 críticos.

## Follow-up V866
- Revisar avisos low como posibles falsos positivos técnicos.
- Corregir texto visible real si aparece como `None`, `null`, `undefined`, mojibake o copy pobre.
- Mantener falsos positivos documentados para que el workflow diario sea más útil.
- Resultado tras ajuste: Sentinel estático V866 queda en score 10.0, 0 issues abiertos y 0 críticos.

## Tareas recomendadas para admin workflow
- Clasificar issue low como `visible`, `admin-only`, `json-protegido` o `falso positivo`.
- Generar prompt seguro para Codex solo si hay texto visible real.
- No ejecutar acciones destructivas desde workflow.
