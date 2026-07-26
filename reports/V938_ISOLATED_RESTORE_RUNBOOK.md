# V938 Isolated Restore Runbook

## Señal de inicio

Validación programada de continuidad o incidente donde un backup deba demostrarse utilizable.

## Procedimiento seguro

1. Confirmar el nombre del backup y su manifest, sin copiar PII a informes.
2. Confirmar que la fuente no es `DB_PATH` ni `/data/database.db`.
3. Crear scratch fuera de `/data`.
4. Copiar el backup al scratch como `isolated_restore.sqlite3`.
5. Comparar hash de fuente y copia.
6. Abrir la copia en modo read-only y ejecutar `PRAGMA quick_check`.
7. Confirmar tablas esperadas y registrar solo recuentos, nunca filas personales.
8. Marcar PASS únicamente si hash e integridad son correctos.
9. Eliminar el scratch conforme a la política del entorno.

## Prohibido

No parar el servicio, no reemplazar DB, no migrar, no escribir usuarios y no usar el persistent disk productivo como scratch.

## Cierre

Guardar fecha Madrid, versión, hash parcial, tamaño, tablas e integridad. Un PASS aislado no autoriza un restore productivo; ese paso requiere incidente P0, aprobación humana y rollback.
