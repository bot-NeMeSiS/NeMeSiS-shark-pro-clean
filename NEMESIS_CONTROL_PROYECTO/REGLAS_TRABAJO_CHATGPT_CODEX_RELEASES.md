# REGLAS DE TRABAJO — CHATGPT / CODEX / RELEASES

## ChatGPT y Codex
1. Partir siempre de la versión real actual, no de ZIPs históricos salvo rollback explícito.
2. Leer primero `NEMESIS_CONTROL_PROYECTO/`.
3. Preservar motores estables y cambiar solo lo necesario.
4. No inventar datos deportivos, comerciales ni de producción.
5. No tocar secretos, usuarios, membresías, pagos reales o Telegram real sin orden explícita.
6. No romper rutas, responsive, permisos o datos al mejorar visual.
7. Toda nueva fuente de estado deportivo pasa por Sports Truth.
8. No crear helpers paralelos para lifecycle/confianza si ya existe contrato canónico.
9. Un deploy correcto no cierra una incidencia: hay que verificar producción después.
10. Distinguir siempre probado local, probado Render, probado público y no probado.

## Releases
- `VERSION.txt` y `APP_VERSION` alineados cuando haya nueva versión funcional.
- ZIP limpio sin `.git`, `.venv`, caches, DB locales, logs, secretos, vídeos, capturas o ZIPs internos.
- QA mínimo: py_compile/compileall, Jinja, checks relevantes, smoke crítico, seguridad cron/secret y ZIP audit.
- No declarar pixel-perfect sin browser QA/capturas reales.
- No declarar Telegram, pagos o proveedor real operativo si solo hubo mocks/dry-run.

## Incidencias de producción
1. Confirmar persistencia antes de alarmar.
2. CRITICAL/HIGH solo con impacto público material.
3. Registrar ruta, hora Madrid, versión/runtime, síntoma y alcance.
4. Corregir causa raíz, no maquillar solo la interfaz.
5. Fail-closed cuando la alternativa sea publicar información deportiva falsa.
6. Validar todas las superficies que consumen el mismo dato.

## Tareas programadas
- Antes de crear otra tarea, comprobar si una existente puede ampliarse.
- Evitar duplicados.
- Condition watches deben callar cuando todo está bien.
- Los informes semanales deben terminar en decisiones concretas.

## Organización documental
- `NEMESIS_CONTROL_PROYECTO/`: estado vivo y decisiones.
- `CHATGPT_CONTINUATION_REPORT.md`: historia larga.
- `reports/`: QA/evidencia técnica por versión.
- PR/issues GitHub: trazabilidad de cambios concretos.
