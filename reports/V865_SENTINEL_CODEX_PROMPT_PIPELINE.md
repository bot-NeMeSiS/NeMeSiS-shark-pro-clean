# V865 Sentinel Codex Prompt Pipeline

El pipeline genera prompts listos para Codex a partir de grupos de incidencias.

Cada prompt incluye:

- Versión base.
- Tipo de fix.
- Rutas afectadas.
- Incidencias detectadas.
- Reglas de preservación V818-V864.
- Prohibición de inventar datos.
- Prohibición de tocar secretos.
- Validaciones esperadas.
- ZIP limpio.
- Honestidad entre probado local, probado real y bloqueado.

Tipos cubiertos:

- Fix visual móvil/PC.
- Fix rutas/botones.
- Fix admin command center.
- Fix datos reales/empty states.
- Fix Telegram premium.
- Fix SHARK IA.
- Fix pagos/membresías.
- Fix security/runtime.
- Fix release/ZIP.

El sistema genera el prompt, pero no lo ejecuta automáticamente.
