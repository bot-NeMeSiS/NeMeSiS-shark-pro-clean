# V938 Disaster Recovery Design

## Principios

1. Nunca restaurar sobre `DB_PATH` durante una comprobación.
2. Separar existencia de backup, hash válido, copia offsite y restore probado.
3. Manifest por copia: versión, hora Madrid, tamaño, hash SHA-256, tipo y origen enmascarado.
4. Verificación SQLite en modo de solo lectura.
5. Restore únicamente sobre scratch aislado; `/data` está prohibido para el ensayo.
6. No reemplazar usuarios, sesiones, pagos ni datos deportivos reales.

## Objetivos iniciales

- RPO objetivo configurable: 24 horas.
- RTO objetivo configurable: 4 horas.
- Retención: política existente, con al menos la copia válida más reciente preservada.

## Estado local

DB local legible e íntegra. No se detectó backup local con manifest/hash, copia offsite ni restore aislado certificado. El gate de recuperación queda **NO CERTIFICADO**, no PASS.
